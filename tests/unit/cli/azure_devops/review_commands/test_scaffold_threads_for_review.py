"""Tests for _scaffold_threads_for_review helper in review_commands."""

from unittest.mock import MagicMock, patch


class TestScaffoldThreadsForReview:
    """Tests for _scaffold_threads_for_review helper function."""

    def _make_pr_info(self, repo_id="repo-guid-123"):
        return {
            "repository": {"id": repo_id},
            "sourceRefName": "refs/heads/feature/test",
            "title": "Test PR",
        }

    def _make_pr_details(self, files=None, iterations=None):
        return {
            "files": files or [],
            "iterations": iterations,
            "threads": [],
        }

    def test_warns_when_no_repo_id(self, capsys):
        """Prints warning and returns early when repo_id is not available."""
        pr_info = {"sourceRefName": "refs/heads/feature/test"}  # no repository.id
        pr_details = self._make_pr_details()

        from agentic_devtools.cli.azure_devops.review_commands import _scaffold_threads_for_review

        _scaffold_threads_for_review(123, pr_details, pr_info, None)

        captured = capsys.readouterr()
        assert "repo ID" in captured.err

    def test_skips_when_no_file_paths(self, capsys):
        """Prints skip message and returns early when file_paths is empty."""
        pr_info = self._make_pr_info()
        pr_details = self._make_pr_details(files=[])  # empty files

        with patch("agentic_devtools.cli.azure_devops.review_commands.AzureDevOpsConfig") as mock_config_cls:
            mock_config_cls.from_state.return_value = MagicMock()
            with patch("agentic_devtools.cli.azure_devops.review_commands.require_requests"):
                with patch("agentic_devtools.cli.azure_devops.review_commands.get_pat"):
                    with patch("agentic_devtools.cli.azure_devops.review_commands.get_auth_headers"):
                        with patch("agentic_devtools.cli.azure_devops.review_commands.is_dry_run", return_value=False):
                            scaffold_mock = MagicMock()
                            with patch(
                                "agentic_devtools.cli.azure_devops.review_scaffold.scaffold_review_threads",
                                scaffold_mock,
                            ):
                                from agentic_devtools.cli.azure_devops.review_commands import (
                                    _scaffold_threads_for_review,
                                )

                                _scaffold_threads_for_review(123, pr_details, pr_info, None)

        out = capsys.readouterr().out
        assert "No files to scaffold" in out
        scaffold_mock.assert_not_called()

    def test_calls_scaffold_with_all_files_when_no_branch_filter(self):
        """Calls scaffold_review_threads with all file paths when files_on_branch is None."""
        pr_info = self._make_pr_info()
        pr_details = self._make_pr_details(
            files=[
                {"path": "/src/app.ts"},
                {"path": "/utils/helpers.ts"},
            ],
            iterations=[{"id": 3}, {"id": 1}, {"id": 2}],
        )

        scaffold_mock = MagicMock()

        with patch("agentic_devtools.cli.azure_devops.review_commands.AzureDevOpsConfig") as mock_config_cls:
            mock_config = MagicMock()
            mock_config.repository = "test-repo"
            mock_config_cls.from_state.return_value = mock_config

            with patch("agentic_devtools.cli.azure_devops.review_commands.require_requests"):
                with patch("agentic_devtools.cli.azure_devops.review_commands.get_pat"):
                    with patch("agentic_devtools.cli.azure_devops.review_commands.get_auth_headers"):
                        with patch("agentic_devtools.cli.azure_devops.review_commands.is_dry_run", return_value=False):
                            with patch(
                                "agentic_devtools.cli.azure_devops.review_scaffold.scaffold_review_threads",
                                scaffold_mock,
                            ):
                                from agentic_devtools.cli.azure_devops.review_commands import (
                                    _scaffold_threads_for_review,
                                )

                                _scaffold_threads_for_review(123, pr_details, pr_info, None)

        scaffold_mock.assert_called_once()
        call_kwargs = scaffold_mock.call_args[1]
        assert set(call_kwargs["files"]) == {"/src/app.ts", "/utils/helpers.ts"}

    def test_applies_files_on_branch_filter(self):
        """Filters file_paths to only those in files_on_branch set."""
        pr_info = self._make_pr_info()
        pr_details = self._make_pr_details(
            files=[
                {"path": "/src/app.ts"},
                {"path": "/utils/helpers.ts"},
            ],
        )
        files_on_branch = {"/src/app.ts"}  # only this file is on branch

        scaffold_mock = MagicMock()

        with patch("agentic_devtools.cli.azure_devops.review_commands.AzureDevOpsConfig") as mock_config_cls:
            mock_config = MagicMock()
            mock_config.repository = "test-repo"
            mock_config_cls.from_state.return_value = mock_config

            with patch("agentic_devtools.cli.azure_devops.review_commands.require_requests"):
                with patch("agentic_devtools.cli.azure_devops.review_commands.get_pat"):
                    with patch("agentic_devtools.cli.azure_devops.review_commands.get_auth_headers"):
                        with patch("agentic_devtools.cli.azure_devops.review_commands.is_dry_run", return_value=False):
                            with patch(
                                "agentic_devtools.cli.azure_devops.review_scaffold.scaffold_review_threads",
                                scaffold_mock,
                            ):
                                from agentic_devtools.cli.azure_devops.review_commands import (
                                    _scaffold_threads_for_review,
                                )

                                _scaffold_threads_for_review(123, pr_details, pr_info, files_on_branch)

        scaffold_mock.assert_called_once()
        call_kwargs = scaffold_mock.call_args[1]
        assert call_kwargs["files"] == ["/src/app.ts"]

    def test_uses_max_iteration_id(self):
        """Passes the maximum iteration ID to scaffold_review_threads."""
        pr_info = self._make_pr_info()
        pr_details = self._make_pr_details(
            files=[{"path": "/src/app.ts"}],
            iterations=[{"id": 1}, {"id": 5}, {"id": 3}],
        )

        scaffold_mock = MagicMock()

        with patch("agentic_devtools.cli.azure_devops.review_commands.AzureDevOpsConfig") as mock_config_cls:
            mock_config = MagicMock()
            mock_config.repository = "test-repo"
            mock_config_cls.from_state.return_value = mock_config

            with patch("agentic_devtools.cli.azure_devops.review_commands.require_requests"):
                with patch("agentic_devtools.cli.azure_devops.review_commands.get_pat"):
                    with patch("agentic_devtools.cli.azure_devops.review_commands.get_auth_headers"):
                        with patch("agentic_devtools.cli.azure_devops.review_commands.is_dry_run", return_value=False):
                            with patch(
                                "agentic_devtools.cli.azure_devops.review_scaffold.scaffold_review_threads",
                                scaffold_mock,
                            ):
                                from agentic_devtools.cli.azure_devops.review_commands import (
                                    _scaffold_threads_for_review,
                                )

                                _scaffold_threads_for_review(123, pr_details, pr_info, None)

        call_kwargs = scaffold_mock.call_args[1]
        assert call_kwargs["latest_iteration_id"] == 5

    def test_uses_zero_when_no_iterations(self):
        """Uses latest_iteration_id=0 when iterations is None or empty."""
        pr_info = self._make_pr_info()
        pr_details = self._make_pr_details(
            files=[{"path": "/src/app.ts"}],
            iterations=None,
        )

        scaffold_mock = MagicMock()

        with patch("agentic_devtools.cli.azure_devops.review_commands.AzureDevOpsConfig") as mock_config_cls:
            mock_config = MagicMock()
            mock_config.repository = "test-repo"
            mock_config_cls.from_state.return_value = mock_config

            with patch("agentic_devtools.cli.azure_devops.review_commands.require_requests"):
                with patch("agentic_devtools.cli.azure_devops.review_commands.get_pat"):
                    with patch("agentic_devtools.cli.azure_devops.review_commands.get_auth_headers"):
                        with patch("agentic_devtools.cli.azure_devops.review_commands.is_dry_run", return_value=False):
                            with patch(
                                "agentic_devtools.cli.azure_devops.review_scaffold.scaffold_review_threads",
                                scaffold_mock,
                            ):
                                from agentic_devtools.cli.azure_devops.review_commands import (
                                    _scaffold_threads_for_review,
                                )

                                _scaffold_threads_for_review(123, pr_details, pr_info, None)

        call_kwargs = scaffold_mock.call_args[1]
        assert call_kwargs["latest_iteration_id"] == 0

    def test_passes_dry_run_flag(self):
        """Passes the is_dry_run() value to scaffold_review_threads."""
        pr_info = self._make_pr_info()
        pr_details = self._make_pr_details(files=[{"path": "/src/app.ts"}])

        scaffold_mock = MagicMock()

        with patch("agentic_devtools.cli.azure_devops.review_commands.AzureDevOpsConfig") as mock_config_cls:
            mock_config = MagicMock()
            mock_config.repository = "test-repo"
            mock_config_cls.from_state.return_value = mock_config

            with patch("agentic_devtools.cli.azure_devops.review_commands.require_requests") as mock_require_requests:
                with patch("agentic_devtools.cli.azure_devops.review_commands.get_pat") as mock_get_pat:
                    with patch("agentic_devtools.cli.azure_devops.review_commands.get_auth_headers"):
                        with patch("agentic_devtools.cli.azure_devops.review_commands.is_dry_run", return_value=True):
                            with patch(
                                "agentic_devtools.cli.azure_devops.review_scaffold.scaffold_review_threads",
                                scaffold_mock,
                            ):
                                from agentic_devtools.cli.azure_devops.review_commands import (
                                    _scaffold_threads_for_review,
                                )

                                _scaffold_threads_for_review(123, pr_details, pr_info, None)

        call_kwargs = scaffold_mock.call_args[1]
        assert call_kwargs["dry_run"] is True
        # In dry-run mode, PAT and requests should NOT be fetched
        mock_require_requests.assert_not_called()
        mock_get_pat.assert_not_called()

    def test_filters_out_files_with_empty_path(self):
        """Files with empty or missing path keys are excluded from scaffolding."""
        pr_info = self._make_pr_info()
        pr_details = self._make_pr_details(
            files=[
                {"path": "/src/app.ts"},
                {"path": ""},  # empty path — excluded
                {},  # missing path key — excluded
            ],
        )

        scaffold_mock = MagicMock()

        with patch("agentic_devtools.cli.azure_devops.review_commands.AzureDevOpsConfig") as mock_config_cls:
            mock_config = MagicMock()
            mock_config.repository = "test-repo"
            mock_config_cls.from_state.return_value = mock_config

            with patch("agentic_devtools.cli.azure_devops.review_commands.require_requests"):
                with patch("agentic_devtools.cli.azure_devops.review_commands.get_pat"):
                    with patch("agentic_devtools.cli.azure_devops.review_commands.get_auth_headers"):
                        with patch("agentic_devtools.cli.azure_devops.review_commands.is_dry_run", return_value=False):
                            with patch(
                                "agentic_devtools.cli.azure_devops.review_scaffold.scaffold_review_threads",
                                scaffold_mock,
                            ):
                                from agentic_devtools.cli.azure_devops.review_commands import (
                                    _scaffold_threads_for_review,
                                )

                                _scaffold_threads_for_review(123, pr_details, pr_info, None)

        call_kwargs = scaffold_mock.call_args[1]
        assert call_kwargs["files"] == ["/src/app.ts"]

    def test_skips_when_all_files_filtered_out_by_branch(self, capsys):
        """Prints skip message when all files are filtered out by files_on_branch."""
        pr_info = self._make_pr_info()
        pr_details = self._make_pr_details(
            files=[{"path": "/src/app.ts"}],
        )
        # The branch has a different file
        files_on_branch = {"/other/file.ts"}

        scaffold_mock = MagicMock()

        with patch("agentic_devtools.cli.azure_devops.review_commands.AzureDevOpsConfig") as mock_config_cls:
            mock_config_cls.from_state.return_value = MagicMock()

            with patch("agentic_devtools.cli.azure_devops.review_commands.require_requests"):
                with patch("agentic_devtools.cli.azure_devops.review_commands.get_pat"):
                    with patch("agentic_devtools.cli.azure_devops.review_commands.get_auth_headers"):
                        with patch("agentic_devtools.cli.azure_devops.review_commands.is_dry_run", return_value=False):
                            with patch(
                                "agentic_devtools.cli.azure_devops.review_scaffold.scaffold_review_threads",
                                scaffold_mock,
                            ):
                                from agentic_devtools.cli.azure_devops.review_commands import (
                                    _scaffold_threads_for_review,
                                )

                                _scaffold_threads_for_review(123, pr_details, pr_info, files_on_branch)

        out = capsys.readouterr().out
        assert "No files to scaffold" in out
        scaffold_mock.assert_not_called()

    def test_prints_warning_when_scaffold_raises(self, capsys):
        """Prints a warning message when scaffold_review_threads raises an exception."""
        pr_info = self._make_pr_info()
        pr_details = self._make_pr_details(files=[{"path": "/src/app.ts"}])

        with patch("agentic_devtools.cli.azure_devops.review_commands.AzureDevOpsConfig") as mock_config_cls:
            mock_config = MagicMock()
            mock_config.repository = "test-repo"
            mock_config_cls.from_state.return_value = mock_config

            with patch("agentic_devtools.cli.azure_devops.review_commands.require_requests"):
                with patch("agentic_devtools.cli.azure_devops.review_commands.get_pat"):
                    with patch("agentic_devtools.cli.azure_devops.review_commands.get_auth_headers"):
                        with patch("agentic_devtools.cli.azure_devops.review_commands.is_dry_run", return_value=False):
                            with patch(
                                "agentic_devtools.cli.azure_devops.review_scaffold.scaffold_review_threads",
                                side_effect=RuntimeError("API error"),
                            ):
                                from agentic_devtools.cli.azure_devops.review_commands import (
                                    _scaffold_threads_for_review,
                                )

                                # Should not raise — exception is caught and logged as a warning
                                _scaffold_threads_for_review(123, pr_details, pr_info, None)

        captured = capsys.readouterr()
        assert "Scaffolding failed" in captured.err
        assert "API error" in captured.err
