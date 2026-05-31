"""Tests for repair_subsequent_header utility."""

from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewState,
)
from agentic_devtools.cli.azure_devops.review_templates import repair_subsequent_header


def _make_review_state(commit_hash=None) -> ReviewState:
    """Build minimal ReviewState with optional commitHash."""
    return ReviewState(
        prId=42,
        repoId="repo-guid",
        repoName="repo",
        project="proj",
        organization="https://dev.azure.com/org",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00Z",
        overallSummary=OverallSummary(threadId=1, commentId=2),
        folders={"src": FolderGroup(files=["/src/a.py"])},
        files={"/src/a.py": FileEntry(threadId=10, commentId=20, folder="src", fileName="a.py", status="approved")},
        commitHash=commit_hash,
    )


class TestRepairSubsequentHeader:
    """Tests for repair_subsequent_header."""

    def test_repairs_file_summary_with_commit_hash(self):
        """Repairs ## File Review Summary: header using ReviewState commitHash."""
        state = _make_review_state(commit_hash="abc1234def5678901234")
        content = "## File Review Summary: app.py\n\n*Status:* ✅ Approved"
        result = repair_subsequent_header(content, state)
        assert result.startswith("### Commit: abc1234")
        assert "*Status:* ✅ Approved" in result

    def test_repairs_overall_summary_with_commit_hash(self):
        """Repairs ## Overall PR Review Summary header using ReviewState commitHash."""
        state = _make_review_state(commit_hash="deadbeef1234567890ab")
        content = "## Overall PR Review Summary\n\n*Status:* ⏳ Unreviewed"
        result = repair_subsequent_header(content, state)
        assert result.startswith("### Commit: deadbee")
        assert "*Status:* ⏳ Unreviewed" in result

    def test_falls_back_to_unknown_when_no_commit_hash(self):
        """Falls back to ### Commit: unknown when commitHash is None."""
        state = _make_review_state(commit_hash=None)
        content = "## File Review Summary: test.py\n\nbody"
        result = repair_subsequent_header(content, state)
        assert result.startswith("### Commit: unknown")
        assert "body" in result

    def test_falls_back_to_unknown_when_empty_commit_hash(self):
        """Falls back to ### Commit: unknown when commitHash is empty string."""
        state = _make_review_state(commit_hash="")
        content = "## Overall PR Review Summary\n\nbody"
        result = repair_subsequent_header(content, state)
        assert result.startswith("### Commit: unknown")

    def test_returns_unchanged_when_no_summary_heading(self):
        """Returns content unchanged when first line is not a summary heading."""
        state = _make_review_state(commit_hash="abc1234")
        content = "### Already correct header\n\nbody"
        result = repair_subsequent_header(content, state)
        assert result == content

    def test_returns_empty_unchanged(self):
        """Returns empty string unchanged."""
        state = _make_review_state(commit_hash="abc1234")
        assert repair_subsequent_header("", state) == ""

    def test_preserves_body_content(self):
        """Body content after the header is preserved unchanged."""
        state = _make_review_state(commit_hash="1234567890abcdef")
        body = "\n*Status:* 📝 Needs Work\n\n### Summary of Changes\nFoo"
        content = "## File Review Summary: x.py" + body
        result = repair_subsequent_header(content, state)
        assert result == "### Commit: 1234567" + body
