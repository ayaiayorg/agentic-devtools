"""Tests for the review_commands module and helper functions."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestSetupPullRequestReviewFocusAreas:
    """Tests for focus-area loading in setup_pull_request_review."""

    def _make_pr_details(self, source_ref="refs/heads/feature/test"):
        return {
            "pullRequest": {
                "pullRequestId": 123,
                "title": "Test PR",
                "createdBy": {"displayName": "Test User"},
                "sourceRefName": source_ref,
                "targetRefName": "refs/heads/main",
            },
            "files": [],
            "threads": [],
        }

    def _default_get_value(self, key, default=None):
        mapping = {
            "pull_request_id": "123",
            "jira.issue_key": None,
            "include_reviewed": "false",
        }
        return mapping.get(key, default)

    def _run_setup(self, pr_details, focus_areas_return):
        """Run setup_pull_request_review with mocked dependencies, return captured calls."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        captured_variables = {}

        def capture_render(workflow_name, step_name, variables, **kwargs):
            captured_variables.update(variables)

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "/repo/root\n"

        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/testorg"
        mock_config.project = "TestProject"
        mock_config.repository = "test-repo"

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=self._default_get_value,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(pr_details)
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(True, None, set()),
                        ):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                return_value=(3, 0, 0, MagicMock()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                ):
                                    with patch("agdt_ai_helpers.state.set_workflow_state"):
                                        with patch(
                                            "agdt_ai_helpers.prompts.loader.load_and_render_prompt",
                                            side_effect=capture_render,
                                        ):
                                            with patch(
                                                "agentic_devtools.config.load_review_focus_areas",
                                                return_value=focus_areas_return,
                                            ):
                                                with patch(
                                                    "agdt_ai_helpers.cli.azure_devops.review_commands.run_safe",
                                                    return_value=mock_git_result,
                                                ):
                                                    with patch(
                                                        "agdt_ai_helpers.cli.azure_devops.review_commands.AzureDevOpsConfig.from_state",
                                                        return_value=mock_config,
                                                    ):
                                                        with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                                            with patch("agdt_ai_helpers.state.set_value"):
                                                                with patch("agdt_ai_helpers.state.delete_value"):
                                                                    setup_pull_request_review()

        return captured_variables

    def test_focus_areas_passed_to_prompt_when_available(self):
        """Test that repo_review_focus_areas is passed when load_review_focus_areas returns content."""
        focus_content = "## .NET DI Patterns\n- Use constructor injection"
        variables = self._run_setup(self._make_pr_details(), focus_content)

        assert variables.get("repo_review_focus_areas") == focus_content

    def test_focus_areas_empty_string_when_none_returned(self):
        """Test that repo_review_focus_areas is empty string when load_review_focus_areas returns None."""
        variables = self._run_setup(self._make_pr_details(), None)

        assert variables.get("repo_review_focus_areas") == ""

    def test_pr_url_passed_to_prompt(self):
        """Test that pr_url is passed to the prompt variables containing the PR ID."""
        variables = self._run_setup(self._make_pr_details(), None)

        pr_url = variables.get("pr_url")
        assert pr_url is not None
        assert "/pullrequest/" in pr_url
        assert "123" in pr_url

    def test_source_code_platform_passed_to_prompt(self):
        """Test that source_code_platform is passed as AzureDevOps."""
        variables = self._run_setup(self._make_pr_details(), None)

        assert variables.get("source_code_platform") == "AzureDevOps"

    def test_load_review_focus_areas_called_with_git_root(self):
        """Test that load_review_focus_areas is called with the git repo root when available."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        pr_details = self._make_pr_details()

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "/repo/root\n"

        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/testorg"
        mock_config.project = "TestProject"
        mock_config.repository = "test-repo"

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=self._default_get_value,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(pr_details)
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(True, None, set()),
                        ):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                return_value=(3, 0, 0, MagicMock()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                ):
                                    with patch("agdt_ai_helpers.state.set_workflow_state"):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch("agentic_devtools.config.load_review_focus_areas") as mock_load:
                                                mock_load.return_value = None
                                                with patch(
                                                    "agdt_ai_helpers.cli.azure_devops.review_commands.run_safe",
                                                    return_value=mock_git_result,
                                                ):
                                                    with patch(
                                                        "agdt_ai_helpers.cli.azure_devops.review_commands.AzureDevOpsConfig.from_state",
                                                        return_value=mock_config,
                                                    ):
                                                        with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                                            with patch("agdt_ai_helpers.state.set_value"):
                                                                with patch("agdt_ai_helpers.state.delete_value"):
                                                                    setup_pull_request_review()
                                                                mock_load.assert_called_once_with("/repo/root")

    def test_load_review_focus_areas_falls_back_to_cwd_when_git_fails(self):
        """Test that load_review_focus_areas falls back to cwd when git rev-parse fails."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        pr_details = self._make_pr_details()

        mock_git_result = MagicMock()
        mock_git_result.returncode = 128
        mock_git_result.stdout = ""

        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/testorg"
        mock_config.project = "TestProject"
        mock_config.repository = "test-repo"

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=self._default_get_value,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(pr_details)
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(True, None, set()),
                        ):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                return_value=(3, 0, 0, MagicMock()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                ):
                                    with patch("agdt_ai_helpers.state.set_workflow_state"):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch("agentic_devtools.config.load_review_focus_areas") as mock_load:
                                                mock_load.return_value = None
                                                with patch(
                                                    "agdt_ai_helpers.cli.azure_devops.review_commands.run_safe",
                                                    return_value=mock_git_result,
                                                ):
                                                    with patch(
                                                        "agdt_ai_helpers.cli.azure_devops.review_commands.AzureDevOpsConfig.from_state",
                                                        return_value=mock_config,
                                                    ):
                                                        with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                                            with patch("agdt_ai_helpers.state.set_value"):
                                                                with patch("agdt_ai_helpers.state.delete_value"):
                                                                    setup_pull_request_review()
                                                                mock_load.assert_called_once_with(str(Path.cwd()))

    def test_load_review_focus_areas_falls_back_to_cwd_when_run_safe_raises(self):
        """Test that load_review_focus_areas falls back to cwd when run_safe raises an exception."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        pr_details = self._make_pr_details()

        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/testorg"
        mock_config.project = "TestProject"
        mock_config.repository = "test-repo"

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=self._default_get_value,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(pr_details)
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(True, None, set()),
                        ):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                return_value=(3, 0, 0, MagicMock()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                ):
                                    with patch("agdt_ai_helpers.state.set_workflow_state"):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch("agentic_devtools.config.load_review_focus_areas") as mock_load:
                                                mock_load.return_value = None
                                                with patch(
                                                    "agdt_ai_helpers.cli.azure_devops.review_commands.run_safe",
                                                    side_effect=OSError("git not found"),
                                                ):
                                                    with patch(
                                                        "agdt_ai_helpers.cli.azure_devops.review_commands.AzureDevOpsConfig.from_state",
                                                        return_value=mock_config,
                                                    ):
                                                        with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                                            with patch("agdt_ai_helpers.state.set_value"):
                                                                with patch("agdt_ai_helpers.state.delete_value"):
                                                                    setup_pull_request_review()
                                                                mock_load.assert_called_once_with(str(Path.cwd()))


class TestSetupPullRequestReview:
    """Tests for setup_pull_request_review function."""

    def test_exits_when_pull_request_id_missing(self, capsys):
        """Test exits with error when pull_request_id not in state."""
        from unittest.mock import patch

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            return_value=None,
        ):
            from agdt_ai_helpers.cli.azure_devops.review_commands import (
                setup_pull_request_review,
            )

            with pytest.raises(SystemExit) as exc_info:
                setup_pull_request_review()
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "pull_request_id is required" in captured.err

    def test_fetches_jira_issue_when_key_provided(self):
        """Test fetches Jira issue when jira.issue_key in state."""
        import json
        from unittest.mock import MagicMock, patch

        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        mock_pr_details = {
            "pullRequest": {
                "pullRequestId": 123,
                "title": "Test PR",
                "createdBy": {"displayName": "Test User"},
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
            },
            "files": [],
            "threads": [],
        }

        def get_value_side_effect(key, default=None):
            mapping = {
                "pull_request_id": "123",
                "jira.issue_key": "DFLY-1234",
                "include_reviewed": "false",
            }
            return mapping.get(key, default)

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=get_value_side_effect,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch(
                "agdt_ai_helpers.cli.azure_devops.review_commands._fetch_and_display_jira_issue"
            ) as mock_fetch_jira:
                with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                    with patch("builtins.open", create=True) as mock_open:
                        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_pr_details)
                        with patch("pathlib.Path.exists", return_value=True):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                                return_value=(True, None, set()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                    return_value=(5, 0, 0, MagicMock()),
                                ):
                                    with patch(
                                        "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                    ):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch("agdt_ai_helpers.state.set_workflow_state"):
                                                with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                                    with patch("agdt_ai_helpers.state.set_value"):
                                                        with patch("agdt_ai_helpers.state.delete_value"):
                                                            setup_pull_request_review()
                                                        mock_fetch_jira.assert_called_once_with("DFLY-1234")

    def test_exits_when_pr_details_file_missing(self, capsys):
        """Test exits with error when PR details file not found."""
        from unittest.mock import patch

        def get_value_side_effect(key, default=None):
            mapping = {
                "pull_request_id": "123",
                "jira.issue_key": None,
                "include_reviewed": "false",
            }
            return mapping.get(key, default)

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=get_value_side_effect,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("pathlib.Path.exists", return_value=False):
                    with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                        with patch("agdt_ai_helpers.state.set_value"):
                            from agdt_ai_helpers.cli.azure_devops.review_commands import (
                                setup_pull_request_review,
                            )

                            with pytest.raises(SystemExit) as exc_info:
                                setup_pull_request_review()
                            assert exc_info.value.code == 1
                            captured = capsys.readouterr()
                            assert "PR details file not found" in captured.err

    def test_exits_on_checkout_failure(self, capsys):
        """Test exits with error when checkout fails."""
        import json
        from unittest.mock import patch

        mock_pr_details = {
            "pullRequest": {
                "sourceRefName": "refs/heads/feature/test",
            },
            "files": [],
            "threads": [],
        }

        def get_value_side_effect(key, default=None):
            mapping = {
                "pull_request_id": "123",
                "jira.issue_key": None,
                "include_reviewed": "false",
            }
            return mapping.get(key, default)

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=get_value_side_effect,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_pr_details)
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(False, "Checkout error", set()),
                        ):
                            with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                with patch("agdt_ai_helpers.state.set_value"):
                                    with patch("agdt_ai_helpers.state.delete_value"):
                                        from agdt_ai_helpers.cli.azure_devops.review_commands import (
                                            setup_pull_request_review,
                                        )

                                        with pytest.raises(SystemExit) as exc_info:
                                            setup_pull_request_review()
                                    assert exc_info.value.code == 1

    def test_warns_when_no_source_branch(self, capsys):
        """Test prints warning when source branch cannot be determined."""
        import json
        from unittest.mock import MagicMock, patch

        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        mock_pr_details = {
            "pullRequest": {
                "sourceRefName": "",  # Empty source branch
                "title": "Test PR",
                "createdBy": {"displayName": "Test"},
                "targetRefName": "refs/heads/main",
            },
            "files": [],
            "threads": [],
        }

        def get_value_side_effect(key, default=None):
            mapping = {
                "pull_request_id": "123",
                "jira.issue_key": None,
                "include_reviewed": "false",
            }
            return mapping.get(key, default)

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=get_value_side_effect,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_pr_details)
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                            return_value=(5, 0, 0, MagicMock()),
                        ):
                            with patch("agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"):
                                with patch("agdt_ai_helpers.state.set_workflow_state"):
                                    with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                        with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                            with patch("agdt_ai_helpers.state.set_value"):
                                                with patch("agdt_ai_helpers.state.delete_value"):
                                                    setup_pull_request_review()
                                                captured = capsys.readouterr()
                                                assert "Could not determine source branch" in captured.err


class TestSetupPullRequestReviewPersistence:
    """Regression tests verifying bootstrap, agdt_run_id, and branch storage."""

    def _make_pr_details(self):
        return {
            "pullRequest": {
                "pullRequestId": 123,
                "title": "Test PR",
                "createdBy": {"displayName": "Test User"},
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
            },
            "files": [],
            "threads": [],
        }

    def _default_get_value(self, key, default=None):
        mapping = {
            "pull_request_id": "123",
            "jira.issue_key": None,
            "include_reviewed": "false",
        }
        return mapping.get(key, default)

    def _run_setup_with_captures(self):
        """Run setup_pull_request_review and capture set_bootstrap_state/set_value/delete_value calls."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "/repo/root\n"

        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/testorg"
        mock_config.project = "TestProject"
        mock_config.repository = "test-repo"

        mock_set_bootstrap = MagicMock()
        mock_set_value = MagicMock()
        mock_delete_value = MagicMock()

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=self._default_get_value,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
                        self._make_pr_details()
                    )
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(True, None, set()),
                        ):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                return_value=(3, 0, 0, MagicMock()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                ):
                                    with patch("agdt_ai_helpers.state.set_workflow_state"):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch(
                                                "agentic_devtools.config.load_review_focus_areas",
                                                return_value=None,
                                            ):
                                                with patch(
                                                    "agdt_ai_helpers.cli.azure_devops.review_commands.run_safe",
                                                    return_value=mock_git_result,
                                                ):
                                                    with patch(
                                                        "agdt_ai_helpers.cli.azure_devops.review_commands.AzureDevOpsConfig.from_state",
                                                        return_value=mock_config,
                                                    ):
                                                        with patch(
                                                            "agdt_ai_helpers.state.set_bootstrap_state",
                                                            mock_set_bootstrap,
                                                        ):
                                                            with patch(
                                                                "agdt_ai_helpers.state.set_value",
                                                                mock_set_value,
                                                            ):
                                                                with patch(
                                                                    "agdt_ai_helpers.state.delete_value",
                                                                    mock_delete_value,
                                                                ):
                                                                    setup_pull_request_review()

        return mock_set_bootstrap, mock_set_value, mock_delete_value

    def test_calls_set_bootstrap_state_with_pr_worktree_key(self):
        """Regression: set_bootstrap_state() must be called with worktree_key=PR{id}."""
        mock_set_bootstrap, _, _ = self._run_setup_with_captures()

        mock_set_bootstrap.assert_called_once_with(worktree_key="PR123")

    def test_sets_agdt_run_id_with_12_char_hex(self):
        """Regression: agdt_run_id must be stored as a 12-character hex string."""
        import re

        _, mock_set_value, _ = self._run_setup_with_captures()

        run_id_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "agdt_run_id"]
        assert len(run_id_calls) == 1
        run_id = run_id_calls[0][0][1]
        assert re.fullmatch(r"[0-9a-f]{12}", run_id), f"Expected 12-char hex, got {run_id!r}"

    def test_does_not_set_version_control_current_branch(self):
        """Regression: versionControl.currentBranch must NOT be set during bootstrap.

        The function checks out the PR source branch after bootstrap, so
        storing the pre-checkout branch would cause persist_if_dirty() to
        target the wrong -agdt branch.  Let persist_if_dirty() resolve it
        from git at runtime instead.
        """
        _, mock_set_value, _ = self._run_setup_with_captures()

        branch_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "versionControl.currentBranch"]
        assert len(branch_calls) == 0

    def test_bootstrap_failure_logs_warning_and_continues(self, capsys):
        """Regression: bootstrap init failure must log to stderr and not abort review setup."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "/repo/root\n"

        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/testorg"
        mock_config.project = "TestProject"
        mock_config.repository = "test-repo"

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=self._default_get_value,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
                        self._make_pr_details()
                    )
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(True, None, set()),
                        ):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                return_value=(3, 0, 0, MagicMock()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                ):
                                    with patch("agdt_ai_helpers.state.set_workflow_state"):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch(
                                                "agentic_devtools.config.load_review_focus_areas",
                                                return_value=None,
                                            ):
                                                with patch(
                                                    "agdt_ai_helpers.cli.azure_devops.review_commands.run_safe",
                                                    return_value=mock_git_result,
                                                ):
                                                    with patch(
                                                        "agdt_ai_helpers.cli.azure_devops.review_commands.AzureDevOpsConfig.from_state",
                                                        return_value=mock_config,
                                                    ):
                                                        with patch(
                                                            "agdt_ai_helpers.state.set_bootstrap_state",
                                                            side_effect=OSError("disk full"),
                                                        ):
                                                            with patch("agdt_ai_helpers.state.set_value"):
                                                                with patch("agdt_ai_helpers.state.delete_value"):
                                                                    setup_pull_request_review()

        captured = capsys.readouterr()
        assert "WARNING: bootstrap state init failed" in captured.err
        assert "disk full" in captured.err

    def test_resets_pull_request_id_in_scoped_state(self):
        """Regression: pull_request_id must be re-set after bootstrap changes state dir."""
        _, mock_set_value, _ = self._run_setup_with_captures()

        pr_id_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "pull_request_id"]
        assert len(pr_id_calls) == 1
        assert pr_id_calls[0][0][1] == "123"

    def test_resets_jira_issue_key_when_present(self):
        """Regression: jira.issue_key must be re-set after bootstrap when originally present."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        def get_value_with_jira(key, default=None):
            mapping = {
                "pull_request_id": "456",
                "jira.issue_key": "DFLY-789",
                "include_reviewed": "false",
            }
            return mapping.get(key, default)

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "/repo/root\n"

        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/testorg"
        mock_config.project = "TestProject"
        mock_config.repository = "test-repo"

        mock_set_value = MagicMock()

        pr_details = self._make_pr_details()

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=get_value_with_jira,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(pr_details)
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(True, None, set()),
                        ):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                return_value=(3, 0, 0, MagicMock()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                ):
                                    with patch("agdt_ai_helpers.state.set_workflow_state"):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch(
                                                "agentic_devtools.config.load_review_focus_areas",
                                                return_value=None,
                                            ):
                                                with patch(
                                                    "agdt_ai_helpers.cli.azure_devops.review_commands.run_safe",
                                                    return_value=mock_git_result,
                                                ):
                                                    with patch(
                                                        "agdt_ai_helpers.cli.azure_devops.review_commands.AzureDevOpsConfig.from_state",
                                                        return_value=mock_config,
                                                    ):
                                                        with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                                            with patch(
                                                                "agdt_ai_helpers.state.set_value",
                                                                mock_set_value,
                                                            ):
                                                                with patch("agdt_ai_helpers.state.delete_value"):
                                                                    setup_pull_request_review()

        jira_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "jira.issue_key"]
        assert len(jira_calls) >= 1
        assert jira_calls[0][0][1] == "DFLY-789"

    def test_does_not_set_jira_issue_key_when_absent(self):
        """Regression: jira.issue_key must NOT be re-set when it was not in state."""
        _, mock_set_value, _ = self._run_setup_with_captures()

        jira_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "jira.issue_key"]
        assert len(jira_calls) == 0

    def test_resets_include_reviewed_when_true(self):
        """Regression: include_reviewed must be re-set after bootstrap when originally true."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        def get_value_with_include_reviewed(key, default=None):
            mapping = {
                "pull_request_id": "456",
                "jira.issue_key": None,
                "include_reviewed": "true",
            }
            return mapping.get(key, default)

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "/repo/root\n"

        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/testorg"
        mock_config.project = "TestProject"
        mock_config.repository = "test-repo"

        mock_set_value = MagicMock()

        pr_details = self._make_pr_details()

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=get_value_with_include_reviewed,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(pr_details)
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(True, None, set()),
                        ):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                return_value=(3, 0, 0, MagicMock()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                ):
                                    with patch("agdt_ai_helpers.state.set_workflow_state"):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch(
                                                "agentic_devtools.config.load_review_focus_areas",
                                                return_value=None,
                                            ):
                                                with patch(
                                                    "agdt_ai_helpers.cli.azure_devops.review_commands.run_safe",
                                                    return_value=mock_git_result,
                                                ):
                                                    with patch(
                                                        "agdt_ai_helpers.cli.azure_devops.review_commands.AzureDevOpsConfig.from_state",
                                                        return_value=mock_config,
                                                    ):
                                                        with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                                            with patch(
                                                                "agdt_ai_helpers.state.set_value",
                                                                mock_set_value,
                                                            ):
                                                                with patch("agdt_ai_helpers.state.delete_value"):
                                                                    setup_pull_request_review()

        include_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "include_reviewed"]
        assert len(include_calls) == 1
        assert include_calls[0][0][1] == "true"

    def test_resets_review_model_id_when_present(self):
        """Regression: review.model_id must be re-set after bootstrap when originally present."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        def get_value_with_model_id(key, default=None):
            mapping = {
                "pull_request_id": "456",
                "jira.issue_key": None,
                "include_reviewed": "false",
                "review.model_id": "gpt-4o",
            }
            return mapping.get(key, default)

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "/repo/root\n"

        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/testorg"
        mock_config.project = "TestProject"
        mock_config.repository = "test-repo"

        mock_set_value = MagicMock()

        pr_details = self._make_pr_details()

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=get_value_with_model_id,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(pr_details)
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(True, None, set()),
                        ):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                return_value=(3, 0, 0, MagicMock()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                ):
                                    with patch("agdt_ai_helpers.state.set_workflow_state"):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch(
                                                "agentic_devtools.config.load_review_focus_areas",
                                                return_value=None,
                                            ):
                                                with patch(
                                                    "agdt_ai_helpers.cli.azure_devops.review_commands.run_safe",
                                                    return_value=mock_git_result,
                                                ):
                                                    with patch(
                                                        "agdt_ai_helpers.cli.azure_devops.review_commands.AzureDevOpsConfig.from_state",
                                                        return_value=mock_config,
                                                    ):
                                                        with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                                            with patch(
                                                                "agdt_ai_helpers.state.set_value",
                                                                mock_set_value,
                                                            ):
                                                                with patch("agdt_ai_helpers.state.delete_value"):
                                                                    setup_pull_request_review()

        model_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "review.model_id"]
        assert len(model_calls) >= 1
        assert model_calls[0][0][1] == "gpt-4o"

    def test_does_not_set_review_model_id_when_absent(self):
        """Regression: review.model_id must NOT be re-set when it was not in state."""
        _, mock_set_value, _ = self._run_setup_with_captures()

        model_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "review.model_id"]
        assert len(model_calls) == 0

    def test_resets_dry_run_when_present(self):
        """Regression: dry_run must be re-set after bootstrap when originally present."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        def get_value_with_dry_run(key, default=None):
            mapping = {
                "pull_request_id": "456",
                "jira.issue_key": None,
                "include_reviewed": "false",
                "dry_run": "true",
            }
            return mapping.get(key, default)

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "/repo/root\n"

        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/testorg"
        mock_config.project = "TestProject"
        mock_config.repository = "test-repo"

        mock_set_value = MagicMock()

        pr_details = self._make_pr_details()

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=get_value_with_dry_run,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(pr_details)
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(True, None, set()),
                        ):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                return_value=(3, 0, 0, MagicMock()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                ):
                                    with patch("agdt_ai_helpers.state.set_workflow_state"):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch(
                                                "agentic_devtools.config.load_review_focus_areas",
                                                return_value=None,
                                            ):
                                                with patch(
                                                    "agdt_ai_helpers.cli.azure_devops.review_commands.run_safe",
                                                    return_value=mock_git_result,
                                                ):
                                                    with patch(
                                                        "agdt_ai_helpers.cli.azure_devops.review_commands.AzureDevOpsConfig.from_state",
                                                        return_value=mock_config,
                                                    ):
                                                        with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                                            with patch(
                                                                "agdt_ai_helpers.state.set_value",
                                                                mock_set_value,
                                                            ):
                                                                with patch("agdt_ai_helpers.state.delete_value"):
                                                                    setup_pull_request_review()

        dry_run_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "dry_run"]
        assert len(dry_run_calls) >= 1
        assert dry_run_calls[0][0][1] == "true"

    def test_does_not_set_dry_run_when_absent(self):
        """Regression: dry_run must NOT be re-set when it was not in state."""
        _, mock_set_value, _ = self._run_setup_with_captures()

        dry_run_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "dry_run"]
        assert len(dry_run_calls) == 0

    def test_stores_commit_hash_short_when_pr_has_source_commit(self):
        """Regression: review.commit_hash_short must be stored from lastMergeSourceCommit.commitId[:8]."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        pr_details_with_commit = {
            "pullRequest": {
                "pullRequestId": 123,
                "title": "Test PR",
                "createdBy": {"displayName": "Test User"},
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
                "lastMergeSourceCommit": {
                    "commitId": "abcdef1234567890abcdef1234567890abcdef12",
                },
            },
            "files": [],
            "threads": [],
        }

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "/repo/root\n"

        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/testorg"
        mock_config.project = "TestProject"
        mock_config.repository = "test-repo"

        mock_set_value = MagicMock()

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=self._default_get_value,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(pr_details_with_commit)
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(True, None, set()),
                        ):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                return_value=(3, 0, 0, MagicMock()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                ):
                                    with patch("agdt_ai_helpers.state.set_workflow_state"):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch(
                                                "agentic_devtools.config.load_review_focus_areas",
                                                return_value=None,
                                            ):
                                                with patch(
                                                    "agdt_ai_helpers.cli.azure_devops.review_commands.run_safe",
                                                    return_value=mock_git_result,
                                                ):
                                                    with patch(
                                                        "agdt_ai_helpers.cli.azure_devops.review_commands.AzureDevOpsConfig.from_state",
                                                        return_value=mock_config,
                                                    ):
                                                        with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                                            with patch(
                                                                "agdt_ai_helpers.state.set_value",
                                                                mock_set_value,
                                                            ):
                                                                with patch("agentic_devtools.state.delete_value"):
                                                                    setup_pull_request_review()

        commit_hash_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "review.commit_hash_short"]
        assert len(commit_hash_calls) == 1
        assert commit_hash_calls[0][0][1] == "abcdef12"

    def test_does_not_store_commit_hash_when_no_source_commit(self):
        """review.commit_hash_short must NOT be set when lastMergeSourceCommit is absent.

        delete_value clears any stale value.
        """
        _, mock_set_value, mock_delete_value = self._run_setup_with_captures()

        commit_hash_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "review.commit_hash_short"]
        assert len(commit_hash_calls) == 0

        delete_calls = [c for c in mock_delete_value.call_args_list if c[0][0] == "review.commit_hash_short"]
        assert len(delete_calls) == 1

    def test_deletes_commit_hash_when_derived_short_hash_is_unsafe(self, capsys):
        """Unsafe first 8 chars in commitId should emit warning and clear stale scoped state."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        pr_details_with_unsafe_commit = {
            "pullRequest": {
                "pullRequestId": 123,
                "title": "Test PR",
                "createdBy": {"displayName": "Test User"},
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
                "lastMergeSourceCommit": {
                    "commitId": "../badidcafefeed1234567890abcdef12345678",
                },
            },
            "files": [],
            "threads": [],
        }

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "/repo/root\n"

        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/testorg"
        mock_config.project = "TestProject"
        mock_config.repository = "test-repo"

        mock_set_value = MagicMock()
        mock_delete_value = MagicMock()

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=self._default_get_value,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = (
                        json.dumps(pr_details_with_unsafe_commit)
                    )
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(True, None, set()),
                        ):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                return_value=(3, 0, 0, MagicMock()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                ):
                                    with patch("agdt_ai_helpers.state.set_workflow_state"):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch(
                                                "agentic_devtools.config.load_review_focus_areas",
                                                return_value=None,
                                            ):
                                                with patch(
                                                    "agdt_ai_helpers.cli.azure_devops.review_commands.run_safe",
                                                    return_value=mock_git_result,
                                                ):
                                                    with patch(
                                                        "agdt_ai_helpers.cli.azure_devops.review_commands.AzureDevOpsConfig.from_state",
                                                        return_value=mock_config,
                                                    ):
                                                        with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                                            with patch(
                                                                "agdt_ai_helpers.state.set_value",
                                                                mock_set_value,
                                                            ):
                                                                with patch(
                                                                    "agdt_ai_helpers.state.delete_value",
                                                                    mock_delete_value,
                                                                ):
                                                                    setup_pull_request_review()

        commit_hash_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "review.commit_hash_short"]
        assert len(commit_hash_calls) == 0

        delete_calls = [c for c in mock_delete_value.call_args_list if c[0][0] == "review.commit_hash_short"]
        assert len(delete_calls) == 1

        captured = capsys.readouterr()
        assert "unexpected characters" in captured.err

    def test_handles_non_string_commit_id(self, capsys):
        """When lastMergeSourceCommit.commitId is not a string, emits a warning and deletes stale key."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        pr_details_with_int_commit_id = {
            "pullRequest": {
                "pullRequestId": 123,
                "title": "Test PR",
                "createdBy": {"displayName": "Test User"},
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
                "lastMergeSourceCommit": {
                    "commitId": 12345,  # non-string: should trigger the isinstance guard
                },
            },
            "files": [],
            "threads": [],
        }

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "/repo/root\n"

        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/testorg"
        mock_config.project = "TestProject"
        mock_config.repository = "test-repo"

        mock_set_value = MagicMock()
        mock_delete_value = MagicMock()

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=self._default_get_value,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
                        pr_details_with_int_commit_id
                    )
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(True, None, set()),
                        ):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                return_value=(3, 0, 0, MagicMock()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                ):
                                    with patch("agdt_ai_helpers.state.set_workflow_state"):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch(
                                                "agentic_devtools.config.load_review_focus_areas",
                                                return_value=None,
                                            ):
                                                with patch(
                                                    "agdt_ai_helpers.cli.azure_devops.review_commands.run_safe",
                                                    return_value=mock_git_result,
                                                ):
                                                    with patch(
                                                        "agdt_ai_helpers.cli.azure_devops.review_commands.AzureDevOpsConfig.from_state",
                                                        return_value=mock_config,
                                                    ):
                                                        with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                                            with patch(
                                                                "agdt_ai_helpers.state.set_value",
                                                                mock_set_value,
                                                            ):
                                                                with patch(
                                                                    "agdt_ai_helpers.state.delete_value",
                                                                    mock_delete_value,
                                                                ):
                                                                    setup_pull_request_review()

        # commit_hash_short must NOT be set — non-str commitId is treated as absent
        commit_hash_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "review.commit_hash_short"]
        assert len(commit_hash_calls) == 0

        # delete_value should have been called to clear any stale key
        delete_calls = [c for c in mock_delete_value.call_args_list if c[0][0] == "review.commit_hash_short"]
        assert len(delete_calls) == 1

        # A warning should have been emitted to stderr
        captured = capsys.readouterr()
        assert "unexpected type" in captured.err

    def test_treats_whitespace_only_commit_id_as_absent(self, capsys):
        """Whitespace-only commit IDs should clear stale scoped state without warning."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        pr_details_with_whitespace_commit_id = {
            "pullRequest": {
                "pullRequestId": 123,
                "title": "Test PR",
                "createdBy": {"displayName": "Test User"},
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
                "lastMergeSourceCommit": {
                    "commitId": "   \t   ",
                },
            },
            "files": [],
            "threads": [],
        }

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "/repo/root\n"

        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/testorg"
        mock_config.project = "TestProject"
        mock_config.repository = "test-repo"

        mock_set_value = MagicMock()
        mock_delete_value = MagicMock()

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=self._default_get_value,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
                        pr_details_with_whitespace_commit_id
                    )
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(True, None, set()),
                        ):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                return_value=(3, 0, 0, MagicMock()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                ):
                                    with patch("agdt_ai_helpers.state.set_workflow_state"):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch(
                                                "agentic_devtools.config.load_review_focus_areas",
                                                return_value=None,
                                            ):
                                                with patch(
                                                    "agdt_ai_helpers.cli.azure_devops.review_commands.run_safe",
                                                    return_value=mock_git_result,
                                                ):
                                                    with patch(
                                                        "agdt_ai_helpers.cli.azure_devops.review_commands.AzureDevOpsConfig.from_state",
                                                        return_value=mock_config,
                                                    ):
                                                        with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                                            with patch(
                                                                "agdt_ai_helpers.state.set_value",
                                                                mock_set_value,
                                                            ):
                                                                with patch(
                                                                    "agdt_ai_helpers.state.delete_value",
                                                                    mock_delete_value,
                                                                ):
                                                                    setup_pull_request_review()

        commit_hash_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "review.commit_hash_short"]
        assert len(commit_hash_calls) == 0

        delete_calls = [c for c in mock_delete_value.call_args_list if c[0][0] == "review.commit_hash_short"]
        assert len(delete_calls) == 1

        captured = capsys.readouterr()
        assert "unexpected type" not in captured.err
        assert "unexpected characters" not in captured.err

    def test_handles_non_dict_last_merge_source_commit(self, capsys):
        """When lastMergeSourceCommit is not a dict (e.g. JSON null → None), no AttributeError; stale key is cleared."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        pr_details_with_null_last_merge = {
            "pullRequest": {
                "pullRequestId": 123,
                "title": "Test PR",
                "createdBy": {"displayName": "Test User"},
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
                "lastMergeSourceCommit": None,  # JSON null: must not raise AttributeError
            },
            "files": [],
            "threads": [],
        }

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "/repo/root\n"

        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/testorg"
        mock_config.project = "TestProject"
        mock_config.repository = "test-repo"

        mock_set_value = MagicMock()
        mock_delete_value = MagicMock()

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=self._default_get_value,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
                        pr_details_with_null_last_merge
                    )
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(True, None, set()),
                        ):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                return_value=(3, 0, 0, MagicMock()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                ):
                                    with patch("agdt_ai_helpers.state.set_workflow_state"):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch(
                                                "agentic_devtools.config.load_review_focus_areas",
                                                return_value=None,
                                            ):
                                                with patch(
                                                    "agdt_ai_helpers.cli.azure_devops.review_commands.run_safe",
                                                    return_value=mock_git_result,
                                                ):
                                                    with patch(
                                                        "agdt_ai_helpers.cli.azure_devops.review_commands.AzureDevOpsConfig.from_state",
                                                        return_value=mock_config,
                                                    ):
                                                        with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                                            with patch(
                                                                "agdt_ai_helpers.state.set_value",
                                                                mock_set_value,
                                                            ):
                                                                with patch(
                                                                    "agdt_ai_helpers.state.delete_value",
                                                                    mock_delete_value,
                                                                ):
                                                                    setup_pull_request_review()

        # commit_hash_short must NOT be set — null lastMergeSourceCommit treated as absent
        commit_hash_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "review.commit_hash_short"]
        assert len(commit_hash_calls) == 0

        # delete_value should have been called to clear any stale key
        delete_calls = [c for c in mock_delete_value.call_args_list if c[0][0] == "review.commit_hash_short"]
        assert len(delete_calls) == 1

        # No type warning for None (it's simply absent, not an unexpected type)
        captured = capsys.readouterr()
        assert "unexpected type" not in captured.err

    def test_warns_on_non_null_non_dict_last_merge_source_commit(self, capsys):
        """When lastMergeSourceCommit is not a dict and not None, emits warning and clears stale key."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        pr_details_with_invalid_last_merge = {
            "pullRequest": {
                "pullRequestId": 123,
                "title": "Test PR",
                "createdBy": {"displayName": "Test User"},
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
                "lastMergeSourceCommit": [],  # non-null, non-dict: should trigger warning
            },
            "files": [],
            "threads": [],
        }

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "/repo/root\n"

        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/testorg"
        mock_config.project = "TestProject"
        mock_config.repository = "test-repo"

        mock_set_value = MagicMock()
        mock_delete_value = MagicMock()

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=self._default_get_value,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
                        pr_details_with_invalid_last_merge
                    )
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(True, None, set()),
                        ):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                return_value=(3, 0, 0, MagicMock()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                ):
                                    with patch("agdt_ai_helpers.state.set_workflow_state"):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch(
                                                "agentic_devtools.config.load_review_focus_areas",
                                                return_value=None,
                                            ):
                                                with patch(
                                                    "agdt_ai_helpers.cli.azure_devops.review_commands.run_safe",
                                                    return_value=mock_git_result,
                                                ):
                                                    with patch(
                                                        "agdt_ai_helpers.cli.azure_devops.review_commands.AzureDevOpsConfig.from_state",
                                                        return_value=mock_config,
                                                    ):
                                                        with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                                            with patch(
                                                                "agdt_ai_helpers.state.set_value",
                                                                mock_set_value,
                                                            ):
                                                                with patch(
                                                                    "agdt_ai_helpers.state.delete_value",
                                                                    mock_delete_value,
                                                                ):
                                                                    setup_pull_request_review()

        commit_hash_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "review.commit_hash_short"]
        assert len(commit_hash_calls) == 0

        delete_calls = [c for c in mock_delete_value.call_args_list if c[0][0] == "review.commit_hash_short"]
        assert len(delete_calls) == 1

        captured = capsys.readouterr()
        assert "unexpected type" in captured.err
        assert "list" in captured.err

    def test_does_not_store_commit_hash_when_unsafe_characters(self, capsys):
        """When derived commit_hash_short fails is_safe_dir_segment(), stale key is cleared and warning emitted."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        pr_details_with_unsafe_commit_id = {
            "pullRequest": {
                "pullRequestId": 123,
                "title": "Test PR",
                "createdBy": {"displayName": "Test User"},
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
                "lastMergeSourceCommit": {
                    "commitId": "..evilXXXXXXXXX",  # contains ".."; fails is_safe_dir_segment guard
                },
            },
            "files": [],
            "threads": [],
        }

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "/repo/root\n"

        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/testorg"
        mock_config.project = "TestProject"
        mock_config.repository = "test-repo"

        mock_set_value = MagicMock()
        mock_delete_value = MagicMock()

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=self._default_get_value,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
                        pr_details_with_unsafe_commit_id
                    )
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(True, None, set()),
                        ):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                return_value=(3, 0, 0, MagicMock()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                ):
                                    with patch("agdt_ai_helpers.state.set_workflow_state"):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch(
                                                "agentic_devtools.config.load_review_focus_areas",
                                                return_value=None,
                                            ):
                                                with patch(
                                                    "agdt_ai_helpers.cli.azure_devops.review_commands.run_safe",
                                                    return_value=mock_git_result,
                                                ):
                                                    with patch(
                                                        "agdt_ai_helpers.cli.azure_devops.review_commands.AzureDevOpsConfig.from_state",
                                                        return_value=mock_config,
                                                    ):
                                                        with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                                            with patch(
                                                                "agdt_ai_helpers.state.set_value",
                                                                mock_set_value,
                                                            ):
                                                                with patch(
                                                                    "agdt_ai_helpers.state.delete_value",
                                                                    mock_delete_value,
                                                                ):
                                                                    setup_pull_request_review()

        # commit_hash_short must NOT be set — unsafe characters are rejected
        commit_hash_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "review.commit_hash_short"]
        assert len(commit_hash_calls) == 0

        # delete_value should have been called to clear any stale key
        delete_calls = [c for c in mock_delete_value.call_args_list if c[0][0] == "review.commit_hash_short"]
        assert len(delete_calls) == 1

        # A warning should have been emitted to stderr
        captured = capsys.readouterr()
        assert "unexpected characters" in captured.err

    def test_does_not_store_commit_hash_when_short_hash_fails_safety_check(self, capsys):
        """When the derived short hash is rejected, setup falls back to PR-scoped artifacts."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            setup_pull_request_review,
        )

        pr_details_with_commit = {
            "pullRequest": {
                "pullRequestId": 123,
                "title": "Test PR",
                "createdBy": {"displayName": "Test User"},
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
                "lastMergeSourceCommit": {
                    "commitId": "abcdef1234567890abcdef1234567890abcdef12",
                },
            },
            "files": [],
            "threads": [],
        }

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "/repo/root\n"

        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/testorg"
        mock_config.project = "TestProject"
        mock_config.repository = "test-repo"

        mock_set_value = MagicMock()
        mock_delete_value = MagicMock()

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=self._default_get_value,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_dry_run",
            return_value=False,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.is_safe_dir_segment",
            return_value=False,
        ) as mock_is_safe_dir_segment:
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
                        pr_details_with_commit
                    )
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(True, None, set()),
                        ):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                return_value=(3, 0, 0, MagicMock()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                ):
                                    with patch("agdt_ai_helpers.state.set_workflow_state"):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch(
                                                "agentic_devtools.config.load_review_focus_areas",
                                                return_value=None,
                                            ):
                                                with patch(
                                                    "agdt_ai_helpers.cli.azure_devops.review_commands.run_safe",
                                                    return_value=mock_git_result,
                                                ):
                                                    with patch(
                                                        "agdt_ai_helpers.cli.azure_devops.review_commands.AzureDevOpsConfig.from_state",
                                                        return_value=mock_config,
                                                    ):
                                                        with patch("agdt_ai_helpers.state.set_bootstrap_state"):
                                                            with patch(
                                                                "agdt_ai_helpers.state.set_value",
                                                                mock_set_value,
                                                            ):
                                                                with patch(
                                                                    "agdt_ai_helpers.state.delete_value",
                                                                    mock_delete_value,
                                                                ):
                                                                    setup_pull_request_review()

        mock_is_safe_dir_segment.assert_called_once_with("abcdef12")

        commit_hash_calls = [c for c in mock_set_value.call_args_list if c[0][0] == "review.commit_hash_short"]
        assert len(commit_hash_calls) == 0

        delete_calls = [c for c in mock_delete_value.call_args_list if c[0][0] == "review.commit_hash_short"]
        assert len(delete_calls) == 1

        captured = capsys.readouterr()
        assert "unexpected characters" in captured.err
