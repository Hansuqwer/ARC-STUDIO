"""Local Capability Card registry.

Stores Capability Cards under:
- <workspace>/.arc/capabilities/cards/ (workspace-local)
- ~/.arc/capabilities/cards/ (global/shared)

All operations are read-only and local; no network calls are made here.
Cards are stored as JSON files named by their card_hash (first 16 chars + id).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


from .hashing import card_hash
from .models import CapabilityCard


class CardRegistry:
    """Persist and compare Capability Cards locally.

    Storage layout:
        .arc/capabilities/cards/
            <card_hash[:16]>_<card_id>.json

    Each card file contains the serialized CapabilityCard with its computed hash.
    """

    DEFAULT_SUBDIR = Path(".arc/capabilities/cards")

    def __init__(self, workspace: Optional[Path] = None, global_only: bool = False) -> None:
        """Initialize the registry.

        Args:
            workspace: Workspace root for workspace-local storage.
                       If None, uses only global storage (~/.arc/capabilities/cards/).
            global_only: If True, only use global storage even if workspace is provided.
        """
        if global_only or workspace is None:
            self._workspace_root: Optional[Path] = None
            self._global_root = Path.home() / ".arc" / "capabilities" / "cards"
            self._global_root.mkdir(parents=True, exist_ok=True)
        else:
            self._workspace_root = workspace.resolve()
            self._global_root = Path.home() / ".arc" / "capabilities" / "cards"
            self._global_root.mkdir(parents=True, exist_ok=True)

    @property
    def storage_root(self) -> Path:
        """Return the primary storage path (workspace-local or global)."""
        if self._workspace_root:
            ws_root = self._workspace_root / self.DEFAULT_SUBDIR
            ws_root.mkdir(parents=True, exist_ok=True)
            return ws_root
        return self._global_root

    def _card_path(self, card: CapabilityCard) -> Path:
        """Compute the storage path for a card."""
        hash_prefix = card_hash(card)[:16]
        safe_id = card.id.replace("/", "_").replace("..", "_")
        return self.storage_root / f"{hash_prefix}_{safe_id}.json"

    def save(self, card: CapabilityCard) -> Path:
        """Save a CapabilityCard to the registry.

        Computes the card_hash, redacts secrets, and writes to disk.
        """
        # Compute hash before saving
        card.card_hash = card_hash(card)

        path = self._card_path(card)

        # Redact secrets before writing
        from .redaction import redact_card

        redacted = redact_card(card)
        if hasattr(redacted, "model_dump_json"):
            content = redacted.model_dump_json(indent=2)
        else:
            content = json.dumps(redacted, indent=2, default=str)

        path.write_text(content, encoding="utf-8")
        return path

    def load(self, card_id: str, hash_prefix: Optional[str] = None) -> Optional[CapabilityCard]:
        """Load a CapabilityCard by ID and optional hash prefix.

        Args:
            card_id: The card's id field.
            hash_prefix: Optional first 16 chars of card_hash for disambiguation.

        Returns:
            The CapabilityCard if found, None otherwise.
        """
        # Try to find the card file
        if hash_prefix:
            # Direct lookup by hash prefix + id
            safe_id = card_id.replace("/", "_").replace("..", "_")
            path = self.storage_root / f"{hash_prefix}_{safe_id}.json"
            if path.exists():
                return self._load_card(path)

        # Search by ID
        safe_id = card_id.replace("/", "_").replace("..", "_")
        for path in self.storage_root.glob(f"*_{safe_id}.json"):
            return self._load_card(path)

        # Try global storage if workspace-local didn't find it
        if self._workspace_root:
            for path in self._global_root.glob(f"*_{safe_id}.json"):
                return self._load_card(path)

        return None

    def _load_card(self, path: Path) -> Optional[CapabilityCard]:
        """Load a card from a path."""
        try:
            text = path.read_text(encoding="utf-8")
            card_dict = json.loads(text)
            return CapabilityCard.model_validate(card_dict)
        except Exception:
            return None

    def list_cards(self, entity_type: Optional[str] = None) -> list[CapabilityCard]:
        """List all cards in the registry.

        Args:
            entity_type: Optional filter by entity_type (e.g. "ir_node", "mcp_tool").

        Returns:
            List of CapabilityCard instances.
        """
        cards: list[CapabilityCard] = []
        seen_ids: set[str] = set()

        for root in (self.storage_root, self._global_root):
            if root == self.storage_root or self._workspace_root:
                # Skip duplicate check for global root if same as storage root
                for path in sorted(root.glob("*.json")):
                    try:
                        text = path.read_text(encoding="utf-8")
                        card_dict = json.loads(text)
                        card = CapabilityCard.model_validate(card_dict)

                        # Skip duplicates (prefer workspace-local)
                        if card.id in seen_ids:
                            continue
                        seen_ids.add(card.id)

                        if entity_type is None or card.entity_type.value == entity_type:
                            cards.append(card)
                    except Exception:
                        continue

        return cards

    def delete(self, card_id: str, hash_prefix: Optional[str] = None) -> bool:
        """Delete a card from the registry.

        Returns True if deleted, False if not found.
        """
        card = self.load(card_id, hash_prefix)
        if card is None:
            return False

        path = self._card_path(card)
        if path.exists():
            path.unlink()
            return True
        return False

    def check_drift(self, card: CapabilityCard) -> dict[str, Any]:
        """Check if a card has drifted from the registry version.

        Returns a drift report with 'drifted', 'stored_hash', 'current_hash', etc.
        """
        stored = self.load(card.id)
        current_hash = card_hash(card)

        if stored is None:
            return {
                "drifted": False,
                "stored": False,
                "current_hash": current_hash,
                "message": "No card in registry; run 'arc capabilities save' to record.",
            }

        stored_hash = stored.card_hash or ""
        return {
            "drifted": stored_hash != current_hash,
            "stored": True,
            "stored_hash": stored_hash,
            "current_hash": current_hash,
            "message": "Card drift detected."
            if stored_hash != current_hash
            else "Card matches registry.",
        }

    def resolve_path(self, card_id: str, hash_prefix: Optional[str] = None) -> Optional[Path]:
        """Resolve the file path for a card without loading it."""
        safe_id = card_id.replace("/", "_").replace("..", "_")

        if hash_prefix:
            path = self.storage_root / f"{hash_prefix}_{safe_id}.json"
            if path.exists():
                return path

        for path in self.storage_root.glob(f"*_{safe_id}.json"):
            return path

        if self._workspace_root:
            for path in self._global_root.glob(f"*_{safe_id}.json"):
                return path

        return None


def create_registry(workspace: Optional[Path] = None) -> CardRegistry:
    """Factory function to create a CardRegistry.

    This is the recommended way to create registries as the API may evolve.
    """
    return CardRegistry(workspace=workspace)
