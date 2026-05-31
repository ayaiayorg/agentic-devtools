"""Tests for GitHubActionsProvider._list_unresolve_reply_parent_comment_ids."""

from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


@patch("agentic_devtools.cli.ci.github_provider._parse_paginated_json")
@patch("agentic_devtools.cli.ci.github_provider._gh_api")
def test__list_unresolve_reply_parent_comment_ids_returns_only_unresolve(mock_gh_api, mock_parse) -> None:
    """Only replies containing the resolution-tier marker and 'Thread left open' text are included."""
    mock_gh_api.return_value = "[]"
    mock_parse.return_value = [
        {
            "in_reply_to_id": 100,
            "body": "<!-- agdt:resolution-tier:sdk_evaluation -->\n❌ **Thread left open** [high]",
        },
        {
            "in_reply_to_id": 101,
            "body": "<!-- agdt:resolution-tier:diff_heuristic -->\n✅ **Thread resolved** [medium]",
        },
        {
            "in_reply_to_id": 102,
            "body": "<!-- agdt:resolution-tier:engine -->\n🔄 **Tentative resolution** [low]",
        },
        {
            "in_reply_to_id": 103,
            "body": "<!-- agdt:resolution-tier:abandoned -->\n⚠️ **Resolution abandoned**",
        },
        {"in_reply_to_id": 104, "body": "Some other reply without marker"},
        {"in_reply_to_id": 105, "body": "Addressed on the updated PR branch."},
    ]
    provider = GitHubActionsProvider(repo="owner/repo")

    result = provider._list_unresolve_reply_parent_comment_ids(42)

    assert result == {100}
    assert 101 not in result
    assert 102 not in result
    assert 103 not in result
    assert 104 not in result
    assert 105 not in result
    mock_gh_api.assert_called_once_with("/repos/owner/repo/pulls/42/comments", paginate=True)


@patch("agentic_devtools.cli.ci.github_provider._parse_paginated_json")
@patch("agentic_devtools.cli.ci.github_provider._gh_api")
def test__list_unresolve_reply_parent_comment_ids_excludes_replies_without_in_reply_to(mock_gh_api, mock_parse) -> None:
    """Top-level comments without in_reply_to_id are excluded."""
    mock_gh_api.return_value = "[]"
    mock_parse.return_value = [
        {"body": "<!-- agdt:resolution-tier:sdk_evaluation -->\n❌ **Thread left open** [high]"},
        {
            "in_reply_to_id": 200,
            "body": "<!-- agdt:resolution-tier:sdk_evaluation -->\n❌ **Thread left open** [high]",
        },
    ]
    provider = GitHubActionsProvider(repo="owner/repo")

    result = provider._list_unresolve_reply_parent_comment_ids(99)

    assert result == {200}


@patch("agentic_devtools.cli.ci.github_provider._parse_paginated_json")
@patch("agentic_devtools.cli.ci.github_provider._gh_api")
def test__list_unresolve_reply_parent_comment_ids_empty_when_no_unresolve_replies(mock_gh_api, mock_parse) -> None:
    """Returns empty set when no comments have the Thread-left-open marker."""
    mock_gh_api.return_value = "[]"
    mock_parse.return_value = [
        {"in_reply_to_id": 10, "body": "Addressed on the updated PR branch."},
        {
            "in_reply_to_id": 20,
            "body": "<!-- agdt:resolution-tier:outdated -->\n✅ **Thread resolved** [high]",
        },
    ]
    provider = GitHubActionsProvider(repo="owner/repo")

    result = provider._list_unresolve_reply_parent_comment_ids(42)

    assert result == set()
