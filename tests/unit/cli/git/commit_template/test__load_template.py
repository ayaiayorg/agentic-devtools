"""Tests for _load_template."""

from agentic_devtools.cli.git.commit_template import TEMPLATE_PATH, _load_template


class TestLoadTemplate:
    """Tests for _load_template."""

    def test_returns_content_for_valid_template(self, tmp_path):
        """Returns template content when file exists and is valid."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("{{ issueType }}: {{ commitMessageTitle }}", encoding="utf-8")
        result = _load_template(tmp_path)
        assert result == "{{ issueType }}: {{ commitMessageTitle }}"

    def test_returns_none_when_missing(self, tmp_path):
        """Returns None when template file does not exist."""
        result = _load_template(tmp_path)
        assert result is None

    def test_returns_none_for_empty_file(self, tmp_path, capsys):
        """Returns None and emits warning for empty file (FR-007)."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("", encoding="utf-8")
        result = _load_template(tmp_path)
        assert result is None
        assert "empty or whitespace-only" in capsys.readouterr().err

    def test_returns_none_for_whitespace_only(self, tmp_path, capsys):
        """Returns None and emits warning for whitespace-only file (FR-007)."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("   \n\t  \n", encoding="utf-8")
        result = _load_template(tmp_path)
        assert result is None
        assert "empty or whitespace-only" in capsys.readouterr().err

    def test_returns_none_for_syntax_error(self, tmp_path, capsys):
        """Returns None and emits warning for Jinja2 syntax error (FR-007)."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("{% if x %}", encoding="utf-8")  # unclosed if
        result = _load_template(tmp_path)
        assert result is None
        assert "syntax error" in capsys.readouterr().err

    def test_returns_none_for_read_error(self, tmp_path, capsys):
        """Returns None and emits warning when file cannot be read."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("content", encoding="utf-8")
        template_file.chmod(0o000)
        try:
            result = _load_template(tmp_path)
            assert result is None
            assert "Cannot read commit template" in capsys.readouterr().err
        finally:
            template_file.chmod(0o644)

    def test_zero_byte_file(self, tmp_path, capsys):
        """Zero-byte file emits appropriate warning (FR-007)."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.touch()
        result = _load_template(tmp_path)
        assert result is None
        assert "empty or whitespace-only" in capsys.readouterr().err
