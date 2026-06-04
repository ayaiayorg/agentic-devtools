"""Tests for _detect_unchanged_files."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.review_commands import _detect_unchanged_files


class TestDetectUnchangedFiles:
    """Tests for _detect_unchanged_files."""

    def test_returns_empty_when_no_current_files(self):
        assert _detect_unchanged_files(123, {"files": []}) == set()

    def test_skips_entries_with_empty_file_path(self):
        pr_details = {
            "pullRequest": {"lastMergeSourceCommit": {"commitId": "same-sha"}},
            "files": [{"path": ""}, {"path": "/src/a.ts"}],
        }
        prior_state = MagicMock()
        prior_state.commitHash = "same-sha"

        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            return_value=prior_state,
        ):
            assert _detect_unchanged_files(123, pr_details) == {"/src/a.ts"}

    def test_returns_empty_when_prior_state_missing(self):
        pr_details = {
            "pullRequest": {"lastMergeSourceCommit": {"commitId": "newsha"}},
            "files": [{"path": "/src/a.ts"}],
        }
        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            side_effect=FileNotFoundError,
        ):
            assert _detect_unchanged_files(123, pr_details) == set()

    def test_returns_all_when_commit_hash_matches(self):
        pr_details = {
            "pullRequest": {"lastMergeSourceCommit": {"commitId": "same-sha"}},
            "files": [{"path": "/src/a.ts"}, {"path": "/src/b.ts"}],
        }
        prior_state = MagicMock()
        prior_state.commitHash = "same-sha"

        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            return_value=prior_state,
        ):
            assert _detect_unchanged_files(123, pr_details) == {"/src/a.ts", "/src/b.ts"}

    def test_returns_empty_when_prior_commit_hash_missing(self):
        pr_details = {
            "pullRequest": {"lastMergeSourceCommit": {"commitId": "newsha"}},
            "files": [{"path": "/src/a.ts"}],
        }
        prior_state = MagicMock()
        prior_state.commitHash = None

        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            return_value=prior_state,
        ):
            assert _detect_unchanged_files(123, pr_details) == set()

    def test_returns_empty_when_last_merge_source_commit_not_dict(self):
        pr_details = {
            "pullRequest": {"lastMergeSourceCommit": None},
            "files": [{"path": "/src/a.ts"}],
        }
        prior_state = MagicMock()
        prior_state.commitHash = "oldsha"

        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            return_value=prior_state,
        ):
            assert _detect_unchanged_files(123, pr_details) == set()

    def test_returns_empty_when_current_commit_hash_invalid(self):
        pr_details = {
            "pullRequest": {"lastMergeSourceCommit": {"commitId": "   "}},
            "files": [{"path": "/src/a.ts"}],
        }
        prior_state = MagicMock()
        prior_state.commitHash = "oldsha"

        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            return_value=prior_state,
        ):
            assert _detect_unchanged_files(123, pr_details) == set()

    def test_returns_empty_when_git_diff_fails(self):
        pr_details = {
            "pullRequest": {"lastMergeSourceCommit": {"commitId": "newsha"}},
            "files": [{"path": "/src/a.ts"}],
        }
        prior_state = MagicMock()
        prior_state.commitHash = "oldsha"
        failed_diff = MagicMock(returncode=1, stdout="")

        with (
            patch(
                "agentic_devtools.cli.azure_devops.review_state.load_review_state",
                return_value=prior_state,
            ),
            patch("agentic_devtools.cli.azure_devops.review_commands.run_safe", return_value=failed_diff),
        ):
            assert _detect_unchanged_files(123, pr_details) == set()

    def test_returns_files_not_in_diff(self):
        pr_details = {
            "pullRequest": {"lastMergeSourceCommit": {"commitId": "newsha"}},
            "files": [{"path": "/src/changed.ts"}, {"path": "/src/unchanged.ts"}],
        }
        prior_state = MagicMock()
        prior_state.commitHash = "oldsha"
        successful_diff = MagicMock(returncode=0, stdout="\nsrc/changed.ts\n")

        with (
            patch(
                "agentic_devtools.cli.azure_devops.review_state.load_review_state",
                return_value=prior_state,
            ),
            patch("agentic_devtools.cli.azure_devops.review_commands.run_safe", return_value=successful_diff),
        ):
            assert _detect_unchanged_files(123, pr_details) == {"/src/unchanged.ts"}

    def test_skips_paths_that_normalize_to_empty(self):
        pr_details = {
            "pullRequest": {"lastMergeSourceCommit": {"commitId": "newsha"}},
            "files": [{"path": "invalid"}, {"path": "/src/unchanged.ts"}],
        }
        prior_state = MagicMock()
        prior_state.commitHash = "oldsha"
        successful_diff = MagicMock(returncode=0, stdout="invalid-diff\n")

        def _normalize(path: str):
            if path in {"invalid", "invalid-diff"}:
                return None
            if path.startswith("/"):
                return path
            return f"/{path}"

        with (
            patch(
                "agentic_devtools.cli.azure_devops.review_state.load_review_state",
                return_value=prior_state,
            ),
            patch("agentic_devtools.cli.azure_devops.review_commands.run_safe", return_value=successful_diff),
            patch("agentic_devtools.cli.azure_devops.review_helpers.normalize_repo_path", side_effect=_normalize),
        ):
            assert _detect_unchanged_files(123, pr_details) == {"/src/unchanged.ts"}
