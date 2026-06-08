"""CR-021 regression guard: README must not document a non-existent `arc wallet` CLI.

Wallet/budget are interactive TUI slash-commands (`/wallet`, `/budget`); the CLI per-run
surface is `arc runs budget <run-id>`. There is no top-level `arc wallet` command, so the
README must not claim one.
"""

from __future__ import annotations

from pathlib import Path

README = Path(__file__).resolve().parents[2] / "README.md"


def test_readme_exists() -> None:
    assert README.is_file()


def test_readme_does_not_claim_arc_wallet_cli() -> None:
    text = README.read_text(encoding="utf-8")
    assert "arc wallet" not in text, "README documents a non-existent 'arc wallet' CLI command"


def test_readme_documents_real_budget_surfaces() -> None:
    text = README.read_text(encoding="utf-8")
    assert "arc runs budget" in text  # real per-run CLI budget command
    assert "/wallet" in text and "/budget" in text  # the TUI wallet/budget commands
