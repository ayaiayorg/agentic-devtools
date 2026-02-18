"""
Network context detection and management for agentic-devtools.

This module provides utilities to detect network context (corporate network,
remote with/without VPN) and manage VPN connections intelligently.
"""

from .commands import network_status_cmd
from .detection import (
    NetworkContext,
    detect_network_context,
    get_network_context_display,
)

__all__ = [
    "NetworkContext",
    "detect_network_context",
    "get_network_context_display",
    "network_status_cmd",
]
