"""Feature flags + remote kill switch for ARC Mobile Runtime (Phase 12).

Deterministic, **default-OFF** flag store. Unknown flags are disabled. A global kill switch
overrides everything to OFF (the remote kill switch). Optional durable persistence. No
network, no LLM — purely local state used by gated paths (e.g. the Phase 11 capability gate).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FeatureFlags:
    """Default-off feature-flag store with a global kill switch."""

    def __init__(
        self,
        flags: dict[str, bool] | None = None,
        kill_switch: bool = False,
        path: Path | None = None,
    ) -> None:
        self._flags: dict[str, bool] = {k: bool(v) for k, v in (flags or {}).items()}
        self._kill_switch = bool(kill_switch)
        self._path = Path(path) if path else None
        if self._path and self._path.exists():
            self._load()

    @property
    def kill_switch(self) -> bool:
        return self._kill_switch

    def is_enabled(self, name: str) -> bool:
        """A flag is enabled only if the kill switch is OFF and the flag is explicitly True."""
        if self._kill_switch:
            return False
        return self._flags.get(name, False)

    def enable(self, name: str) -> None:
        self._flags[name] = True
        self._persist()

    def disable(self, name: str) -> None:
        self._flags[name] = False
        self._persist()

    def set_kill_switch(self, on: bool) -> None:
        """Engage/disengage the global kill switch (overrides all flags to OFF when on)."""
        self._kill_switch = bool(on)
        self._persist()

    def snapshot(self) -> dict[str, Any]:
        return {
            "kill_switch": self._kill_switch,
            "flags": dict(sorted(self._flags.items())),
            # effective state reflects the kill switch override
            "effective": {k: self.is_enabled(k) for k in sorted(self._flags)},
        }

    def _persist(self) -> None:
        if not self._path:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({"kill_switch": self._kill_switch, "flags": self._flags}, sort_keys=True),
            encoding="utf-8",
        )

    def _load(self) -> None:
        assert self._path is not None
        data = json.loads(self._path.read_text(encoding="utf-8"))
        self._kill_switch = bool(data.get("kill_switch", False))
        self._flags = {k: bool(v) for k, v in data.get("flags", {}).items()}
