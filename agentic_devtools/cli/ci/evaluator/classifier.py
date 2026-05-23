"""Post-agent state classifier.

Contains the pure classification function that determines the PR state
after a Copilot agent session. This function performs zero I/O and is
fully unit-testable.
"""

from __future__ import annotations

from .models import PostAgentClassification, PostAgentSnapshot


def classify_post_agent_state(snapshot: PostAgentSnapshot) -> PostAgentClassification:
    """Classify the post-agent PR state into a remediation category.

    This is a pure function — no I/O, no side effects. All decision logic
    for the post-agent evaluator lives here.

    Classification priority:
    1. Concurrent evaluation check (lock held by another run)
    2. Complete (sentinel already present)
    3. Threads resolved but no sentinel
    4. Agent claims fixed (comment present, no code change, unresolved threads)
    5. Changes made but threads still unresolved
    6. Agent silent (fallback)

    Args:
        snapshot: Immutable snapshot of PR state.

    Returns:
        The classification enum value.
    """
    # 1. If another evaluator holds the lock, skip
    if snapshot.lock_holder:
        return PostAgentClassification.concurrent_evaluation_skipped

    # 2. If sentinel is present, the agent completed correctly
    if snapshot.has_sentinel:
        return PostAgentClassification.complete

    # Determine thread states
    unresolved_threads = [t for t in snapshot.threads if not t.is_resolved]
    all_threads_resolved = len(unresolved_threads) == 0 and len(snapshot.threads) > 0

    # 3. All threads resolved but no sentinel posted
    if all_threads_resolved and not snapshot.has_sentinel:
        return PostAgentClassification.threads_resolved_no_sentinel

    # 4. Agent left a comment claiming fixed, but threads still unresolved
    if snapshot.latest_agent_comment is not None and not snapshot.head_changed_since_review and unresolved_threads:
        return PostAgentClassification.agent_claims_fixed_no_sentinel

    # 5. Code was changed but threads remain unresolved
    if snapshot.head_changed_since_review and unresolved_threads:
        return PostAgentClassification.changes_made_threads_unresolved

    # 6. Fallback: agent didn't respond meaningfully
    return PostAgentClassification.agent_silent
