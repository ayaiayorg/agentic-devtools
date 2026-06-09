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


def resolve_pat_identity_snapshot(organization: str, headers: dict[str, str]) -> dict[str, str] | None:
    """Resolve the current PAT-backed user identity snapshot via Connection Data API.

    Returns a dict with ``id``, ``uniqueName``, and ``displayName`` for
    ownership comparison and user-facing attribution.  Returns ``None`` on
    any failure so callers can fall back to 403-based detection.

    Args:
        organization: Azure DevOps organization root URL.
        headers: Auth headers for the API call.

    Returns:
        Identity snapshot dict, or ``None`` if resolution fails.
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
        if not user_id:
            return None
        properties = authenticated_user.get("properties", {})
        unique_name = properties.get("Account", {}).get("$value", "")
        display_name = authenticated_user.get("providerDisplayName", "")
        return {"id": user_id, "uniqueName": unique_name, "displayName": display_name}
    except Exception as exc:
        print(f"Warning: Could not resolve PAT identity snapshot: {exc}", file=sys.stderr)
        return None


class IdentityCache:
    """Caches the current PAT identity snapshot for the session lifetime."""

    def __init__(self) -> None:
        self._snapshot: dict[str, str] | None = None
        self._fetched: bool = False

    def get_or_fetch(self, organization: str, headers: dict[str, str]) -> dict[str, str] | None:
        """Return cached identity snapshot, fetching once if needed.

        Returns:
            Identity snapshot dict or None if fetch failed.
        """
        if not self._fetched:
            self._fetched = True
            self._snapshot = resolve_pat_identity_snapshot(organization, headers)
        return self._snapshot


def is_cross_identity(comment_author: dict[str, Any], cached_identity: dict[str, str]) -> bool:
    """Determine whether a comment author differs from the cached identity.

    Primary comparison uses ``author.id`` vs ``cached.id``.
    Falls back to ``author.uniqueName`` vs ``cached.uniqueName`` when
    ``author.id`` is missing.

    Args:
        comment_author: Author dict from an Azure DevOps comment
            (typically has ``id`` and/or ``uniqueName`` fields).
        cached_identity: Identity snapshot from ``IdentityCache``.

    Returns:
        True if the comment was authored by a different identity.
    """
    author_id = comment_author.get("id")
    cached_id = cached_identity.get("id")

    if author_id and cached_id:
        return author_id != cached_id

    # Fallback to uniqueName comparison
    author_name = comment_author.get("uniqueName", "")
    cached_name = cached_identity.get("uniqueName", "")
    if author_name and cached_name:
        return author_name.lower() != cached_name.lower()

    # Cannot determine — assume same identity (will detect via 403 later)
    return False
