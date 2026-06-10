"""ARC Voice — local voice-to-command interface (R96).

Local speech-to-text (Whisper-class, on-device) feeding the existing
chat/command pipeline. Hands-free, no cloud transcription.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)


class VoiceError(Exception):
    """Raised when voice operations fail (driver unavailable, transcription error, etc.)."""


class VoiceState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    NO_MODEL = "no_model"


@dataclass
class TranscriptionResult:
    text: str
    confidence: float = 0.0
    language: str = "en"
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model: str = "unknown"
    is_final: bool = True


class VoiceDriver(ABC):
    """Abstract base class for speech-to-text drivers."""

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        pass

    @abstractmethod
    def get_state(self) -> VoiceState:
        pass

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        pass


class FakeVoiceDriver(VoiceDriver):
    """Fake driver for testing — no audio hardware, no model downloads."""

    def __init__(self, fixture_transcripts: Optional[dict[str, str]] = None) -> None:
        self._fixture_transcripts = fixture_transcripts or {}
        self._state = VoiceState.READY
        self._transcription_count = 0

    @property
    def transcription_count(self) -> int:
        return self._transcription_count

    def is_available(self) -> bool:
        return True

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        self._transcription_count += 1
        filename = audio_path.name
        if filename in self._fixture_transcripts:
            text = self._fixture_transcripts[filename]
        else:
            text = f"transcribed: {filename}"

        return TranscriptionResult(
            text=text,
            confidence=0.95,
            language="en",
            duration_ms=1000.0,
            model="fake-stt",
        )

    def get_state(self) -> VoiceState:
        return self._state

    def get_model_info(self) -> dict[str, Any]:
        return {
            "model": "fake-stt",
            "available": True,
            "language": "en",
            "description": "Fake STT driver for testing",
        }

    def set_state(self, state: VoiceState) -> None:
        self._state = state


class WhisperVoiceDriver(VoiceDriver):
    """Whisper-based driver — requires whisper optional dependency.

    Local on-device STT only. No cloud transcription.
    """

    def __init__(self, model_name: str = "base") -> None:
        self._model_name = model_name
        self._model = None
        self._state = VoiceState.NO_MODEL

    def _ensure_model(self) -> bool:
        if self._model is not None:
            return True
        try:
            import whisper

            self._model = whisper.load_model(self._model_name)
            self._state = VoiceState.READY
            return True
        except ImportError:
            self._state = VoiceState.NO_MODEL
            log.warning("Whisper not installed. Install with: pip install 'arc-studio[voice]'")
            return False
        except Exception as e:
            self._state = VoiceState.ERROR
            log.error("Failed to load Whisper model: %s", e)
            return False

    def is_available(self) -> bool:
        return self._ensure_model()

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        if not self._ensure_model():
            return TranscriptionResult(
                text="",
                confidence=0.0,
                model=self._model_name,
                is_final=False,
            )

        try:
            self._state = VoiceState.PROCESSING
            result = self._model.transcribe(str(audio_path))
            self._state = VoiceState.READY

            text = result.get("text", "").strip()
            language = result.get("language", "en")
            segments = result.get("segments", [])
            confidence = sum(s.get("avg_logprob", 0) for s in segments) / max(len(segments), 1)

            return TranscriptionResult(
                text=text,
                confidence=confidence,
                language=language,
                model=self._model_name,
            )
        except Exception as e:
            self._state = VoiceState.ERROR
            log.error("Whisper transcription failed: %s", e)
            return TranscriptionResult(
                text="",
                confidence=0.0,
                model=self._model_name,
                is_final=False,
            )

    def get_state(self) -> VoiceState:
        return self._state

    def get_model_info(self) -> dict[str, Any]:
        return {
            "model": self._model_name,
            "available": self._ensure_model(),
            "state": self._state.value,
            "description": "Whisper on-device STT",
        }


class VoicePipeline:
    """Integrates voice transcription with the existing chat/command pipeline."""

    def __init__(self, driver: VoiceDriver) -> None:
        self._driver = driver
        self._history: list[TranscriptionResult] = []

    @property
    def driver(self) -> VoiceDriver:
        return self._driver

    @property
    def history(self) -> list[TranscriptionResult]:
        return self._history

    def is_available(self) -> bool:
        return self._driver.is_available()

    def get_state(self) -> VoiceState:
        return self._driver.get_state()

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        result = self._driver.transcribe(audio_path)
        if result.text:
            self._history.append(result)
        return result

    def transcribe_and_dispatch(self, audio_path: Path) -> dict[str, Any]:
        """Transcribe audio and prepare for pipeline dispatch.

        Returns a dict with the transcription and suggested command type.
        """
        result = self.transcribe(audio_path)
        text = result.text.strip()

        command_type = "chat"
        if text.startswith("/"):
            command_type = "slash"
        elif text.startswith("arc "):
            command_type = "cli"

        return {
            "transcription": result.text,
            "confidence": result.confidence,
            "command_type": command_type,
            "timestamp": result.timestamp,
            "model": result.model,
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "driver_available": self._driver.is_available(),
            "state": self._driver.get_state().value,
            "model_info": self._driver.get_model_info(),
            "transcription_count": len(self._history),
            "history": [
                {
                    "text": r.text,
                    "confidence": r.confidence,
                    "timestamp": r.timestamp,
                }
                for r in self._history[-10:]
            ],
        }


def create_voice_pipeline(
    driver_type: str = "fake",
    model_name: str = "base",
    fixture_transcripts: Optional[dict[str, str]] = None,
) -> VoicePipeline:
    """Factory for creating voice pipelines.

    Args:
        driver_type: "fake" for testing, "whisper" for real STT.
        model_name: Whisper model name (tiny, base, small, medium, large).
        fixture_transcripts: Dict mapping audio filenames to expected transcripts (fake only).

    Returns:
        A VoicePipeline instance.
    """
    if driver_type == "whisper":
        driver = WhisperVoiceDriver(model_name=model_name)
    else:
        driver = FakeVoiceDriver(fixture_transcripts=fixture_transcripts)
    return VoicePipeline(driver)


__all__ = [
    "VoiceError",
    "VoiceState",
    "TranscriptionResult",
    "VoiceDriver",
    "FakeVoiceDriver",
    "WhisperVoiceDriver",
    "VoicePipeline",
    "create_voice_pipeline",
]
