"""Tests for agentic_devtools.submission_manager_instance.get_submission_manager."""

from unittest.mock import patch

from agentic_devtools.submission_manager import SubmissionManager


class TestGetSubmissionManager:
    """Tests for get_submission_manager."""

    def test_returns_submission_manager(self):
        """Returns a SubmissionManager instance."""
        import agentic_devtools.submission_manager_instance as mod

        # Reset singleton
        mod._manager = None
        try:
            manager = mod.get_submission_manager()
            assert isinstance(manager, SubmissionManager)
        finally:
            if mod._manager is not None:
                mod._manager.shutdown(wait=True)
            mod._manager = None

    def test_returns_same_instance(self):
        """Returns the same singleton on repeated calls."""
        import agentic_devtools.submission_manager_instance as mod

        mod._manager = None
        try:
            m1 = mod.get_submission_manager()
            m2 = mod.get_submission_manager()
            assert m1 is m2
        finally:
            if mod._manager is not None:
                mod._manager.shutdown(wait=True)
            mod._manager = None

    def test_calls_create_submission_manager(self):
        """Uses create_submission_manager factory on first call."""
        import agentic_devtools.submission_manager_instance as mod

        mod._manager = None
        try:
            with patch.object(mod, "create_submission_manager") as mock_create:
                mock_manager = SubmissionManager()
                mock_create.return_value = mock_manager
                result = mod.get_submission_manager()
                mock_create.assert_called_once()
                assert result is mock_manager
        finally:
            if mod._manager is not None:
                mod._manager.shutdown(wait=True)
            mod._manager = None
