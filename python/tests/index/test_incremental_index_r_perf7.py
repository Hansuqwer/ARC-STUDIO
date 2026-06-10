"""Tests for ARC Index — incremental workspace index (R-PERF7, Phase 328)."""

from __future__ import annotations

import time
from pathlib import Path

from agent_runtime_cockpit.index import CodebaseIndex


class TestIncrementalIndex:
    def test_update_file(self, tmp_path: Path) -> None:
        idx = CodebaseIndex(tmp_path)
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass", encoding="utf-8")

        result = idx.update_file(test_file)
        assert result is True

        stats = idx.stats()
        assert stats["file_count"] == 1

    def test_update_file_nonexistent_extension(self, tmp_path: Path) -> None:
        idx = CodebaseIndex(tmp_path)
        test_file = tmp_path / "test.xyz"
        test_file.write_text("some content", encoding="utf-8")

        result = idx.update_file(test_file)
        assert result is False

    def test_remove_file(self, tmp_path: Path) -> None:
        idx = CodebaseIndex(tmp_path)
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass", encoding="utf-8")

        idx.update_file(test_file)
        assert idx.stats()["file_count"] == 1

        result = idx.remove_file(test_file)
        assert result is True
        assert idx.stats()["file_count"] == 0

    def test_remove_nonexistent_file(self, tmp_path: Path) -> None:
        idx = CodebaseIndex(tmp_path)
        test_file = tmp_path / "nonexistent.py"

        result = idx.remove_file(test_file)
        assert result is False

    def test_get_changed_files(self, tmp_path: Path) -> None:
        idx = CodebaseIndex(tmp_path)
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass", encoding="utf-8")

        idx.build()
        time.sleep(0.1)

        test_file.write_text("def hello(): return 'world'", encoding="utf-8")
        changed = idx.get_changed_files()
        assert len(changed) == 1
        assert changed[0].name == "test.py"

    def test_incremental_update(self, tmp_path: Path) -> None:
        idx = CodebaseIndex(tmp_path)
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass", encoding="utf-8")

        idx.build()
        time.sleep(0.1)

        test_file.write_text("def hello(): return 'world'", encoding="utf-8")
        result = idx.incremental_update()

        assert result["updated"] == 1
        assert result["removed"] == 0
        assert result["elapsed_s"] < 1.0

    def test_incremental_update_multiple_files(self, tmp_path: Path) -> None:
        idx = CodebaseIndex(tmp_path)
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("def func1(): pass", encoding="utf-8")
        file2.write_text("def func2(): pass", encoding="utf-8")

        idx.build()
        time.sleep(0.1)

        file1.write_text("def func1(): return 1", encoding="utf-8")
        file2.write_text("def func2(): return 2", encoding="utf-8")

        result = idx.incremental_update()
        assert result["updated"] == 2
        assert result["elapsed_s"] < 1.0

    def test_incremental_update_performance(self, tmp_path: Path) -> None:
        idx = CodebaseIndex(tmp_path)
        for i in range(100):
            f = tmp_path / f"file{i}.py"
            f.write_text(f"def func{i}(): pass", encoding="utf-8")

        idx.build()
        time.sleep(0.1)

        (tmp_path / "file0.py").write_text("def func0(): return 'changed'", encoding="utf-8")

        start = time.perf_counter()
        result = idx.incremental_update()
        elapsed = time.perf_counter() - start

        assert result["updated"] == 1
        assert elapsed < 1.0, f"Incremental update took {elapsed:.3f}s, expected < 1s"

    def test_search_after_incremental_update(self, tmp_path: Path) -> None:
        idx = CodebaseIndex(tmp_path)
        test_file = tmp_path / "test.py"
        test_file.write_text("def original_function(): pass", encoding="utf-8")

        idx.build()
        results = idx.search("original_function")
        assert len(results) == 1

        time.sleep(0.1)
        test_file.write_text("def updated_function(): pass", encoding="utf-8")
        idx.incremental_update()

        results = idx.search("updated_function")
        assert len(results) == 1
        assert "updated_function" in results[0].symbols_preview
