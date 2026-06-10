"""CLI commands for ARC Voice — local voice-to-command interface (R96).

Commands:
  arc voice transcribe    Transcribe an audio file to text.
  arc voice listen        Start listening for voice input (placeholder).
  arc voice status        Show voice pipeline status and model info.

All commands accept --json for machine-readable envelope output.
Local on-device STT only. No cloud transcription.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import JSON_FLAG, WORKSPACE_FLAG, _out, _workspace
from ._subapps import voice_app


@voice_app.command("transcribe")
def voice_transcribe(
    audio: str = typer.Argument(..., help="Path to audio file (wav, mp3, etc.)"),
    model: str = typer.Option(
        "base", "--model", "-m", help="STT model: fake, tiny, base, small, medium, large"
    ),
    driver: str = typer.Option("fake", "--driver", "-d", help="Driver: fake or whisper"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Transcribe an audio file to text (local on-device STT)."""
    from ..voice import create_voice_pipeline

    _workspace(workspace)
    pipeline = create_voice_pipeline(driver_type=driver, model_name=model)

    if not pipeline.is_available():
        _out(
            err(
                ArcErrorCode.INTERNAL_ERROR,
                f"Voice driver '{driver}' not available. Install with: pip install 'arc-studio[voice]'",
            ),
            as_json,
        )
        raise typer.Exit(1)

    audio_path = Path(audio)
    if not audio_path.exists():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Audio file not found: {audio}"), as_json)
        raise typer.Exit(1)

    result = pipeline.transcribe_and_dispatch(audio_path)
    _out(ok(result), as_json)

    if not as_json:
        from ._app import console

        console.print("\n[bold]Transcription[/bold]")
        console.print(f"  Text: {result['transcription']}")
        console.print(f"  Confidence: {result['confidence']:.2f}")
        console.print(f"  Command type: {result['command_type']}")
        console.print(f"  Model: {result['model']}")


@voice_app.command("listen")
def voice_listen(
    model: str = typer.Option("base", "--model", "-m", help="STT model"),
    driver: str = typer.Option("fake", "--driver", "-d", help="Driver: fake or whisper"),
    timeout: int = typer.Option(30, "--timeout", "-t", help="Listen timeout in seconds"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Start listening for voice input (placeholder for future real-time integration).

    This is a placeholder for future real-time voice input integration.
    Currently returns a status message indicating the feature is not yet implemented.
    """
    from ..voice import create_voice_pipeline

    _workspace(workspace)
    pipeline = create_voice_pipeline(driver_type=driver, model_name=model)

    _out(
        ok(
            {
                "driver": driver,
                "model": model,
                "timeout_seconds": timeout,
                "available": pipeline.is_available(),
                "state": pipeline.get_state().value,
                "message": "Real-time voice listening is not yet implemented. Use 'arc voice transcribe' for file-based transcription.",
            }
        ),
        as_json,
    )

    if not as_json:
        from ._app import console

        console.print("\n[yellow]Real-time voice listening is not yet implemented.[/yellow]")
        console.print("Use 'arc voice transcribe <audio-file>' for file-based transcription.")


@voice_app.command("status")
def voice_status(
    driver: str = typer.Option("fake", "--driver", "-d", help="Driver: fake or whisper"),
    model: str = typer.Option("base", "--model", "-m", help="STT model"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Show voice pipeline status and model info."""
    from ..voice import create_voice_pipeline

    _workspace(workspace)
    pipeline = create_voice_pipeline(driver_type=driver, model_name=model)
    stats = pipeline.get_stats()

    _out(ok(stats), as_json)

    if not as_json:
        from ._app import console

        console.print("\n[bold]Voice Pipeline Status[/bold]")
        console.print(f"  Driver available: {stats['driver_available']}")
        console.print(f"  State: {stats['state']}")
        console.print(f"  Transcriptions: {stats['transcription_count']}")
        model_info = stats["model_info"]
        console.print(f"  Model: {model_info.get('model', 'unknown')}")
        console.print(f"  Description: {model_info.get('description', 'N/A')}")


__all__ = ["voice_app"]
