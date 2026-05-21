"""Tests for _record_failed_session helper."""

from unittest.mock import MagicMock, patch

from agentic_devtools.orchestration.review.runner import _record_failed_session


class TestRecordFailedSession:
    """Tests for _record_failed_session helper."""

    def test_records_failed_session_when_review_state_exists(self):
        """Appends a failed session entry when review state is loaded."""
        mock_review_state = MagicMock()
        mock_review_state.sessions = []

        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            return_value=mock_review_state,
        ) as mock_load:
            with patch(
                "agentic_devtools.cli.azure_devops.review_state.save_review_state",
            ) as mock_save:
                _record_failed_session(
                    pr_id=123,
                    session_id="def456",
                    started_utc="2024-01-01T00:00:00Z",
                    error="Graph crashed",
                    model_id="gpt-4.1",
                )

        mock_load.assert_called_once_with(123)
        assert len(mock_review_state.sessions) == 1
        session = mock_review_state.sessions[0]
        assert session.sessionId == "def456"
        assert session.modelId == "gpt-4.1"
        assert session.status == "failed"
        assert session.engine == "langchain"
        mock_save.assert_called_once_with(mock_review_state)

    def test_skips_when_no_review_state(self):
        """Does nothing when load_review_state returns None."""
        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            return_value=None,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.review_state.save_review_state",
            ) as mock_save:
                _record_failed_session(
                    pr_id=123,
                    session_id="def456",
                    started_utc="2024-01-01T00:00:00Z",
                    error="oops",
                )

        mock_save.assert_not_called()

    def test_handles_exception_gracefully(self):
        """Does not raise when session recording fails."""
        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            side_effect=RuntimeError("file not found"),
        ):
            # Should not raise
            _record_failed_session(
                pr_id=123,
                session_id="def456",
                started_utc="2024-01-01T00:00:00Z",
                error="oops",
            )
