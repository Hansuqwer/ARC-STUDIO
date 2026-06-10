"""ARC Hub — local-first catalog for sharing configs, policies, and templates.

No central server. Items are shared via git repos, local directories, or Gists.
Install verification uses sha256 checksums (deterministic, no LLM judgment).
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

HUB_DIR_NAME = ".arc_hub"
MANIFEST_FILENAME = "hub_manifest.json"
VALID_ITEM_TYPES = frozenset(
    {"provider-preset", "policy-template", "swarm-def", "eval-suite", "theme"}
)


class HubError(Exception):
    pass


class HubItemNotFound(HubError):
    pass


class HubInvalidType(HubError):
    pass


class HubChecksumMismatch(HubError):
    pass


@dataclass(frozen=True)
class HubItem:
    id: str
    name: str
    item_type: str
    version: str
    description: str
    source_path: str
    sha256: str
    installed_at: Optional[str] = None
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "item_type": self.item_type,
            "version": self.version,
            "description": self.description,
            "source_path": self.source_path,
            "sha256": self.sha256,
            "installed_at": self.installed_at,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HubItem:
        return cls(
            id=data["id"],
            name=data["name"],
            item_type=data["item_type"],
            version=data["version"],
            description=data.get("description", ""),
            source_path=data["source_path"],
            sha256=data["sha256"],
            installed_at=data.get("installed_at"),
            tags=tuple(data.get("tags", [])),
        )


def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_dir_sha256(directory: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(directory.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(directory)).encode())
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
    return h.hexdigest()


def load_hub_item(source: Path) -> HubItem:
    if not source.exists():
        raise HubError(f"Source not found: {source}")

    if source.is_file():
        if source.suffix in {".yaml", ".yml"}:
            with open(source, encoding="utf-8") as f:
                meta = yaml.safe_load(f) or {}
        elif source.suffix == ".json":
            with open(source, encoding="utf-8") as f:
                meta = json.load(f)
        else:
            meta = {}

        item_type = meta.get("item_type", meta.get("type", "provider-preset"))
        if item_type not in VALID_ITEM_TYPES:
            raise HubInvalidType(
                f"Unknown item type '{item_type}'. Valid: {sorted(VALID_ITEM_TYPES)}"
            )

        checksum = compute_file_sha256(source)
        return HubItem(
            id=meta.get("id", source.stem),
            name=meta.get("name", source.stem),
            item_type=item_type,
            version=meta.get("version", "0.1.0"),
            description=meta.get("description", ""),
            source_path=str(source.resolve()),
            sha256=checksum,
            tags=tuple(meta.get("tags", [])),
        )

    if source.is_dir():
        manifest_file = source / MANIFEST_FILENAME
        if manifest_file.exists():
            with open(manifest_file, encoding="utf-8") as f:
                meta = json.load(f)
        else:
            meta = {}

        item_type = meta.get("item_type", meta.get("type", "swarm-def"))
        if item_type not in VALID_ITEM_TYPES:
            raise HubInvalidType(
                f"Unknown item type '{item_type}'. Valid: {sorted(VALID_ITEM_TYPES)}"
            )

        checksum = compute_dir_sha256(source)
        return HubItem(
            id=meta.get("id", source.name),
            name=meta.get("name", source.name),
            item_type=item_type,
            version=meta.get("version", "0.1.0"),
            description=meta.get("description", ""),
            source_path=str(source.resolve()),
            sha256=checksum,
            tags=tuple(meta.get("tags", [])),
        )

    raise HubError(f"Source is neither file nor directory: {source}")


class HubCatalog:
    def __init__(self, hub_dir: Path) -> None:
        self._hub_dir = hub_dir
        self._hub_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._hub_dir / "index.json"

    def _load_index(self) -> dict[str, dict[str, Any]]:
        if not self._index_path.exists():
            return {}
        with open(self._index_path, encoding="utf-8") as f:
            return json.load(f)

    def _save_index(self, index: dict[str, dict[str, Any]]) -> None:
        with open(self._index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
            f.write("\n")

    def list_items(self, item_type: Optional[str] = None) -> list[HubItem]:
        index = self._load_index()
        items = [HubItem.from_dict(v) for v in index.values()]
        if item_type:
            items = [i for i in items if i.item_type == item_type]
        return sorted(items, key=lambda i: i.id)

    def add(self, source: Path, force: bool = False) -> HubItem:
        item = load_hub_item(source)
        index = self._load_index()
        if item.id in index and not force:
            raise HubError(f"Item '{item.id}' already installed. Use --force to overwrite.")

        dest = self._hub_dir / item.id
        if source.is_file():
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest / source.name)
        else:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(source, dest)

        import datetime

        installed_item = HubItem(
            id=item.id,
            name=item.name,
            item_type=item.item_type,
            version=item.version,
            description=item.description,
            source_path=str(source.resolve()),
            sha256=item.sha256,
            installed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            tags=item.tags,
        )
        index[item.id] = installed_item.to_dict()
        self._save_index(index)
        return installed_item

    def remove(self, item_id: str) -> None:
        index = self._load_index()
        if item_id not in index:
            raise HubItemNotFound(f"Item '{item_id}' not found in hub catalog.")
        dest = self._hub_dir / item_id
        if dest.exists():
            shutil.rmtree(dest)
        del index[item_id]
        self._save_index(index)

    def verify(self, item_id: str) -> dict[str, Any]:
        index = self._load_index()
        if item_id not in index:
            raise HubItemNotFound(f"Item '{item_id}' not found in hub catalog.")

        recorded = HubItem.from_dict(index[item_id])
        dest = self._hub_dir / item_id
        if not dest.exists():
            return {
                "id": item_id,
                "ok": False,
                "reason": "installed_files_missing",
                "recorded_sha256": recorded.sha256,
            }

        files = list(dest.rglob("*"))
        file_list = [f for f in files if f.is_file()]
        if len(file_list) == 1 and file_list[0].name != MANIFEST_FILENAME:
            actual = compute_file_sha256(file_list[0])
        else:
            actual = compute_dir_sha256(dest)

        match = actual == recorded.sha256
        return {
            "id": item_id,
            "ok": match,
            "recorded_sha256": recorded.sha256,
            "computed_sha256": actual,
            "reason": None if match else "checksum_mismatch",
        }

    def get(self, item_id: str) -> HubItem:
        index = self._load_index()
        if item_id not in index:
            raise HubItemNotFound(f"Item '{item_id}' not found in hub catalog.")
        return HubItem.from_dict(index[item_id])


def default_hub_dir(workspace: Optional[Path] = None) -> Path:
    if workspace:
        return workspace / HUB_DIR_NAME
    home = Path.home()
    return home / ".arc" / "hub"


def create_catalog(workspace: Optional[Path] = None) -> HubCatalog:
    return HubCatalog(default_hub_dir(workspace))


__all__ = [
    "HubCatalog",
    "HubError",
    "HubItem",
    "HubItemNotFound",
    "HubInvalidType",
    "HubChecksumMismatch",
    "VALID_ITEM_TYPES",
    "compute_file_sha256",
    "compute_dir_sha256",
    "load_hub_item",
    "create_catalog",
    "default_hub_dir",
]
