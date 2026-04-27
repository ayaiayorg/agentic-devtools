"""Tests for _read_log_excerpt()."""

from __future__ import annotations

from unittest.mock import patch

from agentic_devtools.cli.analysis.external_context import _read_log_excerpt


class TestReadLogExcerpt:
    """Tests for reading log file excerpts."""

    def test_os_error_returns_empty_string(self, tmp_path):
        """OSError when opening log file → empty string."""
        log_file = tmp_path / "nonexistent.log"
        result = _read_log_excerpt(log_file)
        assert result == ""

    def test_unicode_decode_error_returns_empty_string(self, tmp_path):
        """UnicodeDecodeError during read → empty string."""
        log_file = tmp_path / "bad.log"
        log_file.write_bytes(b"\x80\x81\x82")

        def bad_open(*args, **kwargs):
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "bad")

        with patch.object(type(log_file), "open", side_effect=bad_open):
            result = _read_log_excerpt(log_file)
        assert result == ""
