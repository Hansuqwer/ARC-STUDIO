from __future__ import annotations

from pathlib import Path

import aiohttp.web as web

WORKSPACE_KEY: web.AppKey[Path] = web.AppKey("workspace", Path)
