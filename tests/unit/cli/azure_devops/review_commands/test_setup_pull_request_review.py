"""Tests for the review_commands module and helper functions."""

import pytest

from agdt_ai_helpers.cli.azure_devops.review_helpers import (
    JIRA_ISSUE_KEY_PATTERN,
    build_reviewed_paths_set,
    convert_to_prompt_filename,
    extract_jira_issue_key_from_title,
    filter_threads,
    get_root_folder,
    get_threads_for_file,
    normalize_repo_path,
)



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
