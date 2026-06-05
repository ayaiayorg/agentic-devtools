"""Tests for ExclusionContext dataclass."""

from agentic_devtools.cli.ci.pipeline.exclusion import ExclusionContext


class TestExclusionContext:
    """Tests for ExclusionContext construction and merge behavior."""

    def test_construction_empty(self) -> None:
        """Default construction creates empty resolved_comment_ids set."""
        ctx = ExclusionContext()
        assert ctx.resolved_comment_ids == set()

    def test_construction_with_ids(self) -> None:
        """Construction with explicit IDs stores them."""
        ctx = ExclusionContext(resolved_comment_ids={1, 2, 3})
        assert ctx.resolved_comment_ids == {1, 2, 3}

    def test_merge_combines_ids(self) -> None:
        """Merge combines resolved_comment_ids from both contexts."""
        ctx1 = ExclusionContext(resolved_comment_ids={1, 2})
        ctx2 = ExclusionContext(resolved_comment_ids={3, 4})
        merged = ctx1.merge(ctx2)
        assert merged.resolved_comment_ids == {1, 2, 3, 4}

    def test_merge_with_overlap(self) -> None:
        """Merge with overlapping IDs deduplicates."""
        ctx1 = ExclusionContext(resolved_comment_ids={1, 2})
        ctx2 = ExclusionContext(resolved_comment_ids={2, 3})
        merged = ctx1.merge(ctx2)
        assert merged.resolved_comment_ids == {1, 2, 3}

    def test_merge_does_not_mutate_originals(self) -> None:
        """Merge returns a new instance without mutating originals."""
        ctx1 = ExclusionContext(resolved_comment_ids={1})
        ctx2 = ExclusionContext(resolved_comment_ids={2})
        merged = ctx1.merge(ctx2)
        assert ctx1.resolved_comment_ids == {1}
        assert ctx2.resolved_comment_ids == {2}
        assert merged.resolved_comment_ids == {1, 2}
