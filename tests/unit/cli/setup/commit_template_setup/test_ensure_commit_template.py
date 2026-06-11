"""Tests for ensure_commit_template."""

from agentic_devtools.cli.git.commit_template import TEMPLATE_PATH
from agentic_devtools.cli.setup.commit_template_setup import (
    DEFAULT_TEMPLATE,
    ensure_commit_template,
)


class TestEnsureCommitTemplate:
    """Tests for ensure_commit_template."""

    def test_creates_template_when_missing(self, tmp_path):
        """Creates the default template when it does not exist (FR-001)."""
        result = ensure_commit_template(tmp_path)
        assert result is True
        template_file = tmp_path / TEMPLATE_PATH
        assert template_file.is_file()
        assert template_file.read_text(encoding="utf-8") == DEFAULT_TEMPLATE

    def test_does_not_overwrite_existing(self, tmp_path):
        """Does not overwrite an existing template (FR-002)."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("custom template", encoding="utf-8")
        result = ensure_commit_template(tmp_path)
        assert result is False
        assert template_file.read_text(encoding="utf-8") == "custom template"

    def test_creates_directory_structure(self, tmp_path):
        """Creates .agdt/config/ directory when missing (FR-008)."""
        config_dir = tmp_path / ".agdt" / "config"
        assert not config_dir.exists()
        ensure_commit_template(tmp_path)
        assert config_dir.is_dir()

    def test_returns_false_when_exists(self, tmp_path):
        """Returns False when template already exists."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("existing", encoding="utf-8")
        assert ensure_commit_template(tmp_path) is False

    def test_default_template_is_valid_jinja2(self, tmp_path):
        """The DEFAULT_TEMPLATE is syntactically valid Jinja2."""
        import jinja2

        env = jinja2.Environment(loader=jinja2.BaseLoader())
        # Should not raise
        env.parse(DEFAULT_TEMPLATE)
