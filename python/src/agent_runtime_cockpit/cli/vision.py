"""CLI commands for ARC Vision — HITL-gated browser automation (R93).

Commands:
  arc vision screenshot   Capture a screenshot (HITL-gated).
  arc vision navigate     Navigate to a URL (HITL-gated).
  arc vision click        Click on an element (HITL-gated).
  arc vision type         Type text into an element (HITL-gated).
  arc vision scroll       Scroll the page (HITL-gated).
  arc vision session      Start an interactive vision session.

All commands accept --json for machine-readable envelope output.
Every action requires HITL approval by default (--auto-approve for testing only).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import JSON_FLAG, WORKSPACE_FLAG, _out, _workspace
from ._subapps import vision_app


@vision_app.command("screenshot")
def vision_screenshot(
    output: str = typer.Argument(..., help="Output path for screenshot (PNG)"),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Skip HITL approval (testing only)"
    ),
    driver: str = typer.Option("fake", "--driver", "-d", help="Driver: fake or playwright"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Capture a screenshot (HITL-gated)."""
    from ..vision import create_vision_session

    _workspace(workspace)
    session = create_vision_session(driver_type=driver, auto_approve=auto_approve)
    try:
        result = session.screenshot(Path(output))
        if result.success and result.approved:
            _out(
                ok(
                    {
                        "action_id": result.action_id,
                        "action_type": result.action_type.value,
                        "success": result.success,
                        "approved": result.approved,
                        "screenshot_path": result.screenshot_path,
                        "timestamp": result.timestamp,
                    }
                ),
                as_json,
            )
        else:
            _out(
                err(
                    ArcErrorCode.PERMISSION_DENIED,
                    result.error or "Action not approved",
                    {"action_id": result.action_id, "approved": result.approved},
                ),
                as_json,
            )
            raise typer.Exit(1)
    finally:
        session.close()


@vision_app.command("navigate")
def vision_navigate(
    url: str = typer.Argument(..., help="URL to navigate to"),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Skip HITL approval (testing only)"
    ),
    driver: str = typer.Option("fake", "--driver", "-d", help="Driver: fake or playwright"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Navigate to a URL (HITL-gated)."""
    from ..vision import create_vision_session

    _workspace(workspace)
    session = create_vision_session(driver_type=driver, auto_approve=auto_approve)
    try:
        result = session.navigate(url)
        if result.success and result.approved:
            _out(
                ok(
                    {
                        "action_id": result.action_id,
                        "action_type": result.action_type.value,
                        "success": result.success,
                        "approved": result.approved,
                        "timestamp": result.timestamp,
                    }
                ),
                as_json,
            )
        else:
            _out(
                err(
                    ArcErrorCode.PERMISSION_DENIED,
                    result.error or "Action not approved",
                    {"action_id": result.action_id, "approved": result.approved},
                ),
                as_json,
            )
            raise typer.Exit(1)
    finally:
        session.close()


@vision_app.command("click")
def vision_click(
    selector: str = typer.Argument(..., help="CSS selector to click"),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Skip HITL approval (testing only)"
    ),
    driver: str = typer.Option("fake", "--driver", "-d", help="Driver: fake or playwright"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Click on an element (HITL-gated)."""
    from ..vision import create_vision_session

    _workspace(workspace)
    session = create_vision_session(driver_type=driver, auto_approve=auto_approve)
    try:
        result = session.click(selector)
        if result.success and result.approved:
            _out(
                ok(
                    {
                        "action_id": result.action_id,
                        "action_type": result.action_type.value,
                        "success": result.success,
                        "approved": result.approved,
                        "timestamp": result.timestamp,
                    }
                ),
                as_json,
            )
        else:
            _out(
                err(
                    ArcErrorCode.PERMISSION_DENIED,
                    result.error or "Action not approved",
                    {"action_id": result.action_id, "approved": result.approved},
                ),
                as_json,
            )
            raise typer.Exit(1)
    finally:
        session.close()


@vision_app.command("type")
def vision_type(
    selector: str = typer.Argument(..., help="CSS selector to type into"),
    text: str = typer.Argument(..., help="Text to type"),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Skip HITL approval (testing only)"
    ),
    driver: str = typer.Option("fake", "--driver", "-d", help="Driver: fake or playwright"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Type text into an element (HITL-gated)."""
    from ..vision import create_vision_session

    _workspace(workspace)
    session = create_vision_session(driver_type=driver, auto_approve=auto_approve)
    try:
        result = session.type_text(selector, text)
        if result.success and result.approved:
            _out(
                ok(
                    {
                        "action_id": result.action_id,
                        "action_type": result.action_type.value,
                        "success": result.success,
                        "approved": result.approved,
                        "timestamp": result.timestamp,
                    }
                ),
                as_json,
            )
        else:
            _out(
                err(
                    ArcErrorCode.PERMISSION_DENIED,
                    result.error or "Action not approved",
                    {"action_id": result.action_id, "approved": result.approved},
                ),
                as_json,
            )
            raise typer.Exit(1)
    finally:
        session.close()


@vision_app.command("scroll")
def vision_scroll(
    direction: str = typer.Option("down", "--direction", help="Scroll direction: up or down"),
    pixels: int = typer.Option(300, "--pixels", help="Pixels to scroll"),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Skip HITL approval (testing only)"
    ),
    driver: str = typer.Option("fake", "--driver", "-d", help="Driver: fake or playwright"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Scroll the page (HITL-gated)."""
    from ..vision import create_vision_session

    _workspace(workspace)
    session = create_vision_session(driver_type=driver, auto_approve=auto_approve)
    try:
        result = session.scroll(direction, pixels)
        if result.success and result.approved:
            _out(
                ok(
                    {
                        "action_id": result.action_id,
                        "action_type": result.action_type.value,
                        "success": result.success,
                        "approved": result.approved,
                        "timestamp": result.timestamp,
                    }
                ),
                as_json,
            )
        else:
            _out(
                err(
                    ArcErrorCode.PERMISSION_DENIED,
                    result.error or "Action not approved",
                    {"action_id": result.action_id, "approved": result.approved},
                ),
                as_json,
            )
            raise typer.Exit(1)
    finally:
        session.close()


@vision_app.command("session")
def vision_session(
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Skip HITL approval (testing only)"
    ),
    driver: str = typer.Option("fake", "--driver", "-d", help="Driver: fake or playwright"),
    headless: bool = typer.Option(True, "--headless/--no-headless", help="Run in headless mode"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Start an interactive vision session (HITL-gated).

    This is a placeholder for future interactive REPL integration.
    """
    from ..vision import create_vision_session

    _workspace(workspace)
    session = create_vision_session(
        driver_type=driver, auto_approve=auto_approve, headless=headless
    )
    _out(
        ok(
            {
                "driver": driver,
                "auto_approve": auto_approve,
                "headless": headless,
                "message": "Vision session created. Use arc vision <action> commands.",
            }
        ),
        as_json,
    )
    session.close()


__all__ = ["vision_app"]
