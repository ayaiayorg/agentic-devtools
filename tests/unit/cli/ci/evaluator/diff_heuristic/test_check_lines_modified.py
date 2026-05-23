"""Tests for check_lines_modified() diff heuristic."""

from agentic_devtools.cli.ci.evaluator.diff_heuristic import check_lines_modified

_SAMPLE_DIFF = """\
diff --git a/src/main.py b/src/main.py
index abc1234..def5678 100644
--- a/src/main.py
+++ b/src/main.py
@@ -10,3 +10,4 @@ def hello():
     print("hello")
+    print("world")
     return True
@@ -20,2 +21,3 @@ def goodbye():
     print("bye")
+    print("farewell")
     return False
"""


class TestCheckLinesModified:
    """Tests for check_lines_modified."""

    def test_line_modified(self):
        """Line 11 was added in the diff."""
        assert check_lines_modified(_SAMPLE_DIFF, "src/main.py", 11, 11) is True

    def test_line_not_modified(self):
        """Line 10 is context, not modified."""
        assert check_lines_modified(_SAMPLE_DIFF, "src/main.py", 10, 10) is False

    def test_range_overlaps_modification(self):
        """Range 10-12 overlaps with the added line 11."""
        assert check_lines_modified(_SAMPLE_DIFF, "src/main.py", 10, 12) is True

    def test_different_file(self):
        """Different file path doesn't match."""
        assert check_lines_modified(_SAMPLE_DIFF, "src/other.py", 11, 11) is False

    def test_pr_level_comment(self):
        """PR-level comments (start_line=None) always return False."""
        assert check_lines_modified(_SAMPLE_DIFF, "src/main.py", None, None) is False

    def test_end_line_defaults_to_start(self):
        """When end_line is None, it defaults to start_line."""
        assert check_lines_modified(_SAMPLE_DIFF, "src/main.py", 11, None) is True

    def test_second_hunk(self):
        """Line 22 was added in the second hunk."""
        assert check_lines_modified(_SAMPLE_DIFF, "src/main.py", 22, 22) is True

    def test_empty_diff(self):
        """Empty diff always returns False."""
        assert check_lines_modified("", "src/main.py", 10, 10) is False

    def test_deletion_only_line_is_not_marked_modified(self):
        """Deletion lines do not count as modified target lines in new-file numbering."""
        deletion_diff = """\
diff --git a/src/main.py b/src/main.py
index abc1234..def5678 100644
--- a/src/main.py
+++ b/src/main.py
@@ -10,2 +10,1 @@ def hello():
-    print("old")
     return True
"""
        assert check_lines_modified(deletion_diff, "src/main.py", 10, 10) is False

    def test_path_prefix_match_does_not_match_different_file(self):
        """Exact b/ path match avoids matching similarly-prefixed file paths."""
        prefix_diff = """\
diff --git a/src/app.py.old b/src/app.py.old
index abc1234..def5678 100644
--- a/src/app.py.old
+++ b/src/app.py.old
@@ -1,1 +1,2 @@
 print("old")
+print("new")
"""
        assert check_lines_modified(prefix_diff, "src/app.py", 2, 2) is False

    def test_malformed_diff_header_is_ignored(self):
        """Malformed diff headers should not be treated as a target file match."""
        malformed_diff = """\
diff --git not-a-valid-header
@@ -1,1 +1,2 @@
+print("new")
"""
        assert check_lines_modified(malformed_diff, "src/main.py", 1, 1) is False
