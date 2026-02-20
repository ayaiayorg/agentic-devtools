"""
Azure CLI authentication utilities.

Provides functions to check, switch, and ensure correct Azure account
is active before running Azure CLI commands.
"""

import json
import sys
from typing import Optional, Tuple

from ..subprocess_utils import run_safe
from .config import AzureAccount


def get_current_azure_account() -> Optional[Tuple[str, str]]:
    """
    Get the currently logged in Azure account.

    Returns:
        Tuple of (account_name, account_email) or None if not logged in.
    """
    result = run_safe(
        ["az", "account", "show", "--output", "json"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return None

    try:
        data = json.loads(result.stdout)
        user_info = data.get("user", {})
        account_name = user_info.get("name", "")
        return (account_name, data.get("name", ""))
    except (json.JSONDecodeError, KeyError):
        return None


def is_aza_account(account_name: str) -> bool:
    """
    Check if the account is an AZA (elevated access) account.

    AZA accounts are identified by having 'AZA' in the username,
    typically in the format: firstname.lastname.aza@domain

    Args:
        account_name: The account username/email.

    Returns:
        True if this is an AZA account.
    """
    if not account_name:
        return False
    # AZA accounts have '.aza' in the username before the domain
    return ".aza@" in account_name.lower() or ".aza" in account_name.lower().split("@")[0]


def detect_account_type(account_name: str) -> AzureAccount:
    """
    Detect the account type from the account name.

    Args:
        account_name: The account username/email.

    Returns:
        The detected account type.
    """
    if is_aza_account(account_name):
        return AzureAccount.AZA
    return AzureAccount.NORMAL


def switch_azure_account(target_account: AzureAccount) -> bool:
    """
    Switch to a different Azure account type.

    This prompts the user to log in with the appropriate account.

    Args:
        target_account: The account type to switch to.

    Returns:
        True if switch was successful.
    """
    account_desc = "AZA (elevated access)" if target_account == AzureAccount.AZA else "normal"
    print(f"\nSwitching to {account_desc} Azure account...")
    print("A browser window will open for authentication.\n")

    result = run_safe(
        ["az", "login"],
        capture_output=False,  # Let user see the login flow
        text=True,
    )

    if result.returncode != 0:
        print("Error: Failed to switch Azure account.", file=sys.stderr)
        return False

    # Verify the new account is correct type
    current = get_current_azure_account()
    if current is None:
        print("Error: Failed to verify account after login.", file=sys.stderr)
        return False

    new_type = detect_account_type(current[0])
    if new_type != target_account:
        print(
            f"\nWarning: Expected {account_desc} account but logged in with {current[0]}",
            file=sys.stderr,
        )
        print("Please log out and try again with the correct account.", file=sys.stderr)
        return False

    print(f"Successfully switched to {account_desc} account: {current[0]}")
    return True


def ensure_azure_account(required_account: AzureAccount, auto_switch: bool = True) -> bool:
    """
    Ensure the correct Azure account is active.

    Args:
        required_account: The account type required.
        auto_switch: If True, prompt user to switch accounts when needed.

    Returns:
        True if the correct account is now active.
    """
    current = get_current_azure_account()

    if current is None:
        print("Error: Not logged in to Azure. Please run: az login", file=sys.stderr)
        if auto_switch:
            return switch_azure_account(required_account)
        return False

    current_type = detect_account_type(current[0])

    if current_type == required_account:
        return True

    # Wrong account type
    required_desc = "AZA (elevated access)" if required_account == AzureAccount.AZA else "normal"
    current_desc = "AZA" if current_type == AzureAccount.AZA else "normal"

    print(f"\nAccount mismatch: Need {required_desc} account, but logged in with {current_desc} ({current[0]})")

    if auto_switch:
        return switch_azure_account(required_account)

    print(f"Please log in with your {required_desc} account: az login", file=sys.stderr)
    return False


def verify_azure_cli() -> bool:
    """
    Verify Azure CLI is installed and working.

    Returns:
        True if Azure CLI is available.
    """
    result = run_safe(
        ["az", "version", "--output", "json"],
        capture_output=True,
        text=True,
    )

    return result.returncode == 0
