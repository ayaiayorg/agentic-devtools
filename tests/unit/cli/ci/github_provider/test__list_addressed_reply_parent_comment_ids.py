"""Tests for GitHubActionsProvider._list_addressed_reply_parent_comment_ids."""

from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


@patch("agentic_devtools.cli.ci.github_provider._parse_paginated_json")
@patch("agentic_devtools.cli.ci.github_provider._gh_api")
def test__list_addressed_reply_parent_comment_ids_filters_addressed_replies(mock_gh_api, mock_parse) -> None:
    mock_gh_api.return_value = "[]"
    mock_parse.return_value = [
        {"in_reply_to_id": 10, "body": "Addressed by fix commit `abc12345`."},
        {"in_reply_to_id": "20", "body": "  ADDRESSED BY FIX COMMIT `def67890`."},
        {"in_reply_to_id": 25, "body": "not addressed by fix commit"},
        {"in_reply_to_id": 30, "body": "Not addressed yet"},
        {"body": "Addressed by fix commit `fedcba98`."},
    ]
    provider = GitHubActionsProvider(repo="owner/repo")

    assert provider._list_addressed_reply_parent_comment_ids(42) == {10, 20}
    mock_gh_api.assert_called_once_with("/repos/owner/repo/pulls/42/comments", paginate=True)
