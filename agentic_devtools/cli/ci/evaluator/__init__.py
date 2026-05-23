"""Post-agent Copilot review evaluator.

Provides programmatic classification and remediation of PR state after
a Copilot agent session completes without proper finalization.

Public API:
- :func:`classify_post_agent_state` — pure classification function
- :func:`build_snapshot` — gathers PR state into an immutable snapshot
- :func:`dispatch_action` — executes the appropriate remediation
- :func:`evaluate_post_agent_state_command` — CLI entry point
"""

from .actions import dispatch_action
from .classifier import classify_post_agent_state
from .command import evaluate_post_agent_state_command
from .models import (
    CommentInfo,
    EvaluationResult,
    PostAgentAction,
    PostAgentClassification,
    PostAgentSnapshot,
    ThreadInfo,
)
from .snapshot import build_snapshot

__all__ = [
    "CommentInfo",
    "EvaluationResult",
    "PostAgentAction",
    "PostAgentClassification",
    "PostAgentSnapshot",
    "ThreadInfo",
    "build_snapshot",
    "classify_post_agent_state",
    "dispatch_action",
    "evaluate_post_agent_state_command",
]
