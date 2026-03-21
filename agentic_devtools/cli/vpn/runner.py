"""
VPN command wrapper and execution utilities.

Provides functions to run commands with automatic VPN management based on
their network requirements.
"""

import shlex
import subprocess
from enum import Enum


class VpnRequirement(Enum):
    """Network requirement for a command."""

    REQUIRE_VPN = "require_vpn"  # Command needs VPN (Jira, ESB, etc.)
    REQUIRE_PUBLIC = "require_public"  # Command needs public access (npm, pip, etc.)
    SMART = "smart"  # Auto-detect from command/URL


def _detect_vpn_requirement_from_command(command: str) -> VpnRequirement:
    """
    Auto-detect whether a command needs VPN or public access.

    Args:
        command: The command string to analyze

    Returns:
        VpnRequirement based on heuristics
    """
    command_lower = command.lower()

    # Commands that typically need public access (no VPN)
    public_access_patterns = [
        "npm install",
        "npm i ",
        "pip install",
        "pip3 install",
        "poetry install",
        "yarn install",
        "pnpm install",
        "apt-get",
        "apt install",
        "brew install",
        "cargo install",
        "go get",
        "go install",
    ]

    for pattern in public_access_patterns:
        if pattern in command_lower:
            return VpnRequirement.REQUIRE_PUBLIC

    # Commands/URLs that typically need VPN
    from agentic_devtools.cli.azure_devops.vpn_toggle import get_vpn_hostnames

    vpn_patterns = get_vpn_hostnames()

    for pattern in vpn_patterns:
        if pattern in command_lower:
            return VpnRequirement.REQUIRE_VPN

    # Default to requiring public access for unknown commands
    # This is safer as it won't block registry access
    return VpnRequirement.REQUIRE_PUBLIC


def run_with_vpn_context(
    command: str,
    requirement: VpnRequirement = VpnRequirement.SMART,
    shell: bool = True,
) -> tuple[int, str, str]:
    """
    Run a command with automatic VPN context management.

    Args:
        command: The command to execute
        requirement: Network requirement (VPN, public, or smart detection)
        shell: Whether to run in shell mode (default True)

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        from ..azure_devops.vpn_toggle import (
            VpnToggleContext,
            get_vpn_url_from_state,
            smart_connect_vpn,
        )
        from ..network.detection import NetworkContext, detect_network_context

        # Detect current network context
        context, _ = detect_network_context()

        # Auto-detect requirement if in smart mode
        if requirement == VpnRequirement.SMART:
            requirement = _detect_vpn_requirement_from_command(command)
            print(f"🔍 Auto-detected requirement: {requirement.value}")

        # If on corporate network, we have both internal and external access issues
        if context == NetworkContext.CORPORATE_NETWORK:
            print("🏢 On corporate network (in office)")
            if requirement == VpnRequirement.REQUIRE_PUBLIC:
                print("⚠️  Command needs public access but corporate network blocks it")
                print("   Consider connecting to a different network (e.g., mobile hotspot)")
                print("   Attempting to run anyway...")
            elif requirement == VpnRequirement.REQUIRE_VPN:
                print("✅ Internal resources accessible via corporate network")

        # Handle VPN requirements based on context
        vpn_url = get_vpn_url_from_state()

        if requirement == VpnRequirement.REQUIRE_VPN:
            # Command needs VPN - ensure it's connected
            if context == NetworkContext.REMOTE_WITHOUT_VPN:
                if vpn_url is None:
                    print("⚠️  Command needs VPN but no VPN URL configured")
                    print("   Run agdt-setup to configure VPN URL")
                    print("   Attempting to run anyway...")
                else:
                    print("🔌 Command needs VPN - connecting...")
                    success, msg = smart_connect_vpn(vpn_url)
                    if msg:
                        print(msg)
                    if not success:
                        error_msg = f"VPN connection failed: {msg}" if msg else "VPN connection failed"
                        print("❌ Unable to establish VPN connection; aborting command.")
                        return 1, "", error_msg
            # Run command (VPN now connected, or already had access)
            return _execute_command(command, shell)

        elif requirement == VpnRequirement.REQUIRE_PUBLIC:
            # Command needs public access - disconnect VPN if connected
            if context == NetworkContext.REMOTE_WITH_VPN:
                print("📡 Command needs public access - temporarily disconnecting VPN...")
                # VpnToggleContext(auto_toggle=True) disconnects on enter, reconnects on exit
                with VpnToggleContext(vpn_url=vpn_url, auto_toggle=True, verbose=True):
                    return _execute_command(command, shell)
            else:
                # Not on VPN (or on corporate network) - run as-is
                return _execute_command(command, shell)

        else:  # pragma: no cover
            # Unknown requirement - run as-is
            return _execute_command(command, shell)

    except ImportError:
        # VPN module not available - run command as-is
        print("ℹ️  VPN management not available on this platform")
        return _execute_command(command, shell)
    except Exception as e:
        print(f"⚠️  VPN management error: {e}")
        print("   Attempting to run command anyway...")
        return _execute_command(command, shell)


def _execute_command(command: str, shell: bool) -> tuple[int, str, str]:
    """
    Execute a command and return its output.

    Args:
        command: The command to execute
        shell: Whether to run in shell mode

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    print(f"\n{'=' * 70}")
    print(f"Executing: {command}")
    print(f"{'=' * 70}\n")

    try:
        if shell:
            result = subprocess.run(  # nosec B602 - shell=True is explicitly requested by the caller for shell-dependent commands
                command,
                shell=True,
                capture_output=True,
                text=True,
            )
        else:
            # Parse command into args for non-shell execution
            args = shlex.split(command)
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
            )

        # Print output in real-time style
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", flush=True)

        print(f"\n{'=' * 70}")
        print(f"Command exited with code: {result.returncode}")
        print(f"{'=' * 70}")

        return result.returncode, result.stdout, result.stderr

    except Exception as e:
        error_msg = f"Failed to execute command: {e}"
        print(f"❌ {error_msg}")
        return 1, "", error_msg
