"""Management commands aggregator (Phase 25; split into mgmt_* modules per CR-026).

Importing this module triggers Typer command registration for the doctor, eval, hitl,
isolation, storage, and config sub-apps via the submodule imports below (decorators run on
import). Kept as the single import point so cli/__init__.py registration is unchanged.
"""

from __future__ import annotations

from . import (  # noqa: F401  -- imported for Typer command-registration side effects
    mgmt_config,
    mgmt_doctor,
    mgmt_eval,
    mgmt_hitl,
    mgmt_isolation,
    mgmt_storage,
)
