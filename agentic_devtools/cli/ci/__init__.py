"""CI platform provider abstraction.

This package provides a CI-platform-agnostic interface for orchestrating
PR workflows, CI check polling, review/merge gates, and related automation.

Public API:
    - CIPlatformProvider: Abstract base class for CI platform providers
    - GitHubActionsProvider: GitHub Actions implementation
    - EventPayload, PRMetadata, CheckRunStatus, ReviewInfo: Data models
    - MalformedEventError, ProviderRateLimitError: Exception types
    - RetryableError, retry_with_backoff: Retry utilities
    - Guards: check_privileged_paths, check_docker_files, etc.
    - Orchestrator: run_ai_pr_loop
"""

from agentic_devtools.cli.ci.ado_provider import AzureDevOpsProvider
from agentic_devtools.cli.ci.exceptions import (
    MalformedEventError,
    ProviderRateLimitError,
)
from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.guards import (
    check_cycle_limit,
    check_deduplication,
    check_docker_files,
    check_exclusion_labels,
    check_fork_pr,
    check_privileged_paths,
)
from agentic_devtools.cli.ci.models import (
    CheckRunStatus,
    EventPayload,
    PRMetadata,
    RepairDecision,
    ReviewInfo,
)
from agentic_devtools.cli.ci.orchestrator import run_ai_pr_loop
from agentic_devtools.cli.ci.provider import CIPlatformProvider
from agentic_devtools.cli.ci.retry import RetryableError, retry_with_backoff

__all__ = [
    "AzureDevOpsProvider",
    "CIPlatformProvider",
    "CheckRunStatus",
    "EventPayload",
    "GitHubActionsProvider",
    "MalformedEventError",
    "PRMetadata",
    "ProviderRateLimitError",
    "RepairDecision",
    "RetryableError",
    "ReviewInfo",
    "check_cycle_limit",
    "check_deduplication",
    "check_docker_files",
    "check_exclusion_labels",
    "check_fork_pr",
    "check_privileged_paths",
    "retry_with_backoff",
    "run_ai_pr_loop",
]
