"""Tests for write_file_prompt function."""


class TestWriteFilePrompt:
    """Tests for _write_file_prompt function."""

    def test_writes_prompt_file(self, tmp_path, monkeypatch):
        """Test writes prompt file with correct content."""
        from agentic_devtools.cli.azure_devops.review_commands import _write_file_prompt

        # Create the file on disk so full content section can read it
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.ts"
        test_file.write_text("const x = 1;", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        file_detail = {
            "path": "/src/test.ts",
            "changeType": "edit",
        }
        threads = [{"id": 1, "comments": [{"content": "test comment"}]}]

        result = _write_file_prompt(tmp_path, file_detail, threads)

        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "# File Review: /src/test.ts" in content
        assert "## File Diff Object" in content
        assert "## Existing Threads" in content
        assert "## Full File Content" in content
        assert "const x = 1;" in content

    def test_handles_empty_threads(self, tmp_path):
        """Test handles empty threads list."""
        from agentic_devtools.cli.azure_devops.review_commands import _write_file_prompt

        file_detail = {"path": "/src/test.ts"}

        result = _write_file_prompt(tmp_path, file_detail, [])

        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "[]" in content
        assert "## Full File Content" in content

    def test_deleted_file_shows_delete_note(self, tmp_path):
        """Test deleted file shows the delete note."""
        from agentic_devtools.cli.azure_devops.review_commands import _write_file_prompt

        file_detail = {
            "path": "/src/old.ts",
            "changeType": "D",
        }

        result = _write_file_prompt(tmp_path, file_detail, [])

        content = result.read_text(encoding="utf-8")
        assert "## Full File Content" in content
        assert "_This file was deleted in this change._" in content
