"""MCP (Model Context Protocol) server for agentic-devtools.

Exposes AGDT tool adapter functions as MCP tools, allowing any
MCP-compatible AI coding agent to discover and call them.
"""

from .server import create_mcp_server

__all__ = ["create_mcp_server"]
