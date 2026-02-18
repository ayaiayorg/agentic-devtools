"""
Azure CLI context management for multi-account support.

Exports all public functions for managing Azure CLI contexts.
"""

from agentic_devtools.cli.azure_context.config import (
    AzureContext,
    AzureContextConfig,
    get_context_config,
)
from agentic_devtools.cli.azure_context.management import (
    ensure_logged_in,
    get_current_context,
    run_with_context,
    show_all_contexts,
    switch_context,
)

__all__ = [
    "AzureContext",
    "AzureContextConfig",
    "get_context_config",
    "ensure_logged_in",
    "get_current_context",
    "run_with_context",
    "show_all_contexts",
    "switch_context",
]
