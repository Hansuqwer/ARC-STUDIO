"""Linux Landlock LSM detection/preflight tests.

DETECTION ONLY — Landlock enforcement is a Linux-CI follow-up and is NOT wired
into command execution. These tests assert the preflight states and, crucially,
that ARC never claims enforcement (``enforced`` is always False). They are
monkeypatched so they run on any host (including macOS CI) without Landlock.
"""

import errno
import json

from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app
from agent_runtime_cockpit.security import sandbox as sandbox_mod
from agent_runtime_cockpit.security.sandbox import landlock_preflight


class TestLandlockPreflightStates:
    def test_unavailable_off_linux(self, monkeypatch):
        monkeypatch.setattr(sandbox_mod.platform, "system", lambda: "Darwin")
        data = landlock_preflight()
        assert data["status"] == "unavailable"
        assert data["reason"] == "Landlock requires Linux"
        assert data["enforced"] is False
        assert data["abi_version"] is None

    def test_ready_when_abi_present(self, monkeypatch):
        monkeypatch.setattr(sandbox_mod.platform, "system", lambda: "Linux")
        monkeypatch.setattr(sandbox_mod, "_landlock_abi_probe", lambda: (4, 0))
        data = landlock_preflight()
        assert data["status"] == "ready"
        assert data["abi_version"] == 4
        assert data["enforced"] is False
        assert data["enforcement_status"] == "detection_only"

    def test_blocked_when_disabled_at_boot(self, monkeypatch):
        monkeypatch.setattr(sandbox_mod.platform, "system", lambda: "Linux")
        monkeypatch.setattr(sandbox_mod, "_landlock_abi_probe", lambda: (-1, errno.EOPNOTSUPP))
        data = landlock_preflight()
        assert data["status"] == "blocked"
        assert "disabled at boot" in data["reason"]
        assert data["enforced"] is False

    def test_unavailable_on_old_kernel(self, monkeypatch):
        monkeypatch.setattr(sandbox_mod.platform, "system", lambda: "Linux")
        monkeypatch.setattr(sandbox_mod, "_landlock_abi_probe", lambda: (-1, errno.ENOSYS))
        data = landlock_preflight()
        assert data["status"] == "unavailable"
        assert "pre-5.13" in data["reason"]

    def test_probe_exception_degrades_to_unavailable(self, monkeypatch):
        def _boom() -> tuple[int, int]:
            raise OSError("no libc syscall")

        monkeypatch.setattr(sandbox_mod.platform, "system", lambda: "Linux")
        monkeypatch.setattr(sandbox_mod, "_landlock_abi_probe", _boom)
        data = landlock_preflight()
        assert data["status"] == "unavailable"
        assert "probe failed" in data["reason"]


class TestLandlockTruthConstraints:
    def test_never_claims_enforcement(self, monkeypatch):
        # Even in the most-capable (ready) state, enforcement must not be claimed.
        monkeypatch.setattr(sandbox_mod.platform, "system", lambda: "Linux")
        monkeypatch.setattr(sandbox_mod, "_landlock_abi_probe", lambda: (6, 0))
        data = landlock_preflight()
        assert data["enforced"] is False
        assert data["enforcement_status"] == "detection_only"

    def test_stable_schema(self):
        data = landlock_preflight()
        for key in ("provider", "platform", "status", "enforced", "enforcement_status"):
            assert key in data
        assert data["provider"] == "landlock"
        assert data["status"] in {"unavailable", "blocked", "ready"}


class TestLandlockDoctorWiring:
    def test_doctor_includes_landlock_provider(self):
        result = CliRunner().invoke(app, ["sandbox", "doctor", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        providers = payload["data"]["providers"]
        landlock = next((p for p in providers if p.get("provider") == "landlock"), None)
        assert landlock is not None
        assert landlock["enforced"] is False
