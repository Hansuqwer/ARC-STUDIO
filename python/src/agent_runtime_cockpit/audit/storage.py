"""Managed audit chain storage — one HMAC-signed JSONL file per run.

Wraps ``HmacAuditChainWriter`` and ``key_manager`` to provide per-run
audit chain lifecycle: create on run start, append events during run,
verify and export after completion.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Optional

from .hmac_chain import HmacAuditChainWriter, verify_hmac_chain
from .key_manager import AuditKeyManager
from .schema import AuditEvent

AUDIT_DIR = Path.home() / ".arc" / "audit"


class AuditChainStore:
    """Manages per-run HMAC-signed audit chains.

    Usage::

        store = AuditChainStore()
        store.ensure_run("run_abc123")
        store.append_event(event)
        ok, msg = store.verify_run("run_abc123")
        bundle = store.export_run("run_abc123")
    """

    def __init__(
        self,
        audit_dir: Path = AUDIT_DIR,
        key_manager: Optional[AuditKeyManager] = None,
    ) -> None:
        self.audit_dir = audit_dir
        self.key_manager = key_manager or AuditKeyManager()
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def _chain_path(self, run_id: str) -> Path:
        return self.audit_dir / f"{run_id}.audit.jsonl"

    def _writer(self, run_id: str) -> HmacAuditChainWriter:
        return HmacAuditChainWriter(self._chain_path(run_id), self.key_manager)

    def ensure_run(self, run_id: str) -> None:
        """Ensure the audit chain file exists for a run.

        Creates an empty file if it doesn't exist. Idempotent.
        """
        path = self._chain_path(run_id)
        if not path.exists():
            path.touch()

    def append_event(self, event: AuditEvent) -> Optional[dict[str, Any]]:
        """Append a typed audit event to its run's chain.

        Returns the signed record dict, or None if no HMAC key is available.
        """
        writer = self._writer(event.run_id)
        return writer.append(event.to_audit_event())

    def verify_run(self, run_id: str) -> tuple[bool, str]:
        """Verify HMAC chain integrity for a run.

        Returns (ok, message). Requires the HMAC key to be available.
        """
        key, status = self.key_manager.get_key()
        if key is None:
            return False, "No audit key available. Run 'arc audit key init'."
        return verify_hmac_chain(self._chain_path(run_id), key)

    def export_run(
        self, run_id: str, output_path: Optional[Path] = None
    ) -> Optional[Path]:
        """Export a signed audit bundle for a run.

        The bundle includes all events plus verification metadata.
        If *output_path* is None, writes to a temp file.
        Returns the output path, or None if verification fails.
        """
        ok, msg = self.verify_run(run_id)
        if not ok:
            return None
        path = self._chain_path(run_id)
        events = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
        bundle = {
            "version": "1",
            "run_id": run_id,
            "exported_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            "events": events,
            "verification": {
                "verified": True,
                "event_count": len(events),
                "message": msg,
            },
        }
        if output_path:
            out = output_path
        else:
            fd = tempfile.NamedTemporaryFile(
                mode='w',
                suffix=f".{run_id}.audit.bundle.json",
                delete=False
            )
            out = Path(fd.name)
            fd.close()
        out.write_text(
            json.dumps(bundle, sort_keys=True, separators=(",", ":"))
            + "\n"
        )
        return out

    def delete_run(self, run_id: str) -> bool:
        """Delete the audit chain for a run. Returns True if deleted."""
        path = self._chain_path(run_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_runs(self) -> list[str]:
        """List all run IDs with audit chains."""
        run_ids = []
        for f in self.audit_dir.glob("*.audit.jsonl"):
            run_id = f.stem.replace(".audit", "")
            run_ids.append(run_id)
        return sorted(run_ids)
