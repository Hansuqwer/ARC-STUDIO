"""Tests for ARC Voice — local voice-to-command interface (R96, Phase 321)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_runtime_cockpit.voice import (
    FakeVoiceDriver,
    TranscriptionResult,
    VoicePipeline,
    VoiceState,
    create_voice_pipeline,
)


@pytest.fixture
def fake_driver() -> FakeVoiceDriver:
    return FakeVoiceDriver(
        fixture_transcripts={
            "hello.wav": "hello world",
            "command.wav": "/help",
            "arc_cmd.wav": "arc run workflow",
        }
    )


@pytest.fixture
def pipeline(fake_driver: FakeVoiceDriver) -> VoicePipeline:
    return VoicePipeline(fake_driver)


@pytest.fixture
def sample_audio(tmp_path: Path) -> Path:
    audio = tmp_path / "hello.wav"
    audio.write_bytes(b"FAKE_WAV_DATA")
    return audio


class TestFakeVoiceDriver:
    def test_is_available(self, fake_driver: FakeVoiceDriver) -> None:
        assert fake_driver.is_available() is True

    def test_transcribe_fixture(self, fake_driver: FakeVoiceDriver, tmp_path: Path) -> None:
        audio = tmp_path / "hello.wav"
        audio.write_bytes(b"FAKE_WAV_DATA")
        result = fake_driver.transcribe(audio)
        assert result.text == "hello world"
        assert result.confidence == 0.95
        assert result.model == "fake-stt"

    def test_transcribe_unknown_file(self, fake_driver: FakeVoiceDriver, tmp_path: Path) -> None:
        audio = tmp_path / "unknown.wav"
        audio.write_bytes(b"FAKE_WAV_DATA")
        result = fake_driver.transcribe(audio)
        assert "transcribed" in result.text
        assert "unknown.wav" in result.text

    def test_get_state(self, fake_driver: FakeVoiceDriver) -> None:
        assert fake_driver.get_state() == VoiceState.READY

    def test_set_state(self, fake_driver: FakeVoiceDriver) -> None:
        fake_driver.set_state(VoiceState.LISTENING)
        assert fake_driver.get_state() == VoiceState.LISTENING

    def test_get_model_info(self, fake_driver: FakeVoiceDriver) -> None:
        info = fake_driver.get_model_info()
        assert info["model"] == "fake-stt"
        assert info["available"] is True

    def test_transcription_count(self, fake_driver: FakeVoiceDriver, tmp_path: Path) -> None:
        audio = tmp_path / "test.wav"
        audio.write_bytes(b"FAKE_WAV_DATA")
        assert fake_driver.transcription_count == 0
        fake_driver.transcribe(audio)
        assert fake_driver.transcription_count == 1
        fake_driver.transcribe(audio)
        assert fake_driver.transcription_count == 2


class TestVoicePipeline:
    def test_is_available(self, pipeline: VoicePipeline) -> None:
        assert pipeline.is_available() is True

    def test_get_state(self, pipeline: VoicePipeline) -> None:
        assert pipeline.get_state() == VoiceState.READY

    def test_transcribe(self, pipeline: VoicePipeline, sample_audio: Path) -> None:
        result = pipeline.transcribe(sample_audio)
        assert result.text == "hello world"
        assert len(pipeline.history) == 1

    def test_transcribe_and_dispatch_chat(
        self, pipeline: VoicePipeline, sample_audio: Path
    ) -> None:
        result = pipeline.transcribe_and_dispatch(sample_audio)
        assert result["transcription"] == "hello world"
        assert result["command_type"] == "chat"

    def test_transcribe_and_dispatch_slash(self, pipeline: VoicePipeline, tmp_path: Path) -> None:
        audio = tmp_path / "command.wav"
        audio.write_bytes(b"FAKE_WAV_DATA")
        result = pipeline.transcribe_and_dispatch(audio)
        assert result["transcription"] == "/help"
        assert result["command_type"] == "slash"

    def test_transcribe_and_dispatch_cli(self, pipeline: VoicePipeline, tmp_path: Path) -> None:
        audio = tmp_path / "arc_cmd.wav"
        audio.write_bytes(b"FAKE_WAV_DATA")
        result = pipeline.transcribe_and_dispatch(audio)
        assert result["transcription"] == "arc run workflow"
        assert result["command_type"] == "cli"

    def test_history(self, pipeline: VoicePipeline, sample_audio: Path) -> None:
        pipeline.transcribe(sample_audio)
        pipeline.transcribe(sample_audio)
        assert len(pipeline.history) == 2

    def test_get_stats(self, pipeline: VoicePipeline, sample_audio: Path) -> None:
        pipeline.transcribe(sample_audio)
        stats = pipeline.get_stats()
        assert stats["driver_available"] is True
        assert stats["state"] == "ready"
        assert stats["transcription_count"] == 1
        assert len(stats["history"]) == 1


class TestCreateVoicePipeline:
    def test_create_fake_pipeline(self) -> None:
        pipeline = create_voice_pipeline(driver_type="fake")
        assert pipeline.is_available() is True

    def test_create_whisper_pipeline_without_dependency(self) -> None:
        pipeline = create_voice_pipeline(driver_type="whisper")
        assert isinstance(pipeline, VoicePipeline)

    def test_create_with_fixtures(self) -> None:
        pipeline = create_voice_pipeline(
            driver_type="fake",
            fixture_transcripts={"test.wav": "test transcript"},
        )
        assert pipeline.is_available() is True


class TestTranscriptionResult:
    def test_create_result(self) -> None:
        result = TranscriptionResult(
            text="hello",
            confidence=0.9,
            language="en",
            model="test",
        )
        assert result.text == "hello"
        assert result.confidence == 0.9
        assert result.is_final is True


class TestVoiceCLI:
    def test_voice_help(self) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["voice", "--help"])
        assert result.exit_code == 0
        assert "voice" in result.output.lower()

    def test_voice_status(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(
            app, ["voice", "status", "--driver", "fake", "--json", "-w", str(tmp_path)]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["driver_available"] is True
        assert data["data"]["state"] == "ready"

    def test_voice_transcribe(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        audio = tmp_path / "test.wav"
        audio.write_bytes(b"FAKE_WAV_DATA")

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "voice",
                "transcribe",
                str(audio),
                "--driver",
                "fake",
                "--json",
                "-w",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert "transcription" in data["data"]

    def test_voice_transcribe_missing_file(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "voice",
                "transcribe",
                str(tmp_path / "nonexistent.wav"),
                "--driver",
                "fake",
                "--json",
                "-w",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["ok"] is False

    def test_voice_listen_placeholder(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(
            app, ["voice", "listen", "--driver", "fake", "--json", "-w", str(tmp_path)]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert "not yet implemented" in data["data"]["message"]


class TestVoiceError:
    """Phase 338 DoD elevation: structured error class + degraded-state coverage."""

    def test_voice_error_is_exception(self) -> None:
        from agent_runtime_cockpit.voice import VoiceError

        assert issubclass(VoiceError, Exception)
        err = VoiceError("test message")
        assert str(err) == "test message"

    def test_voice_error_in_all(self) -> None:
        import agent_runtime_cockpit.voice as voice_mod

        assert "VoiceError" in voice_mod.__all__

    def test_whisper_degraded_when_unavailable(self, tmp_path: Path) -> None:
        """Whisper driver without model installed returns degraded result, not raise."""
        from agent_runtime_cockpit.voice import WhisperVoiceDriver

        driver = WhisperVoiceDriver(model_name="nonexistent")
        result = driver.transcribe(tmp_path / "audio.wav")
        assert result.is_final is False
        assert result.text == ""
        assert result.confidence == 0.0

    def test_voice_status_json_envelope(self) -> None:
        """Verify voice status --json output schema is stable."""
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["voice", "status", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert "data" in data
