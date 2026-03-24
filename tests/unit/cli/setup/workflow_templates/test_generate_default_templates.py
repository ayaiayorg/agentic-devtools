"""Tests for agentic_devtools.cli.setup.workflow_templates.generate_default_templates."""

import logging
from unittest.mock import patch

import pytest

from agentic_devtools.cli.setup.workflow_templates import (
    _TEMPLATES_DIR,
    _read_template,
    generate_default_templates,
    list_available_templates,
)


class TestGenerateDefaultTemplates:
    """Tests for generate_default_templates."""

    def test_generates_all_files(self, tmp_path):
        """All three template files are written into an empty directory."""
        written = generate_default_templates(tmp_path)
        assert len(written) == 3
        for path in written:
            assert path.exists()
            assert path.parent == tmp_path

    def test_return_paths_inside_target(self, tmp_path):
        """Returned paths all reside inside target_dir."""
        written = generate_default_templates(tmp_path)
        for path in written:
            assert str(path).startswith(str(tmp_path))

    def test_content_matches_bundled_source(self, tmp_path):
        """Generated file content matches the bundled source file."""
        generate_default_templates(tmp_path)
        for template in list_available_templates():
            expected = (_TEMPLATES_DIR / template.filename).read_text(encoding="utf-8")
            actual = (tmp_path / template.filename).read_text(encoding="utf-8")
            assert actual == expected

    def test_creates_target_dir_when_missing(self, tmp_path):
        """target_dir is created (with parents) when it does not exist."""
        nested = tmp_path / "sub" / "dir"
        written = generate_default_templates(nested)
        assert nested.is_dir()
        assert len(written) == 3

    def test_no_clobber(self, tmp_path):
        """Existing files are not overwritten when overwrite=False."""
        sentinel = "DO NOT OVERWRITE"
        (tmp_path / "work-on-issue.py").write_text(sentinel, encoding="utf-8")

        written = generate_default_templates(tmp_path, overwrite=False)

        # Only the other two files should have been written.
        written_names = {p.name for p in written}
        assert "work-on-issue.py" not in written_names
        assert len(written) == 2

        # The pre-existing file is untouched.
        assert (tmp_path / "work-on-issue.py").read_text(encoding="utf-8") == sentinel

    def test_overwrite(self, tmp_path):
        """Existing files are replaced when overwrite=True."""
        sentinel = "OLD CONTENT"
        (tmp_path / "work-on-issue.py").write_text(sentinel, encoding="utf-8")

        written = generate_default_templates(tmp_path, overwrite=True)

        assert len(written) == 3
        assert (tmp_path / "work-on-issue.py").read_text(encoding="utf-8") != sentinel

    def test_all_exist_no_overwrite_returns_empty(self, tmp_path):
        """When all files exist and overwrite=False, return list is empty."""
        generate_default_templates(tmp_path)
        written = generate_default_templates(tmp_path, overwrite=False)
        assert written == []

    def test_logs_info_for_written_files(self, tmp_path, caplog):
        """Info-level messages are logged for each written file."""
        with caplog.at_level(logging.DEBUG, logger="agentic_devtools.cli.setup.workflow_templates"):
            generate_default_templates(tmp_path)

        info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert len(info_messages) == 3
        for msg in info_messages:
            assert msg.startswith("Generated template: ")

    def test_logs_debug_for_skipped_files(self, tmp_path, caplog):
        """Debug-level messages are logged for skipped files."""
        generate_default_templates(tmp_path)
        caplog.clear()

        with caplog.at_level(logging.DEBUG, logger="agentic_devtools.cli.setup.workflow_templates"):
            generate_default_templates(tmp_path, overwrite=False)

        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_messages) == 3
        for msg in debug_messages:
            assert "already exists" in msg


class TestReadTemplate:
    """Tests for _read_template helper."""

    def test_reads_existing_template(self):
        """Returns content of a bundled template file."""
        content = _read_template("README.md")
        assert "Workflow Templates" in content

    def test_raises_for_missing_template(self, tmp_path):
        """Raises FileNotFoundError with descriptive message when template is missing."""
        with patch("agentic_devtools.cli.setup.workflow_templates._TEMPLATES_DIR", tmp_path):
            with pytest.raises(FileNotFoundError, match="Bundled template 'missing.py' not found"):
                _read_template("missing.py")
