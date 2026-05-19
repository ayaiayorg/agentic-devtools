"""Tests for GitHubActionsProvider._resolve_rebase_conflicts_via_sdk."""

from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


class TestResolveRebaseConflictsViaSdk:
    """Tests for SDK-driven rebase conflict resolution."""

    @patch.object(GitHubActionsProvider, "_resolve_conflicted_file_content_via_sdk")
    @patch.object(GitHubActionsProvider, "_run_git")
    def test_updates_files_and_continues(
        self,
        mock_run_git,
        mock_resolve_file,
        tmp_path,
        monkeypatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        conflicted = tmp_path / "src.py"
        conflicted.write_text("<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> branch\n", encoding="utf-8")
        mock_run_git.side_effect = ["src.py\n", "", ""]
        mock_resolve_file.return_value = "merged\n"
        provider = GitHubActionsProvider(repo="owner/repo")

        resolved = provider._resolve_rebase_conflicts_via_sdk(base_branch="main", head_branch="feature/test")

        assert resolved is True
        assert conflicted.read_text(encoding="utf-8") == "merged\n"
        mock_run_git.assert_any_call(["add", "src.py"])
        mock_run_git.assert_any_call(["rebase", "--continue"])
        mock_resolve_file.assert_called_once()

    @patch.object(GitHubActionsProvider, "_resolve_conflicted_file_content_via_sdk")
    @patch.object(GitHubActionsProvider, "_run_git")
    def test_returns_false_when_file_not_resolved(
        self,
        mock_run_git,
        mock_resolve_file,
        tmp_path,
        monkeypatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        conflicted = tmp_path / "src.py"
        conflicted.write_text("<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> branch\n", encoding="utf-8")
        mock_run_git.side_effect = ["src.py\n"]
        mock_resolve_file.return_value = None
        provider = GitHubActionsProvider(repo="owner/repo")

        resolved = provider._resolve_rebase_conflicts_via_sdk(base_branch="main", head_branch="feature/test")

        assert resolved is False

    @patch.object(GitHubActionsProvider, "_resolve_conflicted_file_content_via_sdk")
    @patch.object(GitHubActionsProvider, "_run_git")
    def test_returns_false_when_resolution_contains_conflict_markers(
        self,
        mock_run_git,
        mock_resolve_file,
        tmp_path,
        monkeypatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        conflicted = tmp_path / "src.py"
        original = "<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> branch\n"
        conflicted.write_text(original, encoding="utf-8")
        mock_run_git.side_effect = ["src.py\n"]
        mock_resolve_file.return_value = "<<<<<<< HEAD\nstill conflicted\n=======\nnope\n>>>>>>> branch\n"
        provider = GitHubActionsProvider(repo="owner/repo")

        resolved = provider._resolve_rebase_conflicts_via_sdk(base_branch="main", head_branch="feature/test")

        assert resolved is False
        assert conflicted.read_text(encoding="utf-8") == original
        called_git_args = [entry.args[0] for entry in mock_run_git.call_args_list]
        assert ["add", "src.py"] not in called_git_args
        assert ["rebase", "--continue"] not in called_git_args

    @patch.object(GitHubActionsProvider, "_resolve_conflicted_file_content_via_sdk")
    @patch.object(GitHubActionsProvider, "_run_git")
    def test_returns_false_when_no_conflicted_files(
        self,
        mock_run_git,
        mock_resolve_file,
        tmp_path,
        monkeypatch,
    ) -> None:
        """diff --name-only --diff-filter=U returns empty string; resolution returns False."""
        monkeypatch.chdir(tmp_path)
        mock_run_git.return_value = ""
        provider = GitHubActionsProvider(repo="owner/repo")

        resolved = provider._resolve_rebase_conflicts_via_sdk(base_branch="main", head_branch="feature/test")

        assert resolved is False
        mock_resolve_file.assert_not_called()

    @patch.object(GitHubActionsProvider, "_resolve_conflicted_file_content_via_sdk")
    @patch.object(GitHubActionsProvider, "_run_git")
    def test_returns_false_on_file_read_error(
        self,
        mock_run_git,
        mock_resolve_file,
        tmp_path,
        monkeypatch,
    ) -> None:
        """OSError reading a conflicted file causes early return False."""
        monkeypatch.chdir(tmp_path)
        # src.py is listed as conflicted but does not exist on disk
        mock_run_git.return_value = "src.py\n"
        provider = GitHubActionsProvider(repo="owner/repo")

        resolved = provider._resolve_rebase_conflicts_via_sdk(base_branch="main", head_branch="feature/test")

        assert resolved is False
        mock_resolve_file.assert_not_called()

    @patch.object(GitHubActionsProvider, "_resolve_conflicted_file_content_via_sdk")
    @patch.object(GitHubActionsProvider, "_run_git")
    def test_returns_false_when_continue_fails_without_remaining_conflicts(
        self,
        mock_run_git,
        mock_resolve_file,
        tmp_path,
        monkeypatch,
    ) -> None:
        """rebase --continue raises RuntimeError but no files remain conflicted; returns False."""
        monkeypatch.chdir(tmp_path)
        conflicted = tmp_path / "src.py"
        conflicted.write_text("<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> branch\n", encoding="utf-8")
        mock_run_git.side_effect = [
            "src.py\n",  # diff --name-only (get conflicts)
            "",  # add src.py
            RuntimeError("cannot continue"),  # rebase --continue raises
            "",  # diff --name-only (still_conflicted check → empty)
        ]
        mock_resolve_file.return_value = "merged content\n"
        provider = GitHubActionsProvider(repo="owner/repo")

        resolved = provider._resolve_rebase_conflicts_via_sdk(base_branch="main", head_branch="feature/test")

        assert resolved is False

    @patch.object(GitHubActionsProvider, "_resolve_conflicted_file_content_via_sdk")
    @patch.object(GitHubActionsProvider, "_run_git")
    def test_returns_false_after_max_rounds_exhausted(
        self,
        mock_run_git,
        mock_resolve_file,
        tmp_path,
        monkeypatch,
    ) -> None:
        """Each round's rebase --continue leaves remaining conflicts; max rounds exceeded → False."""
        monkeypatch.chdir(tmp_path)
        conflicted = tmp_path / "src.py"
        conflicted.write_text("<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> branch\n", encoding="utf-8")

        # Two rounds: each round → diff, add, rebase --continue (raises), still_conflicted (non-empty)
        mock_run_git.side_effect = [
            "src.py\n",  # round 1: diff --name-only
            "",  # round 1: add src.py
            RuntimeError("conflict remains"),  # round 1: rebase --continue raises
            "src.py\n",  # round 1: still_conflicted (non-empty → retry)
            "src.py\n",  # round 2: diff --name-only
            "",  # round 2: add src.py
            RuntimeError("conflict remains"),  # round 2: rebase --continue raises
            "src.py\n",  # round 2: still_conflicted (non-empty → retry)
        ]
        mock_resolve_file.return_value = "merged content\n"
        provider = GitHubActionsProvider(repo="owner/repo")

        resolved = provider._resolve_rebase_conflicts_via_sdk(
            base_branch="main",
            head_branch="feature/test",
            max_rounds=2,
        )

        assert resolved is False
        assert mock_resolve_file.call_count == 2
