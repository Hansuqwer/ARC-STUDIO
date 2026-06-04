"""Fake upstream stdio MCP server for proxy tests.

Reads JSONRPC from stdin line-by-line, responds to:
- initialize → capabilities
- tools/list → fake tool list
- tools/call → echo arguments back
"""

from __future__ import annotations

import asyncio
import json
import sys


FAKE_TOOLS = [
    {"name": "read_file", "description": "Read a file from disk"},
    {"name": "write_file", "description": "Write/create/modify a file"},
    {"name": "fetch_url", "description": "Fetch content from a URL via http"},
]


def _handle(msg: dict) -> dict:
    method = msg.get("method", "")
    msg_id = msg.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"capabilities": {"tools": {}}},
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": FAKE_TOOLS},
        }

    if method == "tools/call":
        params = msg.get("params", {})
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(params.get("arguments", {}))}]
            },
        }

    # Unknown method
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


async def _run() -> None:
    reader = asyncio.StreamReader()
    await asyncio.get_event_loop().connect_read_pipe(
        lambda: asyncio.StreamReaderProtocol(reader), sys.stdin
    )
    writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(writer_transport, writer_protocol, None, asyncio.get_event_loop())

    while True:
        line = await reader.readline()
        if not line:
            break
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = _handle(msg)
        writer.write(json.dumps(resp).encode("utf-8") + b"\n")
        await writer.drain()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
