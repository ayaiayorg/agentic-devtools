"""Tests for agentic_devtools.cli.pr_template.init_pr_template."""

from unittest.mock import patch

from agentic_devtools.cli import pr_template


class TestInitPrTemplate:
    """Tests for init_pr_template()."""

    @patch("agentic_devtools.cli.pr_template.get_template_path")
    def test_creates_template_when_missing(self, mock_path, tmp_path, capsys):
        """Happy path: creates template when file doesn't exist (FR-001)."""
        template_file = tmp_path / ".agdt" / "config" / "pull-request-template.j2"
        mock_path.return_value = template_file

        pr_template.init_pr_template()

        assert template_file.exists()
        content = template_file.read_text(encoding="utf-8")
        assert "{{ fullCommitMessage }}" in content
        assert "Checkliste" in content
        captured = capsys.readouterr()
        assert "Created PR template" in captured.out

    @patch("agentic_devtools.cli.pr_template.get_template_path")
    def test_skips_when_template_exists(self, mock_path, tmp_path, capsys):
        """Does not overwrite existing template (FR-002)."""
        template_file = tmp_path / "template.md"
        template_file.write_text("Custom content", encoding="utf-8")
        mock_path.return_value = template_file

        pr_template.init_pr_template()

        assert template_file.read_text(encoding="utf-8") == "Custom content"
        captured = capsys.readouterr()
        assert "already exists" in captured.out

    @patch("agentic_devtools.cli.pr_template.get_template_path")
    def test_creates_parent_directories(self, mock_path, tmp_path):
        """Creates parent directories if missing."""
        template_file = tmp_path / "deep" / "nested" / "dir" / "template.md"
        mock_path.return_value = template_file

        pr_template.init_pr_template()

        assert template_file.exists()

    @patch("agentic_devtools.cli.pr_template.get_template_path")
    def test_idempotent_multiple_runs(self, mock_path, tmp_path):
        """Multiple runs don't change the file (FR-002)."""
        template_file = tmp_path / "template.md"
        mock_path.return_value = template_file

        pr_template.init_pr_template()
        first_content = template_file.read_text(encoding="utf-8")

        pr_template.init_pr_template()
        second_content = template_file.read_text(encoding="utf-8")

        assert first_content == second_content

    @patch("agentic_devtools.cli.pr_template.get_template_path")
    def test_does_not_overwrite_customized_template(self, mock_path, tmp_path):
        """User-customized template is never overwritten (FR-002)."""
        template_file = tmp_path / "template.md"
        custom_content = "# My Custom Template\n\n{{fullCommitMessage}}\n"
        template_file.write_text(custom_content, encoding="utf-8")
        mock_path.return_value = template_file

        pr_template.init_pr_template()

        assert template_file.read_text(encoding="utf-8") == custom_content

    @patch("agentic_devtools.cli.pr_template.get_template_path")
    def test_default_content_has_all_checklist_sections(self, mock_path, tmp_path):
        """Default template includes all required sections."""
        template_file = tmp_path / "template.md"
        mock_path.return_value = template_file

        pr_template.init_pr_template()

        content = template_file.read_text(encoding="utf-8")
        assert "Getestet" in content
        assert "Database Schema Changes" in content
        assert "Mgmt-CLI Updates" in content
        assert "Workbench Infrastruktur Updates" in content
        assert "Infrastruktur Kommunikation" in content
        assert "Dokumentation" in content
        assert "Zusatzinformationen" in content
