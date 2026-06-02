"""Tests for GitHubActionsProvider._fetch_outdated_by_comment_id()."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


def _mock_run_safe_response(data):
    class _Result:
        returncode = 0
        stdout = json.dumps(data)
        stderr = ""

    return _Result()


class TestFetchOutdatedByCommentId:
    """Tests for isOutdated mapping via GraphQL thread query."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_maps_comment_ids_to_outdated_status(self, mock_run_safe):
        mock_run_safe.return_value = _mock_run_safe_response(
            {
                "data": {
                    "repository": {
                        "pullRequest": {
                            "reviewThreads": {
                                "pageInfo": {"hasNextPage": False, "endCursor": None},
                                "nodes": [
                                    {
                                        "isOutdated": True,
                                        "comments": {"nodes": [{"databaseId": 10}, {"databaseId": 11}]},
                                    },
                                    {
                                        "isOutdated": False,
                                        "comments": {"nodes": [{"databaseId": 12}]},
                                    },
                                ],
                            }
                        }
                    }
                }
            }
        )
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider._fetch_outdated_by_comment_id(42)

        assert result == {10: True, 11: True, 12: False}
        payload = json.loads(mock_run_safe.call_args.kwargs["input"])
        assert payload["query"]
        assert payload["variables"] == {
            "owner": "owner",
            "repoName": "repo",
            "prNumber": 42,
        }

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_handles_pagination(self, mock_run_safe):
        mock_run_safe.side_effect = [
            _mock_run_safe_response(
                {
                    "data": {
                        "repository": {
                            "pullRequest": {
                                "reviewThreads": {
                                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                                    "nodes": [
                                        {
                                            "isOutdated": True,
                                            "comments": {"nodes": [{"databaseId": 20}]},
                                        }
                                    ],
                                }
                            }
                        }
                    }
                }
            ),
            _mock_run_safe_response(
                {
                    "data": {
                        "repository": {
                            "pullRequest": {
                                "reviewThreads": {
                                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                                    "nodes": [
                                        {
                                            "isOutdated": False,
                                            "comments": {"nodes": [{"databaseId": 21}, {"databaseId": 22}]},
                                        }
                                    ],
                                }
                            }
                        }
                    }
                }
            ),
        ]
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider._fetch_outdated_by_comment_id(42)

        assert result[20] is True
        assert result[21] is False
        assert result[22] is False
        assert mock_run_safe.call_count == 2
        second_payload = json.loads(mock_run_safe.call_args.kwargs["input"])
        assert second_payload["variables"]["threadsCursor"] == "cursor-1"

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_skips_non_integer_database_id(self, mock_run_safe):
        """comment_id that is not an int is silently skipped."""
        mock_run_safe.return_value = _mock_run_safe_response(
            {
                "data": {
                    "repository": {
                        "pullRequest": {
                            "reviewThreads": {
                                "pageInfo": {"hasNextPage": False, "endCursor": None},
                                "nodes": [
                                    {
                                        "isOutdated": True,
                                        "comments": {
                                            "nodes": [
                                                {"databaseId": "not-an-int"},
                                                {"databaseId": 42},
                                            ]
                                        },
                                    }
                                ],
                            }
                        }
                    }
                }
            }
        )
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider._fetch_outdated_by_comment_id(99)

        assert "not-an-int" not in result
        assert result[42] is True

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_thread_with_none_is_outdated(self, mock_run_safe):
        """Thread missing isOutdated yields None for its comment ids."""
        mock_run_safe.return_value = _mock_run_safe_response(
            {
                "data": {
                    "repository": {
                        "pullRequest": {
                            "reviewThreads": {
                                "pageInfo": {"hasNextPage": False, "endCursor": None},
                                "nodes": [
                                    {
                                        "comments": {"nodes": [{"databaseId": 55}]},
                                    }
                                ],
                            }
                        }
                    }
                }
            }
        )
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider._fetch_outdated_by_comment_id(1)

        assert result[55] is None

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_ignores_threads_without_comments(self, mock_run_safe):
        """Threads with no comments are ignored safely."""
        mock_run_safe.return_value = _mock_run_safe_response(
            {
                "data": {
                    "repository": {
                        "pullRequest": {
                            "reviewThreads": {
                                "pageInfo": {"hasNextPage": False, "endCursor": None},
                                "nodes": [
                                    {"isOutdated": True, "comments": {"nodes": []}},
                                    {"isOutdated": False, "comments": {"nodes": [{"databaseId": 77}]}},
                                ],
                            }
                        }
                    }
                }
            }
        )
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider._fetch_outdated_by_comment_id(1)

        assert result == {77: False}

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_latest_body_reuses_cached_thread_signal_scan(self, mock_run_safe):
        mock_run_safe.return_value = _mock_run_safe_response(
            {
                "data": {
                    "repository": {
                        "pullRequest": {
                            "reviewThreads": {
                                "pageInfo": {"hasNextPage": False, "endCursor": None},
                                "nodes": [
                                    {
                                        "isOutdated": True,
                                        "comments": {
                                            "nodes": [
                                                {"databaseId": 10, "body": "first"},
                                                {
                                                    "databaseId": 11,
                                                    "body": "latest",
                                                    "author": {"login": "copilot[bot]"},
                                                },
                                            ]
                                        },
                                    }
                                ],
                            }
                        }
                    }
                }
            }
        )
        provider = GitHubActionsProvider(repo="owner/repo")

        outdated = provider._fetch_outdated_by_comment_id(42)
        latest = provider._fetch_latest_thread_comment_body_by_comment_id(42)
        latest_author = provider._fetch_latest_thread_comment_author_login_by_comment_id(42)

        assert outdated == {10: True, 11: True}
        assert latest == {10: "latest", 11: "latest"}
        assert latest_author == {10: "copilot[bot]", 11: "copilot[bot]"}
        assert mock_run_safe.call_count == 1
