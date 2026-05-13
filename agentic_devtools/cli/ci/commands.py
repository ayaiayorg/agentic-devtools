"""CLI entry points for CI orchestration commands.

Provides ``agdt-ai-pr-loop`` and ``agdt-speckit-trigger`` commands
that read event data from environment variables and invoke the
appropriate orchestrator functions.
"""

from __future__ import annotations

import json
import os
import shutil
import sys

from agentic_devtools.cli.ci.exceptions import MalformedEventError
from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.orchestrator import run_ai_pr_loop


def ai_pr_loop_command() -> None:
    """CLI entry point for the AI PR loop orchestrator.

    Reads event data from ``GITHUB_EVENT_PATH`` and ``GITHUB_EVENT_NAME``
    environment variables, constructs a GitHub Actions provider, and
    invokes the orchestrator.

    Controlled by ``AGDT_USE_PYTHON_ORCHESTRATOR`` feature flag:
    - "1" or "true": Use the Python orchestrator
    - Otherwise: Exit with code 0 (legacy path handles it)

    Exit codes:
        0: Success or deferred to legacy path
        1: Guard blocked
        2: Malformed event
        3: Merge blocked
        4: Metadata resolution failed
        10: Missing dependency or configuration
    """
    # Feature flag check
    flag = os.environ.get("AGDT_USE_PYTHON_ORCHESTRATOR", "").lower()
    if flag not in ("1", "true"):
        # Legacy path — let the YAML handle it
        sys.exit(0)

    # Check gh CLI dependency
    if shutil.which("gh") is None:
        print("Error: 'gh' CLI not found on PATH. Install GitHub CLI to use agdt-ai-pr-loop.", file=sys.stderr)
        sys.exit(10)

    # Read event data
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")

    if not event_path or not event_name:
        print("Error: GITHUB_EVENT_PATH and GITHUB_EVENT_NAME must be set.", file=sys.stderr)
        sys.exit(10)

    try:
        with open(event_path, encoding="utf-8") as f:
            raw_payload = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error: Failed to read event payload: {exc}", file=sys.stderr)
        sys.exit(10)

    # Determine repository
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    # Create provider and run orchestrator
    provider = GitHubActionsProvider(repo=repo)

    try:
        event_payload = provider.parse_event(raw_payload, event_name)
    except MalformedEventError as exc:
        json.dump({"error": "malformed_event", "event_name": exc.event_name, "reason": exc.reason}, sys.stderr)
        sys.stderr.write("\n")
        sys.exit(2)

    exit_code = run_ai_pr_loop(provider, event_payload)
    sys.exit(exit_code)


def speckit_trigger_command() -> None:
    """CLI entry point for the SpecKit trigger handler.

    Reads event data from ``GITHUB_EVENT_PATH`` and ``GITHUB_EVENT_NAME``
    environment variables, constructs a GitHub Actions provider, and
    processes the SpecKit label event.

    Exit codes:
        0: Success
        2: Malformed event
        10: Missing dependency or configuration
        11: Stub implementation — full logic not yet available
    """
    # Feature flag check
    flag = os.environ.get("AGDT_USE_PYTHON_ORCHESTRATOR", "").lower()
    if flag not in ("1", "true"):
        sys.exit(0)

    # Check gh CLI dependency
    if shutil.which("gh") is None:
        print("Error: 'gh' CLI not found on PATH. Install GitHub CLI to use agdt-speckit-trigger.", file=sys.stderr)
        sys.exit(10)

    # Read event data
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")

    if not event_path or not event_name:
        print("Error: GITHUB_EVENT_PATH and GITHUB_EVENT_NAME must be set.", file=sys.stderr)
        sys.exit(10)

    try:
        with open(event_path, encoding="utf-8") as f:
            raw_payload = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error: Failed to read event payload: {exc}", file=sys.stderr)
        sys.exit(10)

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    provider = GitHubActionsProvider(repo=repo)

    try:
        event_payload = provider.parse_event(raw_payload, event_name)
    except MalformedEventError as exc:
        json.dump({"error": "malformed_event", "event_name": exc.event_name, "reason": exc.reason}, sys.stderr)
        sys.stderr.write("\n")
        sys.exit(2)

    # For now, just validate the event was parseable
    # Full speckit trigger logic will be added in Phase 6
    if event_payload.trigger_label:
        print(f"SpecKit trigger: label='{event_payload.trigger_label}'")

    print(
        "Error: agdt-speckit-trigger is using a stub implementation. "
        "Full SpecKit trigger logic will be added in Phase 6.",
        file=sys.stderr,
    )
    sys.exit(11)
