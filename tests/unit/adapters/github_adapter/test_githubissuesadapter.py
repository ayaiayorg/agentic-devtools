"""Tests for agentic_devtools.adapters.github_adapter.GitHubIssuesAdapter."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock

import pytest

from agentic_devtools.adapters.github_adapter import GitHubIssuesAdapter


def _mock_run(stdout: str = "", stderr: str = "", returncode: int = 0) -> MagicMock:
    """Build a mock run_command callable returning a CompletedProcess."""
    mock = MagicMock()
    mock.return_value = subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)
    return mock


class TestGitHubIssuesAdapter:
    """Tests for the GitHubIssuesAdapter concrete implementation."""

    def test_create_issue_parses_url(self) -> None:
        """create_issue extracts issue ID from the URL returned by gh."""
        run = _mock_run(stdout="https://github.com/owner/repo/issues/42\n")
        adapter = GitHubIssuesAdapter(repo="owner/repo", run_command=run)

        result = adapter.create_issue("My title", "My body")

        assert result["issue_id"] == "42"
        assert result["url"] == "https://github.com/owner/repo/issues/42"
        args = run.call_args[0][0]
        assert args[:4] == ["gh", "issue", "create", "--repo"]

    def test_create_issue_with_labels(self) -> None:
        """create_issue adds --label flags for each label."""
        run = _mock_run(stdout="https://github.com/owner/repo/issues/1\n")
        adapter = GitHubIssuesAdapter(repo="owner/repo", run_command=run)

        adapter.create_issue("Title", "Body", labels=["bug", "urgent"])

        args = run.call_args[0][0]
        assert "--label" in args
        label_indices = [i for i, a in enumerate(args) if a == "--label"]
        label_values = [args[i + 1] for i in label_indices]
        assert label_values == ["bug", "urgent"]

    def test_create_issue_without_labels(self) -> None:
        """create_issue omits --label when labels is None."""
        run = _mock_run(stdout="https://github.com/owner/repo/issues/1\n")
        adapter = GitHubIssuesAdapter(repo="owner/repo", run_command=run)

        adapter.create_issue("Title", "Body")

        args = run.call_args[0][0]
        assert "--label" not in args

    def test_get_issue_parses_json(self) -> None:
        """get_issue parses gh JSON output into IssueDetail."""
        data = {
            "number": 42,
            "title": "Test issue",
            "body": "Description",
            "state": "OPEN",
            "labels": [{"name": "bug"}],
            "url": "https://github.com/owner/repo/issues/42",
            "comments": [
                {"id": "c1", "body": "A comment", "createdAt": "2026-01-01T00:00:00Z"},
            ],
        }
        run = _mock_run(stdout=json.dumps(data))
        adapter = GitHubIssuesAdapter(repo="owner/repo", run_command=run)

        detail = adapter.get_issue("42")

        assert detail["issue_id"] == "42"
        assert detail["title"] == "Test issue"
        assert detail["description"] == "Description"
        assert detail["status"] == "OPEN"
        assert detail["labels"] == ["bug"]
        assert len(detail["comments"]) == 1
        assert detail["comments"][0]["body"] == "A comment"

    def test_get_issue_handles_string_labels(self) -> None:
        """get_issue handles labels as plain strings (not dicts)."""
        data = {
            "number": 1,
            "title": "T",
            "body": "",
            "state": "OPEN",
            "labels": ["bug"],
            "url": "",
            "comments": [],
        }
        run = _mock_run(stdout=json.dumps(data))
        adapter = GitHubIssuesAdapter(repo="owner/repo", run_command=run)

        detail = adapter.get_issue("1")
        assert detail["labels"] == ["bug"]

    def test_add_comment_returns_empty_id(self) -> None:
        """add_comment returns empty comment_id since gh doesn't provide one."""
        run = _mock_run(stdout="")
        adapter = GitHubIssuesAdapter(repo="owner/repo", run_command=run)

        result = adapter.add_comment("42", "Hello")

        assert result["comment_id"] == ""
        args = run.call_args[0][0]
        assert "comment" in args
        assert "--body" in args

    def test_list_issues_no_filters(self) -> None:
        """list_issues returns summaries without filters."""
        data = [
            {"number": 1, "title": "A", "state": "OPEN", "labels": [{"name": "bug"}], "url": "u1"},
            {"number": 2, "title": "B", "state": "CLOSED", "labels": [], "url": "u2"},
        ]
        run = _mock_run(stdout=json.dumps(data))
        adapter = GitHubIssuesAdapter(repo="owner/repo", run_command=run)

        summaries = adapter.list_issues()

        assert len(summaries) == 2
        assert summaries[0]["issue_id"] == "1"
        assert summaries[1]["title"] == "B"

    def test_list_issues_with_labels_filter(self) -> None:
        """list_issues passes --label flags from filters."""
        run = _mock_run(stdout="[]")
        adapter = GitHubIssuesAdapter(repo="owner/repo", run_command=run)

        adapter.list_issues(filters={"labels": ["bug", "feature"]})

        args = run.call_args[0][0]
        label_indices = [i for i, a in enumerate(args) if a == "--label"]
        label_values = [args[i + 1] for i in label_indices]
        assert label_values == ["bug", "feature"]

    def test_list_issues_with_state_filter(self) -> None:
        """list_issues passes --state flag from filters."""
        run = _mock_run(stdout="[]")
        adapter = GitHubIssuesAdapter(repo="owner/repo", run_command=run)

        adapter.list_issues(filters={"state": "open"})

        args = run.call_args[0][0]
        state_idx = args.index("--state")
        assert args[state_idx + 1] == "open"

    def test_list_issues_with_assignee_filter(self) -> None:
        """list_issues passes --assignee flag from filters."""
        run = _mock_run(stdout="[]")
        adapter = GitHubIssuesAdapter(repo="owner/repo", run_command=run)

        adapter.list_issues(filters={"assignee": "octocat"})

        args = run.call_args[0][0]
        idx = args.index("--assignee")
        assert args[idx + 1] == "octocat"

    def test_subprocess_failure_raises_runtime_error(self) -> None:
        """Non-zero returncode raises RuntimeError."""
        run = _mock_run(returncode=1, stderr="not authenticated")
        adapter = GitHubIssuesAdapter(repo="owner/repo", run_command=run)

        with pytest.raises(RuntimeError, match="gh command failed"):
            adapter.create_issue("T", "D")

    def test_json_parse_failure_raises_runtime_error(self) -> None:
        """Invalid JSON from gh raises RuntimeError."""
        run = _mock_run(stdout="not json")
        adapter = GitHubIssuesAdapter(repo="owner/repo", run_command=run)

        with pytest.raises(RuntimeError, match="Failed to parse gh output"):
            adapter.get_issue("1")

    def test_get_issue_non_dict_json_raises_runtime_error(self) -> None:
        """get_issue raises when gh returns a JSON list instead of dict."""
        run = _mock_run(stdout="[1,2,3]")
        adapter = GitHubIssuesAdapter(repo="owner/repo", run_command=run)

        with pytest.raises(RuntimeError, match="expected dict"):
            adapter.get_issue("1")

    def test_list_issues_non_list_json_raises_runtime_error(self) -> None:
        """list_issues raises when gh returns a JSON dict instead of list."""
        run = _mock_run(stdout='{"not": "list"}')
        adapter = GitHubIssuesAdapter(repo="owner/repo", run_command=run)

        with pytest.raises(RuntimeError, match="expected list"):
            adapter.list_issues()

    def test_list_issues_non_dict_item_raises_runtime_error(self) -> None:
        """list_issues raises when an item in the list is not a dict."""
        run = _mock_run(stdout='[{"number": 1, "title": "A", "state": "OPEN", "labels": [], "url": "u"}, "bad"]')
        adapter = GitHubIssuesAdapter(repo="owner/repo", run_command=run)

        with pytest.raises(RuntimeError, match="expected each issue to be a dict.*index 1"):
            adapter.list_issues()

    def test_create_issue_empty_url(self) -> None:
        """create_issue handles empty stdout gracefully."""
        run = _mock_run(stdout="")
        adapter = GitHubIssuesAdapter(repo="owner/repo", run_command=run)

        result = adapter.create_issue("T", "D")
        assert result["issue_id"] == ""
        assert result["url"] == ""

    def test_shell_false_always_passed(self) -> None:
        """Verify shell=False is always passed to run_command."""
        run = _mock_run(stdout="https://github.com/o/r/issues/1\n")
        adapter = GitHubIssuesAdapter(repo="o/r", run_command=run)

        adapter.create_issue("T", "D")
        assert run.call_args[1]["shell"] is False

    def test_get_issue_null_labels_and_comments(self) -> None:
        """get_issue handles null labels and comments gracefully."""
        data = {
            "number": 1,
            "title": "T",
            "body": "D",
            "state": "OPEN",
            "labels": None,
            "url": "u",
            "comments": None,
        }
        run = _mock_run(stdout=json.dumps(data))
        adapter = GitHubIssuesAdapter(repo="o/r", run_command=run)

        detail = adapter.get_issue("1")
        assert detail["labels"] == []
        assert detail["comments"] == []

    def test_get_issue_non_list_comments_raises(self) -> None:
        """get_issue raises RuntimeError when comments is not a list."""
        data = {
            "number": 1,
            "title": "T",
            "body": "D",
            "state": "OPEN",
            "labels": [],
            "url": "u",
            "comments": "not-a-list",
        }
        run = _mock_run(stdout=json.dumps(data))
        adapter = GitHubIssuesAdapter(repo="o/r", run_command=run)

        with pytest.raises(RuntimeError, match="expected comments to be a list"):
            adapter.get_issue("1")

    def test_get_issue_non_dict_comment_entry_raises(self) -> None:
        """get_issue raises RuntimeError when a comment entry is not a dict."""
        data = {
            "number": 1,
            "title": "T",
            "body": "D",
            "state": "OPEN",
            "labels": [],
            "url": "u",
            "comments": [{"id": "c1", "body": "ok", "createdAt": ""}, "bad"],
        }
        run = _mock_run(stdout=json.dumps(data))
        adapter = GitHubIssuesAdapter(repo="o/r", run_command=run)

        with pytest.raises(RuntimeError, match="expected each comment to be a dict.*index 1"):
            adapter.get_issue("1")

    def test_get_issue_non_list_labels_normalised_to_empty(self) -> None:
        """get_issue normalises non-list labels to empty list."""
        data = {
            "number": 1,
            "title": "T",
            "body": "D",
            "state": "OPEN",
            "labels": "not-a-list",
            "url": "u",
            "comments": [],
        }
        run = _mock_run(stdout=json.dumps(data))
        adapter = GitHubIssuesAdapter(repo="o/r", run_command=run)

        detail = adapter.get_issue("1")
        assert detail["labels"] == []

    def test_list_issues_non_list_labels_normalised_to_empty(self) -> None:
        """list_issues normalises non-list labels within items to empty list."""
        data = [
            {"number": 1, "title": "A", "state": "OPEN", "labels": {"unexpected": True}, "url": "u"},
        ]
        run = _mock_run(stdout=json.dumps(data))
        adapter = GitHubIssuesAdapter(repo="o/r", run_command=run)

        summaries = adapter.list_issues()
        assert summaries[0]["labels"] == []

    def test_repo_args_non_empty(self) -> None:
        """_repo_args returns ['--repo', slug] when repo is set."""
        adapter = GitHubIssuesAdapter(repo="owner/repo", run_command=_mock_run())
        assert adapter._repo_args() == ["--repo", "owner/repo"]

    def test_repo_args_empty(self) -> None:
        """_repo_args returns [] when repo is empty."""
        adapter = GitHubIssuesAdapter(repo="", run_command=_mock_run())
        assert adapter._repo_args() == []

    def test_create_issue_omits_repo_flag_when_empty(self) -> None:
        """create_issue omits --repo when repo slug is empty."""
        run = _mock_run(stdout="https://github.com/owner/repo/issues/1\n")
        adapter = GitHubIssuesAdapter(repo="", run_command=run)

        adapter.create_issue("T", "D")

        args = run.call_args[0][0]
        assert "--repo" not in args
        assert args[:3] == ["gh", "issue", "create"]

    def test_get_issue_omits_repo_flag_when_empty(self) -> None:
        """get_issue omits --repo when repo slug is empty."""
        data = {"number": 1, "title": "T", "body": "", "state": "OPEN", "labels": [], "url": "", "comments": []}
        run = _mock_run(stdout=json.dumps(data))
        adapter = GitHubIssuesAdapter(repo="", run_command=run)

        adapter.get_issue("1")

        args = run.call_args[0][0]
        assert "--repo" not in args

    def test_add_comment_omits_repo_flag_when_empty(self) -> None:
        """add_comment omits --repo when repo slug is empty."""
        run = _mock_run(stdout="")
        adapter = GitHubIssuesAdapter(repo="", run_command=run)

        adapter.add_comment("1", "Hello")

        args = run.call_args[0][0]
        assert "--repo" not in args

    def test_list_issues_omits_repo_flag_when_empty(self) -> None:
        """list_issues omits --repo when repo slug is empty."""
        run = _mock_run(stdout="[]")
        adapter = GitHubIssuesAdapter(repo="", run_command=run)

        adapter.list_issues()

        args = run.call_args[0][0]
        assert "--repo" not in args
