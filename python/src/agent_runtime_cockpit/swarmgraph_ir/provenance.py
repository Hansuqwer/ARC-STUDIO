"""Adapter provenance builders for SwarmGraph IR.

Records *where* a graph came from (adapter id, runtime, source file) without
leaking absolute filesystem paths.
"""

from __future__ import annotations

import os
from typing import Optional

from .models import IRAdapterProvenance


def _relativize(source_file: Optional[str], workspace: Optional[str]) -> Optional[str]:
    """Make an absolute source path relative to the workspace when possible.

    Absolute paths outside the workspace are reduced to their basename so we never
    persist host-specific absolute paths in the IR.
    """
    if not source_file:
        return None
    if not os.path.isabs(source_file):
        return source_file
    if workspace:
        try:
            return os.path.relpath(source_file, workspace)
        except ValueError:
            pass
    return os.path.basename(source_file)


def build_provenance(
    *,
    adapter_id: str,
    runtime: str,
    source_file: Optional[str] = None,
    adapter_version: Optional[str] = None,
    workspace: Optional[str] = None,
    exported_via: str = "export_workflow",
) -> IRAdapterProvenance:
    return IRAdapterProvenance(
        adapter_id=adapter_id,
        runtime=runtime,
        adapter_version=adapter_version,
        source_file=_relativize(source_file, workspace),
        exported_via=exported_via,
    )
