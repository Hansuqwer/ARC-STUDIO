"""ARC Vision — HITL-gated local browser automation (R93).

Every mouse/keyboard action is human-approved by default via the HITL gate.
Screenshot capture is local-only. Playwright is an optional dependency.
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


class VisionActionType(str, Enum):
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    NAVIGATE = "navigate"
    SCREENSHOT = "screenshot"
    WAIT = "wait"


@dataclass(frozen=True)
class VisionAction:
    action_type: VisionActionType
    target: Optional[str] = None
    value: Optional[str] = None
    coordinates: Optional[tuple[int, int]] = None
    description: str = ""


@dataclass
class VisionActionResult:
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: VisionActionType = VisionActionType.CLICK
    success: bool = False
    approved: bool = False
    operator_id: str = "anonymous"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    screenshot_path: Optional[str] = None
    error: Optional[str] = None


class VisionDriver(ABC):
    """Abstract base class for browser automation drivers."""

    @abstractmethod
    def navigate(self, url: str) -> VisionActionResult:
        pass

    @abstractmethod
    def click(self, selector: str) -> VisionActionResult:
        pass

    @abstractmethod
    def type_text(self, selector: str, text: str) -> VisionActionResult:
        pass

    @abstractmethod
    def screenshot(self, output_path: Path) -> VisionActionResult:
        pass

    @abstractmethod
    def scroll(self, direction: str = "down", pixels: int = 300) -> VisionActionResult:
        pass

    @abstractmethod
    def close(self) -> None:
        pass


class FakeVisionDriver(VisionDriver):
    """Fake driver for testing — no real browser, no network."""

    def __init__(self) -> None:
        self._actions: list[VisionActionResult] = []
        self._current_url: str = "about:blank"

    @property
    def actions(self) -> list[VisionActionResult]:
        return self._actions

    def navigate(self, url: str) -> VisionActionResult:
        result = VisionActionResult(
            action_type=VisionActionType.NAVIGATE,
            success=True,
            approved=True,
        )
        self._current_url = url
        self._actions.append(result)
        return result

    def click(self, selector: str) -> VisionActionResult:
        result = VisionActionResult(
            action_type=VisionActionType.CLICK,
            success=True,
            approved=True,
        )
        self._actions.append(result)
        return result

    def type_text(self, selector: str, text: str) -> VisionActionResult:
        result = VisionActionResult(
            action_type=VisionActionType.TYPE,
            success=True,
            approved=True,
        )
        self._actions.append(result)
        return result

    def screenshot(self, output_path: Path) -> VisionActionResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"FAKE_PNG_DATA")
        result = VisionActionResult(
            action_type=VisionActionType.SCREENSHOT,
            success=True,
            approved=True,
            screenshot_path=str(output_path),
        )
        self._actions.append(result)
        return result

    def scroll(self, direction: str = "down", pixels: int = 300) -> VisionActionResult:
        result = VisionActionResult(
            action_type=VisionActionType.SCROLL,
            success=True,
            approved=True,
        )
        self._actions.append(result)
        return result

    def close(self) -> None:
        pass


class PlaywrightVisionDriver(VisionDriver):
    """Playwright-based driver — requires playwright optional dependency.

    All actions are HITL-gated. Browser launch is explicit opt-in.
    """

    def __init__(self, headless: bool = True) -> None:
        self._headless = headless
        self._browser = None
        self._page = None
        self._playwright = None

    def _ensure_browser(self) -> None:
        if self._browser is not None:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Install with: pip install 'arc-studio[vision]'"
            )
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self._headless)
        self._page = self._browser.new_page()

    def navigate(self, url: str) -> VisionActionResult:
        try:
            self._ensure_browser()
            self._page.goto(url)
            return VisionActionResult(
                action_type=VisionActionType.NAVIGATE,
                success=True,
                approved=True,
            )
        except Exception as e:
            return VisionActionResult(
                action_type=VisionActionType.NAVIGATE,
                success=False,
                approved=True,
                error=str(e),
            )

    def click(self, selector: str) -> VisionActionResult:
        try:
            self._ensure_browser()
            self._page.click(selector)
            return VisionActionResult(
                action_type=VisionActionType.CLICK,
                success=True,
                approved=True,
            )
        except Exception as e:
            return VisionActionResult(
                action_type=VisionActionType.CLICK,
                success=False,
                approved=True,
                error=str(e),
            )

    def type_text(self, selector: str, text: str) -> VisionActionResult:
        try:
            self._ensure_browser()
            self._page.fill(selector, text)
            return VisionActionResult(
                action_type=VisionActionType.TYPE,
                success=True,
                approved=True,
            )
        except Exception as e:
            return VisionActionResult(
                action_type=VisionActionType.TYPE,
                success=False,
                approved=True,
                error=str(e),
            )

    def screenshot(self, output_path: Path) -> VisionActionResult:
        try:
            self._ensure_browser()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self._page.screenshot(path=str(output_path))
            return VisionActionResult(
                action_type=VisionActionType.SCREENSHOT,
                success=True,
                approved=True,
                screenshot_path=str(output_path),
            )
        except Exception as e:
            return VisionActionResult(
                action_type=VisionActionType.SCREENSHOT,
                success=False,
                approved=True,
                error=str(e),
            )

    def scroll(self, direction: str = "down", pixels: int = 300) -> VisionActionResult:
        try:
            self._ensure_browser()
            delta = pixels if direction == "down" else -pixels
            self._page.evaluate(f"window.scrollBy(0, {delta})")
            return VisionActionResult(
                action_type=VisionActionType.SCROLL,
                success=True,
                approved=True,
            )
        except Exception as e:
            return VisionActionResult(
                action_type=VisionActionType.SCROLL,
                success=False,
                approved=True,
                error=str(e),
            )

    def close(self) -> None:
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()


class HitlGatedVisionSession:
    """Vision session where every action requires HITL approval."""

    def __init__(self, driver: VisionDriver, auto_approve: bool = False) -> None:
        self._driver = driver
        self._auto_approve = auto_approve
        self._action_log: list[VisionActionResult] = []

    @property
    def action_log(self) -> list[VisionActionResult]:
        return self._action_log

    def _request_approval(self, action: VisionAction) -> tuple[bool, str]:
        if self._auto_approve:
            return True, "auto-approved"
        return False, "approval_required"

    def navigate(self, url: str) -> VisionActionResult:
        action = VisionAction(
            action_type=VisionActionType.NAVIGATE,
            target=url,
            description=f"Navigate to {url}",
        )
        approved, reason = self._request_approval(action)
        if not approved:
            result = VisionActionResult(
                action_type=VisionActionType.NAVIGATE,
                success=False,
                approved=False,
                error=f"Approval required: {reason}",
            )
            self._action_log.append(result)
            return result
        result = self._driver.navigate(url)
        result.approved = approved
        self._action_log.append(result)
        return result

    def click(self, selector: str) -> VisionActionResult:
        action = VisionAction(
            action_type=VisionActionType.CLICK,
            target=selector,
            description=f"Click on {selector}",
        )
        approved, reason = self._request_approval(action)
        if not approved:
            result = VisionActionResult(
                action_type=VisionActionType.CLICK,
                success=False,
                approved=False,
                error=f"Approval required: {reason}",
            )
            self._action_log.append(result)
            return result
        result = self._driver.click(selector)
        result.approved = approved
        self._action_log.append(result)
        return result

    def type_text(self, selector: str, text: str) -> VisionActionResult:
        action = VisionAction(
            action_type=VisionActionType.TYPE,
            target=selector,
            value=text,
            description=f"Type '{text}' into {selector}",
        )
        approved, reason = self._request_approval(action)
        if not approved:
            result = VisionActionResult(
                action_type=VisionActionType.TYPE,
                success=False,
                approved=False,
                error=f"Approval required: {reason}",
            )
            self._action_log.append(result)
            return result
        result = self._driver.type_text(selector, text)
        result.approved = approved
        self._action_log.append(result)
        return result

    def screenshot(self, output_path: Path) -> VisionActionResult:
        action = VisionAction(
            action_type=VisionActionType.SCREENSHOT,
            target=str(output_path),
            description=f"Capture screenshot to {output_path}",
        )
        approved, reason = self._request_approval(action)
        if not approved:
            result = VisionActionResult(
                action_type=VisionActionType.SCREENSHOT,
                success=False,
                approved=False,
                error=f"Approval required: {reason}",
            )
            self._action_log.append(result)
            return result
        result = self._driver.screenshot(output_path)
        result.approved = approved
        self._action_log.append(result)
        return result

    def scroll(self, direction: str = "down", pixels: int = 300) -> VisionActionResult:
        action = VisionAction(
            action_type=VisionActionType.SCROLL,
            value=f"{direction} {pixels}px",
            description=f"Scroll {direction} by {pixels}px",
        )
        approved, reason = self._request_approval(action)
        if not approved:
            result = VisionActionResult(
                action_type=VisionActionType.SCROLL,
                success=False,
                approved=False,
                error=f"Approval required: {reason}",
            )
            self._action_log.append(result)
            return result
        result = self._driver.scroll(direction, pixels)
        result.approved = approved
        self._action_log.append(result)
        return result

    def close(self) -> None:
        self._driver.close()


def create_vision_session(
    driver_type: str = "fake",
    auto_approve: bool = False,
    headless: bool = True,
) -> HitlGatedVisionSession:
    """Factory for creating HITL-gated vision sessions.

    Args:
        driver_type: "fake" for testing, "playwright" for real browser.
        auto_approve: If True, skip HITL approval (for testing only).
        headless: Run browser in headless mode (playwright only).

    Returns:
        A HitlGatedVisionSession instance.
    """
    if driver_type == "playwright":
        driver = PlaywrightVisionDriver(headless=headless)
    else:
        driver = FakeVisionDriver()
    return HitlGatedVisionSession(driver, auto_approve=auto_approve)


__all__ = [
    "VisionActionType",
    "VisionAction",
    "VisionActionResult",
    "VisionDriver",
    "FakeVisionDriver",
    "PlaywrightVisionDriver",
    "HitlGatedVisionSession",
    "create_vision_session",
]
