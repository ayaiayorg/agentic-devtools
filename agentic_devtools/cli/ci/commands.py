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
import tempfile

from agentic_devtools.cli.ci.exceptions import MalformedEventError
from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.guards import check_edit_relevance
from agentic_devtools.cli.ci.logging_config import setup_logging
from agentic_devtools.cli.ci.models import EventPayload
from agentic_devtools.cli.ci.orchestrator import run_ai_pr_loop
from agentic_devtools.cli.ci.pipeline.command import run_ai_pr_loop_v2
from agentic_devtools.cli.ci.speckit_trigger import process_speckit_label_event
from agentic_devtools.cli.subprocess_utils import run_safe


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

    # Edit-relevance preflight — skip body-only edits before any provider calls
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
    """CLI entry point for the SpecKit trigger handler.

    Reads event data from ``GITHUB_EVENT_PATH`` and ``GITHUB_EVENT_NAME``
    environment variables, constructs a GitHub Actions provider, and
    processes the SpecKit label event.

    Exit codes:
        0: Success
        1: Processing failed (script error or missing outputs)
        2: Malformed event
        10: Missing dependency or configuration
    """
    # Feature flag check
    if not _python_orchestrator_enabled():
        sys.exit(0)

    setup_logging()

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

    synthetic_event_path: str | None = None
    if event_name == "workflow_dispatch":
        event_payload = _synthesize_workflow_dispatch_event(raw_payload, repo)
        synthetic_event_path = os.environ.get("GITHUB_EVENT_PATH")
    else:
        try:
            event_payload = provider.parse_event(raw_payload, event_name)
        except MalformedEventError as exc:
            json.dump({"error": "malformed_event", "event_name": exc.event_name, "reason": exc.reason}, sys.stderr)
            sys.stderr.write("\n")
            sys.exit(2)

    try:
        exit_code = process_speckit_label_event(provider, event_payload)
    finally:
        if synthetic_event_path:
            try:
                os.unlink(synthetic_event_path)
            except OSError:
                pass
    sys.exit(exit_code)


def _synthesize_workflow_dispatch_event(raw_payload: dict, repo: str) -> EventPayload:
    """Synthesize an issues-labeled EventPayload from a workflow_dispatch event.

    Fetches issue data via ``gh api`` and writes a synthetic event file to
    ``GITHUB_EVENT_PATH`` so that ``_load_issue_context_from_event()`` can
    read the issue context as if it were a normal issues/labeled event.
    """
    inputs = raw_payload.get("inputs") or {}
    issue_number_str = str(inputs.get("issue_number", "")).strip()
    if not issue_number_str:
        print("Error: workflow_dispatch requires 'issue_number' input.", file=sys.stderr)
        sys.exit(2)

    if not issue_number_str.isdigit() or int(issue_number_str) <= 0:
        print(f"Error: 'issue_number' must be a positive integer, got: {issue_number_str!r}", file=sys.stderr)
        sys.exit(2)

    if not repo or "/" not in repo:
        print(f"Error: GITHUB_REPOSITORY must be in 'owner/repo' format, got: {repo!r}", file=sys.stderr)
        sys.exit(10)

    result = run_safe(
        ["gh", "api", f"repos/{repo}/issues/{issue_number_str}"],
        capture_output=True,
        text=True,
        shell=False,
    )
    if result.returncode != 0:
        print(f"Error: Failed to fetch issue #{issue_number_str}: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(10)

    try:
        issue_data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"Error: Failed to parse issue data: {exc}", file=sys.stderr)
        sys.exit(10)

    labels = issue_data.get("labels")
    if isinstance(labels, list):
        issue_data["labels"] = [
            label for label in labels if not (isinstance(label, dict) and label.get("name") == "speckit:processing")
        ]

    trigger_label = os.environ.get("SPECKIT_TRIGGER_LABEL", "speckit")
    synthetic_event = {"issue": issue_data, "action": "labeled", "label": {"name": trigger_label}}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(synthetic_event, f)
        os.environ["GITHUB_EVENT_PATH"] = f.name

    return EventPayload(action="labeled", trigger_label=trigger_label)
