"""Tests for _write_unchanged_file_prompt() helper."""

from agentic_devtools.cli.azure_devops.review_commands import _write_unchanged_file_prompt
from agentic_devtools.cli.azure_devops.review_state import FileEntry, ReviewStatus


class TestWriteUnchangedFilePrompt:
    """Tests for _write_unchanged_file_prompt()."""

    def test_writes_prompt_with_prior_entry(self, tmp_path):
        """Test writes a simplified prompt when prior entry exists."""
        prior = FileEntry(
            threadId=100,
            commentId=200,
            folder="src",
            fileName="app.ts",
            status=ReviewStatus.APPROVED.value,
            summary="Looks good overall.",
        )
        file_detail = {"path": "/src/app.ts", "changeType": "edit"}

        result = _write_unchanged_file_prompt(tmp_path, file_detail, prior)

        assert result.exists()
        content = result.read_text()
        assert "# File Review: /src/app.ts" in content
        assert "no changes since last review" in content
        assert f"**Prior review status:** {ReviewStatus.APPROVED.value}" in content
        assert "**Prior review summary:** Looks good overall." in content
        assert "only submit" in content
        assert "differs" in content

    def test_writes_prompt_without_prior_entry(self, tmp_path):
        """Test writes a simplified prompt when prior entry is None."""
        file_detail = {"path": "/src/helper.py", "changeType": "edit"}

        result = _write_unchanged_file_prompt(tmp_path, file_detail, None)

        assert result.exists()
        content = result.read_text()
        assert "# File Review: /src/helper.py" in content
        assert "no changes since last review" in content
        assert "**Prior review status:** unknown" in content
        assert "Prior review summary" not in content

    def test_writes_prompt_without_summary(self, tmp_path):
        """Test prompt excludes summary when prior entry has no summary."""
        prior = FileEntry(
            threadId=100,
            commentId=200,
            folder="src",
            fileName="app.ts",
            status=ReviewStatus.NEEDS_WORK.value,
            summary=None,
        )
        file_detail = {"path": "/src/app.ts", "changeType": "edit"}

        result = _write_unchanged_file_prompt(tmp_path, file_detail, prior)

        content = result.read_text()
        assert f"**Prior review status:** {ReviewStatus.NEEDS_WORK.value}" in content
        assert "Prior review summary" not in content

    def test_filename_uses_convert_to_prompt_filename(self, tmp_path):
        """Test output filename is derived from the file path."""
        file_detail = {"path": "/src/deep/nested/file.ts", "changeType": "edit"}

        result = _write_unchanged_file_prompt(tmp_path, file_detail, None)

        # The filename should follow the convert_to_prompt_filename convention
        assert result.parent == tmp_path
        assert result.suffix == ".md"
        assert result.name.startswith("file-")
