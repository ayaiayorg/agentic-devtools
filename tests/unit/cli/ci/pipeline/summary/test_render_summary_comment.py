"""Tests for render_summary_comment."""

from agentic_devtools.cli.ci.pipeline.models import (
    ActionDecision,
    ActionResult,
    PipelineRunSummary,
)
from agentic_devtools.cli.ci.pipeline.snapshot import PRStateSnapshot
from agentic_devtools.cli.ci.pipeline.summary import (
    SUMMARY_SENTINEL,
    render_summary_comment,
)


class TestRenderSummaryComment:
    """Tests for the summary comment renderer."""

    def test_contains_sentinel(self) -> None:
        summary = PipelineRunSummary()
        comment = render_summary_comment(summary)
        assert SUMMARY_SENTINEL in comment

    def test_contains_run_url(self) -> None:
        summary = PipelineRunSummary(run_url="https://github.com/org/repo/actions/runs/12345")
        comment = render_summary_comment(summary)
        assert "View Logs" in comment
        assert "12345" in comment

    def test_contains_action_table(self) -> None:
        results = [
            ActionResult(name="guards", decision=ActionDecision.EXECUTE, details="All guards passed"),
            ActionResult(name="publish", decision=ActionDecision.SKIP, details="Not a draft"),
            ActionResult(name="merge", decision=ActionDecision.EXECUTE, details="PR merged"),
        ]
        summary = PipelineRunSummary(results=results)
        comment = render_summary_comment(summary)
        assert "guards" in comment
        assert "publish" in comment
        assert "merge" in comment
        assert "skipped" in comment
        assert "Not a draft" in comment
        assert "**executed**" in comment

    def test_contains_state_snapshot(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=42,
            head_sha="abc1234567890",
            commit_count=2,
            ci_status="passing",
            active_session=False,
            unresolved_threads=0,
        )
        summary = PipelineRunSummary(snapshot=snapshot)
        comment = render_summary_comment(summary)
        assert "abc1234" in comment
        assert "Commits above merge-base: 2" in comment
        assert "CI: passing" in comment

    def test_guard_blocked_rendering(self) -> None:
        results = [
            ActionResult(name="guards", decision=ActionDecision.BLOCKED, details="PR is from a fork"),
            ActionResult(name="publish", decision=ActionDecision.BLOCKED_BY_GUARD, details="Blocked by guards"),
        ]
        summary = PipelineRunSummary(results=results)
        comment = render_summary_comment(summary)
        assert "blocked" in comment
        assert "🚫" in comment

    def test_failed_rendering_includes_failure_details_and_error(self) -> None:
        summary = PipelineRunSummary(
            results=[
                ActionResult(
                    name="merge",
                    decision=ActionDecision.FAILED,
                    details="Exception during execution",
                    error="merge API timeout",
                )
            ]
        )
        comment = render_summary_comment(summary)
        assert "**failed**" in comment
        assert "Exception during execution" in comment
        assert "merge API timeout" in comment

    def test_table_cells_with_pipes_and_newlines_are_sanitized(self) -> None:
        """Pipe and newline characters in cell values must not break the table."""
        summary = PipelineRunSummary(
            results=[
                ActionResult(
                    name="merge",
                    decision=ActionDecision.FAILED,
                    details="step1\r\nstep2\rstep3",
                    error="timeout | retry failed",
                )
            ]
        )
        comment = render_summary_comment(summary)
        # Newlines must be replaced with <br>; raw newline within detail must not appear
        assert "step1<br>step2<br>step3" in comment
        assert "step1\r\nstep2\rstep3" not in comment
        # Pipe characters must be escaped; unescaped form must not appear in rendered error
        assert "timeout \\| retry failed" in comment
        assert "timeout | retry failed" not in comment

    def test_format_preconditions_returns_dash_when_no_preconditions(self) -> None:
        """_format_preconditions must return '—' when preconditions dict is empty."""
        result = ActionResult(
            name="guards",
            decision=ActionDecision.SKIP,
            details="some detail text that should only appear in Result column",
            preconditions={},
        )
        summary = PipelineRunSummary(results=[result])
        comment = render_summary_comment(summary)
        # The detail text must appear in the Result column, but not duplicated in Preconditions
        assert "some detail text" in comment
        # Preconditions column should show '—', not the detail text
        # The table row: | guards | ⬜ — | skipped (some detail...) |
        # Verify '—' is present and the detail text is not in the preconditions position
        # by checking the row structure: precond cell must be '⬜ —'
        assert "⬜ —" in comment

    def test_render_state_snapshot_inline_suffix_only_for_commented_or_nonzero(self) -> None:
        """'(N inline)' suffix must only appear for COMMENTED state or non-zero count."""
        # COMMENTED with count: should show suffix
        snapshot_commented = PRStateSnapshot(
            head_sha="abc1234567890",
            review_state="COMMENTED",
            copilot_review_inline_count=3,
        )
        summary_commented = PipelineRunSummary(snapshot=snapshot_commented)
        comment_commented = render_summary_comment(summary_commented)
        assert "3 inline" in comment_commented

        # APPROVED with zero count: must NOT show suffix
        snapshot_approved = PRStateSnapshot(
            head_sha="abc1234567890",
            review_state="APPROVED",
            copilot_review_inline_count=0,
        )
        summary_approved = PipelineRunSummary(snapshot=snapshot_approved)
        comment_approved = render_summary_comment(summary_approved)
        assert "0 inline" not in comment_approved
        assert "inline" not in comment_approved

        # Non-zero count with non-COMMENTED state: should still show suffix
        snapshot_nonzero = PRStateSnapshot(
            head_sha="abc1234567890",
            review_state="CHANGES_REQUESTED",
            copilot_review_inline_count=2,
        )
        summary_nonzero = PipelineRunSummary(snapshot=snapshot_nonzero)
        comment_nonzero = render_summary_comment(summary_nonzero)
        assert "2 inline" in comment_nonzero

    def test_html_metacharacters_are_escaped_in_table_and_snapshot(self) -> None:
        summary = PipelineRunSummary(
            results=[
                ActionResult(
                    name="merge</details>",
                    decision=ActionDecision.SKIP,
                    details="bad <tag> & raw",
                )
            ],
            snapshot=PRStateSnapshot(
                head_sha="abc1234</details>",
                ci_status="pending > unknown",
                review_state="COMMENTED </summary>",
                labels=["x&y", "</details>"],
            ),
        )

        comment = render_summary_comment(summary)

        assert "merge&lt;/details&gt;" in comment
        assert "bad &lt;tag&gt; &amp; raw" in comment
        assert "COMMENTED &lt;/summary&gt;" in comment
        assert "x&amp;y, &lt;/details&gt;" in comment
        assert "merge</details>" not in comment
        assert "bad <tag> & raw" not in comment
