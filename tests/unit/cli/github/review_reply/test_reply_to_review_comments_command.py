"""Tests for reply_to_review_comments_command CLI entry point."""

import json
from unittest.mock import patch

import pytest

from agentic_devtools.cli.github.review_reply import reply_to_review_comments_command


class TestReplyToReviewCommentsCommand:
    """Tests for reply_to_review_comments_command."""

    @patch("agentic_devtools.cli.github.review_reply.reply_to_review_comments")
    @patch("agentic_devtools.cli.github.review_reply.resolve_github_repo")
    @patch("agentic_devtools.cli.github.review_reply.get_value")
    def test_cli_args_parsed(self, mock_get, mock_resolve, mock_reply, capsys, monkeypatch):
        """CLI arguments are correctly parsed and passed to core function."""
        monkeypatch.setattr(
            "sys.argv",
            [
                "agdt-gh-reply-to-review-comments",
                "--pr",
                "1115",
                "--repo",
                "owner/repo",
                "--review-id",
                "4066913338",
                "--replies-file",
                "replies.json",
            ],
        )
        mock_resolve.return_value = "owner/repo"
        mock_reply.return_value = {"totalReplies": 0, "verified": True}

        reply_to_review_comments_command()

        mock_reply.assert_called_once_with(1115, "owner/repo", 4066913338, "replies.json")

    @patch("agentic_devtools.cli.github.review_reply.reply_to_review_comments")
    @patch("agentic_devtools.cli.github.review_reply.resolve_github_repo")
    @patch("agentic_devtools.cli.github.review_reply.get_value")
    def test_fallback_to_state(self, mock_get, mock_resolve, mock_reply, monkeypatch):
        """Falls back to state when CLI args not provided."""
        monkeypatch.setattr(
            "sys.argv",
            ["agdt-gh-reply-to-review-comments"],
        )
        mock_get.side_effect = lambda key: {
            "github.pull_request_number": 42,
            "github.review_id": 12345,
            "github.replies_file": "/tmp/r.json",
        }.get(key)
        mock_resolve.return_value = "owner/repo"
        mock_reply.return_value = {"totalReplies": 0}

        reply_to_review_comments_command()

        mock_reply.assert_called_once_with(42, "owner/repo", 12345, "/tmp/r.json")

    @patch("agentic_devtools.cli.github.review_reply.reply_to_review_comments")
    @patch("agentic_devtools.cli.github.review_reply.resolve_github_repo")
    @patch("agentic_devtools.cli.github.review_reply.get_value")
    def test_fallback_to_copilot_review_id(self, mock_get, mock_resolve, mock_reply, monkeypatch):
        """Falls back to github.copilot_review_id when github.review_id is not set."""
        monkeypatch.setattr(
            "sys.argv",
            ["agdt-gh-reply-to-review-comments"],
        )
        mock_get.side_effect = lambda key: {
            "github.pull_request_number": 42,
            "github.review_id": None,
            "github.copilot_review_id": 67890,
            "github.replies_file": "/tmp/r.json",
        }.get(key)
        mock_resolve.return_value = "owner/repo"
        mock_reply.return_value = {"totalReplies": 0}

        reply_to_review_comments_command()

        mock_reply.assert_called_once_with(42, "owner/repo", 67890, "/tmp/r.json")

    @patch("agentic_devtools.cli.github.review_reply.reply_to_review_comments")
    @patch("agentic_devtools.cli.github.review_reply.resolve_github_repo")
    @patch("agentic_devtools.cli.github.review_reply.get_value")
    def test_stdout_json_output(self, mock_get, mock_resolve, mock_reply, capsys, monkeypatch):
        """Prints JSON result to stdout."""
        monkeypatch.setattr(
            "sys.argv",
            [
                "agdt-gh-reply-to-review-comments",
                "--pr",
                "10",
                "--review-id",
                "99",
                "--replies-file",
                "r.json",
            ],
        )
        mock_resolve.return_value = "owner/repo"
        mock_reply.return_value = {"totalReplies": 5, "verified": True}

        reply_to_review_comments_command()

        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["totalReplies"] == 5

    @patch("agentic_devtools.cli.github.review_reply.get_value")
    def test_error_exit_when_pr_missing(self, mock_get, monkeypatch):
        """sys.exit(1) when PR number not provided anywhere."""
        monkeypatch.setattr(
            "sys.argv",
            ["agdt-gh-reply-to-review-comments"],
        )
        mock_get.return_value = None

        with pytest.raises(SystemExit) as exc_info:
            reply_to_review_comments_command()
        assert exc_info.value.code == 1

    @patch("agentic_devtools.cli.github.review_reply.resolve_github_repo")
    @patch("agentic_devtools.cli.github.review_reply.get_value")
    def test_error_exit_when_review_id_missing(self, mock_get, mock_resolve, monkeypatch):
        """sys.exit(1) when review ID not provided anywhere."""
        monkeypatch.setattr(
            "sys.argv",
            ["agdt-gh-reply-to-review-comments", "--pr", "10"],
        )
        mock_get.return_value = None
        mock_resolve.return_value = "owner/repo"

        with pytest.raises(SystemExit) as exc_info:
            reply_to_review_comments_command()
        assert exc_info.value.code == 1

    @patch("agentic_devtools.cli.github.review_reply.resolve_github_repo")
    @patch("agentic_devtools.cli.github.review_reply.get_value")
    def test_error_exit_when_replies_file_missing(self, mock_get, mock_resolve, monkeypatch):
        """sys.exit(1) when replies file not provided anywhere."""
        monkeypatch.setattr(
            "sys.argv",
            ["agdt-gh-reply-to-review-comments", "--pr", "10", "--review-id", "99"],
        )
        mock_get.return_value = None
        mock_resolve.return_value = "owner/repo"

        with pytest.raises(SystemExit) as exc_info:
            reply_to_review_comments_command()
        assert exc_info.value.code == 1

    @patch("agentic_devtools.cli.github.review_reply._check_gh_available")
    @patch("agentic_devtools.cli.github.review_reply.reply_to_review_comments")
    @patch("agentic_devtools.cli.github.review_reply.resolve_github_repo")
    @patch("agentic_devtools.cli.github.review_reply.get_value")
    def test_check_gh_available_called(self, mock_get, mock_resolve, mock_reply, mock_check, monkeypatch):
        """_check_gh_available is called before invoking the core function."""
        monkeypatch.setattr(
            "sys.argv",
            [
                "agdt-gh-reply-to-review-comments",
                "--pr",
                "10",
                "--review-id",
                "99",
                "--replies-file",
                "r.json",
            ],
        )
        mock_resolve.return_value = "owner/repo"
        mock_reply.return_value = {"totalReplies": 0}

        reply_to_review_comments_command()

        mock_check.assert_called_once()

    @patch("agentic_devtools.cli.github.review_reply._check_gh_available", side_effect=SystemExit(1))
    @patch("agentic_devtools.cli.github.review_reply.resolve_github_repo")
    @patch("agentic_devtools.cli.github.review_reply.get_value")
    def test_exits_when_gh_unavailable(self, mock_get, mock_resolve, mock_check, monkeypatch):
        """sys.exit(1) when gh CLI is not available."""
        monkeypatch.setattr(
            "sys.argv",
            [
                "agdt-gh-reply-to-review-comments",
                "--pr",
                "10",
                "--review-id",
                "99",
                "--replies-file",
                "r.json",
            ],
        )
        mock_resolve.return_value = "owner/repo"

        with pytest.raises(SystemExit) as exc_info:
            reply_to_review_comments_command()
        assert exc_info.value.code == 1

    @patch("agentic_devtools.cli.github.review_reply.resolve_github_repo")
    @patch("agentic_devtools.cli.github.review_reply.get_value")
    def test_non_integer_pr_number_in_state(self, mock_get, mock_resolve, capsys, monkeypatch):
        """sys.exit(1) with remediation message when PR number in state is not castable to int."""
        monkeypatch.setattr(
            "sys.argv",
            ["agdt-gh-reply-to-review-comments"],
        )
        mock_get.side_effect = lambda key: {
            "github.pull_request_number": "not-a-number",
            "github.review_id": 99,
            "github.replies_file": "r.json",
        }.get(key)
        mock_resolve.return_value = "owner/repo"

        with pytest.raises(SystemExit) as exc_info:
            reply_to_review_comments_command()
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "must be an integer" in err
        assert "agdt-set github.pull_request_number" in err

    @patch("agentic_devtools.cli.github.review_reply.resolve_github_repo")
    @patch("agentic_devtools.cli.github.review_reply.get_value")
    def test_non_integer_review_id_in_state(self, mock_get, mock_resolve, capsys, monkeypatch):
        """sys.exit(1) with remediation message when review ID in state is not castable to int."""
        monkeypatch.setattr(
            "sys.argv",
            ["agdt-gh-reply-to-review-comments"],
        )
        mock_get.side_effect = lambda key: {
            "github.pull_request_number": 42,
            "github.review_id": "bad-id",
            "github.copilot_review_id": None,
            "github.replies_file": "r.json",
        }.get(key)
        mock_resolve.return_value = "owner/repo"

        with pytest.raises(SystemExit) as exc_info:
            reply_to_review_comments_command()
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "must be an integer" in err
        assert "agdt-set github.review_id" in err

    @patch("agentic_devtools.cli.github.review_reply._check_gh_available")
    @patch("agentic_devtools.cli.github.review_reply.reply_to_review_comments")
    @patch("agentic_devtools.cli.github.review_reply.resolve_github_repo")
    @patch("agentic_devtools.cli.github.review_reply.get_value")
    def test_pr_zero_not_treated_as_missing(self, mock_get, mock_resolve, mock_reply, mock_check, monkeypatch):
        """--pr 0 is treated as a provided value, not falling back to state."""
        monkeypatch.setattr(
            "sys.argv",
            [
                "agdt-gh-reply-to-review-comments",
                "--pr",
                "0",
                "--review-id",
                "99",
                "--replies-file",
                "r.json",
            ],
        )
        mock_resolve.return_value = "owner/repo"
        mock_reply.return_value = {"totalReplies": 0}

        reply_to_review_comments_command()

        mock_reply.assert_called_once_with(0, "owner/repo", 99, "r.json")
        mock_get.assert_not_called()

    @patch("agentic_devtools.cli.github.review_reply._check_gh_available")
    @patch("agentic_devtools.cli.github.review_reply.reply_to_review_comments")
    @patch("agentic_devtools.cli.github.review_reply.resolve_github_repo")
    @patch("agentic_devtools.cli.github.review_reply.get_value")
    def test_review_id_zero_not_treated_as_missing(self, mock_get, mock_resolve, mock_reply, mock_check, monkeypatch):
        """--review-id 0 is treated as a provided value, not falling back to state."""
        monkeypatch.setattr(
            "sys.argv",
            [
                "agdt-gh-reply-to-review-comments",
                "--pr",
                "10",
                "--review-id",
                "0",
                "--replies-file",
                "r.json",
            ],
        )
        mock_resolve.return_value = "owner/repo"
        mock_reply.return_value = {"totalReplies": 0}

        reply_to_review_comments_command()

        mock_reply.assert_called_once_with(10, "owner/repo", 0, "r.json")
