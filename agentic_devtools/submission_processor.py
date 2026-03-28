"""Submission Manager worker processor for file review submissions.

Implements the processor callable injected into the ``SubmissionManager``
from :mod:`agentic_devtools.submission_manager`.  The processor receives a
``SubmissionItem`` and executes the full PATCH cascade for a single file
review submission: load review state, update file status/summary/suggestions,
POST suggestion threads for request-changes outcomes, PATCH the scaffolded
file summary comment, PATCH the file thread status, mark the file as
reviewed in Azure DevOps, cascade the overall PR summary, and persist state
atomically via ``read_modify_write_review_state()``.

A companion factory ``create_review_processor()`` captures stable
dependencies (config, auth headers, repo_id) at construction time so the
inner closure can be called safely from the worker thread.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .cli.azure_devops.config import AzureDevOpsConfig
from .cli.azure_devops.helpers import build_thread_context, patch_comment, patch_thread_status
from .cli.azure_devops.mark_reviewed import mark_file_reviewed
from .cli.azure_devops.review_attribution import build_commit_file_url, build_commit_pr_url
from .cli.azure_devops.review_scaffold import build_pr_base_url
from .cli.azure_devops.review_state import (
    ReviewStatus,
    SuggestionEntry,
    VerdictType,
    add_suggestion_to_file,
    clear_suggestions_for_re_review,
    normalize_file_path,
    read_modify_write_review_state,
    update_file_status,
)
from .cli.azure_devops.review_templates import render_file_summary
from .cli.azure_devops.status_cascade import cascade_status_update, execute_cascade
from .cli.azure_devops.verdict_protocol import record_verdict
from .submission_manager import SubmissionItem

# Valid outcome strings (compared case-insensitively)
_APPROVE = "approve"
_REQUEST_CHANGES = "request-changes"
_REQUEST_CHANGES_WITH_SUGGESTION = "request-changes-with-suggestion"

_VALID_OUTCOMES = frozenset({_APPROVE, _REQUEST_CHANGES, _REQUEST_CHANGES_WITH_SUGGESTION})


def _get_attribution_params(
    review_state: Any,
    config: AzureDevOpsConfig,
    file_path: str | None = None,
) -> dict[str, str | None]:
    """Extract attribution parameters from ReviewState for comment rendering.

    Replicates the logic from ``file_review_commands._get_attribution_params()``
    so the processor can run independently of CLI internals.

    Returns a dict with keys ``model_name``, ``commit_hash``, and ``commit_url``
    suitable for unpacking into ``render_file_summary()`` and
    ``render_overall_summary()``.
    """
    model_name: str | None
    if getattr(review_state, "sessions", None):
        model_name = review_state.sessions[-1].modelId
    else:
        model_name = getattr(review_state, "modelId", None)

    commit_hash = review_state.commitHash
    commit_url: str | None = None
    if commit_hash and review_state.latestIterationId:
        try:
            if file_path:
                normalized = normalize_file_path(file_path)
                commit_url = build_commit_file_url(
                    config.organization,
                    config.project,
                    config.repository,
                    review_state.prId,
                    normalized,
                    review_state.latestIterationId,
                )
            else:
                commit_url = build_commit_pr_url(
                    config.organization,
                    config.project,
                    config.repository,
                    review_state.prId,
                    review_state.latestIterationId,
                )
        except Exception:
            commit_url = None
    return {"model_name": model_name, "commit_hash": commit_hash, "commit_url": commit_url}


def process_submission(
    item: SubmissionItem,
    config: AzureDevOpsConfig,
    headers: dict[str, str],
    repo_id: str,
    requests_module: Any = None,
) -> None:
    """Execute the full PATCH cascade for a single file review submission.

    This is the core processor function called by the ``SubmissionManager``
    worker thread.  It loads review state under an exclusive lock, updates
    the file status/summary/suggestions, POSTs suggestion threads for
    request-changes outcomes, PATCHes the scaffolded file summary comment
    and thread status, marks the file as reviewed, and cascades the overall
    PR summary.

    Args:
        item: The ``SubmissionItem`` to process.
        config: Azure DevOps configuration (org/project/repository).
        headers: Auth headers for API calls.
        repo_id: Azure DevOps repository ID.
        requests_module: Optional requests module for test injection.
            Defaults to ``import requests`` at runtime.

    Raises:
        ValueError: If ``item.outcome`` is not a recognized outcome.
        FileNotFoundError: If ``review-state.json`` does not exist.
        KeyError: If the file is not present in the review state.
    """
    if requests_module is None:
        import requests as _requests

        requests_module = _requests

    outcome = item.outcome.lower()
    if outcome not in _VALID_OUTCOMES:
        raise ValueError(f"Unknown outcome: {item.outcome!r}")

    is_approve = outcome == _APPROVE
    status = ReviewStatus.APPROVED.value if is_approve else ReviewStatus.NEEDS_WORK.value
    thread_status = "closed" if is_approve else "active"

    with read_modify_write_review_state(item.pr_id) as review_state:
        base_url = build_pr_base_url(config, item.pr_id)

        # Re-review: rotate old suggestions to audit trail.  The KeyError is
        # caught and ignored here because the file may not exist yet in state
        # (e.g. new file added after scaffolding).  The subsequent
        # update_file_status() will raise KeyError with a clear message if
        # the file is truly missing — that error is intentionally NOT caught
        # so the SubmissionManager marks the item as FAILED.
        try:
            clear_suggestions_for_re_review(review_state, item.file_path)
        except KeyError:
            pass

        update_file_status(review_state, item.file_path, status, summary=item.summary)

        normalized = normalize_file_path(item.file_path)
        file_entry = review_state.files[normalized]

        # POST suggestion threads for request-changes outcomes
        if not is_approve and item.suggestions:
            existing = file_entry.suggestions

            def _already_posted(line, end_line, severity, content, out_of_scope, link_text):
                for e in existing:
                    if (
                        e.line == line
                        and e.endLine == end_line
                        and e.severity == severity
                        and e.content == content
                        and e.outOfScope == out_of_scope
                        and e.linkText == link_text
                    ):
                        return True
                return False

            threads_url = config.build_api_url(repo_id, "pullRequests", item.pr_id, "threads")
            for s in item.suggestions:
                line = s["line"]
                end_line = s.get("end_line", line)
                severity = s["severity"]
                out_of_scope = s.get("out_of_scope", False)
                content = s["content"]

                if s.get("link_text"):
                    link_text = s["link_text"]
                elif end_line != line:
                    link_text = f"lines {line} - {end_line}"
                else:
                    link_text = f"line {line}"

                if _already_posted(line, end_line, severity, content, out_of_scope, link_text):
                    continue

                thread_context = build_thread_context(normalized, line, end_line)
                thread_body = {
                    "comments": [{"content": content, "commentType": "text"}],
                    "status": "active",
                    "threadContext": thread_context,
                }
                response = requests_module.post(threads_url, headers=headers, json=thread_body, timeout=30)
                response.raise_for_status()
                result = response.json()
                thread_id = result["id"]
                comment_id = result["comments"][0]["id"]

                add_suggestion_to_file(
                    review_state,
                    item.file_path,
                    SuggestionEntry(
                        threadId=thread_id,
                        commentId=comment_id,
                        line=line,
                        endLine=end_line,
                        severity=severity,
                        outOfScope=out_of_scope,
                        linkText=link_text,
                        content=content,
                    ),
                )

        # Record verdict when a model ID is available
        if review_state.sessions:
            model_id = review_state.sessions[-1].modelId
        else:
            model_id = getattr(review_state, "modelId", None)
        if model_id:
            record_verdict(file_entry, model_id, VerdictType.AGREE, status)

        # PATCH file summary comment
        attrs = _get_attribution_params(review_state, config, file_path=item.file_path)
        suggestions_for_render = [] if is_approve else file_entry.suggestions
        file_content = render_file_summary(file_entry, suggestions_for_render, base_url, **attrs)
        patch_comment(
            requests_module=requests_module,
            headers=headers,
            config=config,
            repo_id=repo_id,
            pull_request_id=item.pr_id,
            thread_id=file_entry.threadId,
            comment_id=file_entry.commentId,
            new_content=file_content,
        )

        # PATCH file thread status
        patch_thread_status(
            requests_module=requests_module,
            headers=headers,
            config=config,
            repo_id=repo_id,
            pull_request_id=item.pr_id,
            thread_id=file_entry.threadId,
            status=thread_status,
        )

        # Mark file as reviewed in Azure DevOps
        mark_file_reviewed(
            file_path=item.file_path,
            pull_request_id=item.pr_id,
            config=config,
            repo_id=repo_id,
        )

        # Cascade overall PR summary
        cascade_attrs = _get_attribution_params(review_state, config)
        patch_operations = cascade_status_update(review_state, item.file_path, base_url, **cascade_attrs)
        execute_cascade(
            patch_operations=patch_operations,
            requests_module=requests_module,
            headers=headers,
            config=config,
            repo_id=repo_id,
            pull_request_id=item.pr_id,
        )


def create_review_processor(
    config: AzureDevOpsConfig,
    headers: dict[str, str],
    repo_id: str,
    requests_module: Any = None,
) -> Callable[[SubmissionItem], None]:
    """Factory that captures stable dependencies and returns a processor callable.

    The returned callable matches the ``Callable[[SubmissionItem], None]``
    signature expected by ``SubmissionManager.__init__()``.

    Args:
        config: Azure DevOps configuration.
        headers: Auth headers for API calls.
        repo_id: Azure DevOps repository ID.
        requests_module: Optional requests module for test injection.

    Returns:
        A callable that processes a single ``SubmissionItem``.
    """

    def _processor(item: SubmissionItem) -> None:
        process_submission(item, config, headers, repo_id, requests_module=requests_module)

    return _processor
