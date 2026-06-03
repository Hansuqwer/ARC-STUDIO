"""Local-only runtime pack registry.

Stores runtime pack *metadata* under:

* ``<workspace>/.arc/runtime-packs/registry.json`` — the index
* ``<workspace>/.arc/runtime-packs/packs/<pack-id>/arc-runtime-pack.json`` — copies

A global registry under ``~/.arc/runtime-packs/`` is supported when no workspace
is supplied. All operations are local and read/copy only:

* installing a pack copies **only** its manifest JSON (metadata) — never code,
  examples, or any executable artifact;
* nothing is imported, executed, fetched over the network, or started as a server;
* installation refuses an invalid manifest (fail-closed) and redacts secrets
  before writing.

This mirrors ``capabilities/registry.py``. There is intentionally no use of
``importlib`` and no network client in this module.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from .hashing import manifest_hash
from .loader import load_manifest
from .models import MANIFEST_FILENAME, RUNTIME_PACK_SCHEMA_VERSION, RuntimePackManifest
from .redaction import redact_manifest
from .validation import validate_manifest


def _safe_id(pack_id: str) -> str:
    return pack_id.replace("/", "_").replace("\\", "_").replace("..", "_")


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


class RuntimePackRegistryEntry(BaseModel):
    """A single registry record describing an installed pack's metadata."""

    id: str
    name: str
    version: str
    manifest_hash: str
    source_path: Optional[str] = None
    manifest_path: Optional[str] = None
    installed_at: Optional[str] = None


class RuntimePackRegistryFile(BaseModel):
    """On-disk shape of ``registry.json``."""

    schema_version: int = RUNTIME_PACK_SCHEMA_VERSION
    packs: dict[str, RuntimePackRegistryEntry] = {}


class RuntimePackInstallError(Exception):
    """Raised when a pack cannot be installed (for example, invalid manifest)."""


class RuntimePackRegistry:
    """Persist and compare runtime pack metadata locally.

    Storage layout::

        .arc/runtime-packs/
            registry.json
            packs/<pack-id>/arc-runtime-pack.json
    """

    DEFAULT_SUBDIR = Path(".arc/runtime-packs")

    def __init__(self, workspace: Optional[Path] = None, global_only: bool = False) -> None:
        if global_only or workspace is None:
            self._root = Path.home() / ".arc" / "runtime-packs"
        else:
            self._root = Path(workspace).resolve() / self.DEFAULT_SUBDIR
        self._root.mkdir(parents=True, exist_ok=True)
        (self._root / "packs").mkdir(parents=True, exist_ok=True)

    # ── Paths ───────────────────────────────────────────────────────────

    @property
    def root(self) -> Path:
        return self._root

    @property
    def registry_path(self) -> Path:
        return self._root / "registry.json"

    def pack_dir(self, pack_id: str) -> Path:
        return self._root / "packs" / _safe_id(pack_id)

    def pack_manifest_path(self, pack_id: str) -> Path:
        return self.pack_dir(pack_id) / MANIFEST_FILENAME

    # ── Registry index ──────────────────────────────────────────────────

    def load_registry(self) -> RuntimePackRegistryFile:
        if not self.registry_path.is_file():
            return RuntimePackRegistryFile()
        try:
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
            return RuntimePackRegistryFile.model_validate(data)
        except Exception:
            # A corrupt index is treated as empty rather than crashing; the
            # installed manifests on disk remain the source of truth.
            return RuntimePackRegistryFile()

    def save_registry(self, registry: RuntimePackRegistryFile) -> Path:
        self.registry_path.write_text(registry.model_dump_json(indent=2), encoding="utf-8")
        return self.registry_path

    def list_packs(self) -> list[RuntimePackRegistryEntry]:
        return list(self.load_registry().packs.values())

    def get_pack(self, pack_id: str) -> Optional[RuntimePackRegistryEntry]:
        return self.load_registry().packs.get(pack_id)

    def load_installed_manifest(self, pack_id: str) -> Optional[RuntimePackManifest]:
        path = self.pack_manifest_path(pack_id)
        if not path.is_file():
            return None
        try:
            return load_manifest(path)
        except Exception:
            return None

    # ── Install / uninstall (metadata only) ─────────────────────────────

    def install(self, source: Path | str, *, force: bool = False) -> RuntimePackRegistryEntry:
        """Install a pack's metadata from a local path.

        Copies only the manifest JSON (after validation + redaction). Raises
        ``RuntimePackInstallError`` if the manifest is invalid. No pack code,
        example, or executable artifact is copied; nothing is executed.
        """
        try:
            manifest = load_manifest(source)
        except Exception as exc:
            raise RuntimePackInstallError(f"Cannot install pack from {source}: {exc}") from exc
        report = validate_manifest(manifest)
        if not report.ok:
            messages = "; ".join(f"{f.field}: {f.message}" for f in report.errors)
            raise RuntimePackInstallError(
                f"Refusing to install invalid pack '{manifest.id}': {messages}"
            )

        existing = self.get_pack(manifest.id)
        if existing and not force:
            raise RuntimePackInstallError(
                f"Pack '{manifest.id}' is already installed; pass force=True to overwrite."
            )

        # Ensure the stored manifest is hash-pinned and secret-free.
        manifest.manifest_hash = manifest_hash(manifest)
        redacted = redact_manifest(manifest)

        target_dir = self.pack_dir(manifest.id)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_manifest = target_dir / MANIFEST_FILENAME
        target_manifest.write_text(
            json.dumps(redacted, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )

        entry = RuntimePackRegistryEntry(
            id=manifest.id,
            name=manifest.name,
            version=manifest.version,
            manifest_hash=manifest.manifest_hash,
            source_path=str(Path(source).resolve()),
            manifest_path=str(target_manifest),
            installed_at=_now_iso(),
        )
        registry = self.load_registry()
        registry.packs[manifest.id] = entry
        self.save_registry(registry)
        return entry

    def uninstall(self, pack_id: str) -> bool:
        """Remove a pack's metadata. Raises ``RuntimePackInstallError`` if not installed."""
        registry = self.load_registry()
        if pack_id not in registry.packs:
            raise RuntimePackInstallError(f"Pack '{pack_id}' is not installed.")
        registry.packs.pop(pack_id)
        self.save_registry(registry)

        target_dir = self.pack_dir(pack_id)
        if target_dir.is_dir():
            manifest_file = target_dir / MANIFEST_FILENAME
            if manifest_file.is_file():
                manifest_file.unlink()
            try:
                target_dir.rmdir()
            except OSError:
                pass

    # ── Drift detection ─────────────────────────────────────────────────

    def check_drift(self, pack_id: str) -> dict[str, Any]:
        """Compare the recorded hash with the stored manifest's recomputed hash."""
        entry = self.get_pack(pack_id)
        if entry is None:
            return {"installed": False, "drifted": False, "message": "Pack not installed."}
        manifest = self.load_installed_manifest(pack_id)
        if manifest is None:
            return {
                "installed": True,
                "drifted": True,
                "recorded_hash": entry.manifest_hash,
                "current_hash": None,
                "message": "Installed manifest is missing or unreadable.",
            }
        current = manifest_hash(manifest)
        drifted = current != entry.manifest_hash
        return {
            "installed": True,
            "drifted": drifted,
            "recorded_hash": entry.manifest_hash,
            "current_hash": current,
            "message": "Manifest drift detected." if drifted else "Manifest matches registry.",
        }


def create_registry(workspace: Optional[Path] = None) -> RuntimePackRegistry:
    """Factory for a :class:`RuntimePackRegistry`."""
    return RuntimePackRegistry(workspace=workspace)


__all__ = [
    "RuntimePackRegistry",
    "RuntimePackRegistryEntry",
    "RuntimePackRegistryFile",
    "RuntimePackInstallError",
    "create_registry",
]
