"""Tests for agentic_devtools.cli.git.agdt_branch.PersistResult."""

from agentic_devtools.cli.git.agdt_branch import PersistResult


class TestPersistResult:
    """Tests for the PersistResult dataclass."""

    def test_defaults(self):
        """Assert default values: success=False, empty strings, error=None."""
        r = PersistResult()
        assert r.success is False
        assert r.branch_name == ""
        assert r.commit_hash == ""
        assert r.worktree_key == ""
        assert r.workflow_type == ""
        assert r.error is None

    def test_success_fields(self):
        """Create with explicit success fields and assert all populated."""
        r = PersistResult(
            success=True,
            branch_name="feat-agdt",
            commit_hash="abc123",
            worktree_key="DFLY-1234",
            workflow_type="review",
        )
        assert r.success is True
        assert r.branch_name == "feat-agdt"
        assert r.commit_hash == "abc123"
        assert r.worktree_key == "DFLY-1234"
        assert r.workflow_type == "review"
        assert r.error is None

    def test_failure_with_error(self):
        """Create with success=False and an error message."""
        r = PersistResult(success=False, error="something broke")
        assert r.success is False
        assert r.error == "something broke"

    def test_docstring_mentions_caller_responsibility(self):
        """Docstring must mention that callers are responsible for tracking."""
        assert "Callers are responsible" in PersistResult.__doc__
