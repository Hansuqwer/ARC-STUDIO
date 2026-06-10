"""Tests for ARC Vision — HITL-gated browser automation (R93, Phase 318)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_runtime_cockpit.vision import (
    FakeVisionDriver,
    HitlGatedVisionSession,
    VisionActionType,
    create_vision_session,
)


@pytest.fixture
def fake_driver() -> FakeVisionDriver:
    return FakeVisionDriver()


@pytest.fixture
def session(fake_driver: FakeVisionDriver) -> HitlGatedVisionSession:
    return HitlGatedVisionSession(fake_driver, auto_approve=True)


class TestFakeVisionDriver:
    def test_navigate(self, fake_driver: FakeVisionDriver) -> None:
        result = fake_driver.navigate("https://example.com")
        assert result.success is True
        assert result.action_type == VisionActionType.NAVIGATE
        assert len(fake_driver.actions) == 1

    def test_click(self, fake_driver: FakeVisionDriver) -> None:
        result = fake_driver.click("#button")
        assert result.success is True
        assert result.action_type == VisionActionType.CLICK

    def test_type_text(self, fake_driver: FakeVisionDriver) -> None:
        result = fake_driver.type_text("#input", "hello")
        assert result.success is True
        assert result.action_type == VisionActionType.TYPE

    def test_screenshot(self, fake_driver: FakeVisionDriver, tmp_path: Path) -> None:
        output = tmp_path / "screenshot.png"
        result = fake_driver.screenshot(output)
        assert result.success is True
        assert result.action_type == VisionActionType.SCREENSHOT
        assert result.screenshot_path == str(output)
        assert output.exists()

    def test_scroll(self, fake_driver: FakeVisionDriver) -> None:
        result = fake_driver.scroll("down", 500)
        assert result.success is True
        assert result.action_type == VisionActionType.SCROLL

    def test_close(self, fake_driver: FakeVisionDriver) -> None:
        fake_driver.close()


class TestHitlGatedVisionSession:
    def test_navigate_auto_approve(self, session: HitlGatedVisionSession) -> None:
        result = session.navigate("https://example.com")
        assert result.success is True
        assert result.approved is True
        assert len(session.action_log) == 1

    def test_click_auto_approve(self, session: HitlGatedVisionSession) -> None:
        result = session.click("#button")
        assert result.success is True
        assert result.approved is True

    def test_type_text_auto_approve(self, session: HitlGatedVisionSession) -> None:
        result = session.type_text("#input", "hello")
        assert result.success is True
        assert result.approved is True

    def test_screenshot_auto_approve(self, session: HitlGatedVisionSession, tmp_path: Path) -> None:
        output = tmp_path / "screenshot.png"
        result = session.screenshot(output)
        assert result.success is True
        assert result.approved is True
        assert output.exists()

    def test_scroll_auto_approve(self, session: HitlGatedVisionSession) -> None:
        result = session.scroll("down", 300)
        assert result.success is True
        assert result.approved is True

    def test_navigate_requires_approval(self, fake_driver: FakeVisionDriver) -> None:
        session = HitlGatedVisionSession(fake_driver, auto_approve=False)
        result = session.navigate("https://example.com")
        assert result.success is False
        assert result.approved is False
        assert "Approval required" in result.error

    def test_click_requires_approval(self, fake_driver: FakeVisionDriver) -> None:
        session = HitlGatedVisionSession(fake_driver, auto_approve=False)
        result = session.click("#button")
        assert result.success is False
        assert result.approved is False

    def test_type_text_requires_approval(self, fake_driver: FakeVisionDriver) -> None:
        session = HitlGatedVisionSession(fake_driver, auto_approve=False)
        result = session.type_text("#input", "hello")
        assert result.success is False
        assert result.approved is False

    def test_screenshot_requires_approval(
        self, fake_driver: FakeVisionDriver, tmp_path: Path
    ) -> None:
        session = HitlGatedVisionSession(fake_driver, auto_approve=False)
        output = tmp_path / "screenshot.png"
        result = session.screenshot(output)
        assert result.success is False
        assert result.approved is False
        assert not output.exists()

    def test_scroll_requires_approval(self, fake_driver: FakeVisionDriver) -> None:
        session = HitlGatedVisionSession(fake_driver, auto_approve=False)
        result = session.scroll("down", 300)
        assert result.success is False
        assert result.approved is False

    def test_action_log(self, session: HitlGatedVisionSession) -> None:
        session.navigate("https://example.com")
        session.click("#button")
        session.type_text("#input", "hello")
        assert len(session.action_log) == 3

    def test_close(self, session: HitlGatedVisionSession) -> None:
        session.close()


class TestCreateVisionSession:
    def test_create_fake_session(self) -> None:
        session = create_vision_session(driver_type="fake", auto_approve=True)
        assert isinstance(session, HitlGatedVisionSession)
        session.close()

    def test_create_playwright_session_without_dependency(self) -> None:
        session = create_vision_session(driver_type="playwright", auto_approve=True)
        assert isinstance(session, HitlGatedVisionSession)
        session.close()


class TestVisionCLI:
    def test_vision_help(self) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["vision", "--help"])
        assert result.exit_code == 0
        assert "vision" in result.output.lower()

    def test_vision_screenshot(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        output = tmp_path / "screenshot.png"
        result = runner.invoke(
            app,
            [
                "vision",
                "screenshot",
                str(output),
                "--auto-approve",
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
        assert data["data"]["success"] is True
        assert data["data"]["approved"] is True

    def test_vision_navigate(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "vision",
                "navigate",
                "https://example.com",
                "--auto-approve",
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
        assert data["data"]["success"] is True

    def test_vision_click(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "vision",
                "click",
                "#button",
                "--auto-approve",
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

    def test_vision_type(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "vision",
                "type",
                "#input",
                "hello",
                "--auto-approve",
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

    def test_vision_scroll(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "vision",
                "scroll",
                "--direction",
                "down",
                "--pixels",
                "500",
                "--auto-approve",
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

    def test_vision_session(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "vision",
                "session",
                "--auto-approve",
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
        assert data["data"]["driver"] == "fake"

    def test_vision_screenshot_requires_approval(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        output = tmp_path / "screenshot.png"
        result = runner.invoke(
            app,
            [
                "vision",
                "screenshot",
                str(output),
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
        assert "Approval required" in data["error"]["message"]
