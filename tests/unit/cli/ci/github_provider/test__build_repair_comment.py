"""Tests for _build_repair_comment() in the GitHub provider."""

from agentic_devtools.cli.ci.github_provider import _build_repair_comment
from agentic_devtools.cli.ci.models import CheckRunStatus


class TestBuildRepairComment:
    """Tests for repair comment body construction."""

    def test_comment_begins_with_at_copilot(self) -> None:
        """Comment MUST begin with @copilot for reliable agent triggering."""
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=["Fix this"],
        )
        assert body.startswith("@copilot")

    def test_review_repair_includes_comments(self) -> None:
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=["Fix the null check", "Add error handling"],
        )
        assert "@copilot" in body
        assert "## Copilot Review Feedback" in body
        assert "### Comment 1" in body
        assert "### Comment 2" in body
        assert "> Fix the null check" in body
        assert "> Add error handling" in body

    def test_ci_repair_includes_failed_checks(self) -> None:
        checks = [
            CheckRunStatus(id=1, name="Python Tests", status="completed", conclusion="failure"),
            CheckRunStatus(id=2, name="Lint", status="completed", conclusion="failure"),
        ]
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="ci",
            failed_checks=checks,
            review_comments=[],
        )
        assert "@copilot" in body
        assert "## CI Failure Context" in body
        assert "### ❌ Python Tests" in body
        assert "### ❌ Lint" in body

    def test_ci_repair_includes_job_links_when_repo_is_known(self) -> None:
        checks = [CheckRunStatus(id=111, name="Python Tests", status="completed", conclusion="failure")]
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="ci",
            failed_checks=checks,
            review_comments=[],
            repository_full_name="owner/repo",
        )
        assert "https://github.com/owner/repo/runs/111" in body

    def test_both_repair_includes_review_and_ci(self) -> None:
        checks = [CheckRunStatus(id=1, name="test", status="completed", conclusion="failure")]
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="both",
            failed_checks=checks,
            review_comments=["Fix naming"],
        )
        assert "## Copilot Review Feedback" in body
        assert "## CI Failure Context" in body

    def test_empty_context_includes_fallback(self) -> None:
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=[],
        )
        assert body.startswith("@copilot")
        assert "abc123de" in body  # short SHA

    def test_footer_includes_metadata(self) -> None:
        body = _build_repair_comment(
            head_sha="abc123def456789",
            repair_type="ci",
            failed_checks=[],
            review_comments=[],
        )
        assert "abc123de" in body
        assert "type: ci" in body

    def test_multiline_review_comment_quoted(self) -> None:
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=["Line 1\nLine 2\nLine 3"],
        )
        assert "> Line 1" in body
        assert "> Line 2" in body
        assert "> Line 3" in body
