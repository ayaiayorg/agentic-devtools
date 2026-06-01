"""Tests for _build_repair_comment() in the GitHub provider."""

from agentic_devtools.cli.ci.github_provider import _build_repair_comment
from agentic_devtools.cli.ci.models import CheckRunStatus, ReviewCommentInfo

_COMMENT_1 = ReviewCommentInfo(
    id=101,
    path="src/foo.py",
    body="Fix the null check here",
    html_url="https://github.com/owner/repo/pull/42#pullreviewcomment-101",
)
_COMMENT_2 = ReviewCommentInfo(
    id=102,
    path="src/foo.py",
    body="Add error handling",
    html_url="https://github.com/owner/repo/pull/42#pullreviewcomment-102",
)
_COMMENT_OTHER = ReviewCommentInfo(
    id=103,
    path="src/bar.py",
    body="Use a helper function",
    html_url="https://github.com/owner/repo/pull/42#pullreviewcomment-103",
)
_COMMENT_DUP_BASENAME_A = ReviewCommentInfo(
    id=108,
    path="pkg_a/__init__.py",
    body="First duplicate basename",
    html_url="https://github.com/owner/repo/pull/42#pullreviewcomment-108",
)
_COMMENT_DUP_BASENAME_B = ReviewCommentInfo(
    id=109,
    path="pkg_b/__init__.py",
    body="Second duplicate basename",
    html_url="https://github.com/owner/repo/pull/42#pullreviewcomment-109",
)
_SUPPRESSED = ReviewCommentInfo(
    id=104,
    path="src/baz.py",
    body="Subjective style preference",
    html_url="https://github.com/owner/repo/pull/42#pullreviewcomment-104",
    is_suppressed=True,
)


class TestBuildRepairComment:
    """Tests for repair comment body construction."""

    def test_comment_begins_with_at_copilot(self) -> None:
        """Comment MUST begin with @copilot for reliable agent triggering."""
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=[_COMMENT_1],
        )
        assert body.startswith("@copilot")

    def test_review_repair_includes_numbered_comment_links(self) -> None:
        """Review comments are listed as numbered links with global and per-file counters."""
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=[_COMMENT_1, _COMMENT_2, _COMMENT_OTHER],
            repository_full_name="owner/repo",
            pr_number=42,
            review_id=456,
        )
        assert "@copilot" in body
        assert "## Comments" in body
        # Comment #1 - first comment on foo.py → foo.py (1)
        assert "[Comment #1 - foo.py (1)]" in body
        assert _COMMENT_1.html_url in body
        # Comment #2 - second comment on foo.py → foo.py (2)
        assert "[Comment #2 - foo.py (2)]" in body
        assert _COMMENT_2.html_url in body
        # Comment #3 - first comment on bar.py → bar.py (1)
        assert "[Comment #3 - bar.py (1)]" in body
        assert _COMMENT_OTHER.html_url in body

    def test_review_repair_includes_review_link(self) -> None:
        """Trigger comment includes a direct link to the parent review."""
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=[_COMMENT_1],
            repository_full_name="owner/repo",
            pr_number=42,
            review_id=456,
        )
        assert "[Review](https://github.com/owner/repo/pull/42#pullrequestreview-456)" in body

    def test_review_repair_includes_dedup_marker(self) -> None:
        """Trigger comment includes the copilot-trigger dedup marker."""
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=[_COMMENT_1],
            review_id=456,
        )
        assert "<!-- copilot-trigger:456 -->" in body

    def test_suppressed_comments_use_quoted_format(self) -> None:
        """Suppressed comments show quoted body inline, no link, with suffix."""
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=[_COMMENT_1, _SUPPRESSED],
        )
        # Suppressed: no link, body quoted, "(suppressed comment)" suffix
        assert '- `Comment #2` - `baz.py (1)`: "Subjective style preference" (suppressed comment)' in body
        # Non-suppressed: link format
        assert "- [Comment #1 - foo.py (1)]" in body
        # Suppressed comment URL should NOT appear as a link
        assert _SUPPRESSED.html_url not in body

    def test_suppressed_comment_body_is_normalized_and_escaped(self) -> None:
        """Suppressed comment body is single-line and escapes double quotes."""
        suppressed = ReviewCommentInfo(
            id=105,
            path="src/baz.py",
            body='First line\nSecond "quoted" line',
            html_url="",
            is_suppressed=True,
        )
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=[suppressed],
        )
        assert '- `Comment #1` - `baz.py (1)`: "First line Second \\"quoted\\" line" (suppressed comment)' in body

    def test_suppressed_comment_body_is_truncated(self) -> None:
        """Suppressed comment body is truncated to keep trigger comment compact."""
        suppressed = ReviewCommentInfo(
            id=106,
            path="src/baz.py",
            body="x" * 260,
            html_url="",
            is_suppressed=True,
        )
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=[suppressed],
        )
        assert "x" * 260 not in body
        assert "…" in body

    def test_non_suppressed_comment_without_url_falls_back_to_plain_text(self) -> None:
        """Comments missing html_url use plain list item text instead of empty link."""
        no_url = ReviewCommentInfo(
            id=107,
            path="src/foo.py",
            body="Missing URL",
            html_url="",
        )
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=[no_url],
        )
        assert "- Comment #1 - foo.py (1)" in body
        assert "[Comment #1 - foo.py (1)]()" not in body

    def test_suppressed_comments_continue_global_numbering(self) -> None:
        """Suppressed comments continue the nC sequence, not a separate counter."""
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=[_COMMENT_1, _SUPPRESSED, _COMMENT_OTHER],
        )
        assert "Comment #1" in body
        assert "Comment #2" in body  # suppressed, continues sequence
        assert "Comment #3" in body  # next visible comment

    def test_ci_repair_lists_failed_checks(self) -> None:
        """CI failures are listed with ❌ markers."""
        checks = [
            CheckRunStatus(id=1, name="Targeted Checks ✅", status="completed", conclusion="failure"),
            CheckRunStatus(id=2, name="Smart Module Tests ✅", status="completed", conclusion="failure"),
        ]
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="ci",
            failed_checks=checks,
            review_comments=[],
        )
        assert "@copilot" in body
        assert "## CI Failures" in body
        assert "❌ Targeted Checks ✅" in body
        assert "❌ Smart Module Tests ✅" in body

    def test_ci_repair_omits_link_when_html_url_missing(self) -> None:
        """CI check without html_url renders as plain text — no constructed /runs/{id} link."""
        checks = [CheckRunStatus(id=111, name="Targeted Checks ✅", status="completed", conclusion="failure")]
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="ci",
            failed_checks=checks,
            review_comments=[],
            repository_full_name="owner/repo",
        )
        # No constructed /runs/{id} URL should appear
        assert "https://github.com/owner/repo/runs/111" not in body
        # Plain-text entry is used instead
        assert "❌ Targeted Checks ✅ — `failure`" in body
        # Must not produce an empty link
        assert "[Targeted Checks ✅]()" not in body

    def test_ci_repair_prefers_html_url_over_constructed_url(self) -> None:
        """When html_url is set on CheckRunStatus, it is used instead of the constructed /runs/{id} URL."""
        checks = [
            CheckRunStatus(
                id=111,
                name="Targeted Checks ✅",
                status="completed",
                conclusion="failure",
                html_url="https://github.com/owner/repo/actions/runs/9999/jobs/111",
            )
        ]
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="ci",
            failed_checks=checks,
            review_comments=[],
            repository_full_name="owner/repo",
        )
        assert "https://github.com/owner/repo/actions/runs/9999/jobs/111" in body
        assert "[Targeted Checks ✅](https://github.com/owner/repo/actions/runs/9999/jobs/111)" in body
        # Must NOT fall back to the constructed check-run-ID URL
        assert "https://github.com/owner/repo/runs/111" not in body

    def test_ci_repair_includes_conclusion_label(self) -> None:
        """Each CI failure line includes the conclusion value."""
        checks = [CheckRunStatus(id=5, name="build", status="completed", conclusion="failure")]
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="ci",
            failed_checks=checks,
            review_comments=[],
        )
        assert "`failure`" in body

    def test_both_repair_includes_review_and_ci_sections(self) -> None:
        """Combined repair includes both ## Comments and ## CI Failures sections."""
        checks = [CheckRunStatus(id=1, name="tests", status="completed", conclusion="failure")]
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="both",
            failed_checks=checks,
            review_comments=[_COMMENT_1],
        )
        assert "## Comments" in body
        assert "## CI Failures" in body

    def test_empty_context_includes_fallback(self) -> None:
        """When no comments and no failures, a fallback message is shown with SHA."""
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=[],
        )
        assert body.startswith("@copilot")
        assert "abc123de" in body  # short SHA in fallback

    def test_review_id_adds_dedup_marker_even_without_prefetched_comments(self) -> None:
        """Review context with review_id still includes structured instructions when comments are unavailable."""
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=[],
            repository_full_name="owner/repo",
            pr_number=42,
            review_id=456,
        )
        assert "<!-- copilot-trigger:456 -->" in body
        assert "[Review](https://github.com/owner/repo/pull/42#pullrequestreview-456)" in body
        assert "## Instructions" in body
        assert "agdt.address-copilot-review.evaluate-and-respond.agent.md" in body

    def test_fallback_does_not_include_skill_reference(self) -> None:
        """Fallback comment (no comments, no failures) uses legacy format without skill."""
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=[],
        )
        assert "## Instructions" not in body

    def test_review_only_references_evaluate_and_respond_skill(self) -> None:
        """Review-only repair references the evaluate-and-respond skill."""
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=[_COMMENT_1],
        )
        assert "agdt.address-copilot-review.evaluate-and-respond.agent.md" in body
        assert "agdt.address-copilot-review.ci-repair.agent.md" not in body

    def test_ci_only_references_ci_repair_skill(self) -> None:
        """CI-only repair references the ci-repair skill."""
        checks = [CheckRunStatus(id=1, name="lint", status="completed", conclusion="failure")]
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="ci",
            failed_checks=checks,
            review_comments=[],
        )
        assert "agdt.address-copilot-review.ci-repair.agent.md" in body
        assert "agdt.address-copilot-review.evaluate-and-respond.agent.md" not in body

    def test_both_references_evaluate_and_respond_skill(self) -> None:
        """Combined repair references evaluate-and-respond (which handles CI as sub-task)."""
        checks = [CheckRunStatus(id=1, name="tests", status="completed", conclusion="failure")]
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="both",
            failed_checks=checks,
            review_comments=[_COMMENT_1],
        )
        assert "agdt.address-copilot-review.evaluate-and-respond.agent.md" in body
        assert "agdt.address-copilot-review.ci-repair.agent.md" not in body

    def test_instructions_section_present_when_context_exists(self) -> None:
        """## Instructions section appears when there are comments or CI failures."""
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=[_COMMENT_1],
        )
        assert "## Instructions" in body
        assert "Follow `.github/agents/" in body

    def test_per_file_counter_resets_for_each_file(self) -> None:
        """nF counter resets to 1 for each new file path."""
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=[_COMMENT_1, _COMMENT_OTHER, _COMMENT_2],
        )
        # foo.py gets (1) for first comment, bar.py gets (1) for its comment,
        # foo.py second comment gets (2)
        assert "foo.py (1)" in body
        assert "bar.py (1)" in body
        assert "foo.py (2)" in body

    def test_duplicate_basenames_render_with_full_paths(self) -> None:
        """When basenames collide, comment labels include full paths to avoid ambiguity."""
        body = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=[_COMMENT_DUP_BASENAME_A, _COMMENT_DUP_BASENAME_B],
        )
        assert "Comment #1 - pkg_a/__init__.py (1)" in body
        assert "Comment #2 - pkg_b/__init__.py (1)" in body

    def test_no_old_section_headers_in_new_format(self) -> None:
        """Old-style headers (## Copilot Review Feedback, ## CI Failure Context) are gone."""
        checks = [CheckRunStatus(id=1, name="lint", status="completed", conclusion="failure")]
        body_ci = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="ci",
            failed_checks=checks,
            review_comments=[],
        )
        body_review = _build_repair_comment(
            head_sha="abc123def456",
            repair_type="review",
            failed_checks=[],
            review_comments=[_COMMENT_1],
        )
        assert "## Copilot Review Feedback" not in body_review
        assert "## CI Failure Context" not in body_ci
        assert "### Comment" not in body_review
