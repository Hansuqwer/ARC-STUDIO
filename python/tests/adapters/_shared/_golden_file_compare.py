"""Diff JSON run-plans with stable key ordering."""

from __future__ import annotations

import json
from pathlib import Path


class GoldenFileCompare:
    def __init__(self, golden_path: Path) -> None:
        self._golden_path = golden_path

    def assert_matches(self, candidate: dict) -> None:
        golden = json.loads(self._golden_path.read_text())
        canonical_golden = json.dumps(golden, sort_keys=True, indent=2)
        canonical_candidate = json.dumps(candidate, sort_keys=True, indent=2)
        if canonical_golden != canonical_candidate:
            raise AssertionError(f"golden mismatch at {self._golden_path}")

    def update(self, candidate: dict) -> None:
        self._golden_path.write_text(json.dumps(candidate, sort_keys=True, indent=2) + "\n")
