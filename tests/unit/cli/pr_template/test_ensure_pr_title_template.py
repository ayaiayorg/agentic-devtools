"""Tests for agentic_devtools.cli.pr_template.ensure_pr_title_template."""

from agentic_devtools.cli.pr_template import PR_TITLE_TEMPLATE_PATH, ensure_pr_title_template


class TestEnsurePrTitleTemplate:
    """Tests for ensure_pr_title_template()."""

    def test_creates_template_when_missing(self, tmp_path):
        """Creates default PR title template when it does not exist."""
        result = ensure_pr_title_template(tmp_path)

        assert result is True
        template_path = tmp_path / PR_TITLE_TEMPLATE_PATH
        assert template_path.exists()
        content = template_path.read_text(encoding="utf-8")
        assert "{{ issueType }}" in content
        assert "{{ issueKey }}" in content
        assert "{{ commitMessageTitle }}" in content

    def test_does_not_overwrite_existing(self, tmp_path):
        """Does not overwrite an existing template."""
        template_path = tmp_path / PR_TITLE_TEMPLATE_PATH
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text("custom template", encoding="utf-8")

        result = ensure_pr_title_template(tmp_path)

        assert result is False
        assert template_path.read_text(encoding="utf-8") == "custom template"

    def test_creates_parent_directories(self, tmp_path):
        """Creates parent directories if they don't exist."""
        result = ensure_pr_title_template(tmp_path)

        assert result is True
        template_path = tmp_path / PR_TITLE_TEMPLATE_PATH
        assert template_path.parent.is_dir()
