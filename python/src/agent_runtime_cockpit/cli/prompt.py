"""Prompt optimization commands: optimize, diff (Phase 25)."""

from __future__ import annotations

import typer

from ._app import console
from ._helpers import (
    DEBUG_FLAG,
    JSON_FLAG,
    _out,
    _setup_logging,
)
from ._subapps import prompt_app

from ..protocol.event_envelope import ok


@prompt_app.command("optimize")
def prompt_optimize(
    prompt: str = typer.Argument(..., help="Prompt text to optimize"),
    model: str = typer.Option("gpt-4o", "--model", "-m", help="Model for token counting"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Apply rule-based optimization to a prompt.

    No provider calls are made. Uses tiktoken for counting (falls back to
    word estimate if tiktoken is not installed).
    """
    _setup_logging(debug)
    from ..optimizer import estimate_cost, optimize_prompt

    result = optimize_prompt(prompt, model=model)
    payload = {
        "original_length": len(prompt),
        "optimized_length": len(result.optimized),
        "original_tokens": result.original_tokens.count,
        "optimized_tokens": result.optimized_tokens.count,
        "tokens_saved": result.tokens_saved,
        "changes": result.changes,
        "encoding": result.original_tokens.encoding,
    }

    cost = estimate_cost(result.original_tokens.count, model)
    if cost is not None:
        payload["estimated_cost_usd"] = round(cost, 6)
        cost_after = estimate_cost(result.optimized_tokens.count, model)
        if cost_after is not None:
            payload["estimated_cost_after_usd"] = round(cost_after, 6)
            payload["estimated_savings_usd"] = round(cost - cost_after, 6)

    _out(ok(payload), json_output)
    if not json_output:
        console.print(
            f"[dim]Original:[/dim] {result.original_tokens.count} tokens ({result.original_tokens.encoding})"
        )
        console.print(f"[green]Optimized:[/green] {result.optimized_tokens.count} tokens")
        console.print(f"[bold]Saved:[/bold] {result.tokens_saved} tokens")
        if result.changes:
            console.print(f"[dim]Rules applied:[/dim] {', '.join(result.changes)}")
        else:
            console.print("[dim]No changes needed[/dim]")
        if cost is not None:
            console.print(f"[dim]Est. cost before:[/dim] ${payload['estimated_cost_usd']:.6f}")
            console.print(
                f"[green]Est. cost after:[/green] ${payload['estimated_cost_after_usd']:.6f}"
            )


@prompt_app.command("diff")
def prompt_diff(
    prompt_a: str = typer.Argument(..., help="First prompt text"),
    prompt_b: str = typer.Argument(..., help="Second prompt text"),
    context_lines: int = typer.Option(3, "--context", "-c", help="Context lines for diff"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Compare two prompts using unified diff."""
    _setup_logging(debug)
    from ..optimizer import count_tokens, diff_prompts

    diff_text = diff_prompts(prompt_a, prompt_b, context_lines=context_lines)
    tokens_a = count_tokens(prompt_a)
    tokens_b = count_tokens(prompt_b)

    payload = {
        "prompt_a_tokens": tokens_a.count,
        "prompt_b_tokens": tokens_b.count,
        "token_diff": tokens_b.count - tokens_a.count,
        "diff": diff_text,
    }
    _out(ok(payload), json_output)
    if not json_output:
        console.print(f"Prompt A: {tokens_a.count} tokens")
        console.print(f"Prompt B: {tokens_b.count} tokens")
        console.print(f"Token diff: {payload['token_diff']:+d}")
        console.print("")
        if diff_text:
            console.print(diff_text)
        else:
            console.print("[dim]No differences[/dim]")
