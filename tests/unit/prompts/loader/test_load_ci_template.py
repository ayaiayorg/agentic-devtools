"""Tests for load_ci_template() function."""

from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_devtools.prompts.loader import load_ci_template


class TestLoadCITemplate:
    """Tests for loading CI comment templates."""

    def test_loads_timeout_template(self) -> None:
        content = load_ci_template("timeout-comment.md")
        assert "{{pr_number}}" in content
        assert "{{head_sha}}" in content
        assert "Timeout" in content

    def test_loads_exhausted_template(self) -> None:
        content = load_ci_template("exhausted-comment.md")
        assert "{{dispatch_count}}" in content
        assert "Exhausted" in content

    def test_loads_merge_failed_template(self) -> None:
        content = load_ci_template("merge-failed-comment.md")
        assert "{{error_message}}" in content
        assert "Merge Failed" in content

    def test_loads_ready_no_merge_template(self) -> None:
        content = load_ci_template("ready-no-merge-comment.md")
        assert "ai-auto-merge-allowed" in content

    def test_returns_raw_string_without_substitution(self) -> None:
        """Templates are returned as raw strings with {{variables}} intact."""
        content = load_ci_template("timeout-comment.md")
        # Variables should NOT be substituted
        assert "{{timeout_minutes}}" in content

    def test_missing_template_raises_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError, match="CI template not found"):
            load_ci_template("nonexistent-template.md")

    def test_rejects_path_separator_in_template_name(self) -> None:
        with pytest.raises(ValueError, match="must be a simple filename"):
            load_ci_template("../loader.py")

    def test_rejects_backslash_in_template_name(self) -> None:
        with pytest.raises(ValueError, match="must be a simple filename"):
            load_ci_template("..\\loader.py")

    def test_rejects_forward_slash_subdirectory(self) -> None:
        with pytest.raises(ValueError, match="must be a simple filename"):
            load_ci_template("subdir/template.md")

    def test_rejects_resolved_path_escaping_ci_directory(self) -> None:
        """Cover the is_relative_to guard via mocked is_relative_to."""
        with patch.object(Path, "is_relative_to", return_value=False):
            with pytest.raises(ValueError, match="escapes prompts/ci directory"):
                load_ci_template("safe-name.md")
