"""Analysis helpers for the agdt.analyze-workflow agent.

This package provides helper functions that the agent calls via
``python -c "..."`` one-liners to resolve analysis context, scan
identity directories for log evidence, and collect external worktree
context.
"""

from .context_resolver import (
    AnalysisContext,
    WorktreeStateDir,
    list_worktree_state_dirs,
    resolve_analysis_context,
)
from .external_context import (
    ExternalContext,
    ExternalLogEvidence,
    build_external_context_field,
    collect_external_context,
)
from .identity_scanner import (
    IdentityDir,
    LogEvidence,
    format_evidence_prefix,
    list_identity_directories,
    scan_identity_logs,
)

__all__ = [
    "AnalysisContext",
    "ExternalContext",
    "ExternalLogEvidence",
    "IdentityDir",
    "LogEvidence",
    "WorktreeStateDir",
    "build_external_context_field",
    "collect_external_context",
    "format_evidence_prefix",
    "list_identity_directories",
    "list_worktree_state_dirs",
    "resolve_analysis_context",
    "scan_identity_logs",
]
