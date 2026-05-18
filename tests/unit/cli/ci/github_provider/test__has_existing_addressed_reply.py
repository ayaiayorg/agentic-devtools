"""Tests for GitHubActionsProvider._has_existing_addressed_reply."""

from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


def test__has_existing_addressed_reply_uses_provided_parent_comment_ids() -> None:
    provider = GitHubActionsProvider(repo="owner/repo")

    assert provider._has_existing_addressed_reply(
        pr_number=42,
        comment_id=10,
        addressed_reply_parent_comment_ids={10, 20},
    )
    assert not provider._has_existing_addressed_reply(
        pr_number=42,
        comment_id=30,
        addressed_reply_parent_comment_ids={10, 20},
    )


@patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
def test__has_existing_addressed_reply_fetches_parent_ids_when_not_provided(mock_list_addressed_ids) -> None:
    mock_list_addressed_ids.return_value = {77}
    provider = GitHubActionsProvider(repo="owner/repo")

    assert provider._has_existing_addressed_reply(pr_number=42, comment_id=77)
    mock_list_addressed_ids.assert_called_once_with(42)
