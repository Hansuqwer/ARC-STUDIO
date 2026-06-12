"""Workspace file scanning helpers."""

from __future__ import annotations

from pathlib import Path

IGNORED_DIRS = {
    ".cache",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".venv2",
    "__pycache__",
    "dist",
    "lib",
    "node_modules",
    "src-gen",
}

# Files that commonly hold secrets. These are never enumerated or read by
# workspace inventory or context scanners, regardless of the requested
# suffix filter. Matching is intentionally precise (exact filename, ``.env*``
# prefix, or a credential-bearing suffix) so ordinary source files such as
# ``credential_provider.py`` are NOT excluded.
SENSITIVE_FILENAMES = frozenset(
    {
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "credentials.json",
        "credentials.yaml",
        "credentials.yml",
        "secrets.json",
        "secrets.yaml",
        "secrets.yml",
        ".npmrc",
        ".pypirc",
        ".netrc",
        ".pgpass",
        ".htpasswd",
        ".dockercfg",
        ".git-credentials",
        "service-account.json",
    }
)
SENSITIVE_SUFFIXES = frozenset(
    {".key", ".pem", ".p12", ".pfx", ".keystore", ".jks", ".ppk", ".kdbx"}
)


def is_sensitive_file(path: Path) -> bool:
    """Return True if a file is likely to contain secrets.

    Such files must never be enumerated or read by inventory/context
    scanners. Deterministic; matches exact sensitive filenames, the
    ``.env`` family, and known credential file suffixes.
    """
    name = path.name.lower()
    if name in SENSITIVE_FILENAMES:
        return True
    if name.startswith(".env"):  # .env, .env.local, .env.production, ...
        return True
    if path.suffix.lower() in SENSITIVE_SUFFIXES:
        return True
    return False


def iter_workspace_files(
    workspace: Path,
    suffixes: tuple[str, ...],
    *,
    max_files: int = 1000,
    max_bytes: int = 10 * 1024 * 1024,
):
    """Generator — yields workspace files while excluding env, cache, dependency, build dirs.

    Uses ``os.scandir`` for streaming traversal so the full file list is never
    accumulated in memory (R-PERF1: prevents OOM on 100K+ file trees).
    Symlinks are skipped, secret-bearing files (``.env``, ``*.pem``,
    ``credentials.json``, ...) are never yielded, and total scan size is
    capped to keep inspection safe for generated workspaces and accidental
    dependency caches.
    """
    import os

    count = 0
    total_bytes = 0
    dirs = [workspace]

    while dirs:
        current = dirs.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    if entry.is_symlink():
                        continue
                    p = Path(entry.path)
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name not in IGNORED_DIRS:
                            dirs.append(p)
                    elif entry.is_file(follow_symlinks=False):
                        if p.suffix not in suffixes or is_sensitive_file(p):
                            continue
                        try:
                            total_bytes += entry.stat().st_size
                        except OSError:
                            continue
                        if count >= max_files or total_bytes > max_bytes:
                            return
                        yield p
                        count += 1
        except PermissionError:
            continue


async def aiter_workspace_files(
    workspace: Path,
    suffixes: tuple[str, ...],
    *,
    max_files: int = 100_000,
    yield_every: int = 200,
):
    """Async generator variant of iter_workspace_files (R-PERF1).

    Yields Path objects without blocking the event loop between directory
    scans. Uses asyncio.sleep(0) to yield control periodically.
    Target: < 5s for 100K files on local SSD.
    """
    import asyncio
    import os

    count = 0
    dirs = [workspace]

    while dirs:
        batch, dirs = dirs[:10], dirs[10:]

        def _scan(d: Path) -> tuple[list[Path], list[Path]]:
            files, subdirs = [], []
            try:
                with os.scandir(d) as it:
                    for e in it:
                        if e.is_symlink():
                            continue
                        p = Path(e.path)
                        if e.is_dir(follow_symlinks=False):
                            if e.name not in IGNORED_DIRS:
                                subdirs.append(p)
                        elif e.is_file(follow_symlinks=False):
                            if p.suffix in suffixes and not is_sensitive_file(p):
                                files.append(p)
            except PermissionError:
                pass
            return files, subdirs

        loop = asyncio.get_event_loop()
        results = await asyncio.gather(*[loop.run_in_executor(None, _scan, d) for d in batch])

        for files, subdirs in results:
            dirs.extend(subdirs)
            for p in files:
                yield p
                count += 1
                if count >= max_files:
                    return
                if count % yield_every == 0:
                    await asyncio.sleep(0)
