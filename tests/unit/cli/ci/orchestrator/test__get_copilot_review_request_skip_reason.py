"""Tests for _get_copilot_review_request_skip_reason."""

from dataclasses import dataclass, field

from agentic_devtools.cli.ci.orchestrator import _get_copilot_review_request_skip_reason


@dataclass
class _PRMetadata:
    number: int = 1
    title: str = "Test PR"
    head_branch: str = "feature"
    head_sha: str = "abc123"
    base_branch: str = "main"
    labels: list[str] = field(default_factory=list)
    requested_reviewers: list[str] = field(default_factory=list)
    is_draft: bool = False


@dataclass
class _ReviewInfo:
    id: int = 1
    user: str = "Copilot"
    state: str = "COMMENTED"
    body: str = ""
    commit_sha: str = ""


class TestGetCopilotReviewRequestSkipReason:
    """Tests for _get_copilot_review_request_skip_reason."""

    def test_returns_none_when_no_skip_reason(self):
        """Returns None when no skip condition is met."""
        pr_meta = _PRMetadata(requested_reviewers=["some-user"])
        result = _get_copilot_review_request_skip_reason(pr_meta, None)
        assert result is None

    def test_returns_copilot_already_requested(self):
        """Returns reason when Copilot is already a requested reviewer."""
        pr_meta = _PRMetadata(requested_reviewers=["Copilot"])
        result = _get_copilot_review_request_skip_reason(pr_meta, None)
        assert result == "copilot_already_requested"

    def test_returns_copilot_no_reviewable_files(self):
        """Returns reason when Copilot commented it can't review files."""
        pr_meta = _PRMetadata(requested_reviewers=[])
        review = _ReviewInfo(
            user="Copilot",
            state="COMMENTED",
            body="I wasn\u2019t able to review any files in this pull request.",
        )
        result = _get_copilot_review_request_skip_reason(pr_meta, review)
        assert result == "copilot_no_reviewable_files"

    def test_no_skip_when_review_state_not_commented(self):
        """Does not skip if review state is not COMMENTED."""
        pr_meta = _PRMetadata(requested_reviewers=[])
        review = _ReviewInfo(
            user="Copilot",
            state="APPROVED",
            body="wasn't able to review any files",
        )
        result = _get_copilot_review_request_skip_reason(pr_meta, review)
        assert result is None

    def test_returns_repair_dispatched(self):
        """Returns reason when a repair was already dispatched in this run."""
        pr_meta = _PRMetadata(requested_reviewers=[])
        result = _get_copilot_review_request_skip_reason(
            pr_meta,
            None,
            repair_dispatched=True,
        )
        assert result == "repair_dispatched"

    def test_returns_unresolved_comments(self):
        """Returns reason when unresolved comments exist."""
        pr_meta = _PRMetadata(requested_reviewers=[])
        result = _get_copilot_review_request_skip_reason(
            pr_meta,
            None,
            unresolved_comment_count=2,
        )
        assert result == "unresolved_comments"
