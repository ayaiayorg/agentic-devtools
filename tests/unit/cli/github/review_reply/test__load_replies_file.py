"""Tests for _load_replies_file helper."""

import json

import pytest

from agentic_devtools.cli.github.review_reply import _load_replies_file


class TestLoadRepliesFile:
    """Tests for _load_replies_file."""

    def test_valid_json_array(self, tmp_path):
        """Returns parsed list from a valid JSON array file."""
        f = tmp_path / "replies.json"
        data = [{"commentId": 1, "body": "ok"}]
        f.write_text(json.dumps(data), encoding="utf-8")
        result = _load_replies_file(str(f))
        assert result == data

    def test_empty_array(self, tmp_path):
        """Returns empty list for empty JSON array."""
        f = tmp_path / "replies.json"
        f.write_text("[]", encoding="utf-8")
        result = _load_replies_file(str(f))
        assert result == []

    def test_file_not_found(self):
        """sys.exit(1) when file does not exist."""
        with pytest.raises(SystemExit) as exc_info:
            _load_replies_file("/nonexistent/replies.json")
        assert exc_info.value.code == 1

    def test_malformed_json(self, tmp_path):
        """sys.exit(1) for invalid JSON."""
        f = tmp_path / "replies.json"
        f.write_text("{bad json", encoding="utf-8")
        with pytest.raises(SystemExit) as exc_info:
            _load_replies_file(str(f))
        assert exc_info.value.code == 1

    def test_non_array_json(self, tmp_path):
        """sys.exit(1) when JSON is a dict instead of array."""
        f = tmp_path / "replies.json"
        f.write_text('{"commentId": 1}', encoding="utf-8")
        with pytest.raises(SystemExit) as exc_info:
            _load_replies_file(str(f))
        assert exc_info.value.code == 1

    def test_unicode_decode_error(self, tmp_path):
        """sys.exit(1) when file contains invalid UTF-8."""
        f = tmp_path / "replies.json"
        f.write_bytes(b"\xff\xfe invalid utf-8")
        with pytest.raises(SystemExit) as exc_info:
            _load_replies_file(str(f))
        assert exc_info.value.code == 1

    def test_os_error_on_directory(self, tmp_path, capsys):
        """sys.exit(1) when path is a directory (OSError)."""
        d = tmp_path / "a_directory"
        d.mkdir()
        with pytest.raises(SystemExit) as exc_info:
            _load_replies_file(str(d))
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "Failed to read" in err
        assert "not found" not in err
