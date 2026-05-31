from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer

from .checkpoint import JsonFileCheckpointStore
from .config import ExecutionMode, SwarmGraphConfig
from .runner import SwarmGraphRunner

app = typer.Typer(help="SwarmGraph SDK CLI")


@app.callback()
def main() -> None:
    """SwarmGraph SDK CLI."""


@app.command("run")
def run_cmd(
    prompt: str = typer.Argument("", help="Prompt to run"),
    workers: int = typer.Option(3, "--workers", "-w", min=1, max=50),
    max_rounds: int = typer.Option(1, "--max-rounds", min=1, max=100),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON result"),
    stream: bool = typer.Option(False, "--stream", help="Emit JSONL event stream"),
    checkpoint_dir: Path | None = typer.Option(
        None,
        "--checkpoint-dir",
        help="Directory for durable JSON checkpoints",
    ),
    resume: str | None = typer.Option(
        None,
        "--resume",
        help="Resume from a checkpoint id (requires --checkpoint-dir)",
    ),
) -> None:
    config = SwarmGraphConfig(
        num_workers=workers,
        max_rounds=max_rounds,
        execution_mode=ExecutionMode.fake_offline,
    )
    store = JsonFileCheckpointStore(checkpoint_dir) if checkpoint_dir is not None else None
    runner = SwarmGraphRunner(config=config, checkpoint_store=store)

    if resume is not None:
        if store is None:
            raise typer.BadParameter("--resume requires --checkpoint-dir")
        result = runner.resume_result(resume)
        if json_output:
            typer.echo(json.dumps(result.to_dict(), sort_keys=True))
            return
        typer.echo(f"status={result.status} tasks={result.completed_tasks}/{result.total_tasks}")
        for task_result in result.results:
            typer.echo(task_result.output)
        return

    if not prompt:
        raise typer.BadParameter("prompt is required unless --resume is used")

    if stream:
        asyncio.run(_stream_run(runner, prompt))
        return

    result = runner.run_result(prompt)
    if json_output:
        typer.echo(json.dumps(result.to_dict(), sort_keys=True))
        return

    typer.echo(f"status={result.status} tasks={result.completed_tasks}/{result.total_tasks}")
    for task_result in result.results:
        typer.echo(task_result.output)


async def _stream_run(runner: SwarmGraphRunner, prompt: str) -> None:
    async for event in runner.stream(prompt):
        typer.echo(json.dumps(event.to_dict(), sort_keys=True))


__all__ = ["app"]
