"""
Azure CLI context management functions.

Provides functions to switch contexts, check login status, and execute commands.
"""

import json
import os
import subprocess
from typing import Dict, Optional, Tuple

from agentic_devtools.cli.azure_context.config import (
    AzureContext,
    get_context_config,
)
from agentic_devtools.state import get_value, set_value


def get_current_context() -> Optional[AzureContext]:
    """
    Get the currently active Azure context from state.

    Returns:
        The active AzureContext, or None if no context is set
    """
    context_name = get_value("azure.context")
    if context_name:
        try:
            return AzureContext(context_name)
        except ValueError:
            return None
    return None


def switch_context(context: AzureContext) -> None:
    """
    Switch to a specific Azure context.

    This updates the state to track the active context. The actual environment
    variables are set when running commands with run_with_context().

    Args:
        context: The Azure context to switch to
    """
    set_value("azure.context", context.value)


def get_context_env(context: AzureContext) -> Dict[str, str]:
    """
    Get environment variables for a specific Azure context.

    Args:
        context: The Azure context to get environment for

    Returns:
        Dictionary of environment variables to set
    """
    config = get_context_config(context)

    # Ensure the config directory exists
    config.config_dir.mkdir(parents=True, exist_ok=True)

    return {
        "AZURE_CONFIG_DIR": str(config.config_dir),
    }


def check_login_status(context: AzureContext) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Check if the Azure CLI is logged in for a specific context.

    Args:
        context: The Azure context to check

    Returns:
        Tuple of (is_logged_in, account_name, error_message)
        - is_logged_in: True if logged in and token is valid
        - account_name: The logged-in account name (or None)
        - error_message: Error message if not logged in (or None)
    """
    config = get_context_config(context)
    env = get_context_env(context)

    # Merge with current environment
    cmd_env = os.environ.copy()
    cmd_env.update(env)

    try:
        result = subprocess.run(
            ["az", "account", "show"],
            capture_output=True,
            text=True,
            env=cmd_env,
            check=False,
        )

        if result.returncode == 0:
            account_info = json.loads(result.stdout)
            account_name = account_info.get("user", {}).get("name", "Unknown")
            return True, account_name, None
        else:
            error_msg = result.stderr.strip() or "Not logged in"
            return False, None, error_msg

    except (subprocess.SubprocessError, json.JSONDecodeError) as e:
        return False, None, str(e)


def ensure_logged_in(context: AzureContext) -> bool:
    """
    Ensure the Azure CLI is logged in for a specific context.

    Checks if already logged in. If not, prompts the user to log in.

    Args:
        context: The Azure context to ensure login for

    Returns:
        True if logged in successfully, False otherwise
    """
    is_logged_in, account_name, error = check_login_status(context)

    if is_logged_in:
        print(f"✓ Already logged in as: {account_name}")
        return True

    print(f"✗ Not logged in to context '{context.value}': {error}")
    print("\nPlease log in using: az login (with AZURE_CONFIG_DIR set)")

    config = get_context_config(context)
    env = get_context_env(context)

    # Merge with current environment
    cmd_env = os.environ.copy()
    cmd_env.update(env)

    print("\nExecuting: az login")
    print(f"Using config directory: {config.config_dir}")

    try:
        result = subprocess.run(
            ["az", "login"],
            env=cmd_env,
            check=False,
        )

        if result.returncode == 0:
            # Verify login succeeded
            is_logged_in, account_name, _ = check_login_status(context)
            if is_logged_in:
                print(f"\n✓ Successfully logged in as: {account_name}")
                return True
            else:
                print("\n✗ Login command succeeded but account verification failed")
                return False
        else:
            print(f"\n✗ Login failed with exit code: {result.returncode}")
            return False

    except subprocess.SubprocessError as e:  # pragma: no cover
        print(f"\n✗ Login failed: {e}")
        return False


def show_all_contexts() -> None:
    """
    Display all available Azure contexts with their login status.

    Shows:
    - Context name and description
    - Login status (logged in or not)
    - Account name if logged in
    - Whether it's the currently active context
    """
    current = get_current_context()

    print("Azure CLI Contexts:")
    print("=" * 80)

    for context in AzureContext:
        config = get_context_config(context)
        is_logged_in, account_name, error = check_login_status(context)

        # Mark current context
        current_marker = " [ACTIVE]" if current == context else ""

        print(f"\n{context.value}{current_marker}")
        print(f"  Description: {config.description}")
        print(f"  Config Dir:  {config.config_dir}")

        if is_logged_in:
            print(f"  Status:      ✓ Logged in as {account_name}")
        else:
            print(f"  Status:      ✗ Not logged in ({error})")

    print("\n" + "=" * 80)
    print("\nTo switch contexts: agdt-azure-context-use <context>")
    print("To log in: Ensure context is active, then run 'az login'")


def run_with_context(context: AzureContext, command: list) -> subprocess.CompletedProcess:
    """
    Execute a shell command with the specified Azure context.

    Args:
        context: The Azure context to use
        command: Command to execute as a list of arguments

    Returns:
        CompletedProcess result from subprocess.run

    Example:
        >>> result = run_with_context(
        ...     AzureContext.DEVOPS,
        ...     ["az", "account", "show"]
        ... )
        >>> print(result.stdout)
    """
    env = get_context_env(context)

    # Merge with current environment
    cmd_env = os.environ.copy()
    cmd_env.update(env)

    return subprocess.run(
        command,
        env=cmd_env,
        capture_output=True,
        text=True,
        check=False,
    )
