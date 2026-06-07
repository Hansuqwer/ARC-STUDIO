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
) -> list[Path]:
    """Return workspace files while excluding env, cache, dependency, build dirs.

    Symlinks are skipped, secret-bearing files (``.env``, ``*.pem``,
    ``credentials.json``, ...) are never returned, and total scan size is
    capped to keep inspection safe for generated workspaces and accidental
    dependency caches.
    """
    results: list[Path] = []
    total_bytes = 0
    for path in workspace.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.relative_to(workspace).parts[:-1]):
            continue
        if is_sensitive_file(path):
            continue
        if path.suffix in suffixes:
            try:
                total_bytes += path.stat().st_size
            except OSError:
                continue
            if len(results) >= max_files or total_bytes > max_bytes:
                break
            results.append(path)
    return results
