"""Tests for GitHubThreadAdapter."""

from agentic_devtools.cli.ci.resolution.github_adapter import GitHubThreadAdapter

_SAMPLE_NODE = {
    "id": "PRT_abc123",
    "isResolved": False,
    "isOutdated": True,
    "path": "src/main.py",
    "line": 15,
    "startLine": 10,
    "comments": {
        "nodes": [
            {
                "databaseId": 101,
                "body": "Fix this typo",
                "createdAt": "2026-01-01T00:00:00Z",
                "author": {"login": "reviewer1"},
                "commit": {"oid": "abc123def"},
            },
            {
                "databaseId": 102,
                "body": "autofix applied",
                "createdAt": "2026-01-02T00:00:00Z",
                "author": {"login": "bot"},
                "commit": {"oid": "def456ghi"},
            },
        ]
    },
}


class TestGitHubThreadAdapter:
    """Tests for the GitHub adapter."""

    def test_adapt_thread(self) -> None:
        adapter = GitHubThreadAdapter()
        thread = adapter.adapt_thread(_SAMPLE_NODE)
        assert thread.thread_id == "PRT_abc123"
        assert thread.file_path == "src/main.py"
        assert thread.start_line == 10
        assert thread.end_line == 15
        assert thread.is_outdated is True
        assert len(thread.comments) == 2
        assert thread.originating_review_commit_oid == "abc123def"

    def test_adapt_thread_comments(self) -> None:
        adapter = GitHubThreadAdapter()
        thread = adapter.adapt_thread(_SAMPLE_NODE)
        assert thread.comments[0].body == "Fix this typo"
        assert thread.comments[0].author_login == "reviewer1"
        assert thread.comments[0].database_id == 101
        assert thread.comments[1].body == "autofix applied"

    def test_adapt_thread_null_outdated(self) -> None:
        """isOutdated: null is mapped to None."""
        node = {**_SAMPLE_NODE, "isOutdated": None}
        adapter = GitHubThreadAdapter()
        thread = adapter.adapt_thread(node)
        assert thread.is_outdated is None

    def test_adapt_thread_missing_fields(self) -> None:
        """Handles missing optional fields gracefully."""
        node = {
            "id": "PRT_minimal",
            "isResolved": False,
            "comments": {"nodes": [{"databaseId": 100}]},
        }
        adapter = GitHubThreadAdapter()
        thread = adapter.adapt_thread(node)
        assert thread.thread_id == "PRT_minimal"
        assert thread.file_path is None
        assert thread.start_line is None
        assert thread.end_line is None
        assert thread.is_outdated is None
        assert thread.comments[0].body == ""

    def test_adapt_threads_batch(self) -> None:
        adapter = GitHubThreadAdapter()
        nodes = [_SAMPLE_NODE, {**_SAMPLE_NODE, "id": "PRT_second"}]
        threads = adapter.adapt_threads(nodes)
        assert len(threads) == 2
        assert threads[1].thread_id == "PRT_second"

    def test_adapt_thread_no_author(self) -> None:
        """Handles comment with null author."""
        node = {
            "id": "PRT_noauthor",
            "isResolved": False,
            "comments": {
                "nodes": [
                    {
                        "databaseId": 200,
                        "body": "test",
                        "createdAt": "2026-01-01T00:00:00Z",
                        "author": None,
                        "commit": {"oid": "xyz789"},
                    }
                ]
            },
        }
        adapter = GitHubThreadAdapter()
        thread = adapter.adapt_thread(node)
        assert thread.comments[0].author_login is None
