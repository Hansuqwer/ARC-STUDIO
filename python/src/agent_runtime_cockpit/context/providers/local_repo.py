"""
Local Repository Context Provider

Scans the workspace for relevant source files matching the task keywords.
No external API required.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
from ...protocol.schemas import ContextPackEntry, SourceType


class LocalRepoProvider:
    """Scans workspace files and extracts relevant snippets."""

    source_type = SourceType.LOCAL_REPO
    MAX_FILES = 50
    MAX_SNIPPET_CHARS = 800

    def retrieve(self, task: str, workspace: Optional[Path] = None) -> list[ContextPackEntry]:
        if not workspace or not workspace.exists():
            return []

        keywords = [w.lower() for w in task.split() if len(w) > 3]
        results: list[ContextPackEntry] = []

        extensions = [".py", ".ts", ".tsx", ".js", ".json", ".yaml", ".yml", ".md", ".toml"]
        files = []
        for ext in extensions:
            files.extend(workspace.rglob(f"*{ext}"))

        # Score and sort files
        scored: list[tuple[float, Path]] = []
        for f in files[:self.MAX_FILES * 3]:
            try:
                text = f.read_text(errors="ignore").lower()
                score = sum(text.count(kw) for kw in keywords)
                if score > 0:
                    scored.append((score, f))
            except Exception:
                pass

        scored.sort(key=lambda x: -x[0])

        for score, fpath in scored[:self.MAX_FILES]:
            try:
                text = fpath.read_text(errors="ignore")
                # Extract best matching snippet
                snippet = self._extract_snippet(text, keywords)
                rel = str(fpath.relative_to(workspace))
                results.append(ContextPackEntry(
                    id=f"local-{hash(str(fpath)):x}",
                    task=task,
                    source=rel,
                    source_type=SourceType.LOCAL_REPO,
                    content=snippet,
                    url=None,
                    relevance_score=min(score / 10.0, 1.0),
                ))
            except Exception:
                pass

        return sorted(results, key=lambda e: -e.relevance_score)

    def _extract_snippet(self, text: str, keywords: list[str]) -> str:
        """Find the most relevant snippet in the text."""
        lines = text.splitlines()
        best_start = 0
        best_score = 0

        for i, line in enumerate(lines):
            score = sum(kw in line.lower() for kw in keywords)
            if score > best_score:
                best_score = score
                best_start = max(0, i - 2)

        snippet_lines = lines[best_start:best_start + 15]
        return "\n".join(snippet_lines)[:self.MAX_SNIPPET_CHARS]
