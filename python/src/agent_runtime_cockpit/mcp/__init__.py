"""
MCP Local Control Plane (Phase 26 / R19).

Exposes ARC capabilities as a local MCP server via stdio transport.
All tools are gated by workspace trust enforcement.
No HTTP/listen sockets unless explicitly requested.
"""

from .server import create_mcp_server

__all__ = ["create_mcp_server"]
