"""Tests for _validate_reply_entries helper."""

import pytest

from agentic_devtools.cli.github.review_reply import _validate_reply_entries


class TestValidateReplyEntries:
    """Tests for _validate_reply_entries."""

    def test_valid_entries(self):
        """No error for valid entries."""
        _validate_reply_entries([
            {"commentId": 1, "body": "ok"},
            {"commentId": 2, "body": "done"},
        ])

    def test_empty_list(self):
        """No error for empty list."""
        _validate_reply_entries([])

    def test_missing_comment_id(self):
        """sys.exit(1) when commentId is missing."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_reply_entries([{"body": "ok"}])
        assert exc_info.value.code == 1

    def test_missing_body(self):
        """sys.exit(1) when body is missing."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_reply_entries([{"commentId": 1}])
        assert exc_info.value.code == 1

    def test_comment_id_not_int(self):
        """sys.exit(1) when commentId is not an integer."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_reply_entries([{"commentId": "abc", "body": "ok"}])
        assert exc_info.value.code == 1

    def test_error_at_correct_index(self, capsys):
        """Error message includes the index of the bad entry."""
        with pytest.raises(SystemExit):
            _validate_reply_entries([
                {"commentId": 1, "body": "ok"},
                {"body": "missing id"},
            ])
        assert "index 1" in capsys.readouterr().err

    def test_duplicate_comment_id(self, capsys):
        """sys.exit(1) when commentId values are not unique."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_reply_entries([
                {"commentId": 1, "body": "first"},
                {"commentId": 1, "body": "duplicate"},
            ])
        assert exc_info.value.code == 1
        assert "duplicate commentId 1" in capsys.readouterr().err
