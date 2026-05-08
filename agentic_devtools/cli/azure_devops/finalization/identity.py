"""PAT identity resolution for authorship scoping."""

from __future__ import annotations

import sys
from typing import Any


def resolve_pat_identity(organization: str, headers: dict[str, str]) -> str | None:
    """Resolve the current PAT-backed user identity via Connection Data API.

    Calls ``/_apis/connectionData`` and returns the authenticated user's
    ``id`` (GUID).  Returns ``None`` on any failure so that no mutations
    occur when authorship cannot be established.

    Args:
        organization: Azure DevOps organization root URL
            (e.g. ``https://dev.azure.com/myorg``).
        headers: Auth headers for the API call.

    Returns:
        User ID GUID string, or ``None`` if resolution fails.
    """
    try:
        from ..helpers import require_requests

        requests: Any = require_requests()
        url = f"{organization}/_apis/connectionData"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        authenticated_user = data.get("authenticatedUser", {})
        user_id = authenticated_user.get("id")
        return user_id if user_id else None
    except Exception as exc:
        print(f"Warning: Could not resolve PAT identity: {exc}", file=sys.stderr)
        return None
