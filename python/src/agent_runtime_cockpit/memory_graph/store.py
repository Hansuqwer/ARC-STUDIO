"""File-backed memory graph store and deterministic extraction helpers."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

from ..security.redaction import REDACT_PLACEHOLDER, Redactor
from .models import MemoryEdge, MemoryGraphSnapshot, MemoryNode, utc_now

DEFAULT_MEMORY_GRAPH_PATH = Path(".arc") / "memory" / "graph.json"
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_+-]{2,}")
STOPWORDS = {
    "and",
    "are",
    "for",
    "from",
    "not",
    "run",
    "the",
    "this",
    "with",
    "without",
}


def _node_id(kind: str, text: str) -> str:
    digest = hashlib.sha256(f"{kind}:{text.lower()}".encode("utf-8")).hexdigest()[:16]
    return f"mem-{digest}"


def _edge_id(source_id: str, target_id: str, edge_type: str) -> str:
    digest = hashlib.sha256(f"{source_id}:{target_id}:{edge_type}".encode("utf-8")).hexdigest()[:16]
    return f"edge-{digest}"


class MemoryGraphStore:
    def __init__(self, path: Path = DEFAULT_MEMORY_GRAPH_PATH) -> None:
        self.path = path

    def load(self) -> MemoryGraphSnapshot:
        if not self.path.exists():
            return MemoryGraphSnapshot()
        return MemoryGraphSnapshot.model_validate_json(self.path.read_text(encoding="utf-8"))

    def save(self, snapshot: MemoryGraphSnapshot) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")

    def merge(self, snapshot: MemoryGraphSnapshot) -> MemoryGraphSnapshot:
        current = self.load()
        nodes = {node.id: node for node in current.nodes}
        for node in snapshot.nodes:
            existing = nodes.get(node.id)
            if existing is None:
                nodes[node.id] = node
                continue
            source_ids = sorted(set(existing.source_run_ids) | set(node.source_run_ids))
            existing.frequency += node.frequency
            existing.confidence = min(1.0, max(existing.confidence, node.confidence))
            existing.source_run_ids = source_ids
            existing.updated_at = utc_now()

        edges = {edge.id: edge for edge in current.edges}
        for edge in snapshot.edges:
            edges.setdefault(edge.id, edge)

        merged = MemoryGraphSnapshot(nodes=list(nodes.values()), edges=list(edges.values()))
        self.save(merged)
        return merged

    def query(self, text: str, limit: int = 20) -> list[MemoryNode]:
        terms = {term.lower() for term in TOKEN_RE.findall(text)}
        nodes = self.load().nodes
        if terms:
            nodes = [
                node for node in nodes if terms & {t.lower() for t in TOKEN_RE.findall(node.text)}
            ]
        return sorted(nodes, key=lambda n: (-n.frequency, -n.confidence, n.text))[:limit]

    def forget_run(self, run_id: str) -> MemoryGraphSnapshot:
        snapshot = self.load()
        nodes: list[MemoryNode] = []
        removed_ids: set[str] = set()
        for node in snapshot.nodes:
            node.source_run_ids = [source for source in node.source_run_ids if source != run_id]
            if node.source_run_ids:
                node.frequency = max(1, min(node.frequency, len(node.source_run_ids)))
                node.updated_at = utc_now()
                nodes.append(node)
            else:
                removed_ids.add(node.id)
        edges = [
            edge
            for edge in snapshot.edges
            if edge.source_id not in removed_ids and edge.target_id not in removed_ids
        ]
        updated = MemoryGraphSnapshot(nodes=nodes, edges=edges)
        self.save(updated)
        return updated


def extract_memories_from_runs(trace_dir: Path, limit: int = 10) -> MemoryGraphSnapshot:
    """Extract deterministic local-only memories from stored JSONL run/event traces."""
    nodes: dict[str, MemoryNode] = {}
    edges: dict[str, MemoryEdge] = {}
    for path in _trace_paths(trace_dir, limit):
        run_id = path.stem.removesuffix("-events")
        text = _trace_text(path)
        for kind, phrase, confidence in _candidate_memories(text):
            node_id = _node_id(kind, phrase)
            node = nodes.get(node_id)
            if node is None:
                node = MemoryNode(
                    id=node_id,
                    type=kind,
                    text=phrase,
                    confidence=confidence,
                    source_run_ids=[run_id],
                )
                nodes[node_id] = node
            else:
                node.frequency += 1
                node.source_run_ids = sorted(set(node.source_run_ids) | {run_id})
        run_nodes = [node for node in nodes.values() if run_id in node.source_run_ids]
        if len(run_nodes) > 1:
            first = run_nodes[0]
            for other in run_nodes[1:]:
                edge_id = _edge_id(first.id, other.id, "co_occurs")
                edges.setdefault(
                    edge_id,
                    MemoryEdge(
                        id=edge_id,
                        source_id=first.id,
                        target_id=other.id,
                        type="co_occurs",
                        confidence=0.4,
                    ),
                )
    return MemoryGraphSnapshot(nodes=list(nodes.values()), edges=list(edges.values()))


def _trace_paths(trace_dir: Path, limit: int) -> Iterable[Path]:
    if not trace_dir.exists():
        return []
    paths = sorted(trace_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return paths[: max(0, limit)]


def _trace_text(path: Path) -> str:
    chunks: list[str] = []
    redactor = Redactor()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        chunks.extend(_strings(redactor.redact_dict(data)))
    return " ".join(chunks)


def _strings(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _candidate_memories(text: str) -> list[tuple[str, str, float]]:
    lowered = text.lower()
    candidates: list[tuple[str, str, float]] = []
    if "decision" in lowered or "chosen" in lowered:
        candidates.append(("decision", _short_phrase(text), 0.7))
    if "risk" in lowered or "blocked" in lowered or "denied" in lowered:
        candidates.append(("risk", _short_phrase(text), 0.65))
    if "pattern" in lowered or "baseline" in lowered or "complete" in lowered:
        candidates.append(("pattern", _short_phrase(text), 0.6))
    for token in TOKEN_RE.findall(text):
        norm = token.lower()
        if norm not in STOPWORDS and len(norm) >= 4:
            if norm == REDACT_PLACEHOLDER.lower().strip("[]"):
                continue
            candidates.append(("concept", norm, 0.45))
    unique: dict[tuple[str, str], tuple[str, str, float]] = {}
    for item in candidates:
        unique.setdefault((item[0], item[1]), item)
    return list(unique.values())[:25]


def _short_phrase(text: str) -> str:
    words = [w.lower() for w in TOKEN_RE.findall(text) if w.lower() not in STOPWORDS]
    return " ".join(words[:12]) or "unknown memory"
