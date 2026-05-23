"""Tests for GitHubActionsProvider.list_review_thread_states()."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


def _mock_run_safe_response(data):
    class _Result:
        returncode = 0
        stdout = json.dumps(data)
        stderr = ""

    return _Result()


class TestListReviewThreadStates:
    """Tests for review thread state mapping."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_maps_comment_ids_to_resolution_and_reply_state(self, mock_run_safe):
        mock_run_safe.return_value = _mock_run_safe_response(
            {
                "data": {
                    "repository": {
                        "pullRequest": {
                            "reviewThreads": {
                                "pageInfo": {"hasNextPage": False, "endCursor": None},
                                "nodes": [
                                    {
                                        "isResolved": True,
                                        "comments": {"nodes": [{"databaseId": 10}, {"databaseId": 11}]},
                                    },
                                    {
                                        "isResolved": False,
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

        result = provider.list_review_thread_states(42)

        assert result == {
            10: (True, True),
            11: (True, True),
            12: (False, False),
        }
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
                                            "isResolved": False,
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
                                            "isResolved": True,
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

        result = provider.list_review_thread_states(42)

        assert result[20] == (False, False)
        assert result[21] == (True, True)
        assert result[22] == (True, True)
        assert mock_run_safe.call_count == 2
        second_payload = json.loads(mock_run_safe.call_args.kwargs["input"])
        assert second_payload["variables"]["threadsCursor"] == "cursor-1"
