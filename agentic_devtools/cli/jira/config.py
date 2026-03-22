"""
Jira configuration: constants, authentication, and headers.
"""

import base64
import os
import re

EPIC_NAME_FIELD = "customfield_10006"


def get_jira_project_keys() -> list[str]:
    """Return configured Jira project keys as a list of uppercase strings.

    Priority:
    1. Project config ``jira_project_keys``
    2. State value ``jira_project_keys``
    3. Environment variable ``JIRA_PROJECT_KEYS``
    4. Empty list (generic fallback)

    The config value is a comma-separated string (e.g. ``"ACME,PROJ"``).
    """
    from agentic_devtools.cli.config.project_config import get_project_config_value
    from agentic_devtools.state import get_value

    raw = (
        get_project_config_value("jira_project_keys")
        or get_value("jira_project_keys")
        or os.environ.get("JIRA_PROJECT_KEYS")
    )
    if not raw:
        return []
    return [k.strip().upper() for k in raw.split(",") if k.strip()]


def build_jira_issue_pattern(project_keys: list[str]) -> re.Pattern[str]:
    """Build a compiled regex for matching Jira issue keys.

    If *project_keys* is non-empty the pattern matches only those projects
    (e.g. ``((?:ACME|PROJ)-\\d+)``).  Otherwise a generic pattern
    ``([A-Z]{2,10}-\\d+)`` is used.
    """
    if project_keys:
        alternation = "|".join(re.escape(k) for k in project_keys)
        return re.compile(rf"((?:{alternation})-\d+)", re.IGNORECASE)
    return re.compile(r"([A-Z]{2,10}-\d+)", re.IGNORECASE)


def get_jira_base_url() -> str:
    """
    Get Jira base URL from project config, state, or environment.

    Priority:
    1. Project config ``jira_base_url``
    2. State value ``jira_base_url``
    3. Environment variable ``JIRA_BASE_URL``
    4. Raises ``ValueError`` if unconfigured

    Raises:
        ValueError: If no Jira base URL is configured anywhere.
    """
    from agentic_devtools.cli.config.project_config import get_project_config_value
    from agentic_devtools.state import get_value

    url = get_project_config_value("jira_base_url") or get_value("jira_base_url") or os.environ.get("JIRA_BASE_URL")
    if url:
        return url
    raise ValueError("Jira base URL not configured. Run agdt-setup or set JIRA_BASE_URL.")


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


def get_jira_headers() -> dict[str, str]:
    """Get HTTP headers for Jira API requests."""
    return {
        "Authorization": get_jira_auth_header(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
