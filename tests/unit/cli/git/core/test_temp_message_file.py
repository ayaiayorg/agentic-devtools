"""Tests for agentic_devtools.cli.git.core.temp_message_file."""

from pathlib import Path

from agentic_devtools.cli.git import core


class TestTempMessageFile:
    """Tests for temporary message file context manager."""

    def test_temp_message_file_creates_and_cleans_up(self):
        """Test temp file is created and cleaned up."""
        message = "Test message\nLine 2"
        temp_path = None

        with core.temp_message_file(message) as path:
            temp_path = path
            assert Path(path).exists()
            assert Path(path).read_text(encoding="utf-8") == message

        assert not Path(temp_path).exists()

    def test_temp_message_file_cleans_up_on_exception(self):
        """Test temp file is cleaned up even on exception."""
        temp_path = None

        try:
            with core.temp_message_file("Test") as path:
                temp_path = path
                raise ValueError("Test exception")
        except ValueError:
            pass

        assert not Path(temp_path).exists()

    def test_temp_message_file_handles_cleanup_oserror(self, monkeypatch):
        """Test that OSError during cleanup is silently handled."""
        message = "Test message"
        cleanup_attempted = []

        def mock_unlink(self, missing_ok=False):
            cleanup_attempted.append(True)
            raise OSError("Permission denied")

        with monkeypatch.context() as m:
            m.setattr(Path, "unlink", mock_unlink)
            with core.temp_message_file(message):
                pass

        assert len(cleanup_attempted) == 1
