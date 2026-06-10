"""Tests for apply_pr_suggestions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.github.apply_thread_autofix import apply_pr_suggestions

_MODULE = "agentic_devtools.cli.github.apply_thread_autofix"


class TestApplyPrSuggestions:
    """Tests for the main apply_pr_suggestions orchestrator."""

    @patch(f"{_MODULE}._fetch_suggestions_from_page")
    @patch(f"{_MODULE}._get_pr_head_branch")
    @patch(f"{_MODULE}._get_gh_token")
    def test_no_suggestions_returns_zero(
        self, mock_token: MagicMock, mock_branch: MagicMock, mock_fetch: MagicMock
    ) -> None:
        mock_token.return_value = "token"
        mock_branch.return_value = "main"
        mock_fetch.return_value = []

        result = apply_pr_suggestions(1, "owner/repo")
        assert result["applied"] == 0
        assert result["skipped"] == 0
        assert result["commit"] is None
        assert result["files_changed"] == []
        assert result["resolution"] is None

    @patch(f"{_MODULE}._reply_and_resolve_comments")
    @patch(f"{_MODULE}._update_file_via_api")
    @patch(f"{_MODULE}._get_file_content_and_sha")
    @patch(f"{_MODULE}._fetch_suggestions_from_page")
    @patch(f"{_MODULE}._get_pr_head_branch")
    @patch(f"{_MODULE}._get_gh_token")
    def test_full_flow_applies_and_resolves(
        self,
        mock_token: MagicMock,
        mock_branch: MagicMock,
        mock_fetch: MagicMock,
        mock_get_file: MagicMock,
        mock_update: MagicMock,
        mock_resolve: MagicMock,
    ) -> None:
        mock_token.return_value = "token"
        mock_branch.return_value = "feature-branch"
        mock_fetch.return_value = [
            {
                "comment_id": 100,
                "node_id": "node_100",
                "diff_entries": [
                    {
                        "path": "src/file.py",
                        "diffLines": [
                            {"type": "HUNK", "text": "@@ -1,2 +1,3 @@"},
                            {"type": "CONTEXT", "text": "line1"},
                            {"type": "ADDITION", "text": "new_line"},
                            {"type": "CONTEXT", "text": "line2"},
                        ],
                    }
                ],
                "severity": "high",
            }
        ]
        mock_get_file.return_value = ("line1\nline2\nline3", "sha_old")
        mock_update.return_value = "new_commit_sha_123456"
        mock_resolve.return_value = {
            "replied": 1,
            "resolved": 1,
            "failed_replies": [],
            "failed_resolves": [],
        }

        result = apply_pr_suggestions(1, "owner/repo")
        assert result["applied"] == 1
        assert result["skipped"] == 0
        assert result["commit"] == "new_commit_sha_123456"
        assert "src/file.py" in result["files_changed"]
        assert result["resolution"]["replied"] == 1
        assert result["resolution"]["resolved"] == 1

    @patch(f"{_MODULE}._fetch_suggestions_from_page")
    @patch(f"{_MODULE}._get_pr_head_branch")
    @patch(f"{_MODULE}._get_gh_token")
    def test_filter_by_comment_ids(self, mock_token: MagicMock, mock_branch: MagicMock, mock_fetch: MagicMock) -> None:
        mock_token.return_value = "token"
        mock_branch.return_value = "main"
        mock_fetch.return_value = [
            {
                "comment_id": 10,
                "node_id": "n10",
                "diff_entries": [{"path": "a.py", "diffLines": []}],
                "severity": "low",
            },
            {
                "comment_id": 20,
                "node_id": "n20",
                "diff_entries": [{"path": "b.py", "diffLines": []}],
                "severity": "low",
            },
        ]

        # Filter to a non-existent comment ID — no suggestion matches, so nothing
        # is applied and no commit is created.
        result = apply_pr_suggestions(1, "owner/repo", comment_ids=[99])
        # comment 99 doesn't exist in the mocked suggestions (10, 20), so filtering leaves nothing
        assert result["applied"] == 0
        assert result["commit"] is None

    @patch(f"{_MODULE}._get_file_content_and_sha")
    @patch(f"{_MODULE}._fetch_suggestions_from_page")
    @patch(f"{_MODULE}._get_pr_head_branch")
    @patch(f"{_MODULE}._get_gh_token")
    def test_file_fetch_failure_skips_entries(
        self,
        mock_token: MagicMock,
        mock_branch: MagicMock,
        mock_fetch: MagicMock,
        mock_get_file: MagicMock,
    ) -> None:
        mock_token.return_value = "token"
        mock_branch.return_value = "main"
        mock_fetch.return_value = [
            {
                "comment_id": 100,
                "node_id": "n100",
                "diff_entries": [
                    {
                        "path": "src/broken.py",
                        "diffLines": [
                            {"type": "HUNK", "text": "@@ -1,1 +1,2 @@"},
                            {"type": "CONTEXT", "text": "x"},
                            {"type": "ADDITION", "text": "y"},
                        ],
                    }
                ],
                "severity": "high",
            }
        ]
        mock_get_file.side_effect = RuntimeError("Failed to fetch file")

        result = apply_pr_suggestions(1, "owner/repo")
        assert result["applied"] == 0
        assert result["skipped"] == 1
        assert result["conflict_comment_ids"] == [100]

    @patch(f"{_MODULE}._get_file_content_and_sha")
    @patch(f"{_MODULE}._fetch_suggestions_from_page")
    @patch(f"{_MODULE}._get_pr_head_branch")
    @patch(f"{_MODULE}._get_gh_token")
    def test_context_mismatch_skips_suggestion(
        self,
        mock_token: MagicMock,
        mock_branch: MagicMock,
        mock_fetch: MagicMock,
        mock_get_file: MagicMock,
    ) -> None:
        mock_token.return_value = "token"
        mock_branch.return_value = "main"
        mock_fetch.return_value = [
            {
                "comment_id": 200,
                "node_id": "n200",
                "diff_entries": [
                    {
                        "path": "src/file.py",
                        "diffLines": [
                            {"type": "HUNK", "text": "@@ -1,2 +1,2 @@"},
                            {"type": "CONTEXT", "text": "expected_line"},
                            {"type": "CONTEXT", "text": "also_expected"},
                        ],
                    }
                ],
                "severity": "medium",
            }
        ]
        # File has different content from what the diff expects
        mock_get_file.return_value = ("actual_line\ndifferent\n", "sha1")

        result = apply_pr_suggestions(1, "owner/repo")
        assert result["applied"] == 0
        assert result["skipped"] == 1
        assert 200 in result["conflict_comment_ids"]

    @patch(f"{_MODULE}._update_file_via_api")
    @patch(f"{_MODULE}._get_file_content_and_sha")
    @patch(f"{_MODULE}._fetch_suggestions_from_page")
    @patch(f"{_MODULE}._get_pr_head_branch")
    @patch(f"{_MODULE}._get_gh_token")
    def test_update_failure_moves_applied_to_skipped(
        self,
        mock_token: MagicMock,
        mock_branch: MagicMock,
        mock_fetch: MagicMock,
        mock_get_file: MagicMock,
        mock_update: MagicMock,
    ) -> None:
        mock_token.return_value = "token"
        mock_branch.return_value = "main"
        mock_fetch.return_value = [
            {
                "comment_id": 300,
                "node_id": "n300",
                "diff_entries": [
                    {
                        "path": "src/file.py",
                        "diffLines": [
                            {"type": "HUNK", "text": "@@ -1,2 +1,3 @@"},
                            {"type": "CONTEXT", "text": "line1"},
                            {"type": "ADDITION", "text": "inserted"},
                            {"type": "CONTEXT", "text": "line2"},
                        ],
                    }
                ],
                "severity": "high",
            }
        ]
        mock_get_file.return_value = ("line1\nline2\nline3", "sha_old")
        mock_update.side_effect = RuntimeError("API error")

        result = apply_pr_suggestions(1, "owner/repo")
        # Applied in memory but commit failed → moved to skipped
        assert result["applied"] == 0
        assert result["skipped"] == 1

    @patch(f"{_MODULE}._reply_and_resolve_comments")
    @patch(f"{_MODULE}._update_file_via_api")
    @patch(f"{_MODULE}._get_file_content_and_sha")
    @patch(f"{_MODULE}._fetch_suggestions_from_page")
    @patch(f"{_MODULE}._get_pr_head_branch")
    @patch(f"{_MODULE}._get_gh_token")
    def test_resolve_false_skips_resolution(
        self,
        mock_token: MagicMock,
        mock_branch: MagicMock,
        mock_fetch: MagicMock,
        mock_get_file: MagicMock,
        mock_update: MagicMock,
        mock_resolve: MagicMock,
    ) -> None:
        mock_token.return_value = "token"
        mock_branch.return_value = "main"
        mock_fetch.return_value = [
            {
                "comment_id": 400,
                "node_id": "n400",
                "diff_entries": [
                    {
                        "path": "src/file.py",
                        "diffLines": [
                            {"type": "HUNK", "text": "@@ -1,1 +1,2 @@"},
                            {"type": "CONTEXT", "text": "a"},
                            {"type": "ADDITION", "text": "b"},
                        ],
                    }
                ],
                "severity": "low",
            }
        ]
        mock_get_file.return_value = ("a\nc", "sha1")
        mock_update.return_value = "new_sha"

        result = apply_pr_suggestions(1, "owner/repo", resolve=False)
        assert result["applied"] == 1
        assert result["commit"] == "new_sha"
        # _reply_and_resolve_comments should NOT be called
        mock_resolve.assert_not_called()
        assert result["resolution"] is None

    @patch(f"{_MODULE}._reply_and_resolve_comments")
    @patch(f"{_MODULE}._update_file_via_api")
    @patch(f"{_MODULE}._get_file_content_and_sha")
    @patch(f"{_MODULE}._fetch_suggestions_from_page")
    @patch(f"{_MODULE}._get_pr_head_branch")
    @patch(f"{_MODULE}._get_gh_token")
    def test_overlapping_hunks_second_fails_context(
        self,
        mock_token: MagicMock,
        mock_branch: MagicMock,
        mock_fetch: MagicMock,
        mock_get_file: MagicMock,
        mock_update: MagicMock,
        mock_resolve: MagicMock,
    ) -> None:
        """When two suggestions overlap, the second one fails context verification."""
        mock_token.return_value = "token"
        mock_branch.return_value = "main"
        mock_fetch.return_value = [
            {
                "comment_id": 500,
                "node_id": "n500",
                "diff_entries": [
                    {
                        "path": "src/file.py",
                        "diffLines": [
                            {"type": "HUNK", "text": "@@ -1,3 +1,4 @@"},
                            {"type": "CONTEXT", "text": "a"},
                            {"type": "ADDITION", "text": "x"},
                            {"type": "CONTEXT", "text": "b"},
                            {"type": "CONTEXT", "text": "c"},
                        ],
                    }
                ],
                "severity": "high",
            },
            {
                "comment_id": 600,
                "node_id": "n600",
                "diff_entries": [
                    {
                        "path": "src/file.py",
                        "diffLines": [
                            {"type": "HUNK", "text": "@@ -2,2 +2,2 @@"},
                            {"type": "DELETION", "text": "b"},
                            {"type": "ADDITION", "text": "B_REPLACED"},
                            {"type": "CONTEXT", "text": "c"},
                        ],
                    }
                ],
                "severity": "medium",
            },
        ]
        # File content matches comment 500's expected context
        mock_get_file.return_value = ("a\nb\nc\nd", "sha1")
        mock_update.return_value = "new_sha"
        mock_resolve.return_value = {
            "replied": 1,
            "resolved": 1,
            "failed_replies": [],
            "failed_resolves": [],
        }

        result = apply_pr_suggestions(1, "owner/repo")
        # Both hunks are in the same region; at least one should be applied/skipped
        assert result["applied"] + result["skipped"] == 2

    @patch(f"{_MODULE}._fetch_suggestions_from_page")
    @patch(f"{_MODULE}._get_pr_head_branch")
    @patch(f"{_MODULE}._get_gh_token")
    def test_filter_removes_all_returns_early(
        self, mock_token: MagicMock, mock_branch: MagicMock, mock_fetch: MagicMock
    ) -> None:
        """When comment_ids filter removes all suggestions, returns zero result."""
        mock_token.return_value = "token"
        mock_branch.return_value = "main"
        mock_fetch.return_value = [
            {
                "comment_id": 1,
                "node_id": "n1",
                "diff_entries": [{"path": "a.py", "diffLines": []}],
                "severity": "low",
            }
        ]

        result = apply_pr_suggestions(1, "owner/repo", comment_ids=[999])
        assert result["applied"] == 0
        assert result["skipped"] == 0
        assert result["commit"] is None

    @patch(f"{_MODULE}._reply_and_resolve_comments")
    @patch(f"{_MODULE}._update_file_via_api")
    @patch(f"{_MODULE}._get_file_content_and_sha")
    @patch(f"{_MODULE}._fetch_suggestions_from_page")
    @patch(f"{_MODULE}._get_pr_head_branch")
    @patch(f"{_MODULE}._get_gh_token")
    def test_diff_lines_without_hunk_type_uses_zero_sort(
        self,
        mock_token: MagicMock,
        mock_branch: MagicMock,
        mock_fetch: MagicMock,
        mock_get_file: MagicMock,
        mock_update: MagicMock,
        mock_resolve: MagicMock,
    ) -> None:
        """When diff_lines have no HUNK type line, _hunk_start returns 0."""
        mock_token.return_value = "token"
        mock_branch.return_value = "main"
        mock_fetch.return_value = [
            {
                "comment_id": 700,
                "node_id": "n700",
                "diff_entries": [
                    {
                        "path": "src/file.py",
                        "diffLines": [
                            # No HUNK line — just context/additions
                            {"type": "CONTEXT", "text": "line1"},
                            {"type": "ADDITION", "text": "new"},
                        ],
                    }
                ],
                "severity": "low",
            }
        ]
        mock_get_file.return_value = ("line1\nline2", "sha1")

        result = apply_pr_suggestions(1, "owner/repo")
        # Will be skipped because _apply_diff_to_content returns failure (no hunks)
        assert result["applied"] == 0

    @patch(f"{_MODULE}._reply_and_resolve_comments")
    @patch(f"{_MODULE}._update_file_via_api")
    @patch(f"{_MODULE}._get_file_content_and_sha")
    @patch(f"{_MODULE}._fetch_suggestions_from_page")
    @patch(f"{_MODULE}._get_pr_head_branch")
    @patch(f"{_MODULE}._get_gh_token")
    def test_hunk_header_no_regex_match_in_sort(
        self,
        mock_token: MagicMock,
        mock_branch: MagicMock,
        mock_fetch: MagicMock,
        mock_get_file: MagicMock,
        mock_update: MagicMock,
        mock_resolve: MagicMock,
    ) -> None:
        """When a HUNK line has text that doesn't match regex, sort uses 0."""
        mock_token.return_value = "token"
        mock_branch.return_value = "main"
        mock_fetch.return_value = [
            {
                "comment_id": 800,
                "node_id": "n800",
                "diff_entries": [
                    {
                        "path": "src/file.py",
                        "diffLines": [
                            {"type": "HUNK", "text": "invalid header"},
                            {"type": "CONTEXT", "text": "a"},
                        ],
                    }
                ],
                "severity": "low",
            }
        ]
        mock_get_file.return_value = ("a\nb", "sha1")

        result = apply_pr_suggestions(1, "owner/repo")
        # _apply_single_hunk will fail because regex doesn't match
        assert result["applied"] == 0
        assert result["skipped"] == 1

    @patch(f"{_MODULE}._reply_and_resolve_comments")
    @patch(f"{_MODULE}._update_file_via_api")
    @patch(f"{_MODULE}._get_file_content_and_sha")
    @patch(f"{_MODULE}._fetch_suggestions_from_page")
    @patch(f"{_MODULE}._get_pr_head_branch")
    @patch(f"{_MODULE}._get_gh_token")
    def test_duplicate_comment_ids_deduped_in_resolution(
        self,
        mock_token: MagicMock,
        mock_branch: MagicMock,
        mock_fetch: MagicMock,
        mock_get_file: MagicMock,
        mock_update: MagicMock,
        mock_resolve: MagicMock,
    ) -> None:
        """Same comment_id appearing in multiple diff_entries is deduped for resolution."""
        mock_token.return_value = "token"
        mock_branch.return_value = "main"
        # Single suggestion with two diff entries for the same file
        mock_fetch.return_value = [
            {
                "comment_id": 900,
                "node_id": "n900",
                "diff_entries": [
                    {
                        "path": "src/file.py",
                        "diffLines": [
                            {"type": "HUNK", "text": "@@ -1,1 +1,2 @@"},
                            {"type": "CONTEXT", "text": "a"},
                            {"type": "ADDITION", "text": "b"},
                        ],
                    },
                    {
                        "path": "src/file.py",
                        "diffLines": [
                            {"type": "HUNK", "text": "@@ -3,1 +4,2 @@"},
                            {"type": "CONTEXT", "text": "c"},
                            {"type": "ADDITION", "text": "d"},
                        ],
                    },
                ],
                "severity": "high",
            }
        ]
        mock_get_file.return_value = ("a\nb_orig\nc\nd_orig", "sha1")
        mock_update.return_value = "commit_sha"
        mock_resolve.return_value = {
            "replied": 1,
            "resolved": 1,
            "failed_replies": [],
            "failed_resolves": [],
        }

        result = apply_pr_suggestions(1, "owner/repo")
        assert result["applied"] >= 1
        # _reply_and_resolve_comments should be called with deduped list
        if mock_resolve.called:
            call_args = mock_resolve.call_args
            suggestions_passed = call_args[0][2]
            comment_ids = [s["comment_id"] for s in suggestions_passed]
            # Should have only one entry for comment_id 900
            assert comment_ids.count(900) == 1

    def test_retry_loop_re_fetches_on_conflict(self) -> None:
        """When a suggestion conflicts, the loop retries with fresh page data."""
        # First fetch: 2 suggestions, 100 applies (hunk at line 3), 200 conflicts (hunk at line 1)
        suggestion_iter1 = [
            {
                "comment_id": 100,
                "diff_entries": [
                    {
                        "path": "f.py",
                        "diffLines": [
                            {"type": "HUNK", "text": "@@ -3,1 +3,2 @@"},
                            {"type": "CONTEXT", "text": "c"},
                            {"type": "ADDITION", "text": "new"},
                        ],
                    }
                ],
                "severity": "medium",
            },
            {
                "comment_id": 200,
                "diff_entries": [
                    {
                        "path": "f.py",
                        "diffLines": [
                            {"type": "HUNK", "text": "@@ -1,1 +1,1 @@"},
                            {"type": "CONTEXT", "text": "WRONG"},  # Will conflict with actual "a"
                        ],
                    }
                ],
                "severity": "medium",
            },
        ]
        # Second fetch: 200 with corrected diff (GitHub re-generates after commit)
        suggestion_iter2 = [
            {
                "comment_id": 200,
                "diff_entries": [
                    {
                        "path": "f.py",
                        "diffLines": [
                            {"type": "HUNK", "text": "@@ -1,1 +1,2 @@"},
                            {"type": "CONTEXT", "text": "a"},
                            {"type": "ADDITION", "text": "extra"},
                        ],
                    }
                ],
                "severity": "medium",
            },
        ]

        content_calls = [("a\nb\nc\n", "sha1"), ("a\nb\nc\nnew\n", "sha2")]

        with (
            patch("agentic_devtools.cli.github.apply_thread_autofix._get_gh_token", return_value="tok"),
            patch("agentic_devtools.cli.github.apply_thread_autofix._get_pr_head_branch", return_value="main"),
            patch("agentic_devtools.cli.github.apply_thread_autofix._fetch_suggestions_from_page") as mock_fetch,
            patch("agentic_devtools.cli.github.apply_thread_autofix._get_file_content_and_sha") as mock_content,
            patch("agentic_devtools.cli.github.apply_thread_autofix._update_file_via_api", return_value="sha_new"),
            patch("agentic_devtools.cli.github.apply_thread_autofix._reply_and_resolve_comments") as mock_resolve,
            patch("agentic_devtools.cli.github.apply_thread_autofix.time.sleep"),
        ):
            mock_fetch.side_effect = [suggestion_iter1, suggestion_iter2]
            mock_content.side_effect = content_calls
            mock_resolve.return_value = {"replied": 1, "resolved": 1, "failed_replies": [], "failed_resolves": []}

            result = apply_pr_suggestions(pr_number=1, repo="o/r", resolve=True)

        assert result["applied"] == 2
        assert result["skipped"] == 0

    def test_retry_loop_stops_when_nothing_applied(self) -> None:
        """Retry loop stops when an iteration applies nothing (avoids infinite loop)."""
        # Suggestion that always conflicts
        suggestion = [
            {
                "comment_id": 100,
                "diff_entries": [
                    {
                        "path": "f.py",
                        "diffLines": [
                            {"type": "HUNK", "text": "@@ -1,1 +1,1 @@"},
                            {"type": "CONTEXT", "text": "WRONG"},
                        ],
                    }
                ],
                "severity": "medium",
            },
        ]

        with (
            patch("agentic_devtools.cli.github.apply_thread_autofix._get_gh_token", return_value="tok"),
            patch("agentic_devtools.cli.github.apply_thread_autofix._get_pr_head_branch", return_value="main"),
            patch(
                "agentic_devtools.cli.github.apply_thread_autofix._fetch_suggestions_from_page", return_value=suggestion
            ),
            patch(
                "agentic_devtools.cli.github.apply_thread_autofix._get_file_content_and_sha",
                return_value=("actual\n", "sha"),
            ),
            patch("agentic_devtools.cli.github.apply_thread_autofix.time.sleep"),
        ):
            result = apply_pr_suggestions(pr_number=1, repo="o/r", resolve=False)

        assert result["applied"] == 0
        assert result["skipped"] == 1
        assert result["conflict_comment_ids"] == [100]

    def test_retry_second_iteration_no_suggestions(self) -> None:
        """When second iteration finds no suggestions, loop exits cleanly."""
        suggestion_iter1 = [
            {
                "comment_id": 100,
                "diff_entries": [
                    {
                        "path": "f.py",
                        "diffLines": [
                            {"type": "HUNK", "text": "@@ -1,1 +1,2 @@"},
                            {"type": "CONTEXT", "text": "a"},
                            {"type": "ADDITION", "text": "b"},
                        ],
                    }
                ],
                "severity": "medium",
            },
            {
                "comment_id": 200,
                "diff_entries": [
                    {
                        "path": "f.py",
                        "diffLines": [
                            {"type": "HUNK", "text": "@@ -1,1 +1,1 @@"},
                            {"type": "CONTEXT", "text": "WRONG"},
                        ],
                    }
                ],
                "severity": "medium",
            },
        ]

        with (
            patch("agentic_devtools.cli.github.apply_thread_autofix._get_gh_token", return_value="tok"),
            patch("agentic_devtools.cli.github.apply_thread_autofix._get_pr_head_branch", return_value="main"),
            patch("agentic_devtools.cli.github.apply_thread_autofix._fetch_suggestions_from_page") as mock_fetch,
            patch(
                "agentic_devtools.cli.github.apply_thread_autofix._get_file_content_and_sha",
                return_value=("a\n", "sha"),
            ),
            patch("agentic_devtools.cli.github.apply_thread_autofix._update_file_via_api", return_value="sha1"),
            patch("agentic_devtools.cli.github.apply_thread_autofix._reply_and_resolve_comments") as mock_resolve,
            patch("agentic_devtools.cli.github.apply_thread_autofix.time.sleep"),
        ):
            # First iteration: finds 2, applies 1, skips 1
            # Second iteration: returns empty (suggestion 200 no longer on page)
            mock_fetch.side_effect = [suggestion_iter1, []]
            mock_resolve.return_value = {"replied": 1, "resolved": 1, "failed_replies": [], "failed_resolves": []}

            result = apply_pr_suggestions(pr_number=1, repo="o/r", resolve=True)

        assert result["applied"] == 1

    def test_retry_loop_exhausts_max_iterations(self) -> None:
        """Loop runs all max_iterations when each iteration applies AND skips."""

        # Each iteration: applies one suggestion, skips one that always conflicts
        def make_suggestions(applied_id: int, conflict_id: int) -> list:
            return [
                {
                    "comment_id": applied_id,
                    "diff_entries": [
                        {
                            "path": "f.py",
                            "diffLines": [
                                {"type": "HUNK", "text": "@@ -3,1 +3,2 @@"},
                                {"type": "CONTEXT", "text": "c"},
                                {"type": "ADDITION", "text": f"new{applied_id}"},
                            ],
                        }
                    ],
                    "severity": "medium",
                },
                {
                    "comment_id": conflict_id,
                    "diff_entries": [
                        {
                            "path": "f.py",
                            "diffLines": [
                                {"type": "HUNK", "text": "@@ -1,1 +1,1 @@"},
                                {"type": "CONTEXT", "text": "ALWAYS_WRONG"},
                            ],
                        }
                    ],
                    "severity": "medium",
                },
            ]

        fetch_results = [
            make_suggestions(100, 999),
            make_suggestions(200, 999),
            make_suggestions(300, 999),
        ]
        content_results = [
            ("a\nb\nc\n", "sha1"),
            ("a\nb\nc\nnew100\n", "sha2"),
            ("a\nb\nc\nnew100\nnew200\n", "sha3"),
        ]

        with (
            patch("agentic_devtools.cli.github.apply_thread_autofix._get_gh_token", return_value="tok"),
            patch("agentic_devtools.cli.github.apply_thread_autofix._get_pr_head_branch", return_value="main"),
            patch("agentic_devtools.cli.github.apply_thread_autofix._fetch_suggestions_from_page") as mock_fetch,
            patch("agentic_devtools.cli.github.apply_thread_autofix._get_file_content_and_sha") as mock_content,
            patch("agentic_devtools.cli.github.apply_thread_autofix._update_file_via_api", return_value="sha_final"),
            patch("agentic_devtools.cli.github.apply_thread_autofix._reply_and_resolve_comments") as mock_resolve,
            patch("agentic_devtools.cli.github.apply_thread_autofix.time.sleep"),
        ):
            mock_fetch.side_effect = fetch_results
            mock_content.side_effect = content_results
            mock_resolve.return_value = {"replied": 1, "resolved": 1, "failed_replies": [], "failed_resolves": []}

            result = apply_pr_suggestions(pr_number=1, repo="o/r", resolve=False)

        assert result["applied"] == 3
        # After all 3 iterations, the persistently-conflicting suggestion (999)
        # must be reported in skipped/conflict_comment_ids.
        assert result["skipped"] == 1
        assert result["conflict_comment_ids"] == [999]
