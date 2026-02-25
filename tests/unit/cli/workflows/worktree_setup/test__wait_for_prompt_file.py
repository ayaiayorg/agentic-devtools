"""Tests for WaitForPromptFile."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import _wait_for_prompt_file


class TestWaitForPromptFile:
    """Tests for _wait_for_prompt_file function."""

    def test_returns_true_immediately_when_file_exists(self, tmp_path):
        """Test that True is returned immediately when the file already exists."""
        prompt_file = tmp_path / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Review Prompt", encoding="utf-8")

        result = _wait_for_prompt_file(prompt_file, timeout=10, poll_interval=0.1)

        assert result is True

    def test_returns_false_when_file_never_appears(self, tmp_path):
        """Test that False is returned when the file does not appear within timeout."""
        prompt_file = tmp_path / "nonexistent-prompt.md"

        result = _wait_for_prompt_file(prompt_file, timeout=0.05, poll_interval=0.01)

        assert result is False

    def test_returns_true_after_file_created_during_wait(self, tmp_path):
        """Test that True is returned when the file appears during polling."""
        import threading
        import time

        prompt_file = tmp_path / "delayed-prompt.md"

        def create_file_after_delay():
            time.sleep(0.05)
            prompt_file.write_text("# Delayed prompt", encoding="utf-8")

        thread = threading.Thread(target=create_file_after_delay)
        thread.start()

        result = _wait_for_prompt_file(prompt_file, timeout=5, poll_interval=0.02)
        thread.join()

        assert result is True

    def test_polls_with_specified_interval(self, tmp_path):
        """Test that the function sleeps between polls."""
        prompt_file = tmp_path / "missing.md"

        with patch("time.sleep") as mock_sleep:
            _wait_for_prompt_file(prompt_file, timeout=0.05, poll_interval=0.05)

        # sleep should have been called at least once
        assert mock_sleep.called
