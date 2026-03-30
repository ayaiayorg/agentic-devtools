"""Tests for agentic_devtools.submission_manager.SubmissionStatus."""

from agentic_devtools.submission_manager import SubmissionStatus


class TestSubmissionStatus:
    """Tests for SubmissionStatus enum."""

    def test_status_values(self):
        """Test SubmissionStatus enum has expected values."""
        assert SubmissionStatus.QUEUED.value == "queued"
        assert SubmissionStatus.PROCESSING.value == "processing"
        assert SubmissionStatus.SUCCEEDED.value == "succeeded"
        assert SubmissionStatus.FAILED.value == "failed"
        assert SubmissionStatus.RETRYING.value == "retrying"

    def test_status_is_str_subclass(self):
        """Test SubmissionStatus members are str instances."""
        for member in SubmissionStatus:
            assert isinstance(member, str)

    def test_status_from_string(self):
        """Test creating SubmissionStatus from string value."""
        assert SubmissionStatus("queued") == SubmissionStatus.QUEUED
        assert SubmissionStatus("processing") == SubmissionStatus.PROCESSING
        assert SubmissionStatus("succeeded") == SubmissionStatus.SUCCEEDED
        assert SubmissionStatus("failed") == SubmissionStatus.FAILED
        assert SubmissionStatus("retrying") == SubmissionStatus.RETRYING
