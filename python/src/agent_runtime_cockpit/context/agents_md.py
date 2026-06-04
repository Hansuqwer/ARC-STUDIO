"""AGENTS.md workspace ingestion — discovery, hashing, nearest-wins, override.

Provides deterministic discovery and classification of AGENTS.md files within
a workspace tree. The LLM-generated heuristic uses 4 signals (3-of-4 → True).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Directories excluded from discovery
_EXCLUDED_DIRS = frozenset(
    ["node_modules", ".git", "dist", "build", "coverage", ".venv", "__pycache__"]
)

# Size cap for warning (32 KiB)
SIZE_CAP_BYTES = 32_768

# Repeated bullet phrases that indicate LLM generation
_LLM_PHRASES = re.compile(r"\b(Ensure|Make sure|Always)\b")

# Emoji regex (Unicode emoji ranges)
_EMOJI_RE = re.compile(
    "[\U0001f300-\U0001f9ff\U00002702-\U000027b0\U0000fe00-\U0000fe0f"
    "\U0000200d\U00002600-\U000026ff\U00002700-\U000027bf]"
)


@dataclass(frozen=True)
class AgentsMdEntry:
    """A discovered AGENTS.md file."""

    path: Path
    sha256: str
    size_bytes: int
    over_cap: bool
    is_override: bool
    likely_llm_generated: bool


@dataclass
class DriftReport:
    """Result of check_drift()."""

    drifted: bool
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _is_excluded(path: Path, gitignore_patterns: Optional[list[str]] = None) -> bool:
    """Check if any path component is in exclusion set."""
    for part in path.parts:
        if part in _EXCLUDED_DIRS:
            return True
    if gitignore_patterns:
        rel = str(path)
        for pat in gitignore_patterns:
            if pat in rel:
                return True
    return False


def _emoji_density(text: str) -> float:
    """Fraction of characters that are emoji."""
    if not text:
        return 0.0
    emoji_count = len(_EMOJI_RE.findall(text))
    return emoji_count / len(text)


def _repeated_phrase_count(text: str) -> int:
    """Count occurrences of LLM-indicator phrases."""
    return len(_LLM_PHRASES.findall(text))


def _stop_word_ratio(text: str) -> float:
    """Shannon-entropy-based stop-word ratio heuristic.

    Measures the ratio of common English stop words to total words.
    Returns value outside [0.3, 0.6] as a signal of LLM generation.
    """
    _STOP_WORDS = frozenset(
        "the a an is are was were be been being have has had do does did "
        "will would shall should may might can could of in to for on with "
        "at by from and or but not this that it its".split()
    )
    words = re.findall(r"[a-z]+", text.lower())
    if len(words) < 20:
        return 0.45  # Neutral for very short texts
    stop_count = sum(1 for w in words if w in _STOP_WORDS)
    return stop_count / len(words)


def _has_project_identifiers(text: str, workspace_name: str) -> bool:
    """Check if workspace directory name appears in body text."""
    return workspace_name.lower() in text.lower()


def is_likely_llm_generated(text: str, workspace_name: str) -> bool:
    """Deterministic LLM-generated heuristic: 3-of-4 signals → True.

    Signals:
    1. emoji density > 2%
    2. repeated 'Ensure'/'Make sure'/'Always' >= 6 times
    3. stop-word ratio outside [0.3, 0.6]
    4. absence of project-specific identifiers
    """
    signals = 0
    if _emoji_density(text) > 0.02:
        signals += 1
    if _repeated_phrase_count(text) >= 6:
        signals += 1
    ratio = _stop_word_ratio(text)
    if ratio < 0.3 or ratio > 0.6:
        signals += 1
    if not _has_project_identifiers(text, workspace_name):
        signals += 1
    return signals >= 3


def discovery(workspace: Path) -> list[AgentsMdEntry]:
    """Discover all AGENTS.md and AGENTS.override.md files in workspace.

    Excludes: node_modules, .git, dist, build, coverage, .venv, __pycache__.
    Returns entries sorted by path depth (shallowest first).
    """
    entries: list[AgentsMdEntry] = []
    workspace_name = workspace.name

    for md_path in sorted(workspace.rglob("AGENTS.md")):
        rel = md_path.relative_to(workspace)
        if _is_excluded(rel):
            continue
        content = md_path.read_bytes()
        entries.append(
            AgentsMdEntry(
                path=md_path,
                sha256=_sha256(content),
                size_bytes=len(content),
                over_cap=len(content) > SIZE_CAP_BYTES,
                is_override=False,
                likely_llm_generated=is_likely_llm_generated(
                    content.decode("utf-8", errors="replace"), workspace_name
                ),
            )
        )

    for md_path in sorted(workspace.rglob("AGENTS.override.md")):
        rel = md_path.relative_to(workspace)
        if _is_excluded(rel):
            continue
        content = md_path.read_bytes()
        entries.append(
            AgentsMdEntry(
                path=md_path,
                sha256=_sha256(content),
                size_bytes=len(content),
                over_cap=len(content) > SIZE_CAP_BYTES,
                is_override=True,
                likely_llm_generated=is_likely_llm_generated(
                    content.decode("utf-8", errors="replace"), workspace_name
                ),
            )
        )

    return sorted(entries, key=lambda e: len(e.path.parts))


def nearest_for(target: Path, workspace: Path) -> Optional[AgentsMdEntry]:
    """Find the closest ancestor AGENTS.md (or override) for a given path.

    Override files take priority over AGENTS.md at the same directory level.
    """
    entries = discovery(workspace)
    if not entries:
        return None

    target = target.resolve()
    best: Optional[AgentsMdEntry] = None
    best_depth = -1

    for entry in entries:
        entry_dir = entry.path.parent.resolve()
        try:
            target.relative_to(entry_dir)
        except ValueError:
            continue
        depth = len(entry_dir.parts)
        if depth > best_depth:
            best = entry
            best_depth = depth
        elif depth == best_depth and entry.is_override:
            best = entry

    return best


def pin(workspace: Path) -> Path:
    """Write discovered entries to .arc/agents-md/index.json."""
    entries = discovery(workspace)
    index_dir = workspace / ".arc" / "agents-md"
    index_dir.mkdir(parents=True, exist_ok=True)
    index_path = index_dir / "index.json"

    data = {
        "version": 1,
        "entries": [
            {
                "path": str(e.path.relative_to(workspace)),
                "sha256": e.sha256,
                "size_bytes": e.size_bytes,
                "is_override": e.is_override,
                "likely_llm_generated": e.likely_llm_generated,
            }
            for e in entries
        ],
    }
    index_path.write_text(json.dumps(data, indent=2) + "\n")
    return index_path


def check_drift(workspace: Path) -> DriftReport:
    """Compare current workspace against pinned index.

    Returns {drifted, added, removed, changed}.
    """
    index_path = workspace / ".arc" / "agents-md" / "index.json"
    if not index_path.exists():
        current = discovery(workspace)
        if current:
            return DriftReport(
                drifted=True,
                added=[str(e.path.relative_to(workspace)) for e in current],
            )
        return DriftReport(drifted=False)

    pinned_data = json.loads(index_path.read_text())
    pinned_map: dict[str, str] = {e["path"]: e["sha256"] for e in pinned_data.get("entries", [])}

    current = discovery(workspace)
    current_map: dict[str, str] = {str(e.path.relative_to(workspace)): e.sha256 for e in current}

    added = [p for p in current_map if p not in pinned_map]
    removed = [p for p in pinned_map if p not in current_map]
    changed = [p for p in current_map if p in pinned_map and current_map[p] != pinned_map[p]]
    drifted = bool(added or removed or changed)

    return DriftReport(drifted=drifted, added=added, removed=removed, changed=changed)
