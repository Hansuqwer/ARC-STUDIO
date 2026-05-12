"""Tests: Context retrieval — engine, providers, ranker, cache, pack."""
import tempfile
from pathlib import Path

from agent_runtime_cockpit.context.engine import ContextEngine
from agent_runtime_cockpit.context.cache import ContextCache
from agent_runtime_cockpit.context.ranker import rank
from agent_runtime_cockpit.context.pack import ContextPackGenerator
from agent_runtime_cockpit.context.providers.local_repo import LocalRepoProvider
from agent_runtime_cockpit.context.providers.context7 import Context7Provider
from agent_runtime_cockpit.context.providers.vercel_grep import VercelGrepProvider
from agent_runtime_cockpit.context.providers.github_code_search import GitHubCodeSearchProvider
from agent_runtime_cockpit.context.providers.web_search import WebSearchProvider
from agent_runtime_cockpit.protocol.schemas import ContextPackEntry, SourceType


class TestLocalRepoProvider:
    def test_returns_entries_for_relevant_files(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / "agent.py").write_text("class ResearchAgent:\n    def research(self): pass\n")
            provider = LocalRepoProvider()
            entries = provider.retrieve("research agent", tdp)
            assert isinstance(entries, list)
            assert len(entries) > 0
            assert entries[0].source_type == SourceType.LOCAL_REPO

    def test_returns_empty_for_nonexistent_workspace(self):
        provider = LocalRepoProvider()
        entries = provider.retrieve("anything", Path("/nonexistent/path/xyz"))
        assert entries == []

    def test_entries_have_required_fields(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / "graph.py").write_text("# agent graph definition\nclass Agent: pass\n")
            provider = LocalRepoProvider()
            entries = provider.retrieve("agent graph", tdp)
            if entries:
                e = entries[0]
                assert e.id
                assert e.task == "agent graph"
                assert e.content
                assert 0.0 <= e.relevance_score <= 1.0


class TestOfflineProviders:
    """External providers must return honest empty results when credentials are absent."""

    def test_context7_offline_returns_empty(self, monkeypatch):
        monkeypatch.delenv("ARC_CONTEXT7_API_KEY", raising=False)
        provider = Context7Provider()
        entries = provider.retrieve("theia extension")
        assert entries == []

    def test_vercel_grep_unavailable_returns_empty(self, monkeypatch):
        provider = VercelGrepProvider()
        monkeypatch.setattr(provider, "_scrape", lambda task: (_ for _ in ()).throw(RuntimeError("offline")))
        entries = provider.retrieve("theia widget")
        assert entries == []

    def test_github_offline_returns_empty(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        provider = GitHubCodeSearchProvider()
        entries = provider.retrieve("CommandContribution")
        assert entries == []

    def test_web_search_offline_returns_empty(self, monkeypatch):
        monkeypatch.delenv("ARC_SEARCH_API_KEY", raising=False)
        provider = WebSearchProvider()
        entries = provider.retrieve("langgraph 2025 changes")
        assert entries == []

    def test_offline_entries_are_empty_or_well_formed(self, monkeypatch):
        monkeypatch.delenv("ARC_CONTEXT7_API_KEY", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("ARC_SEARCH_API_KEY", raising=False)
        for ProviderClass in [Context7Provider, VercelGrepProvider, GitHubCodeSearchProvider, WebSearchProvider]:
            provider = ProviderClass()
            entries = provider.retrieve("test task")
            for e in entries:
                assert e.source_type is not None
                assert isinstance(e.relevance_score, float)
                assert 0.0 <= e.relevance_score <= 1.0


class TestContextCache:
    def test_miss_returns_none(self):
        cache = ContextCache()
        assert cache.get("unknown task") is None

    def test_set_and_get(self):
        cache = ContextCache()
        entry = ContextPackEntry(
            id="test-1", task="test", source="local", source_type=SourceType.LOCAL_REPO,
            content="test content", relevance_score=0.8
        )
        cache.set("my task", [entry])
        result = cache.get("my task")
        assert result is not None
        assert len(result) == 1
        assert result[0].id == "test-1"

    def test_cache_expiry(self):
        cache = ContextCache(ttl=0)  # instant expiry
        import time
        entry = ContextPackEntry(
            id="test-2", task="test", source="local", source_type=SourceType.LOCAL_REPO,
            content="content", relevance_score=0.5
        )
        cache.set("task", [entry])
        time.sleep(0.01)
        result = cache.get("task")
        assert result is None  # expired


class TestRanker:
    def test_ranks_by_relevance_score(self):
        entries = [
            ContextPackEntry(id="a", task="t", source="x", source_type=SourceType.LOCAL_REPO, content="theia widget", relevance_score=0.3),
            ContextPackEntry(id="b", task="t", source="x", source_type=SourceType.CONTEXT7, content="theia widget docs", relevance_score=0.9),
        ]
        ranked = rank(entries, "theia widget")
        assert ranked[0].id == "b"  # higher score first

    def test_local_repo_boosted(self):
        local = ContextPackEntry(id="local", task="t", source="x", source_type=SourceType.LOCAL_REPO, content="agent", relevance_score=0.5)
        web = ContextPackEntry(id="web", task="t", source="x", source_type=SourceType.WEB_SEARCH, content="agent", relevance_score=0.5)
        ranked = rank([web, local], "agent")
        # Local should rank higher than web at same base score
        assert ranked[0].id == "local"


class TestContextEngine:
    def test_retrieve_returns_list(self):
        with tempfile.TemporaryDirectory() as td:
            engine = ContextEngine()
            results = engine.retrieve("agent runtime", Path(td))
            assert isinstance(results, list)

    def test_no_duplicates(self):
        with tempfile.TemporaryDirectory() as td:
            engine = ContextEngine()
            results = engine.retrieve("test task", Path(td))
            contents = [e.content[:100] for e in results]
            # Should not have exact duplicate content
            assert len(contents) == len(set(contents)) or len(results) < 2


class TestContextPackGenerator:
    def test_generates_and_caches(self):
        with tempfile.TemporaryDirectory() as td:
            gen = ContextPackGenerator(output_dir=Path(td) / "context-packs")
            entries1 = gen.generate("test task", workspace=Path(td), save=True)
            entries2 = gen.generate("test task", workspace=Path(td), save=False)
            # Second call should return cached results
            assert len(entries1) == len(entries2)

    def test_saves_pack_file(self):
        with tempfile.TemporaryDirectory() as td:
            output_dir = Path(td) / "packs"
            gen = ContextPackGenerator(output_dir=output_dir)
            gen.generate("save test task", workspace=Path(td), save=True)
            assert output_dir.exists()
            pack_files = list(output_dir.glob("pack-*.json"))
            assert len(pack_files) > 0
