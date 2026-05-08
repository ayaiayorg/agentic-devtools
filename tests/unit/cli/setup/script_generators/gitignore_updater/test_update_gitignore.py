"""Tests for update_gitignore."""

from agentic_devtools.cli.setup.script_generators.gitignore_updater import update_gitignore


class TestUpdateGitignore:
    """Tests for update_gitignore."""

    def test_replaces_agdt_dir_with_glob(self, tmp_path):
        """Replaces '.agdt/' with '.agdt/*'."""
        gi = tmp_path / ".gitignore"
        gi.write_text("node_modules/\n.agdt/\n*.log\n", encoding="utf-8")
        msg = update_gitignore(tmp_path)
        content = gi.read_text(encoding="utf-8")
        assert ".agdt/*" in content
        assert ".agdt/\n" not in content
        assert "updated" in msg

    def test_adds_negation_rule(self, tmp_path):
        """Adds negation rule for managed scripts."""
        gi = tmp_path / ".gitignore"
        gi.write_text(".agdt/\n", encoding="utf-8")
        update_gitignore(tmp_path)
        content = gi.read_text(encoding="utf-8")
        assert "!.agdt/agentic-devtools-*.py" in content

    def test_idempotent(self, tmp_path):
        """Running twice produces same result."""
        gi = tmp_path / ".gitignore"
        gi.write_text(".agdt/\n", encoding="utf-8")
        update_gitignore(tmp_path)
        first = gi.read_text(encoding="utf-8")
        update_gitignore(tmp_path)
        second = gi.read_text(encoding="utf-8")
        assert first == second

    def test_no_gitignore(self, tmp_path):
        """Returns info message when no .gitignore exists."""
        msg = update_gitignore(tmp_path)
        assert "No .gitignore" in msg

    def test_already_has_glob_and_negation(self, tmp_path):
        """Returns up-to-date message when already configured."""
        gi = tmp_path / ".gitignore"
        gi.write_text(".agdt/*\n!.agdt/agentic-devtools-*.py\n", encoding="utf-8")
        msg = update_gitignore(tmp_path)
        assert "up to date" in msg

    def test_preserves_other_rules(self, tmp_path):
        """Other gitignore rules are preserved."""
        gi = tmp_path / ".gitignore"
        gi.write_text("node_modules/\n.agdt/\n*.log\n", encoding="utf-8")
        update_gitignore(tmp_path)
        content = gi.read_text(encoding="utf-8")
        assert "node_modules/" in content
        assert "*.log" in content
