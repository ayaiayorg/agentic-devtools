"""
Network context detection utilities.

Provides functions to detect whether the developer is on the corporate network
(in office), remote with VPN, or remote without VPN.
"""

from enum import Enum
from typing import Tuple


class NetworkContext(Enum):
    """Network context for determining VPN requirements."""

    CORPORATE_NETWORK = "corporate_network"  # In office - VPN not needed
    REMOTE_WITH_VPN = "remote_with_vpn"  # Remote, VPN connected
    REMOTE_WITHOUT_VPN = "remote_without_vpn"  # Remote, VPN not connected
    UNKNOWN = "unknown"  # Cannot determine context


def detect_network_context() -> Tuple[NetworkContext, str]:
    """
    Detect the current network context.

    This function determines whether the developer is:
    1. On the corporate network (in office) - VPN operations not needed
    2. Remote with VPN connected - Can access internal resources
    3. Remote without VPN - Cannot access internal resources

    Returns:
        Tuple of (NetworkContext, human-readable description)
    """
    try:
        from ..azure_devops.vpn_toggle import is_on_corporate_network, is_vpn_connected

        # Check if VPN is connected first (fast check)
        if is_vpn_connected():
            return (
                NetworkContext.REMOTE_WITH_VPN,
                "Remote with VPN connected - internal resources accessible",
            )

        # Check if on corporate network (in office)
        if is_on_corporate_network():
            return (
                NetworkContext.CORPORATE_NETWORK,
                "On corporate network (in office) - VPN not needed",
            )

        # Not on VPN and not on corporate network
        return (
            NetworkContext.REMOTE_WITHOUT_VPN,
            "Remote without VPN - internal resources not accessible",
        )

    except ImportError:
        # VPN module not available (e.g., non-Windows platform)
        return (
            NetworkContext.UNKNOWN,
            "Network detection not available on this platform",
        )
    except Exception as e:
        return (
            NetworkContext.UNKNOWN,
            f"Network detection failed: {e}",
        )


def get_network_context_display(context: NetworkContext, description: str) -> str:
    """
    Get a formatted display string for the network context.

    Args:
        context: The detected network context
        description: Human-readable description

    Returns:
        Formatted string with emoji and details
    """
    if context == NetworkContext.CORPORATE_NETWORK:
        emoji = "🏢"
        recommendation = "VPN operations will be skipped automatically"
    elif context == NetworkContext.REMOTE_WITH_VPN:
        emoji = "🔌"
        recommendation = "Use 'agdt-vpn-off' to temporarily disconnect for npm/pip installs"
    elif context == NetworkContext.REMOTE_WITHOUT_VPN:
        emoji = "📡"
        recommendation = "Use 'agdt-vpn-on' to connect for Jira/ESB access"
    else:
        emoji = "❓"
        recommendation = "VPN management may not be available"

    return f"{emoji} {description}\n   {recommendation}"
