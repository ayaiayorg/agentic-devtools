"""
VPN wrapper for Jira API commands.

Provides a decorator that ensures VPN is connected (or on corporate network)
before executing Jira API calls, and restores VPN state afterward.
"""

from functools import wraps
from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable)


def with_jira_vpn_context(func: F) -> F:
    """
    Decorator to wrap a function with automatic VPN management for Jira API access.

    When applied to a function that makes Jira API calls, this decorator:
    1. Checks if on corporate network - if so, no VPN action needed
    2. If at home with VPN off/suspended, connects VPN before the function runs
    3. Restores VPN to its previous state after the function completes

    Usage:
        @with_jira_vpn_context
        def my_jira_function():
            # VPN is guaranteed to be available here
            make_jira_api_call()

    This decorator is safe to use even when:
    - Already on corporate network (no-op)
    - VPN is already connected (no-op)
    - Pulse Secure is not installed (proceeds without VPN management)
    - Running on non-Windows platforms (proceeds without VPN management)
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Import VPN utilities - may fail on non-Windows or without Pulse Secure
            from ..azure_devops.vpn_toggle import (
                JiraVpnContext,
                get_vpn_url_from_state,
            )

            vpn_url = get_vpn_url_from_state()
            with JiraVpnContext(vpn_url=vpn_url, verbose=True):
                return func(*args, **kwargs)
        except ImportError:
            # VPN module not available (e.g., non-Windows platform)
            # Proceed without VPN management
            return func(*args, **kwargs)
        except Exception as e:
            # VPN management failed, but we should still try the Jira operation
            print(f"⚠️  VPN management warning: {e}")
            print("   Proceeding with Jira operation anyway...")
            return func(*args, **kwargs)

    return wrapper  # type: ignore
