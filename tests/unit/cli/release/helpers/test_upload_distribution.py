"""Tests for upload_distribution function."""

from agentic_devtools.cli.release.helpers import upload_distribution


class TestUploadDistribution:
    """Tests for upload_distribution function."""

    def test_function_exists(self):
        """Verify upload_distribution is importable and callable."""
        assert callable(upload_distribution)
