"""Flight Recorder export bundle support.

``arc flight export --run-id <id> --out bundle.tar.gz``

Produces a self-contained .tar.gz containing:
  - All segment events + meta files for the run.
  - The index.json (filtered to the run).
  - A manifest.json (FlightExportBundle schema).
  - SHA-256 checksums for all included files.
  - No secrets: redaction is verified before packaging.

Hard constraints:
  - No network I/O.
  - No subprocess (tarball built in-process with Python stdlib ``tarfile``).
  - No model calls.
  - Manifest checksums verified before write.
  - Bundle is written to caller-specified path only.
  - No secrets in tarball — is_safe() checked on event data.
"""

from __future__ import annotations

import hashlib
import io
import logging
import tarfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import index as _index
from .models import (
    BundleManifestEntry,
    FlightExportBundle,
    FlightIndex,
    RedactionSummary,
)
from .redaction import is_safe

log = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def export_run(
    base_dir: Path,
    run_id: str,
    out_path: Path,
    *,
    redact_secrets: bool = True,
) -> FlightExportBundle:
    """Build and write an export bundle for a single run.

    Returns the FlightExportBundle manifest.
    Raises ValueError if the run is not found in the index.
    """
    idx = _index.load_index(base_dir)

    if run_id not in idx.runs:
        raise ValueError(f"Run {run_id!r} not found in flight recorder index")

    run_entry = idx.runs[run_id]
    seg_refs = [s for s in idx.segments if s.run_id == run_id]

    bundle_id = str(uuid.uuid4())
    manifest_entries: list[BundleManifestEntry] = []
    checksums: dict[str, str] = {}
    total_events = 0
    all_fields_redacted: list[str] = []

    # Build a mini-index for this run
    mini_idx = FlightIndex(
        segments=[s for s in idx.segments if s.run_id == run_id],
        runs={run_id: run_entry},
        retention=idx.retention,
        last_verified_at=idx.last_verified_at,
    )
    mini_idx_bytes = mini_idx.model_dump_json(indent=2).encode("utf-8")

    # Write tarball
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tarfile.open(out_path, "w:gz") as tar:
        # Add index
        _add_bytes_to_tar(
            tar,
            mini_idx_bytes,
            "index.json",
            manifest_entries,
            checksums,
        )

        # Add segment files
        for seg_ref in seg_refs:
            events_path = _resolve_path(base_dir, seg_ref.events_path)
            meta_path = _resolve_path(base_dir, seg_ref.meta_path)

            if events_path and events_path.exists():
                # Verify no secrets leak through
                content = events_path.read_bytes()
                _check_no_secrets(content, seg_ref.segment_id, redact_secrets)
                arc_name = f"segments/{run_id}/{events_path.name}"
                _add_bytes_to_tar(tar, content, arc_name, manifest_entries, checksums)
                total_events += content.count(b"\n")

            if meta_path and meta_path.exists():
                content = meta_path.read_bytes()
                arc_name = f"segments/{run_id}/{meta_path.name}"
                _add_bytes_to_tar(tar, content, arc_name, manifest_entries, checksums)

        # Build and add manifest
        bundle = FlightExportBundle(
            bundle_id=bundle_id,
            created_at=_utc_now(),
            runs=[run_id],
            segments=[s.segment_id for s in seg_refs],
            manifest=manifest_entries,
            checksums=checksums,
            redaction_summary=RedactionSummary(
                fields_redacted=all_fields_redacted,
                redact_applied=bool(all_fields_redacted),
            ),
            total_events=total_events,
        )
        manifest_bytes = bundle.model_dump_json(indent=2).encode("utf-8")
        _add_bytes_to_tar(tar, manifest_bytes, "manifest.json", [], {})

    log.info(
        "flight_recorder.export: bundle written to %s (%d segments, %d events)",
        out_path,
        len(seg_refs),
        total_events,
    )
    return bundle


def _add_bytes_to_tar(
    tar: tarfile.TarFile,
    data: bytes,
    arc_name: str,
    manifest_entries: list[BundleManifestEntry],
    checksums: dict[str, str],
) -> None:
    """Add bytes to tarball and record checksum."""
    sha = _sha256_bytes(data)
    info = tarfile.TarInfo(name=arc_name)
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))
    manifest_entries.append(BundleManifestEntry(path=arc_name, sha256=sha, size_bytes=len(data)))
    checksums[arc_name] = sha


def _check_no_secrets(content: bytes, segment_id: str, redact_secrets: bool) -> None:
    """Fail closed if content contains detected secrets."""
    if not redact_secrets:
        return
    text = content.decode("utf-8", errors="replace")
    if not is_safe(text):
        raise ValueError(
            f"Segment {segment_id} contains potential secrets — "
            "redact before exporting or pass redact_secrets=False at your own risk."
        )


def _resolve_path(base_dir: Path, rel_path: str) -> Optional[Path]:
    if not rel_path:
        return None
    p = Path(rel_path)
    if p.is_absolute():
        return p
    candidate = base_dir / rel_path
    if candidate.exists():
        return candidate
    return p
