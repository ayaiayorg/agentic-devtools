"""
VPN command wrapper for agentic-devtools.

This module provides utilities to run commands with automatic VPN context
management based on their network requirements.
"""

from .commands import vpn_run_cmd
from .runner import VpnRequirement, run_with_vpn_context

__all__ = [
    "VpnRequirement",
    "run_with_vpn_context",
    "vpn_run_cmd",
]
