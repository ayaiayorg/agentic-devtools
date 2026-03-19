"""Tests for agentic_devtools.skill_injector._list_md_files."""

from agentic_devtools.skill_injector import _list_md_files


class TestListMdFiles:
    """Tests for the _list_md_files helper."""

    def test_agents_returns_all_non_hidden_md_files(self, tmp_path):
        """For agents, returns all non-hidden *.md files."""
        (tmp_path / "a.agent.md").write_text("content", encoding="utf-8")
        (tmp_path / "readme.md").write_text("content", encoding="utf-8")
        (tmp_path / ".hidden.agent.md").write_text("content", encoding="utf-8")
        (tmp_path / "notes.txt").write_text("content", encoding="utf-8")

        result = _list_md_files(tmp_path, "agents")
        names = [p.name for p in result]

        assert "a.agent.md" in names
        assert "readme.md" in names
        assert ".hidden.agent.md" not in names
        assert "notes.txt" not in names

    def test_prompts_returns_only_prompt_md_files(self, tmp_path):
        """For prompts, returns only *.prompt.md files excluding hidden ones."""
        (tmp_path / "a.prompt.md").write_text("content", encoding="utf-8")
        (tmp_path / "other.md").write_text("content", encoding="utf-8")
        (tmp_path / ".hidden.prompt.md").write_text("content", encoding="utf-8")

        result = _list_md_files(tmp_path, "prompts")
        names = [p.name for p in result]

        assert "a.prompt.md" in names
        assert "other.md" not in names
        assert ".hidden.prompt.md" not in names

    def test_returns_sorted_list(self, tmp_path):
        """Returns files in sorted order."""
        (tmp_path / "c.agent.md").write_text("", encoding="utf-8")
        (tmp_path / "a.agent.md").write_text("", encoding="utf-8")
        (tmp_path / "b.agent.md").write_text("", encoding="utf-8")

        result = _list_md_files(tmp_path, "agents")
        names = [p.name for p in result]

        assert names == ["a.agent.md", "b.agent.md", "c.agent.md"]

    def test_empty_directory(self, tmp_path):
        """Returns empty list for an empty directory."""
        result = _list_md_files(tmp_path, "agents")
        assert result == []

    def test_skips_directories(self, tmp_path):
        """Skips subdirectories even if they have .md suffix."""
        subdir = tmp_path / "subdir.md"
        subdir.mkdir()
        (tmp_path / "file.agent.md").write_text("", encoding="utf-8")

        result = _list_md_files(tmp_path, "agents")
        names = [p.name for p in result]

        assert "file.agent.md" in names
        assert "subdir.md" not in names

    def test_recurses_into_subdirectories(self, tmp_path):
        """Returns files from subdirectories, preserving relative paths."""
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (tmp_path / "root.agent.md").write_text("", encoding="utf-8")
        (subdir / "nested.agent.md").write_text("", encoding="utf-8")

        result = _list_md_files(tmp_path, "agents")
        rel_paths = [str(p.relative_to(tmp_path)) for p in result]

        assert "root.agent.md" in rel_paths
        assert str(subdir.relative_to(tmp_path) / "nested.agent.md") in rel_paths

    def test_excludes_files_in_hidden_subdirectories(self, tmp_path):
        """Files inside hidden subdirectories are excluded."""
        hidden = tmp_path / ".hidden_dir"
        hidden.mkdir()
        (hidden / "secret.agent.md").write_text("", encoding="utf-8")
        (tmp_path / "visible.agent.md").write_text("", encoding="utf-8")

        result = _list_md_files(tmp_path, "agents")
        names = [p.name for p in result]

        assert "visible.agent.md" in names
        assert "secret.agent.md" not in names
