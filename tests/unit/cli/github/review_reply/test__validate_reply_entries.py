"""Tests for _validate_reply_entries helper."""

import pytest

from agentic_devtools.cli.github.review_reply import _validate_reply_entries


class TestValidateReplyEntries:
    """Tests for _validate_reply_entries."""

    def test_valid_entries(self):
        """No error for valid entries."""
        _validate_reply_entries(
            [
                {"commentId": 1, "body": "ok"},
                {"commentId": 2, "body": "done"},
            ]
        )

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
            _validate_reply_entries(
                [
                    {"commentId": 1, "body": "ok"},
                    {"body": "missing id"},
                ]
            )
        assert "index 1" in capsys.readouterr().err

    def test_duplicate_comment_id(self, capsys):
        """sys.exit(1) when commentId values are not unique."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_reply_entries(
                [
                    {"commentId": 1, "body": "first"},
                    {"commentId": 1, "body": "duplicate"},
                ]
            )
        assert exc_info.value.code == 1
        assert "duplicate commentId 1" in capsys.readouterr().err

    def test_non_dict_entry(self, capsys):
        """sys.exit(1) when an entry is not a dict."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_reply_entries([42])
        assert exc_info.value.code == 1
        assert "index 0" in capsys.readouterr().err

    def test_non_dict_entry_string(self, capsys):
        """sys.exit(1) with type name when entry is a string."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_reply_entries([{"commentId": 1, "body": "ok"}, "not a dict"])
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "index 1" in err
        assert "str" in err

    def test_boolean_true_rejected(self, capsys):
        """sys.exit(1) when commentId is True (bool is subclass of int)."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_reply_entries([{"commentId": True, "body": "ok"}])
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "boolean" in err.lower()

    def test_boolean_false_rejected(self, capsys):
        """sys.exit(1) when commentId is False (bool is subclass of int)."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_reply_entries([{"commentId": False, "body": "ok"}])
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "boolean" in err.lower()

    def test_body_not_string_int(self, capsys):
        """sys.exit(1) when body is an integer instead of a string."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_reply_entries([{"commentId": 1, "body": 42}])
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "index 0" in err
        assert "'body' must be a string" in err
        assert "int" in err

    def test_body_not_string_list(self, capsys):
        """sys.exit(1) when body is a list instead of a string."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_reply_entries([{"commentId": 1, "body": ["a", "b"]}])
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "'body' must be a string" in err
        assert "list" in err

    def test_body_not_string_dict(self, capsys):
        """sys.exit(1) when body is a dict instead of a string."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_reply_entries([{"commentId": 1, "body": {"key": "val"}}])
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "'body' must be a string" in err
        assert "dict" in err

    def test_body_not_string_bool(self, capsys):
        """sys.exit(1) when body is a boolean instead of a string."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_reply_entries([{"commentId": 1, "body": True}])
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "'body' must be a string" in err
        assert "bool" in err

    def test_body_not_string_none(self, capsys):
        """sys.exit(1) when body is None instead of a string."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_reply_entries([{"commentId": 1, "body": None}])
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "'body' must be a string" in err
        assert "NoneType" in err

    def test_body_empty_string(self, capsys):
        """sys.exit(1) when body is an empty string."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_reply_entries([{"commentId": 1, "body": ""}])
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "index 0" in err
        assert "empty or whitespace-only" in err

    def test_body_whitespace_only(self, capsys):
        """sys.exit(1) when body is whitespace-only."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_reply_entries([{"commentId": 1, "body": "   \n\t  "}])
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "index 0" in err
        assert "empty or whitespace-only" in err
