"""Tests for _record_session helper."""

from unittest.mock import MagicMock, patch

from agentic_devtools.orchestration.review.runner import _record_session


class TestRecordSession:
    """Tests for _record_session helper."""

    def test_records_session_when_review_state_exists(self):
        """Appends a session entry when review state is loaded."""
        mock_review_state = MagicMock()
        mock_review_state.sessions = []

        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            return_value=mock_review_state,
        ) as mock_load:
            with patch(
                "agentic_devtools.cli.azure_devops.review_state.save_review_state",
            ) as mock_save:
                _record_session(
                    pr_id=123,
                    session_id="abc123",
                    started_utc="2024-01-01T00:00:00Z",
                    final_state={"status": "completed", "config": {"model": "gpt-4.1"}},
                )

        mock_load.assert_called_once_with(123)
        assert len(mock_review_state.sessions) == 1
        session = mock_review_state.sessions[0]
        assert session.sessionId == "abc123"
        assert session.modelId == "gpt-4.1"
        assert session.engine == "langchain"
        assert session.status == "completed"
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
                _record_session(
                    pr_id=123,
                    session_id="abc123",
                    started_utc="2024-01-01T00:00:00Z",
                    final_state={"status": "completed"},
                )

        mock_save.assert_not_called()

    def test_handles_exception_gracefully(self):
        """Does not raise when session recording fails."""
        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            side_effect=RuntimeError("file not found"),
        ):
            # Should not raise
            _record_session(
                pr_id=123,
                session_id="abc123",
                started_utc="2024-01-01T00:00:00Z",
                final_state={"status": "completed"},
            )
