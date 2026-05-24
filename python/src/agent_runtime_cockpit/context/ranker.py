"""Context entry ranker — boosts entries from reliable sources."""

from __future__ import annotations

from ..protocol.schemas import ContextPackEntry, SourceType

SOURCE_BOOST = {
    SourceType.LOCAL_REPO: 1.2,
    SourceType.CONTEXT7: 1.1,
    SourceType.GITHUB_SEARCH: 1.0,
    SourceType.VERCEL_GREP: 0.9,
    SourceType.WEB_SEARCH: 0.8,
}


def rank(entries: list[ContextPackEntry], task: str) -> list[ContextPackEntry]:
    keywords = set(w.lower() for w in task.split() if len(w) > 3)

    def score(e: ContextPackEntry) -> float:
        base = e.relevance_score * SOURCE_BOOST.get(e.source_type, 1.0)
        kw_hits = sum(kw in e.content.lower() for kw in keywords)
        return base + kw_hits * 0.05

    return sorted(entries, key=lambda e: -score(e))
