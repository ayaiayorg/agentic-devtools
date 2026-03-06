"""Tests for should_use_emoji function."""

import sys
from unittest.mock import PropertyMock, patch

from agentic_devtools.cli.azure_devops.review_attribution import should_use_emoji


class TestShouldUseEmoji:
    """Tests for should_use_emoji."""

    def test_env_var_true_returns_true(self, monkeypatch):
        """Test that AGDT_USE_EMOJI=true returns True."""
        monkeypatch.setenv("AGDT_USE_EMOJI", "true")
        assert should_use_emoji() is True

    def test_env_var_false_returns_false(self, monkeypatch):
        """Test that AGDT_USE_EMOJI=false returns False."""
        monkeypatch.setenv("AGDT_USE_EMOJI", "false")
        assert should_use_emoji() is False

    def test_env_var_true_case_insensitive(self, monkeypatch):
        """Test that AGDT_USE_EMOJI=TRUE (uppercase) returns True."""
        monkeypatch.setenv("AGDT_USE_EMOJI", "TRUE")
        assert should_use_emoji() is True

    def test_env_var_false_case_insensitive(self, monkeypatch):
        """Test that AGDT_USE_EMOJI=FALSE (uppercase) returns False."""
        monkeypatch.setenv("AGDT_USE_EMOJI", "FALSE")
        assert should_use_emoji() is False

    def test_env_var_invalid_falls_through_to_auto_detect(self, monkeypatch):
        """Test that an invalid AGDT_USE_EMOJI value falls through to auto-detection."""
        monkeypatch.setenv("AGDT_USE_EMOJI", "maybe")
        # Auto-detect: non-TTY → False
        with patch.object(sys.stdout, "isatty", return_value=False):
            result = should_use_emoji()
        assert result is False

    def test_env_var_unset_falls_through_to_auto_detect(self, monkeypatch):
        """Test that an unset AGDT_USE_EMOJI falls through to auto-detection."""
        monkeypatch.delenv("AGDT_USE_EMOJI", raising=False)
        with patch.object(sys.stdout, "isatty", return_value=False):
            result = should_use_emoji()
        assert result is False

    def test_non_tty_returns_false(self, monkeypatch):
        """Test that a non-TTY stdout returns False."""
        monkeypatch.delenv("AGDT_USE_EMOJI", raising=False)
        with patch.object(sys.stdout, "isatty", return_value=False):
            result = should_use_emoji()
        assert result is False

    def test_tty_with_utf8_encoding_returns_true(self, monkeypatch):
        """Test that a TTY with UTF-8 encoding returns True."""
        monkeypatch.delenv("AGDT_USE_EMOJI", raising=False)
        with patch.object(sys.stdout, "isatty", return_value=True):
            with patch.object(type(sys.stdout), "encoding", new_callable=PropertyMock, return_value="utf-8"):
                result = should_use_emoji()
        assert result is True

    def test_tty_with_ascii_encoding_returns_false(self, monkeypatch):
        """Test that a TTY with ASCII encoding returns False."""
        monkeypatch.delenv("AGDT_USE_EMOJI", raising=False)
        with patch.object(sys.stdout, "isatty", return_value=True):
            with patch.object(type(sys.stdout), "encoding", new_callable=PropertyMock, return_value="ascii"):
                result = should_use_emoji()
        assert result is False

    def test_env_var_overrides_tty_detection(self, monkeypatch):
        """Test that AGDT_USE_EMOJI=false overrides a UTF-8 TTY."""
        monkeypatch.setenv("AGDT_USE_EMOJI", "false")
        with patch.object(sys.stdout, "isatty", return_value=True):
            result = should_use_emoji()
        assert result is False
