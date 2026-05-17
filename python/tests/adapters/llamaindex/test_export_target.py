from __future__ import annotations

import os
from unittest import mock

from agent_runtime_cockpit.adapters.llamaindex import EXPORT_ENV, LlamaIndexAdapter


def test_reports_missing_dependency_with_export_env_ref(tmp_path):
    adapter = LlamaIndexAdapter()

    with (
        mock.patch.dict(os.environ, {}, clear=True),
        mock.patch("importlib.util.find_spec", return_value=None),
    ):
        report = adapter.capability_report(tmp_path)

    assert report.can_run is False
    assert report.availability == "missing_dependency"
    assert report.required_env == [EXPORT_ENV]
    assert report.doctor_actions[0].command == "pip install llama-index"


def test_reports_missing_export_target_without_raw_secret(tmp_path):
    adapter = LlamaIndexAdapter()
    fake_module = mock.Mock(__version__="1.2.3")

    with (
        mock.patch.dict(os.environ, {"LLAMA_INDEX_API_KEY": "raw-secret-value"}, clear=True),
        mock.patch("importlib.util.find_spec", return_value=mock.Mock()),
        mock.patch("importlib.import_module", return_value=fake_module),
    ):
        report = adapter.capability_report(tmp_path)

    assert report.can_run is False
    assert report.availability == "missing_export_target"
    assert EXPORT_ENV in report.reason
    assert report.required_env == [EXPORT_ENV]
    assert report.version == "1.2.3"
    assert report.doctor_actions[0].id == "set-llamaindex-export"
    assert EXPORT_ENV in report.doctor_actions[0].command
    serialized = report.model_dump_json()
    assert "raw-secret-value" not in serialized
    assert "LLAMA_INDEX_API_KEY" not in serialized


def test_export_configured_still_not_runnable(tmp_path):
    adapter = LlamaIndexAdapter()
    fake_module = mock.Mock(__version__="1.2.3")

    with (
        mock.patch.dict(os.environ, {EXPORT_ENV: "secret_module:secret_attr"}, clear=True),
        mock.patch("importlib.util.find_spec", return_value=mock.Mock()),
        mock.patch("importlib.import_module", return_value=fake_module),
    ):
        report = adapter.capability_report(tmp_path)

    assert report.can_run is False
    assert report.availability == "detected_not_runnable"
    assert "does not expose a runnable path" in report.reason
    assert "secret_module:secret_attr" not in report.model_dump_json()


def test_preserves_static_export_workflow(tmp_path):
    adapter = LlamaIndexAdapter()
    (tmp_path / "index.py").write_text("from llama_index import VectorStoreIndex\n")

    with mock.patch("importlib.util.find_spec", return_value=None):
        workflows = adapter.export_workflow(tmp_path)

    assert len(workflows) == 1
    assert workflows[0].runtime == "llamaindex"
