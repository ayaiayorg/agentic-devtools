"""Tests for PatchOperation dataclass."""

from agentic_devtools.cli.azure_devops.status_cascade import PatchOperation


class TestPatchOperation:
    """Tests for PatchOperation dataclass."""

    def test_stores_thread_id(self):
        """Should store thread_id."""
        op = PatchOperation(thread_id=10, comment_id=20, new_content="content", thread_status="active")

        assert op.thread_id == 10

    def test_stores_comment_id(self):
        """Should store comment_id."""
        op = PatchOperation(thread_id=10, comment_id=20, new_content="content", thread_status="active")

        assert op.comment_id == 20

    def test_stores_new_content(self):
        """Should store new_content."""
        op = PatchOperation(thread_id=10, comment_id=20, new_content="my content", thread_status="active")

        assert op.new_content == "my content"

    def test_stores_thread_status(self):
        """Should store thread_status."""
        op = PatchOperation(thread_id=10, comment_id=20, new_content="content", thread_status="closed")

        assert op.thread_status == "closed"

    def test_equality(self):
        """Two PatchOperations with same fields should be equal."""
        op1 = PatchOperation(thread_id=1, comment_id=2, new_content="c", thread_status="active")
        op2 = PatchOperation(thread_id=1, comment_id=2, new_content="c", thread_status="active")

        assert op1 == op2

    def test_inequality_different_thread_status(self):
        """PatchOperations with different thread_status should not be equal."""
        op1 = PatchOperation(thread_id=1, comment_id=2, new_content="c", thread_status="active")
        op2 = PatchOperation(thread_id=1, comment_id=2, new_content="c", thread_status="closed")

        assert op1 != op2
