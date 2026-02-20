"""Tests for write_file_prompt function."""


class TestWriteFilePrompt:
    """Tests for _write_file_prompt function."""

    def test_writes_prompt_file(self, tmp_path):
        """Test writes prompt file with correct content."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import _write_file_prompt

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

    def test_handles_empty_threads(self, tmp_path):
        """Test handles empty threads list."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import _write_file_prompt

        file_detail = {"path": "/src/test.ts"}

        result = _write_file_prompt(tmp_path, file_detail, [])

        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "[]" in content
