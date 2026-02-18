"""
CLI commands for VPN command wrapper.
"""

import argparse
import sys

from .runner import VpnRequirement, run_with_vpn_context


def vpn_run_cmd() -> None:
    """
    CLI command to run a command with automatic VPN management.

    Usage:
        agdt-vpn-run --require-vpn "curl https://jira.swica.ch/rest/api/2/serverInfo"
        agdt-vpn-run --require-public "npm install"
        agdt-vpn-run --smart "az devops ..."

    The command will automatically:
    - Connect VPN if needed (--require-vpn)
    - Disconnect VPN temporarily if needed (--require-public)
    - Auto-detect from command content (--smart)
    - Skip VPN operations when on corporate network (in office)
    """
    parser = argparse.ArgumentParser(
        description="Run a command with automatic VPN context management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agdt-vpn-run --require-vpn "curl https://jira.swica.ch/rest/api/2/issue/DP-123"
  agdt-vpn-run --require-public "npm install"
  agdt-vpn-run --smart "az devops ..."

Network Requirements:
  --require-vpn     Ensure VPN is connected before running (for Jira, ESB, etc.)
  --require-public  Disconnect VPN temporarily for public access (npm, pip, etc.)
  --smart           Auto-detect requirement from command content (default)
        """,
    )

    # Mutually exclusive group for network requirement
    requirement_group = parser.add_mutually_exclusive_group()
    requirement_group.add_argument(
        "--require-vpn",
        action="store_const",
        const=VpnRequirement.REQUIRE_VPN,
        dest="requirement",
        help="Command needs VPN (Jira, ESB, etc.)",
    )
    requirement_group.add_argument(
        "--require-public",
        action="store_const",
        const=VpnRequirement.REQUIRE_PUBLIC,
        dest="requirement",
        help="Command needs public access (npm, pip, etc.)",
    )
    requirement_group.add_argument(
        "--smart",
        action="store_const",
        const=VpnRequirement.SMART,
        dest="requirement",
        help="Auto-detect requirement from command (default)",
    )

    # Command to execute
    parser.add_argument(
        "command",
        nargs="+",
        help="Command to execute with VPN management",
    )

    args = parser.parse_args()

    # Default to smart detection if no requirement specified
    requirement = args.requirement or VpnRequirement.SMART

    # Join command parts into a single string
    command = " ".join(args.command)

    # Run the command with VPN context
    return_code, _, _ = run_with_vpn_context(command, requirement)

    # Exit with the same return code as the command
    sys.exit(return_code)
