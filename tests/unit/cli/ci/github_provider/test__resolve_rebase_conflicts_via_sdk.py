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

        def git_side_effect(args):
            if args == ["diff", "--name-only", "--diff-filter=U"]:
                return "src.py\n"
            if args[0] == "show" and args[1].startswith(":"):
                raise RuntimeError("not available")
            if args[0] == "log" and "--oneline" in args:
                raise RuntimeError("not available")
            if args == ["add", "src.py"]:
                return ""
            if args == ["-c", "core.editor=true", "rebase", "--continue"]:
                return ""
            return ""

        mock_run_git.side_effect = git_side_effect
        mock_resolve_file.return_value = "merged\n"
        provider = GitHubActionsProvider(repo="owner/repo")

        resolved = provider._resolve_rebase_conflicts_via_sdk(base_branch="main", head_branch="feature/test")

        assert resolved is True
        assert conflicted.read_text(encoding="utf-8") == "merged\n"
        mock_run_git.assert_any_call(["add", "src.py"])
        mock_run_git.assert_any_call(["-c", "core.editor=true", "rebase", "--continue"])
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

        def git_side_effect(args):
            if args == ["diff", "--name-only", "--diff-filter=U"]:
                return "src.py\n"
            if args[0] == "show" and args[1].startswith(":"):
                raise RuntimeError("not available")
            if args[0] == "log" and "--oneline" in args:
                raise RuntimeError("not available")
            return ""

        mock_run_git.side_effect = git_side_effect
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

        def git_side_effect(args):
            if args == ["diff", "--name-only", "--diff-filter=U"]:
                return "src.py\n"
            if args[0] == "show" and args[1].startswith(":"):
                raise RuntimeError("not available")
            if args[0] == "log" and "--oneline" in args:
                raise RuntimeError("not available")
            return ""

        mock_run_git.side_effect = git_side_effect
        mock_resolve_file.return_value = "<<<<<<< HEAD\nstill conflicted\n=======\nnope\n>>>>>>> branch\n"
        provider = GitHubActionsProvider(repo="owner/repo")

        resolved = provider._resolve_rebase_conflicts_via_sdk(base_branch="main", head_branch="feature/test")

        assert resolved is False
        assert conflicted.read_text(encoding="utf-8") == original
        called_git_args = [entry.args[0] for entry in mock_run_git.call_args_list]
        assert ["add", "src.py"] not in called_git_args
        assert ["-c", "core.editor=true", "rebase", "--continue"] not in called_git_args

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

        call_counter = {"rebase_continue": 0, "diff_filter": 0}

        def git_side_effect(args):
            if args == ["diff", "--name-only", "--diff-filter=U"]:
                call_counter["diff_filter"] += 1
                if call_counter["diff_filter"] == 1:
                    return "src.py\n"  # First call: conflicted files
                return ""  # Second call: still_conflicted check → empty
            if args[0] == "show" and args[1].startswith(":"):
                raise RuntimeError("not available")
            if args[0] == "log" and "--oneline" in args:
                raise RuntimeError("not available")
            if args == ["add", "src.py"]:
                return ""
            if args == ["-c", "core.editor=true", "rebase", "--continue"]:
                raise RuntimeError("cannot continue")
            return ""

        mock_run_git.side_effect = git_side_effect
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

        def git_side_effect(args):
            if args == ["diff", "--name-only", "--diff-filter=U"]:
                return "src.py\n"  # Always still conflicted
            if args[0] == "show" and args[1].startswith(":"):
                raise RuntimeError("not available")
            if args[0] == "log" and "--oneline" in args:
                raise RuntimeError("not available")
            if args == ["add", "src.py"]:
                return ""
            if args == ["-c", "core.editor=true", "rebase", "--continue"]:
                raise RuntimeError("conflict remains")
            return ""

        mock_run_git.side_effect = git_side_effect
        mock_resolve_file.return_value = "merged content\n"
        provider = GitHubActionsProvider(repo="owner/repo")

        resolved = provider._resolve_rebase_conflicts_via_sdk(
            base_branch="main",
            head_branch="feature/test",
            max_rounds=2,
        )

        assert resolved is False
        assert mock_resolve_file.call_count == 2
