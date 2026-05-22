#!/usr/bin/env python3
"""CLI help text audit — verify every arc command has non-empty --help output.

Usage: python scripts/audit-cli-help.py
Exit 0 if all commands pass. Lists gaps found.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Root command
ROOT = Path(__file__).resolve().parent.parent

# All commands: (invocation, name for reporting)
COMMANDS: list[tuple[list[str], str, str]] = [
    # Top-level
    (["arc", "--help"], "arc --help", "help"),
    (["arc", "--version"], "arc --version", "version"),
    # Core commands
    (["arc", "version", "--help"], "arc version --help", "help"),
    (["arc", "health", "--help"], "arc health --help", "help"),
    (["arc", "status", "--help"], "arc status --help", "help"),
    (["arc", "inspect", "--help"], "arc inspect --help", "help"),
    (["arc", "runtimes", "--help"], "arc runtimes --help", "help"),
    (["arc", "workflows", "--help"], "arc workflows --help", "help"),
    (["arc", "schemas", "--help"], "arc schemas --help", "help"),
    (["arc", "serve", "--help"], "arc serve --help", "help"),
    (["arc", "run", "--help"], "arc run --help", "help"),
    (["arc", "bug-report", "--help"], "arc bug-report --help", "help"),
    # Sub-typer groups
    (["arc", "context", "--help"], "arc context --help", "help"),
    (["arc", "context", "pack", "--help"], "arc context pack --help", "help"),
    (["arc", "adapter", "--help"], "arc adapter --help", "help"),
    (["arc", "adapter", "list", "--help"], "arc adapter list --help", "help"),
    (["arc", "adapter", "test", "--help"], "arc adapter test --help", "help"),
    (["arc", "doctor", "--help"], "arc doctor --help", "help"),
    (["arc", "doctor", "all", "--help"], "arc doctor all --help", "help"),
    (["arc", "doctor", "swarmgraph", "--help"], "arc doctor swarmgraph --help", "help"),
    (["arc", "doctor", "env", "--help"], "arc doctor env --help", "help"),
    (["arc", "doctor", "network", "--help"], "arc doctor network --help", "help"),
    (["arc", "doctor", "storage", "--help"], "arc doctor storage --help", "help"),
    (["arc", "workspace", "--help"], "arc workspace --help", "help"),
    (["arc", "workspace", "info", "--help"], "arc workspace info --help", "help"),
    (["arc", "workspace", "trust", "--help"], "arc workspace trust --help", "help"),
    (["arc", "isolation", "--help"], "arc isolation --help", "help"),
    (["arc", "isolation", "list", "--help"], "arc isolation list --help", "help"),
    (["arc", "isolation", "status", "--help"], "arc isolation status --help", "help"),
    (["arc", "isolation", "doctor", "--help"], "arc isolation doctor --help", "help"),
    (["arc", "isolation", "setup", "--help"], "arc isolation setup --help", "help"),
    (["arc", "isolation", "test", "--help"], "arc isolation test --help", "help"),
    (["arc", "config", "--help"], "arc config --help", "help"),
    (["arc", "config", "init", "--help"], "arc config init --help", "help"),
    (["arc", "config", "show", "--help"], "arc config show --help", "help"),
    (["arc", "hitl", "--help"], "arc hitl --help", "help"),
    (["arc", "hitl", "pending", "--help"], "arc hitl pending --help", "help"),
    (["arc", "hitl", "approve", "--help"], "arc hitl approve --help", "help"),
    (["arc", "hitl", "reject", "--help"], "arc hitl reject --help", "help"),
    (["arc", "hitl", "respond", "--help"], "arc hitl respond --help", "help"),
    (["arc", "storage", "--help"], "arc storage --help", "help"),
    (["arc", "storage", "vacuum", "--help"], "arc storage vacuum --help", "help"),
    (["arc", "storage", "status", "--help"], "arc storage status --help", "help"),
    (["arc", "studio", "--help"], "arc studio --help", "help"),
    (["arc", "studio", "chat", "--help"], "arc studio chat --help", "help"),
    (["arc", "studio", "sessions", "--help"], "arc studio sessions --help", "help"),
    (["arc", "studio", "sessions-migrate", "--help"], "arc studio sessions-migrate --help", "help"),
    (["arc", "runs", "--help"], "arc runs --help", "help"),
    (["arc", "runs", "search", "--help"], "arc runs search --help", "help"),
    (["arc", "runs", "export", "--help"], "arc runs export --help", "help"),
    (["arc", "runs", "import", "--help"], "arc runs import --help", "help"),
    (["arc", "runs", "replay", "--help"], "arc runs replay --help", "help"),
    (["arc", "runs", "delete", "--help"], "arc runs delete --help", "help"),
    (["arc", "runs", "backfill", "--help"], "arc runs backfill --help", "help"),
    (["arc", "runs", "prune", "--help"], "arc runs prune --help", "help"),
    (["arc", "runs", "fork", "--help"], "arc runs fork --help", "help"),
    (["arc", "runs", "links", "--help"], "arc runs links --help", "help"),
    (["arc", "runs", "status", "--help"], "arc runs status --help", "help"),
    (["arc", "runs", "diff", "--help"], "arc runs diff --help", "help"),
    # Audit sub-typer
    (["arc", "audit", "--help"], "arc audit --help", "help"),
    (["arc", "audit", "verify", "--help"], "arc audit verify --help", "help"),
    (["arc", "audit", "export", "--help"], "arc audit export --help", "help"),
    (["arc", "audit", "key", "--help"], "arc audit key --help", "help"),
    (["arc", "audit", "key", "init", "--help"], "arc audit key init --help", "help"),
    (["arc", "audit", "key", "show", "--help"], "arc audit key show --help", "help"),
    (["arc", "audit", "key", "delete", "--help"], "arc audit key delete --help", "help"),
    # Additional commands
    (["arc", "providers", "--help"], "arc providers --help", "help"),
    (["arc", "profiles", "--help"], "arc profiles --help", "help"),
    (["arc", "eval", "--help"], "arc eval --help", "help"),
]


def audit() -> list[tuple[str, str]]:
    """Run all CLI help commands. Returns [(name, error)] for failures."""
    failures = []
    for args, name, kind in COMMANDS:
        result = subprocess.run(
            ["uv", "run"] + args,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=ROOT / "python",
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0:
            failures.append((name, f"exit code {result.returncode}: {stderr[:200]}"))
        elif kind == "help" and not stdout and not stderr:
            failures.append((name, "empty output (no stdout or stderr)"))
        elif kind == "help":
            combined = stdout + stderr
            if "Usage:" not in combined and "Usage" not in combined:
                failures.append((name, "no help text found"))
    return failures


def main() -> int:
    print("=" * 60)
    print("CLI Help Text Audit")
    print("=" * 60)
    print(f"Testing {len(COMMANDS)} commands...\n")

    failures = audit()

    if failures:
        print(f"\n❌ {len(failures)} failure(s):")
        for name, error in failures:
            print(f"  [{name}] {error}")
        print(f"\n{len(COMMANDS) - len(failures)}/{len(COMMANDS)} passed.")
        return 1
    else:
        print(f"\n✅ All {len(COMMANDS)} commands pass.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
