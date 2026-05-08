"""Tests for comment_key function."""

from agentic_devtools.cli.azure_devops.finalization.models import EligibleComment, comment_key


class TestCommentKey:
    """Tests for comment_key function."""

    def test_returns_tuple_of_thread_and_comment_id(self):
        """Should return (thread_id, comment_id) tuple."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=3,
            marker_type="file-summary",
            marker_data={},
            current_content="content",
        )
        assert comment_key(comment) == (10, 3)

    def test_different_threads_same_comment_id_produce_different_keys(self):
        """Composite key must distinguish comments with the same comment_id in different threads."""
        c1 = EligibleComment(thread_id=10, comment_id=1, marker_type="file-summary", marker_data={}, current_content="a")
        c2 = EligibleComment(thread_id=20, comment_id=1, marker_type="file-summary", marker_data={}, current_content="b")
        assert comment_key(c1) != comment_key(c2)

    def test_same_thread_different_comment_ids_produce_different_keys(self):
        """Composite key must distinguish comments within the same thread."""
        c1 = EligibleComment(thread_id=10, comment_id=1, marker_type="file-summary", marker_data={}, current_content="a")
        c2 = EligibleComment(thread_id=10, comment_id=2, marker_type="file-summary", marker_data={}, current_content="b")
        assert comment_key(c1) != comment_key(c2)

    def test_usable_as_dict_key(self):
        """CommentKey tuples must be usable as dictionary keys."""
        comment = EligibleComment(thread_id=5, comment_id=7, marker_type="x", marker_data={}, current_content="")
        d: dict = {comment_key(comment): "value"}
        assert d[(5, 7)] == "value"
