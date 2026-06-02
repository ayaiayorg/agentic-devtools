"""CLI entry points for CI orchestration commands.

Provides ``agdt-ai-pr-loop`` and ``agdt-speckit-trigger`` commands
that read event data from environment variables and invoke the
appropriate orchestrator functions.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys

from agentic_devtools.cli.ci.exceptions import MalformedEventError
from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.guards import check_edit_relevance
from agentic_devtools.cli.ci.logging_config import setup_logging
from agentic_devtools.cli.ci.orchestrator import run_ai_pr_loop
from agentic_devtools.cli.ci.pipeline.command import run_ai_pr_loop_v2
from agentic_devtools.cli.ci.speckit_trigger import DEPRECATION_MESSAGE


def _python_orchestrator_enabled() -> bool:
    """Return True when the Python CI orchestrator path is enabled."""
    return os.environ.get("AGDT_USE_PYTHON_ORCHESTRATOR", "").lower() in ("1", "true")


def _pipeline_v2_enabled() -> bool:
    """Return True when the idempotent pipeline v2 is enabled."""
    return os.environ.get("AGDT_USE_PIPELINE_V2", "").lower() in ("1", "true")


def ai_pr_loop_command() -> None:
    """CLI entry point for the AI PR loop orchestrator.

    Reads event data from ``GITHUB_EVENT_PATH`` and ``GITHUB_EVENT_NAME``
    environment variables, constructs a GitHub Actions provider, and
    invokes the appropriate orchestrator or pipeline.

    Routing is controlled by two feature flags, evaluated in order:

    1. ``AGDT_USE_PYTHON_ORCHESTRATOR`` must be ``"1"`` or ``"true"`` to
       activate any Python-side processing.  When absent/false the function
       exits with code 0 so the legacy YAML path handles the run.

    2. ``AGDT_USE_PIPELINE_V2`` (requires flag 1 to be set): when ``"1"``
       or ``"true"``, routes to the idempotent action-evaluator pipeline
       (``run_ai_pr_loop_v2``).  Otherwise routes to the event-branching
       orchestrator (``run_ai_pr_loop``).

    Exit codes:
        0: Success or deferred to legacy path
        1: Guard blocked
        2: Malformed event
        3: Merge blocked
        4: Metadata resolution failed
        5: Repair dispatched
        10: Missing dependency or configuration
    """
    # Feature flag check
    if not _python_orchestrator_enabled():
        # Legacy path — let the YAML handle it
        sys.exit(0)

    setup_logging()

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

    # Edit-relevance preflight — skip body-only edits before orchestrator calls
    should_skip, skip_reason = check_edit_relevance(event_payload)
    if should_skip:
        logger = logging.getLogger(__name__)
        logger.info("PR #%d: %s", event_payload.pr_number, skip_reason)
        sys.exit(0)

    if _pipeline_v2_enabled():
        exit_code = run_ai_pr_loop_v2(provider, event_payload)
    else:
        exit_code = run_ai_pr_loop(provider, event_payload)
    sys.exit(exit_code)


def speckit_trigger_command() -> None:
    """CLI entry point for the SpecKit trigger handler — DEPRECATED.

    This command is deprecated. Phase 1 is now handled by the unified
    ``speckit-phase-progression.yml`` workflow. The ``speckit-issue-trigger.yml``
    workflow dispatches to it directly via ``workflow_dispatch``.

    Exit codes:
        1: Always exits with 1 to indicate deprecation
    """
    print(f"Error: {DEPRECATION_MESSAGE}", file=sys.stderr)
    sys.exit(1)
