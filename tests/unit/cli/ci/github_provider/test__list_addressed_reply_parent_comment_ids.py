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
        {"in_reply_to_id": 25, "body": "Addressed on the updated PR branch."},
        {"in_reply_to_id": 27, "body": "  addressed on the updated pr branch.  "},
        {"in_reply_to_id": 28, "body": "not addressed by fix commit"},
        {"in_reply_to_id": 30, "body": "Not addressed yet"},
        {"body": "Addressed on the updated PR branch."},
    ]
    provider = GitHubActionsProvider(repo="owner/repo")

    assert provider._list_addressed_reply_parent_comment_ids(42) == {10, 20, 25, 27}
    mock_gh_api.assert_called_once_with("/repos/owner/repo/pulls/42/comments", paginate=True)


@patch("agentic_devtools.cli.ci.github_provider._parse_paginated_json")
@patch("agentic_devtools.cli.ci.github_provider._gh_api")
def test__list_addressed_reply_parent_comment_ids_recognizes_only_resolved_tier_markers(
    mock_gh_api, mock_parse
) -> None:
    mock_gh_api.return_value = "[]"
    mock_parse.return_value = [
        {
            "in_reply_to_id": 100,
            "body": "<!-- agdt:resolution-tier:outdated -->\n✅ **Thread resolved** [high]",
        },
        {
            "in_reply_to_id": 101,
            "body": "<!-- agdt:resolution-tier:sdk_evaluation -->\n✅ **Thread resolved** [medium]",
        },
        {
            "in_reply_to_id": 102,
            "body": "<!-- agdt:resolution-tier:abandoned -->\n⚠️ **Resolution abandoned**",
        },
        {
            "in_reply_to_id": 104,
            "body": "<!-- agdt:resolution-tier:engine -->\n🔄 **Tentative resolution** [low]",
        },
        {"in_reply_to_id": 103, "body": "Some other reply without marker"},
    ]
    provider = GitHubActionsProvider(repo="owner/repo")

    result = provider._list_addressed_reply_parent_comment_ids(42)
    assert result == {100, 101}
    assert 103 not in result
    assert 104 not in result
