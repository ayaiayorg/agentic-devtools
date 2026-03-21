"""``agdt-review consolidate`` — conflict resolution command.

The consolidator resolves conflicts between reviewer models. It has full
access to source code and file diffs (same as reviewers) but uses
resolution-specific logic, not review logic.

.. note::
    The actual LLM API call is **stubbed out** in this implementation.
    The function signature and data flow are complete, but the API call
    returns a mock resolution result.
"""

import logging
import sys
from pathlib import Path

from agentic_devtools.cli.azure_devops.review_attribution import (
    format_status,
    should_use_emoji,
)
from agentic_devtools.cli.azure_devops.review_config import (
    ReviewConfigError,
    load_review_config,
)

logger = logging.getLogger(__name__)


def _load_amendment_replies(pr_id: int) -> dict:
    """Load amendment replies from review-state.json.

    .. note::
        Stub — reads from the local review state file in production.
    """
    # TODO: Wire to load_review_state() and extract amendment replies.
    logger.info("Loading amendment replies for PR %d", pr_id)
    return {}


def _build_consolidation_prompt(
    pr_id: int,
    amendment_replies: dict,
) -> str:
    """Build the structured prompt for the consolidator.

    The prompt includes: file diff, current commit review threads,
    other threads, and advisory consensus information.

    .. note::
        Stub — builds a placeholder prompt.
    """
    # TODO: Wire to actual prompt construction with file diffs and threads.
    return f"Consolidation prompt for PR {pr_id} with {len(amendment_replies)} files"


def _invoke_consolidator_model(
    model_id: str,
    prompt: str,
) -> dict:
    """Send prompt to the consolidator model and receive resolution.

    .. note::
        **Stubbed out** — returns a mock resolution result.
        The function signature and data flow are complete.

    Args:
        model_id: The consolidator model identifier.
        prompt: The structured consolidation prompt.

    Returns:
        A dictionary with resolution results per file.
    """
    # TODO: Wire to actual LLM API call for consolidation.
    logger.info("Invoking consolidator model %s (STUB)", model_id)
    return {"resolution": "mock", "files_resolved": 0}


def _apply_resolution(pr_id: int, resolution: dict) -> None:
    """Apply the consolidation resolution.

    Steps:
    1. PATCH main comments with resolved content.
    2. Delete all amendment replies.
    3. Set final file statuses.
    4. Trigger cascade to folder/PR summaries.

    .. note::
        Stub — logs the resolution but does not perform API calls.
    """
    # TODO: Wire to actual Azure DevOps API calls for PATCHing comments,
    # deleting amendments, and setting statuses.
    logger.info(
        "Applying resolution for PR %d: %s (STUB)",
        pr_id,
        resolution,
    )


def run_consolidate(pr_id: int, model_id: str | None = None) -> None:
    """Execute consolidation for a PR.

    Args:
        pr_id: Pull request ID.
        model_id: Optional consolidator model ID override. If not provided,
            the consolidator model is loaded from the repo config.
    """
    use_emoji = should_use_emoji()

    # Resolve the effective model ID from config when not provided.
    effective_model_id = model_id
    if not effective_model_id:
        try:
            config = load_review_config(Path.cwd())
        except ReviewConfigError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        if config.consolidation:
            effective_model_id = config.consolidation.model_id
        else:
            effective_model_id = config.reviewers[0].model_id if config.reviewers else "unknown"

    print("=" * 60)
    print(f"CONSOLIDATION — PR {pr_id}")
    print(f"Status: {format_status('in-progress', use_emoji=use_emoji)}")
    print("=" * 60)
    print(f"Consolidator model: {effective_model_id}")

    # Step 1: Load amendment replies
    amendment_replies = _load_amendment_replies(pr_id)
    if not amendment_replies:
        print("No amendment replies found. Consolidation not needed.")
        return

    # Step 2: Build prompt
    prompt = _build_consolidation_prompt(pr_id, amendment_replies)

    # Step 3: Invoke consolidator model (STUB)
    resolution = _invoke_consolidator_model(effective_model_id, prompt)

    # Step 4: Apply resolution
    _apply_resolution(pr_id, resolution)

    print()
    # TODO: Replace with actual terminal status from consolidation results.
    status_text = format_status("in-progress", use_emoji=use_emoji)
    print(f"Consolidation complete (stub). Status: {status_text}")
