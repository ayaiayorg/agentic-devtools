"""Tests for _classify_merge_error helper."""

from agentic_devtools.cli.github.pr_merge import _classify_merge_error


class TestClassifyMergeError:
    """Tests for _classify_merge_error."""

    def test_conflict_keyword(self):
        """Detects 'conflict' in stderr."""
        assert _classify_merge_error("merge conflict detected") == "merge_conflict"

    def test_conflict_mixed_case(self):
        """Case-insensitive conflict detection."""
        assert _classify_merge_error("Merge Conflict Detected") == "merge_conflict"

    def test_protected_branch(self):
        """Detects 'protected branch' in stderr."""
        assert _classify_merge_error("protected branch rules apply") == "branch_protection"

    def test_required_status(self):
        """Detects 'required status' in stderr."""
        assert _classify_merge_error("required status checks have not passed") == "branch_protection"

    def test_branch_protection(self):
        """Detects 'branch protection' in stderr."""
        assert _classify_merge_error("branch protection rule prevents merge") == "branch_protection"

    def test_not_mergeable(self):
        """Detects 'not mergeable' in stderr."""
        assert _classify_merge_error("Pull request is not mergeable") == "not_mergeable"

    def test_not_in_a_mergeable_state(self):
        """Detects 'not in a mergeable state' in stderr."""
        assert _classify_merge_error("PR is not in a mergeable state") == "not_mergeable"

    def test_generic_fallback(self):
        """Falls back to merge_failed for unknown errors."""
        assert _classify_merge_error("unknown error occurred") == "merge_failed"

    def test_empty_string(self):
        """Empty string falls back to merge_failed."""
        assert _classify_merge_error("") == "merge_failed"
