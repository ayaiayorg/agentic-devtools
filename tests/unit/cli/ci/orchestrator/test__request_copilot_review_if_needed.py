"""Tests for _request_copilot_review_if_needed unresolved threads gate."""

import logging
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.models import PRMetadata, ReviewInfo
from agentic_devtools.cli.ci.orchestrator import _request_copilot_review_if_needed


def _make_pr_meta(**kwargs):
    defaults = {
        "number": 42,
        "title": "feat: test",
        "head_branch": "feature/test",
        "head_sha": "abc123",
        "base_branch": "main",
        "head_repo_full_name": "owner/repo",
        "base_repo_full_name": "owner/repo",
        "labels": ["ai-auto-merge-allowed"],
    }
    defaults.update(kwargs)
    return PRMetadata(**defaults)


class TestUnresolvedThreadsGate:
    """Tests for unresolved threads gate in _request_copilot_review_if_needed."""

    def test_unresolved_threads_blocks_review_request(self):
        """When unresolved_threads > 0, returns 'awaiting_thread_resolution' and does NOT call request_reviewer."""
        provider = MagicMock()
        pr_meta = _make_pr_meta()

        result = _request_copilot_review_if_needed(
            provider,
            42,
            pr_meta,
            None,
            failure_context="PR",
            unresolved_threads=3,
        )

        assert result == "awaiting_thread_resolution"
        provider.request_reviewer.assert_not_called()

    def test_negative_sentinel_blocks_review_request(self):
        """When unresolved_threads == -1 (API failure sentinel), blocks review request (fail-closed)."""
        provider = MagicMock()
        pr_meta = _make_pr_meta()

        result = _request_copilot_review_if_needed(
            provider,
            42,
            pr_meta,
            None,
            failure_context="PR",
            unresolved_threads=-1,
        )

        assert result == "awaiting_thread_resolution"
        provider.request_reviewer.assert_not_called()

    def test_negative_sentinel_logs_dedicated_message(self, caplog):
        """Sentinel logging should describe unavailable thread count instead of '-1 threads'."""
        provider = MagicMock()
        pr_meta = _make_pr_meta()

        with caplog.at_level(logging.INFO, logger="agentic_devtools.cli.ci.orchestrator"):
            result = _request_copilot_review_if_needed(
                provider,
                42,
                pr_meta,
                None,
                failure_context="PR",
                unresolved_threads=-1,
            )

        assert result == "awaiting_thread_resolution"
        assert "unresolved thread count unavailable" in caplog.text
        assert "-1 unresolved thread" not in caplog.text

    @patch("agentic_devtools.cli.ci.orchestrator._get_copilot_review_request_skip_reason")
    def test_zero_unresolved_threads_proceeds_to_existing_logic(self, mock_skip_reason):
        """When unresolved_threads == 0, proceeds past the gate to existing skip_reason logic."""
        mock_skip_reason.return_value = None
        provider = MagicMock()
        pr_meta = _make_pr_meta()

        result = _request_copilot_review_if_needed(
            provider,
            42,
            pr_meta,
            None,
            failure_context="PR",
            unresolved_threads=0,
        )

        assert result is None
        provider.request_reviewer.assert_called_once()

    @patch("agentic_devtools.cli.ci.orchestrator._get_copilot_review_request_skip_reason")
    def test_gate_checked_before_skip_reason(self, mock_skip_reason):
        """Unresolved threads gate fires BEFORE _get_copilot_review_request_skip_reason."""
        mock_skip_reason.return_value = "already_requested"
        provider = MagicMock()
        pr_meta = _make_pr_meta()

        result = _request_copilot_review_if_needed(
            provider,
            42,
            pr_meta,
            None,
            failure_context="PR",
            unresolved_threads=2,
        )

        # Gate takes priority; skip_reason is never called
        assert result == "awaiting_thread_resolution"
        mock_skip_reason.assert_not_called()


class TestRegressionPR1545:
    """Regression test for the PR #1545 scenario."""

    def test_pr1545_multiple_unresolved_threads_blocks_review(self):
        """Simulates PR #1545: 2+ unresolved threads, review request must be blocked."""
        provider = MagicMock()
        pr_meta = _make_pr_meta()
        copilot_review = ReviewInfo(id=100, user="copilot-pull-request-reviewer[bot]", state="COMMENTED", body="")

        result = _request_copilot_review_if_needed(
            provider,
            1545,
            pr_meta,
            copilot_review,
            failure_context="PR",
            unresolved_threads=2,
        )

        assert result == "awaiting_thread_resolution"
        provider.request_reviewer.assert_not_called()
