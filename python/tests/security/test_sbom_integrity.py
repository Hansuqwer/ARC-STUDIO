from __future__ import annotations

import subprocess
from pathlib import Path


def test_sbom_help_lists_strict():
    result = subprocess.run(
        [
            "bash",
            str(Path(__file__).resolve().parents[3] / "scripts/check-sbom-integrity.sh"),
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--strict" in result.stdout
