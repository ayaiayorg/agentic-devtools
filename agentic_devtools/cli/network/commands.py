"""
CLI commands for network context management.
"""

from .detection import detect_network_context, get_network_context_display


def network_status_cmd() -> None:
    """
    CLI command to show current network context and VPN status.

    Usage:
        agdt-network-status

    Reports:
    - Whether on corporate network (in office)
    - VPN connection status
    - Recommendations for VPN management
    """
    print("Detecting network context...")
    context, description = detect_network_context()

    print("\n" + "=" * 70)
    print("Network Status")
    print("=" * 70)
    print(get_network_context_display(context, description))
    print("=" * 70)
