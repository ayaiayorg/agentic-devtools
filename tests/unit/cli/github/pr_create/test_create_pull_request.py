"""Tests for agentic_devtools.cli.github.pr_create.create_pull_request."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.github import pr_create


class TestCreatePullRequest:
    """Tests for GitHub create_pull_request()."""

    @patch("agentic_devtools.cli.github.pr_create.set_value")
    @patch("agentic_devtools.cli.github.pr_create.run_safe")
    @patch("agentic_devtools.cli.github.pr_create.is_dry_run", return_value=False)
    @patch("agentic_devtools.cli.github.pr_create.resolve_pr_body")
    @patch("agentic_devtools.cli.github.pr_create.get_value")
    def test_creates_pr_with_resolved_body(
        self, mock_get_value, mock_resolve, mock_dry_run, mock_run_safe, mock_set_value
    ):
        """Happy path: creates PR with template-resolved body via --body-file."""
        mock_get_value.return_value = None
        mock_resolve.return_value = "# PR\n\nfeat: commit msg"

        captured = {}

        def _capture_body(cmd, **kwargs):
            idx = cmd.index("--body-file")
            with open(cmd[idx + 1], encoding="utf-8") as f:
                captured["body"] = f.read()
            return MagicMock(returncode=0, stdout="https://github.com/org/repo/pull/42\n")

        mock_run_safe.side_effect = _capture_body

        pr_create.create_pull_request(title="My PR", body=None)

        mock_resolve.assert_called_once()
        call_args = mock_run_safe.call_args[0][0]
        assert "--body-file" in call_args
        assert "--body" not in call_args
        assert captured["body"] == "# PR\n\nfeat: commit msg"

    @patch("agentic_devtools.cli.github.pr_create.set_value")
    @patch("agentic_devtools.cli.github.pr_create.run_safe")
    @patch("agentic_devtools.cli.github.pr_create.is_dry_run", return_value=False)
    @patch("agentic_devtools.cli.github.pr_create.get_value")
    def test_uses_explicit_body_when_provided(self, mock_get_value, mock_dry_run, mock_run_safe, mock_set_value):
        """Explicit body parameter bypasses template resolution and is written to --body-file."""
        mock_get_value.return_value = None

        captured = {}

        def _capture_body(cmd, **kwargs):
            idx = cmd.index("--body-file")
            with open(cmd[idx + 1], encoding="utf-8") as f:
                captured["body"] = f.read()
            return MagicMock(returncode=0, stdout="https://github.com/org/repo/pull/42\n")

        mock_run_safe.side_effect = _capture_body

        pr_create.create_pull_request(title="My PR", body="Explicit body")

        call_args = mock_run_safe.call_args[0][0]
        assert "--body-file" in call_args
        assert "--body" not in call_args
        assert captured["body"] == "Explicit body"

    @patch("agentic_devtools.cli.github.pr_create.is_dry_run", return_value=True)
    @patch("agentic_devtools.cli.github.pr_create.resolve_pr_body")
    @patch("agentic_devtools.cli.github.pr_create.get_value")
    def test_dry_run_does_not_call_gh(self, mock_get_value, mock_resolve, mock_dry_run, capsys):
        """Dry run mode only prints, doesn't execute."""
        mock_get_value.return_value = None
        mock_resolve.return_value = "body"

        pr_create.create_pull_request(title="My PR")

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out

    @patch("agentic_devtools.cli.github.pr_create.is_dry_run", return_value=False)
    @patch("agentic_devtools.cli.github.pr_create.get_value")
    def test_exits_when_no_title(self, mock_get_value, mock_dry_run):
        """Exits with error when no title is available."""
        mock_get_value.return_value = None

        with pytest.raises(SystemExit):
            pr_create.create_pull_request(title=None)

    @patch("agentic_devtools.cli.github.pr_create.set_value")
    @patch("agentic_devtools.cli.github.pr_create.run_safe")
    @patch("agentic_devtools.cli.github.pr_create.is_dry_run", return_value=False)
    @patch("agentic_devtools.cli.github.pr_create.get_value")
    def test_includes_draft_flag_by_default(self, mock_get_value, mock_dry_run, mock_run_safe, mock_set_value):
        """Draft flag is included by default."""
        mock_get_value.return_value = None
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="https://github.com/org/repo/pull/1\n")

        pr_create.create_pull_request(title="PR", body="body")

        call_args = mock_run_safe.call_args[0][0]
        assert "--draft" in call_args

    @patch("agentic_devtools.cli.github.pr_create.run_safe")
    @patch("agentic_devtools.cli.github.pr_create.is_dry_run", return_value=False)
    @patch("agentic_devtools.cli.github.pr_create.get_value")
    def test_gh_failure_exits(self, mock_get_value, mock_dry_run, mock_run_safe):
        """Exits on gh CLI failure."""
        mock_get_value.return_value = None
        mock_run_safe.return_value = MagicMock(returncode=1, stdout="", stderr="error: something failed")

        with pytest.raises(SystemExit):
            pr_create.create_pull_request(title="PR", body="body")

    @patch("agentic_devtools.cli.github.pr_create.run_safe")
    @patch("agentic_devtools.cli.github.pr_create.is_dry_run", return_value=False)
    @patch("agentic_devtools.cli.github.pr_create.get_value")
    def test_draft_bool_from_state(self, mock_get_value, mock_dry_run, mock_run_safe):
        """Draft mode from state as boolean False disables draft."""

        def _get_value(key, **kwargs):
            if key == "draft":
                return False
            return None

        mock_get_value.side_effect = _get_value
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="url\n")

        pr_create.create_pull_request(title="PR", body="body")

        call_args = mock_run_safe.call_args[0][0]
        assert "--draft" not in call_args

    @patch("agentic_devtools.cli.github.pr_create.run_safe")
    @patch("agentic_devtools.cli.github.pr_create.is_dry_run", return_value=False)
    @patch("agentic_devtools.cli.github.pr_create.get_value")
    def test_draft_string_false_from_state(self, mock_get_value, mock_dry_run, mock_run_safe):
        """Draft mode from state as string 'false' disables draft."""

        def _get_value(key, **kwargs):
            if key == "draft":
                return "false"
            return None

        mock_get_value.side_effect = _get_value
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="url\n")

        pr_create.create_pull_request(title="PR", body="body")

        call_args = mock_run_safe.call_args[0][0]
        assert "--draft" not in call_args

    @patch("agentic_devtools.cli.github.pr_create.run_safe")
    @patch("agentic_devtools.cli.github.pr_create.is_dry_run", return_value=False)
    @patch("agentic_devtools.cli.github.pr_create.get_value")
    def test_explicit_base_skips_state_lookup(self, mock_get_value, mock_dry_run, mock_run_safe):
        """When base is explicitly provided, state lookup is skipped."""
        mock_get_value.return_value = None
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="url\n")

        pr_create.create_pull_request(title="PR", body="body", base="develop")

        call_args = mock_run_safe.call_args[0][0]
        assert "--base" in call_args
        base_idx = call_args.index("--base")
        assert call_args[base_idx + 1] == "develop"

    @patch("agentic_devtools.cli.github.pr_create.is_dry_run", return_value=True)
    @patch("agentic_devtools.cli.github.pr_create.resolve_pr_body")
    @patch("agentic_devtools.cli.github.pr_create.get_value")
    def test_dry_run_with_empty_body(self, mock_get_value, mock_resolve, mock_dry_run, capsys):
        """Dry run with empty body skips body output line."""
        mock_get_value.return_value = None
        mock_resolve.return_value = ""

        pr_create.create_pull_request(title="My PR")

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Body:" not in captured.out

    @patch("agentic_devtools.cli.github.pr_create.run_safe")
    @patch("agentic_devtools.cli.github.pr_create.is_dry_run", return_value=False)
    @patch("agentic_devtools.cli.github.pr_create.get_value")
    def test_explicit_draft_false_not_overridden_by_state(self, mock_get_value, mock_dry_run, mock_run_safe):
        """Explicit draft=False is never overridden by a truthy draft state key."""

        def _get_value(key, **kwargs):
            if key == "draft":
                return True  # state says draft=True
            return None

        mock_get_value.side_effect = _get_value
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="url\n")

        # Caller explicitly says draft=False (mirrors --no-draft)
        pr_create.create_pull_request(title="PR", body="body", draft=False)

        call_args = mock_run_safe.call_args[0][0]
        assert "--draft" not in call_args

    @patch("agentic_devtools.cli.github.pr_create.run_safe")
    @patch("agentic_devtools.cli.github.pr_create.is_dry_run", return_value=False)
    @patch("agentic_devtools.cli.github.pr_create.get_value")
    def test_draft_none_defaults_to_true_when_no_state(self, mock_get_value, mock_dry_run, mock_run_safe):
        """draft=None with no state key defaults to draft mode."""
        mock_get_value.return_value = None
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="url\n")

        pr_create.create_pull_request(title="PR", body="body", draft=None)

        call_args = mock_run_safe.call_args[0][0]
        assert "--draft" in call_args

    @patch("agentic_devtools.cli.github.pr_create.set_value")
    @patch("agentic_devtools.cli.github.pr_create.run_safe")
    @patch("agentic_devtools.cli.github.pr_create.is_dry_run", return_value=False)
    @patch("agentic_devtools.cli.github.pr_create.get_value")
    def test_persists_pr_number_to_state(self, mock_get_value, mock_dry_run, mock_run_safe, mock_set_value):
        """PR number is extracted from the returned URL and written to state."""
        mock_get_value.return_value = None
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="https://github.com/org/repo/pull/42\n")

        pr_create.create_pull_request(title="PR", body="body")

        mock_set_value.assert_called_once_with("github.pull_request_number", 42)

    @patch("agentic_devtools.cli.github.pr_create.set_value")
    @patch("agentic_devtools.cli.github.pr_create.run_safe")
    @patch("agentic_devtools.cli.github.pr_create.is_dry_run", return_value=False)
    @patch("agentic_devtools.cli.github.pr_create.get_value")
    def test_no_pr_number_persisted_when_url_unrecognised(
        self, mock_get_value, mock_dry_run, mock_run_safe, mock_set_value
    ):
        """When gh outputs an unrecognised URL, set_value is not called."""
        mock_get_value.return_value = None
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="url\n")

        pr_create.create_pull_request(title="PR", body="body")

        mock_set_value.assert_not_called()

    @patch("agentic_devtools.cli.github.pr_create.set_value")
    @patch("agentic_devtools.cli.github.pr_create.os.unlink")
    @patch("agentic_devtools.cli.github.pr_create.run_safe")
    @patch("agentic_devtools.cli.github.pr_create.is_dry_run", return_value=False)
    @patch("agentic_devtools.cli.github.pr_create.get_value")
    def test_temp_file_unlink_oserror_is_silenced(
        self, mock_get_value, mock_dry_run, mock_run_safe, mock_unlink, mock_set_value
    ):
        """OSError during temp file cleanup is silenced; PR creation still succeeds."""
        mock_get_value.return_value = None
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="url\n")
        mock_unlink.side_effect = OSError("permission denied")

        # Should not raise even though unlink fails
        pr_create.create_pull_request(title="PR", body="body")

        mock_set_value.assert_not_called()


class TestCreatePullRequestCommand:
    """Tests for create_pull_request_command CLI entry point."""

    @patch("agentic_devtools.cli.github.pr_create.create_pull_request")
    def test_parses_arguments(self, mock_create, monkeypatch):
        """CLI entry point parses and passes args correctly."""
        monkeypatch.setattr(
            "sys.argv",
            ["agdt-gh-create-pull-request", "--title", "My PR", "--base", "develop"],
        )

        pr_create.create_pull_request_command()

        mock_create.assert_called_once_with(
            title="My PR",
            body=None,
            base="develop",
            draft=None,
        )

    @patch("agentic_devtools.cli.github.pr_create.create_pull_request")
    def test_no_draft_flag(self, mock_create, monkeypatch):
        """--no-draft sets draft to False."""
        monkeypatch.setattr(
            "sys.argv",
            ["agdt-gh-create-pull-request", "--title", "PR", "--no-draft"],
        )

        pr_create.create_pull_request_command()

        mock_create.assert_called_once_with(
            title="PR",
            body=None,
            base=None,
            draft=False,
        )
