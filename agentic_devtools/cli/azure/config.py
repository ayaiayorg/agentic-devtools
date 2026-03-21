"""
Azure CLI configuration for different environments.

Defines Application Insights instances and Azure account mappings per environment.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AzureAccount(Enum):
    """Azure account types for different operations."""

    NORMAL = "normal"  # Default account for Azure DevOps, general operations
    AZA = "aza"  # Elevated access account for App Insights, resource queries


@dataclass(frozen=True)
class AppInsightsConfig:
    """Configuration for an Application Insights instance."""

    name: str  # Resource name (e.g., "appi-mgmt-dev-chn-1")
    resource_group: str  # Resource group (e.g., "rg-mgmt-dev-chn-1-logs")
    subscription: str  # Subscription name or ID
    subscription_id: str  # Subscription GUID for REST API calls
    environment: str  # DEV, INT, or PROD

    @property
    def resource_id(self) -> str:
        """Get the full Azure resource ID for this Application Insights instance."""
        return (
            f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}"
            f"/providers/Microsoft.Insights/components/{self.name}"
        )


# Application Insights configurations per environment
APP_INSIGHTS_CONFIG = {
    "DEV": AppInsightsConfig(
        name="appi-mgmt-dev-chn-1",
        resource_group="rg-mgmt-dev-chn-1-logs",
        subscription="dflmgmt-dev-1",
        subscription_id="b72ea43e-5adc-4a61-bdda-3b090cca5f7a",
        environment="DEV",
    ),
    "INT": AppInsightsConfig(
        name="appi-mgmt-int-chn-1",
        resource_group="rg-mgmt-int-chn-1-logs",
        subscription="dflmgmt-int-1",
        subscription_id="1e84831e-a46e-41d5-80e0-280ccb11da78",
        environment="INT",
    ),
    "PROD": AppInsightsConfig(
        name="appi-mgmt-prod-chn-1",
        resource_group="rg-mgmt-prod-chn-1-logs",
        subscription="dflmgmt-prod-1",
        subscription_id="0f04e0a2-2d2b-4521-967f-c44a6ab2ee32",
        environment="PROD",
    ),
}


def get_account_for_environment(environment: str) -> AzureAccount:
    """
    Get the required Azure account for querying an environment.

    For Application Insights queries, the AZA account is always required
    because these are read operations on production-sensitive data.

    Args:
        environment: The environment (DEV, INT, PROD).

    Returns:
        The Azure account type required.
    """
    # All App Insights queries require AZA account
    return AzureAccount.AZA


def get_app_insights_config(environment: str) -> Optional[AppInsightsConfig]:
    """
    Get Application Insights configuration for an environment.

    Args:
        environment: The environment (DEV, INT, PROD).

    Returns:
        The Application Insights configuration, or None if not found.
    """
    return APP_INSIGHTS_CONFIG.get(environment.upper())
