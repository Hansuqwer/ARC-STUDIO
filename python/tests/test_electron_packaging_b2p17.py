"""B2P-17: Electron app shell + daemon lifecycle + signed/auto-update packaging (structure guard).

The Electron desktop app is post-v0.1 (browser stays the canonical release target). This guard
locks the shell/lifecycle/signing/auto-update assets so they don't silently regress; the full
`theia build` + `electron-builder` packaging is exercised in CI (signing-preflight workflow).
"""

from __future__ import annotations

from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve()
for _ in range(8):
    _ROOT = _ROOT.parent
    if (_ROOT / "applications" / "electron").is_dir():
        break
_ELECTRON = _ROOT / "applications" / "electron"


@pytest.mark.skipif(not _ELECTRON.is_dir(), reason="electron app not present")
def test_daemon_manager_has_lifecycle() -> None:
    src = (_ELECTRON / "src" / "daemon-manager.ts").read_text(encoding="utf-8")
    assert "class DaemonManager" in src
    assert "async start(" in src
    assert "spawn(" in src  # manages the Python daemon process


@pytest.mark.skipif(not _ELECTRON.is_dir(), reason="electron app not present")
def test_release_packaging_is_signing_gated() -> None:
    pkg = (_ELECTRON / "package.json").read_text(encoding="utf-8")
    assert "require-electron-signing.mjs" in pkg  # release build refuses to run unsigned
    rel = (_ELECTRON / "electron-builder.release.yml").read_text(encoding="utf-8")
    assert "forceCodeSigning: true" in rel
    for target in ("mac:", "win:", "linux:"):
        assert target in rel


@pytest.mark.skipif(not _ELECTRON.is_dir(), reason="electron app not present")
def test_auto_update_feed_configured() -> None:
    rel = (_ELECTRON / "electron-builder.release.yml").read_text(encoding="utf-8")
    assert "publish:" in rel
    assert "provider: github" in rel
