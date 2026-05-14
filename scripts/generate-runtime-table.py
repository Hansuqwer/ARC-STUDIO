#!/usr/bin/env python3
"""
Generate the runtime capabilities table for README.md.

Reads JSON from `arc runtimes --capabilities --json` on stdin, then rewrites
the content between <!-- RUNTIMES:START --> and <!-- RUNTIMES:END --> markers
in the README.md file given as the first argument.
"""
import json
import sys
import os


def build_table(runtimes: list[dict]) -> str:
    """Build a Markdown table from runtime capability reports."""
    rows = []
    for r in runtimes:
        rid = r["runtime_id"]
        detected = "yes" if r["detected"] else "no"
        can_run = "yes" if r["can_run"] else "no"
        paid = "yes" if r["requires_paid_calls"] else "no"

        # Build a concise note
        notes = []
        if not r["detected"]:
            notes.append("not detected")
        elif r["availability"] == "missing_dependency":
            notes.append("install missing")
        elif r["availability"] == "missing_export_target":
            notes.append("requires export target")
        elif r["availability"] == "detected_not_runnable":
            notes.append("detected, not runnable")

        for env_var in r.get("required_env", []):
            notes.append(f"set `{env_var}`")

        note = "; ".join(notes) if notes else ""
        rows.append((rid, detected, can_run, paid, note))

    # Determine column widths
    col_widths = [7, 8, 7, 4, 5]  # minimum widths
    for r in rows:
        for i, val in enumerate(r):
            if len(val) > col_widths[i]:
                col_widths[i] = len(val)

    # Columns: Runtime (left), Detected (right), Can run (right), Paid (right), Notes (left)
    positions = ["left", "right", "right", "right", "left"]
    sep_parts = []
    for i, pos in enumerate(positions):
        w = col_widths[i]
        if pos == "left":
            sep_parts.append(":" + "-" * w + "-")
        elif pos == "right":
            sep_parts.append("-" * w + ":")
        else:
            sep_parts.append(":" + "-" * w + ":")
    sep = "|" + "|".join(sep_parts) + "|"

    header = (
        f"| {'Runtime'.ljust(col_widths[0])} "
        f"| {'Detected'.ljust(col_widths[1])} "
        f"| {'Can run'.ljust(col_widths[2])} "
        f"| {'Paid'.ljust(col_widths[3])} "
        f"| {'Notes'.ljust(col_widths[4])} |"
    )

    lines = [header, sep]
    for r in rows:
        lines.append(
            f"| {r[0].ljust(col_widths[0])} "
            f"| {r[1].ljust(col_widths[1])} "
            f"| {r[2].ljust(col_widths[2])} "
            f"| {r[3].ljust(col_widths[3])} "
            f"| {r[4].ljust(col_widths[4])} |"
        )

    return "\n".join(lines) + "\n"


def update_readme(readme_path: str, table: str, quiet: bool = False) -> None:
    """Replace content between RUNTIMES markers in the README."""
    with open(readme_path, "r") as f:
        content = f.read()

    marker_start = "<!-- RUNTIMES:START -->"
    marker_end = "<!-- RUNTIMES:END -->"

    idx_start = content.find(marker_start)
    idx_end = content.find(marker_end)

    if idx_start == -1 or idx_end == -1:
        print("ERROR: RUNTIMES markers not found in README.md", file=sys.stderr)
        sys.exit(1)

    before = content[: idx_start + len(marker_start)]
    after = content[idx_end:]

    new_content = before + "\n" + table + after

    with open(readme_path, "w") as f:
        f.write(new_content)

    if not quiet:
        print("README.md updated.")


def main() -> None:
    args = sys.argv[1:]
    quiet = "--quiet" in args
    readme_args = [a for a in args if not a.startswith("--")]

    if len(readme_args) < 1:
        print(f"Usage: {sys.argv[0]} [--quiet] <readme-path>", file=sys.stderr)
        sys.exit(1)

    readme_path = readme_args[0]
    data = json.load(sys.stdin)

    if not data.get("ok"):
        print("ERROR: JSON response not OK", file=sys.stderr)
        sys.exit(1)

    runtimes = data["data"]["runtimes"]
    table = build_table(runtimes)
    update_readme(readme_path, table, quiet=quiet)


if __name__ == "__main__":
    main()
