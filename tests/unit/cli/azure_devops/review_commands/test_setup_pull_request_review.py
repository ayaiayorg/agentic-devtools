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
        captured_variables = {}

        def capture_render(workflow_name, step_name, variables, **kwargs):
            captured_variables.update(variables)

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "/repo/root\n"

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=self._default_get_value,
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
                                                    from agdt_ai_helpers.cli.azure_devops.review_commands import (
                                                        setup_pull_request_review,
                                                    )

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

    def test_load_review_focus_areas_called_with_git_root(self):
        """Test that load_review_focus_areas is called with the git repo root when available."""
        pr_details = self._make_pr_details()

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "/repo/root\n"

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=self._default_get_value,
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
                                                    from agdt_ai_helpers.cli.azure_devops.review_commands import (
                                                        setup_pull_request_review,
                                                    )

                                                    setup_pull_request_review()
                                                    mock_load.assert_called_once_with("/repo/root")

    def test_load_review_focus_areas_falls_back_to_cwd_when_git_fails(self):
        """Test that load_review_focus_areas falls back to cwd when git rev-parse fails."""
        pr_details = self._make_pr_details()

        mock_git_result = MagicMock()
        mock_git_result.returncode = 128
        mock_git_result.stdout = ""

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=self._default_get_value,
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
                                                    from agdt_ai_helpers.cli.azure_devops.review_commands import (
                                                        setup_pull_request_review,
                                                    )

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
                                                from agdt_ai_helpers.cli.azure_devops.review_commands import (
                                                    setup_pull_request_review,
                                                )

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
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_pr_details)
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(False, "Checkout error", set()),
                        ):
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
                                        from agdt_ai_helpers.cli.azure_devops.review_commands import (
                                            setup_pull_request_review,
                                        )

                                        setup_pull_request_review()
                                        captured = capsys.readouterr()
                                        assert "Could not determine source branch" in captured.err
