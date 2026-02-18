"""
Configuration for Azure CLI context management.

Defines contexts, their configurations, and helper functions.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict


class AzureContext(str, Enum):
    """Named Azure CLI contexts for different account purposes."""

    DEVOPS = "devops"
    AZURE_RESOURCES = "resources"


@dataclass(frozen=True)
class AzureContextConfig:
    """
    Configuration for an Azure CLI context.

    Attributes:
        name: Context name (matches AzureContext enum value)
        config_dir: Path to the Azure CLI config directory for this context
        expected_account_hint: Expected substring in the account UPN (e.g., "@company.com")
        description: Human-readable description of the context purpose
    """

    name: str
    config_dir: Path
    expected_account_hint: str
    description: str


def get_context_config(context: AzureContext) -> AzureContextConfig:
    """
    Get the configuration for a specific Azure context.

    Args:
        context: The Azure context to get configuration for

    Returns:
        AzureContextConfig with the context's settings

    Example:
        >>> config = get_context_config(AzureContext.DEVOPS)
        >>> print(config.config_dir)
        ~/.azure-contexts/devops
    """
    home = Path.home()
    contexts_base = home / ".azure-contexts"

    configs: Dict[AzureContext, AzureContextConfig] = {
        AzureContext.DEVOPS: AzureContextConfig(
            name="devops",
            config_dir=contexts_base / "devops",
            expected_account_hint="@swica.ch",
            description="Corporate account for Azure DevOps, Service Bus, etc.",
        ),
        AzureContext.AZURE_RESOURCES: AzureContextConfig(
            name="resources",
            config_dir=contexts_base / "resources",
            expected_account_hint="@swica.ch",
            description="AZA account for App Insights, Azure resources, Terraform, etc.",
        ),
    }

    return configs[context]
