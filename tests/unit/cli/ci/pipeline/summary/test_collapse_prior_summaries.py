"""Tests for collapse_prior_summaries."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.models import IssueCommentInfo
from agentic_devtools.cli.ci.pipeline.summary import collapse_prior_summaries


class TestCollapsePriorSummaries:
    """Tests for collapsing prior summary comments."""

    def test_normalizes_markdown_link_in_summary_header(self) -> None:
        provider = MagicMock()
        provider.list_issue_comments = None
        body = (
            "<!-- agdt:ai-pr-loop-summary -->\n"
            "\n"
            "**🤖 AI PR Loop Run** — [View Logs](https://github.com/org/repo/actions/runs/123)"
        )
        provider.find_comment.side_effect = [(42, body), None]

        collapsed = collapse_prior_summaries(provider, pr_number=1565)

        assert collapsed == 1
        provider.update_comment.assert_called_once()
        provider.find_comment.assert_called()
        updated_body = provider.update_comment.call_args.args[1]
        assert (
            "<summary>🤖 AI PR Loop Run — View Logs: https://github.com/org/repo/actions/runs/123</summary>"
            in updated_body
        )
        assert "<summary>🤖 AI PR Loop Run — [View Logs](" not in updated_body

    def test_uses_single_comment_listing_call_when_supported(self) -> None:
        provider = MagicMock()
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=11,
                author="github-actions[bot]",
                body="<!-- agdt:ai-pr-loop-summary -->\n\n**🤖 AI PR Loop Run** — run 1",
            ),
            IssueCommentInfo(
                id=12,
                author="github-actions[bot]",
                body="<!-- agdt:ai-pr-loop-summary -->\n\n**🤖 AI PR Loop Run** — run 2",
            ),
        ]

        collapsed = collapse_prior_summaries(provider, pr_number=1565)

        assert collapsed == 2
        provider.list_issue_comments.assert_called_once_with(1565)
        provider.update_comment.assert_any_call(
            11,
            (
                "<!-- agdt:ai-pr-loop-summary-collapsed -->\n"
                "<details><summary>🤖 AI PR Loop Run — run 1</summary>\n\n"
                "**🤖 AI PR Loop Run** — run 1\n"
                "</details>"
            ),
        )
        provider.update_comment.assert_any_call(
            12,
            (
                "<!-- agdt:ai-pr-loop-summary-collapsed -->\n"
                "<details><summary>🤖 AI PR Loop Run — run 2</summary>\n\n"
                "**🤖 AI PR Loop Run** — run 2\n"
                "</details>"
            ),
        )
        provider.find_comment.assert_not_called()

    def test_skips_non_bot_summary_comments_when_listing_supported(self) -> None:
        provider = MagicMock()
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=21,
                author="octocat",
                body="<!-- agdt:ai-pr-loop-summary -->\n\n**🤖 AI PR Loop Run** — user marker",
            )
        ]

        collapsed = collapse_prior_summaries(provider, pr_number=1565)

        assert collapsed == 0
        provider.update_comment.assert_not_called()

    def test_continues_collapsing_when_one_update_fails(self) -> None:
        provider = MagicMock()
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=31,
                author="github-actions[bot]",
                body="<!-- agdt:ai-pr-loop-summary -->\n\n**🤖 AI PR Loop Run** — first",
            ),
            IssueCommentInfo(
                id=32,
                author="github-actions[bot]",
                body="<!-- agdt:ai-pr-loop-summary -->\n\n**🤖 AI PR Loop Run** — second",
            ),
        ]

        provider.update_comment.side_effect = [RuntimeError("cannot edit"), None]

        collapsed = collapse_prior_summaries(provider, pr_number=1565)

        assert collapsed == 1
        assert provider.update_comment.call_count == 2

    def test_allows_actor_authored_comment_when_not_bot(self) -> None:
        provider = MagicMock()
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=41,
                author="acmarsn-agdt",
                body="<!-- agdt:ai-pr-loop-summary -->\n\n**🤖 AI PR Loop Run** — actor",
            )
        ]

        with patch.dict("os.environ", {"GITHUB_ACTOR": "acmarsn-agdt"}):
            collapsed = collapse_prior_summaries(provider, pr_number=1565)

        assert collapsed == 1
        provider.update_comment.assert_called_once()

    def test_skips_empty_author_comment_when_listing_supported(self) -> None:
        """Empty/unknown author must not be treated as editable (fail closed)."""
        provider = MagicMock()
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=51,
                author="",
                body="<!-- agdt:ai-pr-loop-summary -->\n\n**🤖 AI PR Loop Run** — no author",
            )
        ]

        collapsed = collapse_prior_summaries(provider, pr_number=1565)

        assert collapsed == 0
        provider.update_comment.assert_not_called()

    def test_list_comments_skips_body_not_starting_with_sentinel(self) -> None:
        """list_issue_comments path: comment whose body only contains (not starts with) the sentinel is skipped."""
        provider = MagicMock()
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=61,
                author="github-actions[bot]",
                # Contains sentinel but doesn't start with it
                body="Some human text\n<!-- agdt:ai-pr-loop-summary -->\n\n**🤖 AI PR Loop Run** — buried",
            )
        ]

        collapsed = collapse_prior_summaries(provider, pr_number=1565)

        assert collapsed == 0
        provider.update_comment.assert_not_called()

    def test_list_comments_skips_body_missing_pipeline_header(self) -> None:
        """list_issue_comments path: comment starting with sentinel but lacking the pipeline header is skipped."""
        provider = MagicMock()
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=62,
                author="github-actions[bot]",
                # Starts with sentinel but no "AI PR Loop Run" header
                body="<!-- agdt:ai-pr-loop-summary -->\n\nSome other content",
            )
        ]

        collapsed = collapse_prior_summaries(provider, pr_number=1565)

        assert collapsed == 0
        provider.update_comment.assert_not_called()

    def test_fallback_skips_comment_body_not_starting_with_sentinel(self) -> None:
        """Fallback path: comment whose body only contains (not starts with) the sentinel is skipped."""
        provider = MagicMock()
        provider.list_issue_comments = None
        # Body contains sentinel but doesn't start with it
        body = "Some human text\n<!-- agdt:ai-pr-loop-summary -->\n\n**🤖 AI PR Loop Run** — buried"
        provider.find_comment.return_value = (99, body)

        collapsed = collapse_prior_summaries(provider, pr_number=1565)

        assert collapsed == 0
        provider.update_comment.assert_not_called()

    def test_fallback_skips_comment_body_missing_pipeline_header(self) -> None:
        """Fallback path: comment starting with sentinel but lacking the pipeline header is skipped."""
        provider = MagicMock()
        provider.list_issue_comments = None
        # Starts with sentinel but no "AI PR Loop Run" header
        body = "<!-- agdt:ai-pr-loop-summary -->\n\nSome other content"
        provider.find_comment.return_value = (100, body)

        collapsed = collapse_prior_summaries(provider, pr_number=1565)

        assert collapsed == 0
        provider.update_comment.assert_not_called()
