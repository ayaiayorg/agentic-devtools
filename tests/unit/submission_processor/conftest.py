"""Shared fixtures and helpers for submission_processor tests."""

from unittest.mock import MagicMock

import pytest

from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewSession,
    ReviewState,
    ReviewStatus,
    SuggestionEntry,
)
from agentic_devtools.submission_manager import SubmissionItem

ORG = "https://dev.azure.com/testorg"
PROJECT = "testproject"
REPO = "testrepo"
REPO_ID = "repo-guid-123"
PR_ID = 42
FILE_PATH = "/src/app.ts"
THREAD_ID = 100
COMMENT_ID = 200


@pytest.fixture()
def config() -> AzureDevOpsConfig:
    return AzureDevOpsConfig(organization=ORG, project=PROJECT, repository=REPO)


def make_review_state(
    file_status: str = ReviewStatus.UNREVIEWED.value,
    sessions: list[ReviewSession] | None = None,
    model_id: str | None = "test-model",
    suggestions: list[SuggestionEntry] | None = None,
    commit_hash: str | None = "abc1234",
) -> ReviewState:
    file_entry = FileEntry(
        threadId=THREAD_ID,
        commentId=COMMENT_ID,
        folder="src",
        fileName="app.ts",
        status=file_status,
        suggestions=suggestions or [],
    )
    return ReviewState(
        prId=PR_ID,
        repoId=REPO_ID,
        repoName=REPO,
        project=PROJECT,
        organization=ORG,
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00Z",
        overallSummary=OverallSummary(threadId=1, commentId=2),
        folders={"src": FolderGroup(files=[FILE_PATH])},
        files={FILE_PATH: file_entry},
        commitHash=commit_hash,
        modelId=model_id,
        sessions=sessions or [],
    )


def make_item(
    outcome: str = "approve",
    summary: str = "LGTM",
    suggestions: list[dict] | None = None,
) -> SubmissionItem:
    return SubmissionItem(
        id="item-001",
        pr_id=PR_ID,
        file_path=FILE_PATH,
        outcome=outcome,
        summary=summary,
        suggestions=suggestions,
    )


def make_session(model_id: str = "claude-opus-4") -> ReviewSession:
    return ReviewSession(sessionId="sess-1", modelId=model_id, startedUtc="2026-01-01T00:00:00Z")


def setup_rmw_mock(mock_rmw: MagicMock, review_state: ReviewState) -> None:
    """Configure a mock for read_modify_write_review_state to yield the given state."""
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=review_state)
    ctx.__exit__ = MagicMock(return_value=False)
    mock_rmw.return_value = ctx
