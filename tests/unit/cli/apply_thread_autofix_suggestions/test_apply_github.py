"""Tests for _apply_github."""

from unittest.mock import patch

from agentic_devtools.cli.apply_thread_autofix_suggestions import _apply_github


class TestApplyGithub:
    """Tests for GitHub dispatch."""

    def test_calls_apply_pr_suggestions(self) -> None:
        with (
            patch("agentic_devtools.cli.github.apply_thread_autofix.apply_pr_suggestions") as mock_apply,
            patch("agentic_devtools.cli.github.repo_resolution.resolve_github_repo") as mock_resolve,
        ):
            mock_resolve.return_value = "owner/repo"
            mock_apply.return_value = {"applied": 1, "commit": "abc123"}
            result = _apply_github(
                pr_number=1,
                repo="owner/repo",
                comment_ids=None,
                message="test",
                resolve=True,
            )
        assert result["applied"] == 1
