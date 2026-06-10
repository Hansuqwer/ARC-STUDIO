"""ARC Release Intelligence — auto-generate release intelligence from CI (R-PROC1).

Provides:
- Git log parsing for commit information
- Release intelligence report generation
- Automated release notes from commit history

Integrates with CI pipelines to generate release intelligence on merge to main.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)

RELEASE_INTELLIGENCE_SCHEMA_VERSION = 1


@dataclass
class CommitInfo:
    """Information about a single commit."""

    sha: str
    short_sha: str
    author: str
    author_email: str
    date: str
    message: str
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "sha": self.sha,
            "short_sha": self.short_sha,
            "author": self.author,
            "author_email": self.author_email,
            "date": self.date,
            "message": self.message,
            "files_changed": self.files_changed,
            "insertions": self.insertions,
            "deletions": self.deletions,
        }


@dataclass
class ReleaseIntelligence:
    """Release intelligence report."""

    schema_version: int = RELEASE_INTELLIGENCE_SCHEMA_VERSION
    version: str = ""
    git_commit: str = ""
    git_short: str = ""
    git_branch: str = ""
    git_dirty: bool = False
    date_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    commits_since_last_release: list[CommitInfo] = field(default_factory=list)
    total_commits: int = 0
    total_files_changed: int = 0
    total_insertions: int = 0
    total_deletions: int = 0
    python_tests: int = 0
    ruff_clean: bool = False
    banned_clean: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "version": self.version,
            "git_commit": self.git_commit,
            "git_short": self.git_short,
            "git_branch": self.git_branch,
            "git_dirty": self.git_dirty,
            "date_utc": self.date_utc,
            "commits_since_last_release": [c.to_dict() for c in self.commits_since_last_release],
            "total_commits": self.total_commits,
            "total_files_changed": self.total_files_changed,
            "total_insertions": self.total_insertions,
            "total_deletions": self.total_deletions,
            "python_tests": self.python_tests,
            "ruff_clean": self.ruff_clean,
            "banned_clean": self.banned_clean,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def parse_git_log(
    repo_path: Path, since: Optional[str] = None, max_count: int = 100
) -> list[CommitInfo]:
    """Parse git log and return list of CommitInfo objects."""
    cmd = ["git", "log", f"--max-count={max_count}", "--pretty=format:%H|%h|%an|%ae|%ai|%s"]
    if since:
        cmd.append(f"--since={since}")

    try:
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        log.error("Failed to run git log: %s", e)
        return []

    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 5)
        if len(parts) < 6:
            continue

        sha, short_sha, author, email, date, message = parts
        commits.append(
            CommitInfo(
                sha=sha,
                short_sha=short_sha,
                author=author,
                author_email=email,
                date=date,
                message=message,
            )
        )

    return commits


def get_commit_stats(repo_path: Path, sha: str) -> tuple[int, int, int]:
    """Get files changed, insertions, deletions for a commit."""
    try:
        result = subprocess.run(
            ["git", "show", "--numstat", "--format=", sha],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return 0, 0, 0

    files_changed = 0
    insertions = 0
    deletions = 0

    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            files_changed += 1
            try:
                insertions += int(parts[0]) if parts[0] != "-" else 0
                deletions += int(parts[1]) if parts[1] != "-" else 0
            except ValueError:
                continue

    return files_changed, insertions, deletions


def generate_release_intelligence(
    repo_path: Path,
    version: str = "",
    since: Optional[str] = None,
    max_commits: int = 100,
) -> ReleaseIntelligence:
    """Generate release intelligence report from git history."""
    intelligence = ReleaseIntelligence(version=version)

    # Get current git info
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        intelligence.git_commit = result.stdout.strip()
        intelligence.git_short = intelligence.git_commit[:8]
    except subprocess.CalledProcessError:
        pass

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        intelligence.git_branch = result.stdout.strip()
    except subprocess.CalledProcessError:
        pass

    try:
        result = subprocess.run(
            ["git", "diff", "--quiet"],
            cwd=repo_path,
            capture_output=True,
        )
        intelligence.git_dirty = result.returncode != 0
    except subprocess.CalledProcessError:
        pass

    # Parse commits
    commits = parse_git_log(repo_path, since=since, max_count=max_commits)
    intelligence.commits_since_last_release = commits
    intelligence.total_commits = len(commits)

    # Get stats for each commit
    for commit in commits:
        files, ins, dels = get_commit_stats(repo_path, commit.sha)
        commit.files_changed = files
        commit.insertions = ins
        commit.deletions = dels
        intelligence.total_files_changed += files
        intelligence.total_insertions += ins
        intelligence.total_deletions += dels

    return intelligence


def save_release_intelligence(intelligence: ReleaseIntelligence, output_path: Path) -> None:
    """Save release intelligence report to a JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(intelligence.to_json(), encoding="utf-8")


def load_release_intelligence(input_path: Path) -> ReleaseIntelligence:
    """Load release intelligence report from a JSON file."""
    data = json.loads(input_path.read_text(encoding="utf-8"))
    commits = [
        CommitInfo(
            sha=c["sha"],
            short_sha=c["short_sha"],
            author=c["author"],
            author_email=c["author_email"],
            date=c["date"],
            message=c["message"],
            files_changed=c.get("files_changed", 0),
            insertions=c.get("insertions", 0),
            deletions=c.get("deletions", 0),
        )
        for c in data.get("commits_since_last_release", [])
    ]
    return ReleaseIntelligence(
        schema_version=data.get("schema_version", RELEASE_INTELLIGENCE_SCHEMA_VERSION),
        version=data.get("version", ""),
        git_commit=data.get("git_commit", ""),
        git_short=data.get("git_short", ""),
        git_branch=data.get("git_branch", ""),
        git_dirty=data.get("git_dirty", False),
        date_utc=data.get("date_utc", ""),
        commits_since_last_release=commits,
        total_commits=data.get("total_commits", 0),
        total_files_changed=data.get("total_files_changed", 0),
        total_insertions=data.get("total_insertions", 0),
        total_deletions=data.get("total_deletions", 0),
        python_tests=data.get("python_tests", 0),
        ruff_clean=data.get("ruff_clean", False),
        banned_clean=data.get("banned_clean", False),
        metadata=data.get("metadata", {}),
    )


__all__ = [
    "RELEASE_INTELLIGENCE_SCHEMA_VERSION",
    "CommitInfo",
    "ReleaseIntelligence",
    "parse_git_log",
    "get_commit_stats",
    "generate_release_intelligence",
    "save_release_intelligence",
    "load_release_intelligence",
]
