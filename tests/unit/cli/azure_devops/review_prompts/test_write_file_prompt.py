"""Tests for write_file_prompt function."""


class TestWriteFilePrompt:
    """Tests for write_file_prompt function."""

    def test_writes_prompt_file(self, tmp_path):
        """Test that prompt file is written correctly."""
        from agentic_devtools.cli.azure_devops.review_prompts import write_file_prompt

        result = write_file_prompt(
            file_path="/src/components/Button.tsx",
            change_type="edit",
            pr_id=123,
            file_content="code changes",
            threads=[],
            output_dir=tmp_path,
        )

        assert result.exists()
        assert result.suffix == ".md"
        content = result.read_text(encoding="utf-8")
        assert "# PR Review: /src/components/Button.tsx" in content
