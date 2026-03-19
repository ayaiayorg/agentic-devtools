"""Tests for agentic_devtools.skill_injector._get_source_dir."""

from unittest.mock import patch

from agentic_devtools.skill_injector import _get_source_dir


class TestGetSourceDir:
    """Tests for the _get_source_dir helper."""

    def test_returns_bundled_dir_when_md_files_exist(self, tmp_path):
        """Returns the _bundled_skills/<kind> dir when it contains .md files."""
        bundled = tmp_path / "agents"
        bundled.mkdir()
        (bundled / "test.agent.md").write_text("content", encoding="utf-8")

        with patch("agentic_devtools.skill_injector._BUNDLED_DIR", tmp_path):
            result = _get_source_dir("agents")

        assert result == bundled

    def test_falls_back_to_github_dir_for_editable_install(self, tmp_path):
        """Falls back to .github/<kind> when bundled dir has no .md files (editable install)."""
        import agentic_devtools.skill_injector as mod

        # Create a fake repo root with a .github/agents directory containing a .md file.
        repo_root = tmp_path / "repo"
        agents_dir = repo_root / ".github" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "from_github.agent.md").write_text("content", encoding="utf-8")

        # Create a fake bundled directory with no .md files so the fallback is exercised.
        bundled = tmp_path / "bundled"
        bundled_agents = bundled / "agents"
        bundled_agents.mkdir(parents=True, exist_ok=True)
        (bundled_agents / "__init__.py").write_text("", encoding="utf-8")

        # Point the module's __file__ at a fake skill_injector.py inside the fake repo root
        # so that _get_source_dir resolves .github/<kind> relative to repo_root.
        fake_file = repo_root / "agentic_devtools" / "skill_injector.py"
        fake_file.parent.mkdir(parents=True, exist_ok=True)
        fake_file.write_text("", encoding="utf-8")

        original_file = mod.__file__
        try:
            mod.__file__ = str(fake_file)
            with patch("agentic_devtools.skill_injector._BUNDLED_DIR", bundled):
                result = _get_source_dir("agents")
        finally:
            mod.__file__ = original_file

        assert result == agents_dir
        assert result.is_dir()

    def test_returns_none_when_both_paths_missing(self, tmp_path):
        """Returns None when neither bundled nor .github dir exists."""
        import agentic_devtools.skill_injector as mod

        bundled = tmp_path / "nonexistent"
        fake_file = tmp_path / "pkg" / "skill_injector.py"
        fake_file.parent.mkdir(parents=True, exist_ok=True)
        fake_file.write_text("", encoding="utf-8")

        original_file = mod.__file__
        try:
            mod.__file__ = str(fake_file)
            with patch("agentic_devtools.skill_injector._BUNDLED_DIR", bundled):
                result = _get_source_dir("agents")
        finally:
            mod.__file__ = original_file

        assert result is None
