"""
Jira configuration: constants, authentication, and headers.
"""

import base64
import os
from typing import Dict

# Constants
DEFAULT_JIRA_BASE_URL = "https://jira.swica.ch"
DEFAULT_PROJECT_KEY = "DFLY"
EPIC_NAME_FIELD = "customfield_10006"


def get_jira_base_url() -> str:
    """
    Get Jira base URL from state, environment, or default.

    Priority:
    1. State value 'jira_base_url'
    2. Environment variable JIRA_BASE_URL
    3. Default URL
    """
    # Import here to avoid circular dependency
    from agentic_devtools.state import get_value

    return get_value("jira_base_url") or os.environ.get("JIRA_BASE_URL") or DEFAULT_JIRA_BASE_URL


def get_jira_auth_header() -> str:
    """
    Get the Jira authorization header.

    Supports:
    - Bearer token (default): JIRA_COPILOT_PAT
    - Basic auth: JIRA_COPILOT_PAT + (JIRA_EMAIL or JIRA_USERNAME)

    Set JIRA_AUTH_SCHEME=basic for basic authentication.

    Raises:
        EnvironmentError: If required environment variables are missing
        ValueError: If unsupported auth scheme is specified
    """
    pat = os.environ.get("JIRA_COPILOT_PAT")
    if not pat:
        raise OSError("Set JIRA_COPILOT_PAT environment variable with a Jira PAT or API token")

    auth_scheme = os.environ.get("JIRA_AUTH_SCHEME", "bearer").lower()

    if auth_scheme in ("bearer", "token"):
        return f"Bearer {pat}"
    elif auth_scheme == "basic":
        identity = os.environ.get("JIRA_EMAIL") or os.environ.get("JIRA_USERNAME")
        if not identity:
            raise OSError("Set JIRA_EMAIL or JIRA_USERNAME alongside JIRA_COPILOT_PAT for basic auth")
        credentials = f"{identity}:{pat}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
        return f"Basic {encoded}"
    else:
        raise ValueError(f"Unsupported JIRA_AUTH_SCHEME: {auth_scheme}")


def get_jira_headers() -> Dict[str, str]:
    """Get HTTP headers for Jira API requests."""
    return {
        "Authorization": get_jira_auth_header(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
