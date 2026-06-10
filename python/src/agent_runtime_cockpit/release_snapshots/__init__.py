"""ARC Release Snapshots — dated, locked, HEAD-derived markdown (R-PROC2).

Provides:
- SnapshotGenerator: generates markdown snapshots from release intelligence
- Snapshot naming: YYYY-MM-DD-<short-sha>.md
- Immutability: existing snapshots are never edited

Integrates with release_intelligence module for data source.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..release_intelligence import ReleaseIntelligence

log = logging.getLogger(__name__)

RELEASE_SNAPSHOTS_SCHEMA_VERSION = 1
SNAPSHOT_DIR_NAME = "RELEASE_SNAPSHOTS"


def generate_snapshot_filename(intelligence: ReleaseIntelligence) -> str:
    """Generate snapshot filename: YYYY-MM-DD-<short-sha>.md"""
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    short_sha = intelligence.git_short or "unknown"
    return f"{date_str}-{short_sha}.md"


def generate_snapshot_markdown(intelligence: ReleaseIntelligence) -> str:
    """Generate markdown content from release intelligence."""
    lines = [
        "# ARC Studio Release Snapshot",
        "",
        f"**Generated:** {intelligence.date_utc}",
        f"**Schema Version:** {intelligence.schema_version}",
        "",
        "## Version Information",
        "",
        f"- **Version:** {intelligence.version or 'unknown'}",
        f"- **Git Commit:** `{intelligence.git_commit or 'unknown'}`",
        f"- **Git Branch:** {intelligence.git_branch or 'unknown'}",
        f"- **Git Dirty:** {intelligence.git_dirty}",
        "",
        "## Quality Gates",
        "",
        f"- **Python Tests:** {intelligence.python_tests}",
        f"- **Ruff Clean:** {intelligence.ruff_clean}",
        f"- **Banned Claims Clean:** {intelligence.banned_clean}",
        "",
        "## Commit Statistics",
        "",
        f"- **Total Commits:** {intelligence.total_commits}",
        f"- **Total Files Changed:** {intelligence.total_files_changed}",
        f"- **Total Insertions:** +{intelligence.total_insertions}",
        f"- **Total Deletions:** -{intelligence.total_deletions}",
        "",
        "## Recent Commits",
        "",
    ]

    if intelligence.commits_since_last_release:
        lines.append("| SHA | Author | Date | Message |")
        lines.append("|-----|--------|------|---------|")
        for commit in intelligence.commits_since_last_release[:20]:
            sha_link = f"[`{commit.short_sha}`]({commit.sha})"
            date_short = commit.date.split(" ")[0] if commit.date else ""
            message = commit.message[:80] + "..." if len(commit.message) > 80 else commit.message
            lines.append(f"| {sha_link} | {commit.author} | {date_short} | {message} |")
    else:
        lines.append("*No commits recorded.*")

    lines.extend(
        [
            "",
            "## Metadata",
            "",
            "```json",
            intelligence.to_json(indent=2),
            "```",
            "",
            "---",
            "*This snapshot is immutable. Do not edit existing snapshots.*",
            "",
        ]
    )

    return "\n".join(lines)


def save_snapshot(
    intelligence: ReleaseIntelligence,
    output_dir: Path,
    filename: Optional[str] = None,
) -> Path:
    """Save release intelligence as a markdown snapshot file.

    Args:
        intelligence: Release intelligence data
        output_dir: Directory to save snapshot (e.g., docs/RELEASE_SNAPSHOTS)
        filename: Optional custom filename (defaults to YYYY-MM-DD-<short-sha>.md)

    Returns:
        Path to the saved snapshot file
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    fname = filename or generate_snapshot_filename(intelligence)
    output_path = output_dir / fname

    if output_path.exists():
        log.warning("Snapshot already exists: %s (immutability preserved)", output_path)
        return output_path

    content = generate_snapshot_markdown(intelligence)
    output_path.write_text(content, encoding="utf-8")
    log.info("Snapshot saved: %s", output_path)
    return output_path


def list_snapshots(snapshot_dir: Path) -> list[Path]:
    """List all snapshot files in the directory, sorted by name (newest first)."""
    if not snapshot_dir.exists():
        return []
    snapshots = sorted(snapshot_dir.glob("*.md"), reverse=True)
    return snapshots


def get_latest_snapshot(snapshot_dir: Path) -> Optional[Path]:
    """Get the most recent snapshot file."""
    snapshots = list_snapshots(snapshot_dir)
    return snapshots[0] if snapshots else None


def verify_snapshot_immutability(snapshot_dir: Path) -> dict[str, bool]:
    """Verify that existing snapshots have not been modified.

    Returns a dict with verification status for each snapshot.
    """
    results = {}
    for snapshot in list_snapshots(snapshot_dir):
        # Check if file is tracked by git and has no uncommitted changes
        try:
            import subprocess

            result = subprocess.run(
                ["git", "diff", "--quiet", str(snapshot)],
                cwd=snapshot_dir.parent,
                capture_output=True,
            )
            results[str(snapshot.name)] = result.returncode == 0
        except Exception as e:
            log.warning("Failed to verify snapshot %s: %s", snapshot.name, e)
            results[str(snapshot.name)] = False

    return results


__all__ = [
    "RELEASE_SNAPSHOTS_SCHEMA_VERSION",
    "SNAPSHOT_DIR_NAME",
    "generate_snapshot_filename",
    "generate_snapshot_markdown",
    "save_snapshot",
    "list_snapshots",
    "get_latest_snapshot",
    "verify_snapshot_immutability",
]
