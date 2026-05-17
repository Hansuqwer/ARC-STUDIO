from __future__ import annotations

from pathlib import Path

import aiohttp.web as web

from ..orchestration.event_broker import EventBroker

WORKSPACE_KEY: web.AppKey[Path] = web.AppKey("workspace", Path)
EVENT_BROKER_KEY: web.AppKey[EventBroker] = web.AppKey("event_broker", EventBroker)
