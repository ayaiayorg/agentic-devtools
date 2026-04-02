"""Tests for build_full_file_content_section function."""

from unittest.mock import patch


class TestBuildFullFileContentSection:
    """Tests for build_full_file_content_section function."""

    def test_deleted_file_returns_delete_note(self):
        """Test that deleted files return a delete note."""
        from agentic_devtools.cli.azure_devops.review_helpers import build_full_file_content_section

        result = build_full_file_content_section("/src/old.ts", "delete")

        assert "## Full File Content" in result
        assert "_This file was deleted in this change._" in result

    def test_binary_file_returns_binary_note(self):
        """Test that binary files return a binary note."""
        from agentic_devtools.cli.azure_devops.review_helpers import build_full_file_content_section

        result = build_full_file_content_section("/assets/logo.png", "add")

        assert "## Full File Content" in result
        assert "_Binary file — content not included._" in result

    def test_file_not_on_disk_returns_not_found_note(self, tmp_path):
        """Test that missing files return a not-found note."""
        from agentic_devtools.cli.azure_devops.review_helpers import build_full_file_content_section

        result = build_full_file_content_section("/nonexistent/file.ts", "edit", repo_root=tmp_path)

        assert "## Full File Content" in result
        assert "_File not found on disk._" in result

    def test_file_over_size_limit_returns_too_large_note(self, tmp_path):
        """Test that files over the size limit return a too-large note."""
        from agentic_devtools.cli.azure_devops.review_helpers import (
            MAX_FILE_CONTENT_SIZE,
            build_full_file_content_section,
        )

        large_file = tmp_path / "large.ts"
        large_file.write_bytes(b"x" * (MAX_FILE_CONTENT_SIZE + 1))

        result = build_full_file_content_section("large.ts", "edit", repo_root=tmp_path)
        joined = "\n".join(result)

        assert "## Full File Content" in joined
        assert "_File too large" in joined
        assert f"Threshold: {MAX_FILE_CONTENT_SIZE} bytes._" in joined

    def test_normal_file_returns_content_in_fenced_block(self, tmp_path):
        """Test that a normal file returns content in a fenced code block."""
        from agentic_devtools.cli.azure_devops.review_helpers import build_full_file_content_section

        test_file = tmp_path / "app.ts"
        test_file.write_text("const x = 1;", encoding="utf-8")

        result = build_full_file_content_section("app.ts", "edit", repo_root=tmp_path)

        assert "## Full File Content" in result
        assert "```typescript" in result
        assert "const x = 1;" in result
        assert result[-1] == "```"

    def test_unknown_extension_returns_content_with_no_language(self, tmp_path):
        """Test that unknown extension uses empty language identifier."""
        from agentic_devtools.cli.azure_devops.review_helpers import build_full_file_content_section

        test_file = tmp_path / "data.xyz"
        test_file.write_text("some data", encoding="utf-8")

        result = build_full_file_content_section("data.xyz", "edit", repo_root=tmp_path)

        assert "## Full File Content" in result
        assert "```\n" in "\n".join(result) or "```" in result
        assert "some data" in result

    def test_file_read_error_returns_could_not_read_note(self, tmp_path):
        """Test that OSError during read returns a could-not-read note."""
        from agentic_devtools.cli.azure_devops.review_helpers import build_full_file_content_section

        test_file = tmp_path / "error.ts"
        test_file.write_text("content", encoding="utf-8")

        with patch("agentic_devtools.cli.azure_devops.review_helpers.Path.read_text", side_effect=OSError("denied")):
            result = build_full_file_content_section("error.ts", "edit", repo_root=tmp_path)

        assert "## Full File Content" in result
        assert "_File could not be read._" in result

    def test_file_exactly_at_threshold_is_included(self, tmp_path):
        """Test that a file exactly at 51200 bytes is included."""
        from agentic_devtools.cli.azure_devops.review_helpers import (
            MAX_FILE_CONTENT_SIZE,
            build_full_file_content_section,
        )

        exact_file = tmp_path / "exact.py"
        exact_file.write_bytes(b"x" * MAX_FILE_CONTENT_SIZE)

        result = build_full_file_content_section("exact.py", "edit", repo_root=tmp_path)

        assert "## Full File Content" in result
        assert "```python" in result
        assert "_File too large" not in result

    def test_empty_path_returns_not_found(self):
        """Test that empty file path returns not-found note."""
        from agentic_devtools.cli.azure_devops.review_helpers import build_full_file_content_section

        result = build_full_file_content_section("", "edit")

        assert "_File not found on disk._" in result

    def test_leading_slash_is_stripped(self, tmp_path):
        """Test that leading slash is stripped for path resolution."""
        from agentic_devtools.cli.azure_devops.review_helpers import build_full_file_content_section

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "app.py"
        test_file.write_text("print('hello')", encoding="utf-8")

        result = build_full_file_content_section("/src/app.py", "edit", repo_root=tmp_path)

        assert "## Full File Content" in result
        assert "```python" in result
        assert "print('hello')" in result

    def test_rename_change_type_includes_content(self, tmp_path):
        """Test that rename change type treats file as existing."""
        from agentic_devtools.cli.azure_devops.review_helpers import build_full_file_content_section

        test_file = tmp_path / "renamed.ts"
        test_file.write_text("export const a = 1;", encoding="utf-8")

        result = build_full_file_content_section("renamed.ts", "rename", repo_root=tmp_path)

        assert "## Full File Content" in result
        assert "```typescript" in result
        assert "export const a = 1;" in result

    def test_stat_oserror_returns_could_not_read(self, tmp_path):
        """Test that OSError during stat returns a could-not-read note."""
        from pathlib import Path as PathCls

        from agentic_devtools.cli.azure_devops.review_helpers import build_full_file_content_section

        test_file = tmp_path / "stat_error.ts"
        test_file.write_text("content", encoding="utf-8")

        original_stat = PathCls.stat

        def counting_stat(self_path, *args, **kwargs):
            if self_path.name == "stat_error.ts":
                raise OSError("perm")
            return original_stat(self_path, *args, **kwargs)

        with patch.object(PathCls, "stat", counting_stat):
            result = build_full_file_content_section("stat_error.ts", "edit", repo_root=tmp_path)

        assert "## Full File Content" in result
        assert "_File could not be read._" in result

    def test_content_with_triple_backticks_uses_longer_fence(self, tmp_path):
        """Test fence delimiter expands when content already contains triple backticks."""
        from agentic_devtools.cli.azure_devops.review_helpers import build_full_file_content_section

        test_file = tmp_path / "snippet.md"
        test_file.write_text("before\n```python\nprint('x')\n```\nafter", encoding="utf-8")

        result = build_full_file_content_section("snippet.md", "edit", repo_root=tmp_path)

        assert "````markdown" in result
        assert result[-1] == "````"

    def test_path_traversal_outside_repo_root_is_blocked(self, tmp_path):
        """Test path traversal attempts outside repo root are blocked."""
        from agentic_devtools.cli.azure_devops.review_helpers import build_full_file_content_section

        outside_file = tmp_path.parent / "outside.txt"
        outside_file.write_text("secret", encoding="utf-8")

        result = build_full_file_content_section("../outside.txt", "edit", repo_root=tmp_path)

        assert "## Full File Content" in result
        assert "_File path is outside repository root._" in result
        assert "secret" not in result
