#!/usr/bin/env python3
"""
spec_verify.py — Validate that all `file:line` citations in a spec doc
actually resolve in the repo.

Usage:
    python scripts/spec_verify.py docs/spec/v0.5.0-alpha-r02-and-qw4.md
    python scripts/spec_verify.py docs/spec/*.md
    python scripts/spec_verify.py --repo-root . docs/spec/v0.4.1-alpha-persistence-and-pricing.md

Exit codes:
    0 — All citations resolve cleanly
    1 — One or more citations are stale (file missing, or line out of range,
        or expected pattern not present)
    2 — Usage error

This is a STATIC check. It doesn't run pytest or any agent. The goal is to
catch stale spec assumptions BEFORE the agent starts a sprint and runs
into them mid-task.

Cited patterns it checks:
  - `path/to/file.py:N`         — file exists, line N exists
  - `path/to/file.py:N-M`       — file exists, lines N through M exist
  - `path/to/file.py:funcname`  — file exists, funcname is grep-findable in it
  - `path/to/file.py`           — file exists (no line check)
  - `path/to/file.py::test_x`   — pytest-style; file exists, test_x defined in it

Patterns it DELIBERATELY skips:
  - URLs (already-cited research links don't need filesystem check)
  - SHAs (can't validate without git)
  - Code blocks (treat as illustrative pseudo-code, not citations)
  - Numbers without leading file path (e.g., "~50 LOC")
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


# Match `path/to/file.ext:N`, `:N-M`, `::test_name`, or `:funcname`
# Path must contain a `/` and end with a known extension.
# Allows backticks around the citation.
CITATION_RE = re.compile(
    r"`?"  # optional opening backtick
    r"(?P<path>(?:[\w\-\.]+/)+[\w\-\.]+\.(?:py|ts|tsx|js|jsx|json|md|yaml|yml|toml|sh|sql))"
    r"(?:"
    r":(?P<lines>\d+(?:-\d+)?)"  # :N or :N-M
    r"|::(?P<test>[\w_]+)"  # ::test_name
    r"|:(?P<funcname>[a-z_][\w_]*)"  # :funcname (lowercase-leading)
    r")?"
    r"`?"  # optional closing backtick
)

# Strip code fences before scanning, so code inside ``` blocks isn't treated as citations.
CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


@dataclass(frozen=True)
class Citation:
    raw: str
    path: str
    lines: tuple[int, int] | None  # (start, end) inclusive
    test_name: str | None
    funcname: str | None
    spec_file: str
    spec_line_no: int


@dataclass
class CheckResult:
    citation: Citation
    ok: bool
    reason: str


def strip_code_blocks(text: str) -> str:
    """Remove fenced and inline code so we don't scan code as citations."""
    text = CODE_FENCE_RE.sub("", text)
    # Don't strip inline code — citations are often inside backticks in prose.
    return text


def extract_citations(spec_path: Path) -> list[Citation]:
    """Pull citations out of a spec markdown file."""
    raw_text = spec_path.read_text(encoding="utf-8")
    cleaned = strip_code_blocks(raw_text)
    citations: list[Citation] = []

    for line_no, line in enumerate(cleaned.splitlines(), start=1):
        for m in CITATION_RE.finditer(line):
            path = m.group("path")
            # Skip obvious URLs (path includes "://" or "https://" or starts with "www.")
            if "://" in path or path.startswith("www."):
                continue
            # Skip patches/ paths (they're outputs we author, not state to verify)
            if path.startswith("patches/"):
                continue
            # Skip docs/spec/ self-references in templates (they're meta)
            if path.startswith("docs/spec/TEMPLATE") or "TEMPLATE" in path:
                continue

            lines_str = m.group("lines")
            lines: tuple[int, int] | None = None
            if lines_str:
                if "-" in lines_str:
                    a, b = lines_str.split("-", 1)
                    lines = (int(a), int(b))
                else:
                    lines = (int(lines_str), int(lines_str))

            citations.append(
                Citation(
                    raw=m.group(0),
                    path=path,
                    lines=lines,
                    test_name=m.group("test"),
                    funcname=m.group("funcname"),
                    spec_file=str(spec_path),
                    spec_line_no=line_no,
                )
            )

    return citations


def check_citation(c: Citation, repo_root: Path) -> CheckResult:
    """Verify one citation against the filesystem."""
    target = repo_root / c.path
    if not target.exists():
        return CheckResult(c, False, f"file does not exist: {c.path}")
    if not target.is_file():
        return CheckResult(c, False, f"path is not a file: {c.path}")

    if c.lines is None and c.test_name is None and c.funcname is None:
        # Just a file existence check
        return CheckResult(c, True, "file exists")

    try:
        content = target.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as e:
        return CheckResult(c, False, f"could not read file: {e}")

    file_lines = content.splitlines()
    file_line_count = len(file_lines)

    if c.lines is not None:
        start, end = c.lines
        if start > file_line_count:
            return CheckResult(
                c,
                False,
                f"line {start} out of range (file has {file_line_count} lines)",
            )
        if end > file_line_count:
            return CheckResult(
                c,
                False,
                f"line range end {end} out of range (file has {file_line_count} lines)",
            )
        return CheckResult(c, True, f"line(s) {start}-{end} in range")

    if c.test_name is not None:
        # Look for `def test_name(` or `async def test_name(`
        pattern = re.compile(rf"^\s*(?:async\s+)?def\s+{re.escape(c.test_name)}\s*\(", re.MULTILINE)
        if pattern.search(content):
            return CheckResult(c, True, f"test {c.test_name} defined in file")
        return CheckResult(c, False, f"test {c.test_name} NOT defined in {c.path}")

    if c.funcname is not None:
        # Look for `def funcname(`, `class funcname(`, `funcname =`, or `FUNCNAME =` (constant)
        pattern = re.compile(
            rf"^\s*(?:def|class|async\s+def)\s+{re.escape(c.funcname)}\b"
            rf"|^\s*{re.escape(c.funcname)}\s*[:=]",
            re.MULTILINE,
        )
        if pattern.search(content):
            return CheckResult(c, True, f"symbol {c.funcname} found in file")
        return CheckResult(c, False, f"symbol {c.funcname} NOT found in {c.path}")

    return CheckResult(c, True, "passed")


def render_report(results: list[CheckResult]) -> tuple[int, int]:
    """Print human-readable report. Return (ok_count, fail_count)."""
    ok = [r for r in results if r.ok]
    bad = [r for r in results if not r.ok]

    if bad:
        print(f"\n❌ {len(bad)} stale citation(s) found:\n")
        # Group by spec file
        by_spec: dict[str, list[CheckResult]] = {}
        for r in bad:
            by_spec.setdefault(r.citation.spec_file, []).append(r)
        for spec_file, items in sorted(by_spec.items()):
            print(f"  In {spec_file}:")
            for r in items:
                print(f"    L{r.citation.spec_line_no}  {r.citation.raw}\n       → {r.reason}")
            print()

    print(f"\nSummary: {len(ok)} ok, {len(bad)} stale (of {len(results)} total)")
    return len(ok), len(bad)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Verify file:line citations in spec docs resolve in the repo.",
        epilog="Exit codes: 0=clean, 1=stale citations found, 2=usage error",
    )
    parser.add_argument(
        "spec_files",
        nargs="+",
        type=Path,
        help="Spec markdown files to verify (e.g., docs/spec/v0.5.0-*.md)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: cwd)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print failures",
    )
    args = parser.parse_args(argv)

    if not args.repo_root.is_dir():
        print(f"Repo root does not exist: {args.repo_root}", file=sys.stderr)
        return 2

    all_results: list[CheckResult] = []
    for spec_path in args.spec_files:
        if not spec_path.exists():
            print(f"Spec file does not exist: {spec_path}", file=sys.stderr)
            return 2
        citations = extract_citations(spec_path)
        if not args.quiet:
            print(f"Checking {len(citations)} citation(s) in {spec_path}")
        for c in citations:
            result = check_citation(c, args.repo_root)
            all_results.append(result)

    ok, bad = render_report(all_results)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
