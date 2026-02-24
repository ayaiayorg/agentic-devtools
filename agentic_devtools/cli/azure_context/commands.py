"""
CLI commands for Azure context management.

Provides entry points for agdt-azure-context-* commands.
"""

import argparse
import sys

from agentic_devtools.cli.azure_context.config import AzureContext
from agentic_devtools.cli.azure_context.management import (
    ensure_logged_in,
    get_current_context,
    show_all_contexts,
    switch_context,
)


def azure_context_use_command() -> None:
    """
    CLI command to switch to a specific Azure context.

    Usage:
        agdt-azure-context-use devops
        agdt-azure-context-use resources
    """
    parser = argparse.ArgumentParser(description="Switch to a specific Azure CLI context")
    parser.add_argument(
        "context",
        type=str,
        choices=[c.value for c in AzureContext],
        help="Azure context to switch to",
    )
    parser.add_argument(
        "--ensure-login",
        action="store_true",
        help="Ensure logged in after switching (prompts if needed)",
    )

    args = parser.parse_args()

    try:
        context = AzureContext(args.context)
        switch_context(context)
        print(f"✓ Switched to Azure context: {context.value}")

        if args.ensure_login:
            print()
            if not ensure_logged_in(context):
                print(f"\n✗ Failed to ensure login for context: {context.value}")
                sys.exit(1)

    except ValueError:  # pragma: no cover
        print(f"✗ Invalid context: {args.context}")
        print(f"Available contexts: {', '.join(c.value for c in AzureContext)}")
        sys.exit(1)


def azure_context_status_command() -> None:
    """
    CLI command to show status of all Azure contexts.

    Usage:
        agdt-azure-context-status
    """
    parser = argparse.ArgumentParser(description="Show status of all Azure CLI contexts")
    parser.parse_args()

    show_all_contexts()


def azure_context_current_command() -> None:
    """
    CLI command to show the currently active Azure context.

    Usage:
        agdt-azure-context-current
    """
    parser = argparse.ArgumentParser(description="Show the currently active Azure CLI context")
    parser.parse_args()

    current = get_current_context()
    if current:
        print(f"Current Azure context: {current.value}")
    else:
        print("No Azure context is currently set")
        print(f"Available contexts: {', '.join(c.value for c in AzureContext)}")
        print("Use: agdt-azure-context-use <context>")


def azure_context_ensure_login_command() -> None:
    """
    CLI command to ensure login for a specific context.

    Usage:
        agdt-azure-context-ensure-login devops
        agdt-azure-context-ensure-login resources
    """
    parser = argparse.ArgumentParser(description="Ensure logged in to a specific Azure CLI context")
    parser.add_argument(
        "context",
        type=str,
        nargs="?",
        choices=[c.value for c in AzureContext],
        help="Azure context to ensure login for (uses current if not specified)",
    )

    args = parser.parse_args()

    if args.context:
        try:
            context = AzureContext(args.context)
        except ValueError:  # pragma: no cover
            print(f"✗ Invalid context: {args.context}")
            print(f"Available contexts: {', '.join(c.value for c in AzureContext)}")
            sys.exit(1)
    else:
        context = get_current_context()
        if not context:
            print("✗ No Azure context is currently set")
            print("Use: agdt-azure-context-use <context>")
            sys.exit(1)

    if not ensure_logged_in(context):
        print(f"\n✗ Failed to ensure login for context: {context.value}")
        sys.exit(1)
