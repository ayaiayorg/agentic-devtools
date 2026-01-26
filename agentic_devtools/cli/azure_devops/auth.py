"""
Azure DevOps authentication utilities.
"""

import base64
import os
from typing import Dict


def get_pat() -> str:
    """
    Get the Azure DevOps PAT from environment.

    Checks for PAT in order:
    1. AZURE_DEV_OPS_COPILOT_PAT (preferred)
    2. AZURE_DEVOPS_EXT_PAT (Azure CLI extension PAT)
    """
    pat = os.environ.get("AZURE_DEV_OPS_COPILOT_PAT")
    if not pat:
        pat = os.environ.get("AZURE_DEVOPS_EXT_PAT")
    if not pat:
        raise OSError(
            "Set AZURE_DEV_OPS_COPILOT_PAT or AZURE_DEVOPS_EXT_PAT environment variable with an Azure DevOps PAT"
        )
    return pat


def get_auth_headers(pat: str) -> Dict[str, str]:
    """Get HTTP headers for Azure DevOps API authentication."""
    encoded = base64.b64encode(f":{pat}".encode("ascii")).decode("ascii")
    return {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json",
    }
