"""Tests for the fix_markdown_deterministic.py CLI helper script."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "scripts"
    / "speckit-trigger"
    / "fix_markdown_deterministic.py"
)


def _load_module():
    """Load fix_markdown_deterministic.py as a module."""
    spec = importlib.util.spec_from_file_location("fix_markdown_deterministic", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {SCRIPT_PATH!s}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestFixMD040:
    """Tests for the MD040 fixer (fenced-code-language)."""

    def test_bare_backtick_fence_gets_text_language(self):
        mod = _load_module()
        lines = ["# Heading\n", "\n", "```\n", "some code\n", "```\n"]
        result = mod.fix_md040(lines)
        assert result[2] == "```text\n"
        # Closing fence unchanged
        assert result[4] == "```\n"

    def test_bare_tilde_fence_gets_text_language(self):
        mod = _load_module()
        lines = ["~~~\n", "code here\n", "~~~\n"]
        result = mod.fix_md040(lines)
        assert result[0] == "~~~text\n"

    def test_fence_with_language_unchanged(self):
        mod = _load_module()
        lines = ["```python\n", "print('hi')\n", "```\n"]
        result = mod.fix_md040(lines)
        assert result == lines

    def test_indented_bare_fence(self):
        mod = _load_module()
        lines = ["  ```\n", "  code\n", "  ```\n"]
        result = mod.fix_md040(lines)
        assert result[0] == "  ```text\n"

    def test_does_not_modify_content_inside_fence(self):
        """Lines inside a fenced block that look like fences are not touched."""
        mod = _load_module()
        lines = ["```python\n", "```\n", "nested example\n", "```\n"]
        result = mod.fix_md040(lines)
        # The inner ``` is content, should be unchanged
        assert result[1] == "```\n"

    def test_multiple_bare_fences(self):
        mod = _load_module()
        lines = [
            "```\n", "block 1\n", "```\n",
            "\n",
            "```\n", "block 2\n", "```\n",
        ]
        result = mod.fix_md040(lines)
        assert result[0] == "```text\n"
        assert result[4] == "```text\n"


class TestFixMD056:
    """Tests for the MD056 fixer (table-column-count)."""

    def test_table_with_consistent_columns_unchanged(self):
        mod = _load_module()
        lines = [
            "| A | B | C |\n",
            "|---|---|---|\n",
            "| 1 | 2 | 3 |\n",
        ]
        result = mod.fix_md056(lines)
        # Should be unchanged (all rows have 3 columns)
        assert result == lines

    def test_short_row_gets_padded(self):
        mod = _load_module()
        lines = [
            "| A | B | C |\n",
            "|---|---|---|\n",
            "| 1 | 2 |\n",
        ]
        result = mod.fix_md056(lines)
        # The data row should now have 3 columns
        assert result[2].count("|") == 4  # 3 columns = 4 pipes (outer + separators)

    def test_long_row_gets_truncated(self):
        mod = _load_module()
        lines = [
            "| A | B |\n",
            "|---|---|\n",
            "| 1 | 2 | 3 | 4 |\n",
        ]
        result = mod.fix_md056(lines)
        # The data row should be truncated to 2 columns
        assert result[2].count("|") == 3  # 2 columns = 3 pipes

    def test_does_not_modify_tables_inside_fences(self):
        mod = _load_module()
        lines = [
            "```text\n",
            "| A | B |\n",
            "| 1 |\n",
            "```\n",
        ]
        result = mod.fix_md056(lines)
        # Table inside fence should not be modified
        assert result[2] == "| 1 |\n"


class TestFixFile:
    """Tests for the fix_file() integration function."""

    def test_file_with_bare_fence_and_bad_table(self, tmp_path):
        mod = _load_module()
        md_file = tmp_path / "test.md"
        md_file.write_text(
            "# Test\n\n"
            "```\n"
            "code\n"
            "```\n\n"
            "| A | B | C |\n"
            "|---|---|---|\n"
            "| 1 | 2 |\n",
            encoding="utf-8",
        )
        modified = mod.fix_file(md_file)
        assert modified is True

        content = md_file.read_text(encoding="utf-8")
        assert "```text\n" in content
        # Table row should have been padded
        lines = content.splitlines()
        table_data_line = [l for l in lines if l.startswith("| 1")]
        assert len(table_data_line) == 1
        assert table_data_line[0].count("|") == 4

    def test_file_already_correct_not_modified(self, tmp_path):
        mod = _load_module()
        md_file = tmp_path / "clean.md"
        md_file.write_text(
            "# Clean\n\n```python\ncode\n```\n\n| A | B |\n|---|---|\n| 1 | 2 |\n",
            encoding="utf-8",
        )
        modified = mod.fix_file(md_file)
        assert modified is False

    def test_nonexistent_file_returns_false(self, tmp_path):
        mod = _load_module()
        modified = mod.fix_file(tmp_path / "nonexistent.md")
        assert modified is False
