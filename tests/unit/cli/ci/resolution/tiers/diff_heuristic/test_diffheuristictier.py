"""Tests for Tier 3: DiffHeuristicTier."""

from dataclasses import dataclass, field

from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict
from agentic_devtools.cli.ci.resolution.tiers.diff_heuristic import DiffHeuristicTier


@dataclass(frozen=True)
class _MockComment:
    body: str = "test"
    created_at: str = "2026-01-01T00:00:00Z"
    author_login: str | None = None


@dataclass(frozen=True)
class _MockThread:
    thread_id: str = "PRT_123"
    file_path: str | None = "src/main.py"
    start_line: int | None = 10
    end_line: int | None = 15
    is_outdated: bool | None = False
    comments: list = field(default_factory=list)
    originating_review_commit_oid: str = "abc123"


@dataclass(frozen=True)
class _MockContext:
    diff_text: str = ""
    head_commit_oid: str = "head123"


_SAMPLE_DIFF = """\
diff --git a/src/main.py b/src/main.py
index abc123..def456 100644
--- a/src/main.py
+++ b/src/main.py
@@ -8,7 +8,7 @@
 line 8 context
 line 9 context
-old line 10
+new line 10
 line 11 context
 line 12 context
"""


class TestDiffHeuristicTier:
    """Tests for the diff heuristic tier."""

    def test_resolves_when_lines_modified(self) -> None:
        tier = DiffHeuristicTier()
        thread = _MockThread(file_path="src/main.py", start_line=10, end_line=10)
        context = _MockContext(diff_text=_SAMPLE_DIFF)
        result = tier.evaluate(thread, context)
        assert result is not None
        assert result.verdict == ResolutionVerdict.RESOLVE
        assert result.confidence == "medium"
        assert result.tier_name == "diff_heuristic"

    def test_returns_none_when_lines_not_modified(self) -> None:
        tier = DiffHeuristicTier()
        thread = _MockThread(file_path="src/main.py", start_line=1, end_line=5)
        context = _MockContext(diff_text=_SAMPLE_DIFF)
        result = tier.evaluate(thread, context)
        assert result is None

    def test_skips_pr_level_comments(self) -> None:
        """PR-level comments have no file/line anchor."""
        tier = DiffHeuristicTier()
        thread = _MockThread(file_path=None, start_line=None, end_line=None)
        context = _MockContext(diff_text=_SAMPLE_DIFF)
        result = tier.evaluate(thread, context)
        assert result is None

    def test_skips_when_no_start_line(self) -> None:
        tier = DiffHeuristicTier()
        thread = _MockThread(file_path="src/main.py", start_line=None)
        context = _MockContext(diff_text=_SAMPLE_DIFF)
        result = tier.evaluate(thread, context)
        assert result is None

    def test_handles_multi_line_range_overlap(self) -> None:
        """Any overlap between modified lines and comment range resolves."""
        tier = DiffHeuristicTier()
        thread = _MockThread(file_path="src/main.py", start_line=8, end_line=12)
        context = _MockContext(diff_text=_SAMPLE_DIFF)
        result = tier.evaluate(thread, context)
        assert result is not None
        assert result.verdict == ResolutionVerdict.RESOLVE

    def test_name(self) -> None:
        tier = DiffHeuristicTier()
        assert tier.name == "diff_heuristic"
