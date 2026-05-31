"""Guard that the swarmgraph-sdk release workflow stays hard-gated.

Publishing must never be automatic. These tests assert the workflow shape:
- a `publish` job exists but is conditional on an explicit dispatch input,
- the publish job runs in a protected `pypi` environment with OIDC,
- the default (non-publish) path is dry-run only.
"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

_WORKFLOW = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "swarmgraph-sdk-release.yml"
)


def _load() -> dict:
    return yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))


def test_workflow_exists() -> None:
    assert _WORKFLOW.exists()


def test_publish_job_is_conditional_on_explicit_input() -> None:
    wf = _load()
    publish = wf["jobs"]["publish"]
    condition = publish["if"]
    assert "workflow_dispatch" in condition
    assert "publish == 'true'" in condition


def test_publish_job_uses_protected_environment_and_oidc() -> None:
    wf = _load()
    publish = wf["jobs"]["publish"]
    assert publish["environment"]["name"] == "pypi"
    assert publish["permissions"]["id-token"] == "write"


def test_dry_run_is_the_default_path() -> None:
    wf = _load()
    dry = wf["jobs"]["publish-dry-run"]
    assert "publish != 'true'" in dry["if"]


def test_no_pypi_token_secret_referenced() -> None:
    # Trusted publishing only; ensure no long-lived token secret is used.
    text = _WORKFLOW.read_text(encoding="utf-8")
    assert "PYPI_TOKEN" not in text
    assert "secrets.PYPI" not in text
