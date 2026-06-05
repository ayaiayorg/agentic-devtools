"""Tests for ApplySuggestionsAction."""

import os
from typing import cast
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.pipeline.actions.apply_suggestions import ApplySuggestionsAction
from agentic_devtools.cli.ci.pipeline.models import ActionDecision
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot


class TestApplySuggestionsActionEvaluate:
    """Tests for ApplySuggestionsAction.evaluate()."""

    @patch.dict(os.environ, {"ENABLE_AUTO_APPLY_SUGGESTIONS": "true"}, clear=False)
    def test_skip_when_no_actionable_review(self) -> None:
        """SKIP when review state is APPROVED."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="APPROVED",
            copilot_review_id=1,
            copilot_review_inline_count=0,
        )
        derived = DerivedState(snapshot)
        action = ApplySuggestionsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP

    @patch.dict(os.environ, {"ENABLE_AUTO_APPLY_SUGGESTIONS": "true"}, clear=False)
    def test_skip_when_no_review_id(self) -> None:
        """SKIP when copilot_review_id is 0."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=0,
        )
        derived = DerivedState(snapshot)
        action = ApplySuggestionsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP

    @patch.dict(os.environ, {"ENABLE_AUTO_APPLY_SUGGESTIONS": "true"}, clear=False)
    def test_execute_when_changes_requested_with_inline(self) -> None:
        """EXECUTE when CHANGES_REQUESTED with inline comments."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=3,
        )
        derived = DerivedState(snapshot)
        action = ApplySuggestionsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

    @patch.dict(os.environ, {"ENABLE_AUTO_APPLY_SUGGESTIONS": "true"}, clear=False)
    def test_execute_when_changes_requested_without_inline(self) -> None:
        """EXECUTE when CHANGES_REQUESTED even with inline count explicitly set to 0."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=0,
        )
        derived = DerivedState(snapshot)
        action = ApplySuggestionsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

    @patch.dict(os.environ, {"ENABLE_AUTO_APPLY_SUGGESTIONS": "true"}, clear=False)
    def test_execute_when_commented_with_inline(self) -> None:
        """EXECUTE when COMMENTED with inline comments."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="COMMENTED",
            copilot_review_id=100,
            copilot_review_inline_count=2,
        )
        derived = DerivedState(snapshot)
        action = ApplySuggestionsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

    @patch.dict(os.environ, {"ENABLE_AUTO_APPLY_SUGGESTIONS": "true"}, clear=False)
    def test_skip_when_commented_without_inline(self) -> None:
        """SKIP when COMMENTED and inline count is explicitly zero."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="COMMENTED",
            copilot_review_id=100,
            copilot_review_inline_count=0,
        )
        derived = DerivedState(snapshot)
        action = ApplySuggestionsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP

    @patch.dict(os.environ, {"ENABLE_AUTO_APPLY_SUGGESTIONS": "true"}, clear=False)
    def test_execute_when_commented_inline_count_is_none(self) -> None:
        """EXECUTE when COMMENTED and inline count is unknown/None (fail-closed)."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="COMMENTED",
            copilot_review_id=100,
            copilot_review_inline_count=cast(int, None),
        )
        derived = DerivedState(snapshot)
        action = ApplySuggestionsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

    @patch.dict(os.environ, {"ENABLE_AUTO_APPLY_SUGGESTIONS": "true"}, clear=False)
    def test_execute_when_unknown_inline_count(self) -> None:
        """EXECUTE when inline count is -1 (unknown, fail-closed)."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=-1,
        )
        derived = DerivedState(snapshot)
        action = ApplySuggestionsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

    @patch.dict(os.environ, {"ENABLE_AUTO_APPLY_SUGGESTIONS": ""}, clear=False)
    def test_skip_when_feature_disabled_empty_string(self) -> None:
        """SKIP when ENABLE_AUTO_APPLY_SUGGESTIONS is empty string."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=3,
        )
        derived = DerivedState(snapshot)
        action = ApplySuggestionsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "disabled" in result.details.lower()
        assert result.preconditions["feature_enabled"] is False

    @patch.dict(os.environ, {"ENABLE_AUTO_APPLY_SUGGESTIONS": "false"}, clear=False)
    def test_skip_when_feature_explicitly_false(self) -> None:
        """SKIP when ENABLE_AUTO_APPLY_SUGGESTIONS is 'false'."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=3,
        )
        derived = DerivedState(snapshot)
        action = ApplySuggestionsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert result.preconditions["feature_enabled"] is False

    @patch.dict(os.environ, {}, clear=True)
    def test_skip_when_env_var_not_set(self) -> None:
        """SKIP when ENABLE_AUTO_APPLY_SUGGESTIONS env var is not present at all."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=3,
        )
        derived = DerivedState(snapshot)
        action = ApplySuggestionsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert result.preconditions["feature_enabled"] is False

    @patch.dict(os.environ, {"ENABLE_AUTO_APPLY_SUGGESTIONS": "true"}, clear=False)
    def test_proceeds_when_feature_enabled_lowercase(self) -> None:
        """Proceeds past feature gate when ENABLE_AUTO_APPLY_SUGGESTIONS='true'."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=3,
        )
        derived = DerivedState(snapshot)
        action = ApplySuggestionsAction()
        result = action.evaluate(snapshot, derived)
        # Should NOT skip due to feature gate — may EXECUTE or SKIP for other reasons
        assert result.preconditions.get("feature_enabled") is True

    @patch.dict(os.environ, {"ENABLE_AUTO_APPLY_SUGGESTIONS": "TRUE"}, clear=False)
    def test_proceeds_when_feature_enabled_uppercase(self) -> None:
        """Proceeds past feature gate when ENABLE_AUTO_APPLY_SUGGESTIONS='TRUE' (case-insensitive)."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=3,
        )
        derived = DerivedState(snapshot)
        action = ApplySuggestionsAction()
        result = action.evaluate(snapshot, derived)
        assert result.preconditions.get("feature_enabled") is True

    @patch.dict(os.environ, {"ENABLE_AUTO_APPLY_SUGGESTIONS": "True"}, clear=False)
    def test_proceeds_when_feature_enabled_mixed_case(self) -> None:
        """Proceeds past feature gate when ENABLE_AUTO_APPLY_SUGGESTIONS='True' (mixed case)."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=3,
        )
        derived = DerivedState(snapshot)
        action = ApplySuggestionsAction()
        result = action.evaluate(snapshot, derived)
        assert result.preconditions.get("feature_enabled") is True


class TestApplySuggestionsActionExecute:
    """Tests for ApplySuggestionsAction.execute()."""

    def test_skip_when_no_suggestions_found(self) -> None:
        """SKIP when fetch returns no applicable suggestions."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=3,
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_issue_comments.return_value = []

        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.fetch_applicable_suggestions"
        ) as mock_fetch:
            mock_fetch.return_value = ([], "PR_1")
            action = ApplySuggestionsAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.SKIP
        assert "No applicable suggestions" in result.details

    def test_skip_when_threshold_exceeded(self) -> None:
        """SKIP when suggestion count exceeds threshold."""
        from agentic_devtools.cli.ci.pipeline.suggestions import SuggestedChange

        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=60,
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_issue_comments.return_value = []

        # Create 51 suggestions (exceeds 50 threshold)
        suggestions = [
            SuggestedChange(
                suggestion_id=f"SC{i}",
                outdated=False,
                comment_database_id=i,
                thread_id=f"T{i}",
            )
            for i in range(51)
        ]

        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.fetch_applicable_suggestions"
        ) as mock_fetch:
            mock_fetch.return_value = (suggestions, "PR_1")
            action = ApplySuggestionsAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.SKIP
        assert "exceeds threshold" in result.details

    def test_execute_successful_batch_apply(self) -> None:
        """EXECUTE with invalidates_snapshot=True on successful apply."""
        from agentic_devtools.cli.ci.pipeline.suggestions import (
            ApplySuggestionsResult,
            SuggestedChange,
        )

        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=2,
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_issue_comments.return_value = []

        suggestions = [
            SuggestedChange(
                suggestion_id="SC1",
                outdated=False,
                comment_database_id=101,
                thread_id="T1",
            ),
            SuggestedChange(
                suggestion_id="SC2",
                outdated=False,
                comment_database_id=102,
                thread_id="T2",
            ),
        ]

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.fetch_applicable_suggestions"
            ) as mock_fetch,
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.apply_suggestions_with_bisection"
            ) as mock_apply,
        ):
            mock_fetch.return_value = (suggestions, "PR_1")
            mock_apply.return_value = ApplySuggestionsResult(
                applied_ids=["SC1", "SC2"],
                commit_shas=["abc1234"],
            )
            action = ApplySuggestionsAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE
        assert result.invalidates_snapshot is True
        assert "Applied 2 suggestions" in result.details

        # Verify ExclusionContext was set
        exclusion_ctx = derived.get("exclusion_context")
        assert exclusion_ctx is not None
        assert exclusion_ctx.resolved_comment_ids == {101, 102}

    def test_skip_when_fetch_raises_exception(self) -> None:
        """SKIP (not FAILED) when fetch raises per FR-010."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=3,
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_issue_comments.return_value = []

        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.fetch_applicable_suggestions"
        ) as mock_fetch:
            mock_fetch.side_effect = RuntimeError("API error")
            action = ApplySuggestionsAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.SKIP
        assert "Failed to fetch" in result.details

    def test_partial_application_on_conflict(self) -> None:
        """Partial apply result is used when some suggestions conflict."""
        from agentic_devtools.cli.ci.pipeline.suggestions import (
            ApplySuggestionsResult,
            SuggestedChange,
        )

        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=2,
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_issue_comments.return_value = []

        suggestions = [
            SuggestedChange(
                suggestion_id="SC1",
                outdated=False,
                comment_database_id=101,
                thread_id="T1",
            ),
            SuggestedChange(
                suggestion_id="SC2",
                outdated=False,
                comment_database_id=102,
                thread_id="T2",
            ),
        ]

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.fetch_applicable_suggestions"
            ) as mock_fetch,
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.apply_suggestions_with_bisection"
            ) as mock_bisect,
        ):
            mock_fetch.return_value = (suggestions, "PR_1")
            mock_bisect.return_value = ApplySuggestionsResult(
                applied_ids=["SC1"],
                skipped_ids=["SC2"],
                commit_shas=["abc1234"],
            )
            action = ApplySuggestionsAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE
        assert result.invalidates_snapshot is True
        mock_bisect.assert_called_once()

    def test_comment_excluded_only_when_all_suggestions_applied(self) -> None:
        """Comment is excluded only if ALL its suggestions are applied; partial apply leaves it visible."""
        from agentic_devtools.cli.ci.pipeline.suggestions import (
            ApplySuggestionsResult,
            SuggestedChange,
        )

        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=2,
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_issue_comments.return_value = []

        # Comment 101 has two suggestions; only SC1 will be applied, SC2 conflicts
        suggestions = [
            SuggestedChange(
                suggestion_id="SC1",
                outdated=False,
                comment_database_id=101,
                thread_id="T1",
            ),
            SuggestedChange(
                suggestion_id="SC2",
                outdated=False,
                comment_database_id=101,
                thread_id="T1",
            ),
            # Comment 102 has one suggestion that is fully applied
            SuggestedChange(
                suggestion_id="SC3",
                outdated=False,
                comment_database_id=102,
                thread_id="T2",
            ),
        ]

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.fetch_applicable_suggestions"
            ) as mock_fetch,
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.apply_suggestions_with_bisection"
            ) as mock_bisect,
        ):
            mock_fetch.return_value = (suggestions, "PR_1")
            mock_bisect.return_value = ApplySuggestionsResult(
                applied_ids=["SC1", "SC3"],
                skipped_ids=["SC2"],
                commit_shas=["abc1234"],
            )
            action = ApplySuggestionsAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE
        exclusion_ctx = derived.get("exclusion_context")
        assert exclusion_ctx is not None
        # Comment 101 has an unapplied suggestion (SC2) — must NOT be excluded
        assert 101 not in exclusion_ctx.resolved_comment_ids
        # Comment 102 had its only suggestion applied — must be excluded
        assert 102 in exclusion_ctx.resolved_comment_ids

    def test_skip_when_batch_apply_raises_exception(self) -> None:
        """SKIP (not FAILED) when apply raises exception."""
        from agentic_devtools.cli.ci.pipeline.suggestions import SuggestedChange

        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=1,
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_issue_comments.return_value = []
        suggestions = [
            SuggestedChange(
                suggestion_id="SC1",
                outdated=False,
                comment_database_id=101,
                thread_id="T1",
            )
        ]

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.fetch_applicable_suggestions"
            ) as mock_fetch,
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.apply_suggestions_with_bisection"
            ) as mock_apply,
        ):
            mock_fetch.return_value = (suggestions, "PR_1")
            mock_apply.side_effect = RuntimeError("rate limited")
            action = ApplySuggestionsAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.SKIP
        assert "Failed to apply suggestions" in result.details

    def test_skip_when_bisection_applies_nothing(self) -> None:
        """SKIP when apply returns nothing (all conflicted)."""
        from agentic_devtools.cli.ci.pipeline.suggestions import (
            ApplySuggestionsResult,
            SuggestedChange,
        )

        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=2,
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_issue_comments.return_value = []

        suggestions = [
            SuggestedChange(
                suggestion_id="SC1",
                outdated=False,
                comment_database_id=101,
                thread_id="T1",
            ),
        ]

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.fetch_applicable_suggestions"
            ) as mock_fetch,
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.apply_suggestions_with_bisection"
            ) as mock_bisect,
        ):
            mock_fetch.return_value = (suggestions, "PR_1")
            mock_bisect.return_value = ApplySuggestionsResult(
                skipped_ids=["SC1"],
                error="Single suggestion conflict",
            )
            action = ApplySuggestionsAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.SKIP
        assert "No suggestions applied" in result.details

    def test_post_summary_comment_with_skipped(self) -> None:
        """Summary comment includes skipped count."""
        from agentic_devtools.cli.ci.pipeline.suggestions import (
            ApplySuggestionsResult,
            SuggestedChange,
        )

        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=3,
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_issue_comments.return_value = []

        suggestions = [
            SuggestedChange(
                suggestion_id="SC1",
                outdated=False,
                comment_database_id=101,
                thread_id="T1",
            ),
            SuggestedChange(
                suggestion_id="SC2",
                outdated=False,
                comment_database_id=102,
                thread_id="T2",
            ),
            SuggestedChange(
                suggestion_id="SC3",
                outdated=False,
                comment_database_id=103,
                thread_id="T3",
            ),
        ]

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.fetch_applicable_suggestions"
            ) as mock_fetch,
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.apply_suggestions_with_bisection"
            ) as mock_apply,
        ):
            mock_fetch.return_value = (suggestions, "PR_1")
            mock_apply.return_value = ApplySuggestionsResult(
                applied_ids=["SC1", "SC2"],
                skipped_ids=["SC3"],
                commit_shas=["abc1234"],
            )
            action = ApplySuggestionsAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE
        # Verify post_comment was called with skipped info
        comment_body = provider.post_comment.call_args[0][1]
        assert "1 suggestion" in comment_body
        assert "could not be applied" in comment_body

    def test_post_summary_comment_failure_does_not_crash(self) -> None:
        """post_comment failure is logged but does not crash."""
        from agentic_devtools.cli.ci.pipeline.suggestions import (
            ApplySuggestionsResult,
            SuggestedChange,
        )

        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=1,
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_issue_comments.return_value = []
        provider.post_comment.side_effect = RuntimeError("Network error")

        suggestions = [
            SuggestedChange(
                suggestion_id="SC1",
                outdated=False,
                comment_database_id=101,
                thread_id="T1",
            ),
        ]

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.fetch_applicable_suggestions"
            ) as mock_fetch,
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.apply_suggestions_with_bisection"
            ) as mock_apply,
        ):
            mock_fetch.return_value = (suggestions, "PR_1")
            mock_apply.return_value = ApplySuggestionsResult(
                applied_ids=["SC1"],
                commit_shas=["abc1234"],
            )
            action = ApplySuggestionsAction()
            result = action.execute(provider, snapshot, derived)

        # Should still succeed despite post_comment failure
        assert result.decision == ActionDecision.EXECUTE

    def test_post_summary_no_sha_list_when_pending_refresh(self) -> None:
        """Summary omits commit list when only pending_refresh sha present."""
        from agentic_devtools.cli.ci.pipeline.suggestions import (
            ApplySuggestionsResult,
            SuggestedChange,
        )

        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=1,
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_issue_comments.return_value = []

        suggestions = [
            SuggestedChange(
                suggestion_id="SC1",
                outdated=False,
                comment_database_id=101,
                thread_id="T1",
            ),
        ]

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.fetch_applicable_suggestions"
            ) as mock_fetch,
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.apply_suggestions_with_bisection"
            ) as mock_apply,
        ):
            mock_fetch.return_value = (suggestions, "PR_1")
            mock_apply.return_value = ApplySuggestionsResult(
                applied_ids=["SC1"],
                commit_shas=["pending_refresh"],
            )
            action = ApplySuggestionsAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE
        comment_body = provider.post_comment.call_args[0][1]
        # Should not include commit sha when only "pending_refresh"
        assert "pending_refresh" not in comment_body

    def test_post_summary_no_commit_shas(self) -> None:
        """Summary comment when commit_shas is empty."""
        from agentic_devtools.cli.ci.pipeline.suggestions import (
            ApplySuggestionsResult,
            SuggestedChange,
        )

        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=1,
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_issue_comments.return_value = []

        suggestions = [
            SuggestedChange(
                suggestion_id="SC1",
                outdated=False,
                comment_database_id=101,
                thread_id="T1",
            ),
        ]

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.fetch_applicable_suggestions"
            ) as mock_fetch,
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.apply_suggestions_with_bisection"
            ) as mock_apply,
        ):
            mock_fetch.return_value = (suggestions, "PR_1")
            mock_apply.return_value = ApplySuggestionsResult(
                applied_ids=["SC1"],
                commit_shas=[],
            )
            action = ApplySuggestionsAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE
        comment_body = provider.post_comment.call_args[0][1]
        assert "Auto-applied 1 suggestion" in comment_body
        assert "commit" not in comment_body

    def test_skip_when_autofix_cycle_limit_reached(self) -> None:
        """SKIP when prior autofix count >= _MAX_AUTOFIX_CYCLES."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=3,
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()

        # Simulate 20 prior autofix comments
        mock_comments = [MagicMock(body="🔧 **Auto-applied 2 suggestions** in commit `abc1234`") for _ in range(20)]
        provider.list_issue_comments.return_value = mock_comments

        action = ApplySuggestionsAction()
        result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.SKIP
        assert "cycle limit" in result.details.lower()
        assert result.preconditions.get("cycle_limit_reached") is True

    def test_proceeds_when_under_cycle_limit(self) -> None:
        """Proceeds past cycle limit when count < _MAX_AUTOFIX_CYCLES."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=3,
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()

        # Simulate 5 prior autofix comments (under limit)
        mock_comments = [MagicMock(body="🔧 **Auto-applied 1 suggestion** in commit `abc1234`") for _ in range(5)]
        provider.list_issue_comments.return_value = mock_comments

        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.fetch_applicable_suggestions"
        ) as mock_fetch:
            mock_fetch.return_value = ([], "PR_1")
            action = ApplySuggestionsAction()
            result = action.execute(provider, snapshot, derived)

        # Should pass cycle check but SKIP due to no suggestions
        assert result.decision == ActionDecision.SKIP
        assert "No applicable suggestions" in result.details

    def test_proceeds_when_cycle_count_check_fails(self) -> None:
        """Fail-open: proceeds when list_issue_comments raises exception."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=3,
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_issue_comments.side_effect = RuntimeError("API error")

        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.fetch_applicable_suggestions"
        ) as mock_fetch:
            mock_fetch.return_value = ([], "PR_1")
            action = ApplySuggestionsAction()
            result = action.execute(provider, snapshot, derived)

        # Should proceed past cycle check (fail-open) and SKIP for no suggestions
        assert result.decision == ActionDecision.SKIP
        assert "No applicable suggestions" in result.details

    def test_non_autofix_comments_not_counted(self) -> None:
        """Only comments with the autofix prefix are counted toward cycle limit."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=3,
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()

        # Mix of autofix comments and regular comments
        mock_comments = [
            MagicMock(body="🔧 **Auto-applied 1 suggestion** in commit `abc1234`"),
            MagicMock(body="Regular comment about the PR"),
            MagicMock(body="Another regular comment"),
            MagicMock(body=None),  # Edge case: None body
        ]
        provider.list_issue_comments.return_value = mock_comments

        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.apply_suggestions.fetch_applicable_suggestions"
        ) as mock_fetch:
            mock_fetch.return_value = ([], "PR_1")
            action = ApplySuggestionsAction()
            result = action.execute(provider, snapshot, derived)

        # Only 1 autofix comment (under limit of 20), so should proceed
        assert result.decision == ActionDecision.SKIP
        assert "No applicable suggestions" in result.details


def test_count_prior_autofix_comments_helper() -> None:
    """_count_prior_autofix_comments counts only autofix summary comments."""
    from agentic_devtools.cli.ci.pipeline.actions.apply_suggestions import _count_prior_autofix_comments

    provider = MagicMock()
    provider.list_issue_comments.return_value = [
        MagicMock(body="🔧 **Auto-applied 2 suggestions** in commit `abc1234`"),
        MagicMock(body="Regular comment"),
        MagicMock(body="🔧 **Auto-applied 1 suggestion**"),
        MagicMock(body=None),
        MagicMock(body=""),
    ]

    count = _count_prior_autofix_comments(provider, 42)
    assert count == 2


def test_count_prior_autofix_comments_returns_zero_on_exception() -> None:
    """Returns 0 when list_issue_comments raises."""
    from agentic_devtools.cli.ci.pipeline.actions.apply_suggestions import _count_prior_autofix_comments

    provider = MagicMock()
    provider.list_issue_comments.side_effect = RuntimeError("API error")

    count = _count_prior_autofix_comments(provider, 42)
    assert count == 0
