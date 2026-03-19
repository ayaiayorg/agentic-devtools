"""Tests for agentic_devtools.skill_injector.inject_skills."""

from unittest.mock import patch

from agentic_devtools.skill_injector import inject_skills


class TestInjectSkills:
    """Tests for the inject_skills function."""

    @staticmethod
    def _source_selector(agents_source, prompts_source):
        """Return a side_effect function for _get_source_dir(kind)."""

        def _select(kind):
            if kind == "agents":
                return agents_source
            return prompts_source

        return _select

    def test_returns_false_when_git_root_is_none(self):
        """Returns False when git_root is None."""
        assert inject_skills(None) is False

    def test_creates_agdt_dirs_if_missing(self, tmp_path):
        """Creates .github/agents/.agdt/ and .github/prompts/.agdt/ directories with README."""
        agents_source = tmp_path / "source_agents"
        prompts_source = tmp_path / "source_prompts"
        agents_source.mkdir()
        prompts_source.mkdir()

        with patch("agentic_devtools.skill_injector._get_source_dir") as mock_src:
            mock_src.side_effect = self._source_selector(agents_source, prompts_source)
            result = inject_skills(tmp_path)

        assert result is True
        assert (tmp_path / ".github" / "agents" / ".agdt").is_dir()
        assert (tmp_path / ".github" / "prompts" / ".agdt").is_dir()
        assert (tmp_path / ".github" / "agents" / ".agdt" / "README.md").exists()
        assert (tmp_path / ".github" / "prompts" / ".agdt" / "README.md").exists()

    def test_copies_agent_files(self, tmp_path):
        """Copies .md files from bundled agents source to target .agdt/ directory."""
        source = tmp_path / "source_agents"
        empty_prompts_source = tmp_path / "source_prompts"
        source.mkdir()
        empty_prompts_source.mkdir()
        (source / "test.agent.md").write_text(
            "---\ndescription: Test agent\n---\n# Content",
            encoding="utf-8",
        )

        with patch("agentic_devtools.skill_injector._get_source_dir") as mock_src:
            mock_src.side_effect = self._source_selector(source, empty_prompts_source)
            result = inject_skills(tmp_path)

        assert result is True
        target = tmp_path / ".github" / "agents" / ".agdt" / "test.agent.md"
        assert target.exists()
        assert "# Content" in target.read_text(encoding="utf-8")

    def test_copies_prompt_files(self, tmp_path):
        """Copies .prompt.md files from bundled prompts source to target .agdt/ directory."""
        empty_agents_source = tmp_path / "source_agents"
        source = tmp_path / "source_prompts"
        empty_agents_source.mkdir()
        source.mkdir()
        (source / "test.prompt.md").write_text(
            "---\nagent: test-agent\n---\n# Prompt",
            encoding="utf-8",
        )

        with patch("agentic_devtools.skill_injector._get_source_dir") as mock_src:
            mock_src.side_effect = self._source_selector(empty_agents_source, source)
            result = inject_skills(tmp_path)

        assert result is True
        target = tmp_path / ".github" / "prompts" / ".agdt" / "test.prompt.md"
        assert target.exists()
        assert "# Prompt" in target.read_text(encoding="utf-8")

    def test_generates_readme_with_manifest(self, tmp_path):
        """Generates README.md with a file manifest table in each .agdt/ directory."""
        source = tmp_path / "source_agents"
        empty_prompts_source = tmp_path / "source_prompts"
        source.mkdir()
        empty_prompts_source.mkdir()
        (source / "my.agent.md").write_text(
            "---\ndescription: My test agent\n---\n# Body",
            encoding="utf-8",
        )

        with patch("agentic_devtools.skill_injector._get_source_dir") as mock_src:
            mock_src.side_effect = self._source_selector(source, empty_prompts_source)
            inject_skills(tmp_path)

        readme = tmp_path / ".github" / "agents" / ".agdt" / "README.md"
        assert readme.exists()
        content = readme.read_text(encoding="utf-8")
        assert "my.agent.md" in content
        assert "My test agent" in content
        assert "Managed" in content

    def test_removes_stale_files(self, tmp_path):
        """Removes .md files in .agdt/ that are not in the current bundled source."""
        agents_source = tmp_path / "source_agents"
        prompts_source = tmp_path / "source_prompts"
        agents_source.mkdir()
        prompts_source.mkdir()

        target_dir = tmp_path / ".github" / "agents" / ".agdt"
        target_dir.mkdir(parents=True)
        stale = target_dir / "old-agent.agent.md"
        stale.write_text("stale content", encoding="utf-8")

        with patch("agentic_devtools.skill_injector._get_source_dir") as mock_src:
            mock_src.side_effect = self._source_selector(agents_source, prompts_source)
            inject_skills(tmp_path)

        assert not stale.exists()

    def test_does_not_remove_non_md_files(self, tmp_path):
        """Does not remove non-.md files in .agdt/ directories."""
        agents_source = tmp_path / "source_agents"
        prompts_source = tmp_path / "source_prompts"
        agents_source.mkdir()
        prompts_source.mkdir()

        target_dir = tmp_path / ".github" / "agents" / ".agdt"
        target_dir.mkdir(parents=True)
        non_md = target_dir / "notes.txt"
        non_md.write_text("keep me", encoding="utf-8")

        with patch("agentic_devtools.skill_injector._get_source_dir") as mock_src:
            mock_src.side_effect = self._source_selector(agents_source, prompts_source)
            inject_skills(tmp_path)

        assert non_md.exists()

    def test_overwrites_existing_files(self, tmp_path):
        """Overwrites existing .md files in .agdt/ with current source content."""
        source = tmp_path / "source_agents"
        empty_prompts_source = tmp_path / "source_prompts"
        source.mkdir()
        empty_prompts_source.mkdir()
        (source / "a.agent.md").write_text(
            "---\ndescription: Updated\n---\nnew content",
            encoding="utf-8",
        )
        target_dir = tmp_path / ".github" / "agents" / ".agdt"
        target_dir.mkdir(parents=True)
        (target_dir / "a.agent.md").write_text("old content", encoding="utf-8")

        with patch("agentic_devtools.skill_injector._get_source_dir") as mock_src:
            mock_src.side_effect = self._source_selector(source, empty_prompts_source)
            inject_skills(tmp_path)

        content = (target_dir / "a.agent.md").read_text(encoding="utf-8")
        assert "new content" in content
        assert "old content" not in content

    def test_returns_false_on_write_error(self, tmp_path):
        """Returns False when an OSError is raised during write."""
        with patch("pathlib.Path.mkdir", side_effect=OSError("permission denied")):
            result = inject_skills(tmp_path)

        assert result is False

    def test_returns_false_when_source_file_cannot_be_decoded(self, tmp_path):
        """Decode errors do not crash injection and mark overall result as failure."""
        source = tmp_path / "source_agents"
        empty_prompts_source = tmp_path / "source_prompts"
        source.mkdir()
        empty_prompts_source.mkdir()

        bad = source / "bad.agent.md"
        bad.write_bytes(b"\xff\xfe\xfa")

        with patch("agentic_devtools.skill_injector._get_source_dir") as mock_src:
            mock_src.side_effect = self._source_selector(source, empty_prompts_source)
            result = inject_skills(tmp_path)

        assert result is False
        assert (tmp_path / ".github" / "agents" / ".agdt" / "bad.agent.md").exists()
        assert (tmp_path / ".github" / "agents" / ".agdt" / "README.md").exists()

    def test_prompts_only_copies_prompt_md_files(self, tmp_path):
        """For prompts, only *.prompt.md files are copied (not arbitrary .md)."""
        empty_agents_source = tmp_path / "source_agents"
        source = tmp_path / "source_prompts"
        empty_agents_source.mkdir()
        source.mkdir()
        (source / "valid.prompt.md").write_text(
            "---\nagent: x\n---\ncontent",
            encoding="utf-8",
        )
        (source / "other.md").write_text("should not copy", encoding="utf-8")

        with patch("agentic_devtools.skill_injector._get_source_dir") as mock_src:
            mock_src.side_effect = self._source_selector(empty_agents_source, source)
            inject_skills(tmp_path)

        target_dir = tmp_path / ".github" / "prompts" / ".agdt"
        assert (target_dir / "valid.prompt.md").exists()
        assert not (target_dir / "other.md").exists()

    def test_agents_copies_all_non_hidden_md_files(self, tmp_path):
        """For agents, all non-hidden *.md files are copied."""
        source = tmp_path / "source_agents"
        empty_prompts_source = tmp_path / "source_prompts"
        source.mkdir()
        empty_prompts_source.mkdir()
        (source / "foo.agent.md").write_text(
            "---\ndescription: foo\n---\n",
            encoding="utf-8",
        )
        (source / "copilot-instructions.md").write_text(
            "# Instructions",
            encoding="utf-8",
        )
        (source / ".markdownlint.json").write_text("{}", encoding="utf-8")

        with patch("agentic_devtools.skill_injector._get_source_dir") as mock_src:
            mock_src.side_effect = self._source_selector(source, empty_prompts_source)
            inject_skills(tmp_path)

        target_dir = tmp_path / ".github" / "agents" / ".agdt"
        assert (target_dir / "foo.agent.md").exists()
        assert (target_dir / "copilot-instructions.md").exists()
        assert not (target_dir / ".markdownlint.json").exists()

    def test_does_not_remove_readme_during_stale_cleanup(self, tmp_path):
        """README.md is not removed during stale file cleanup."""
        agents_source = tmp_path / "source_agents"
        prompts_source = tmp_path / "source_prompts"
        agents_source.mkdir()
        prompts_source.mkdir()

        target_dir = tmp_path / ".github" / "agents" / ".agdt"
        target_dir.mkdir(parents=True)
        readme = target_dir / "README.md"
        readme.write_text("old readme", encoding="utf-8")

        with patch("agentic_devtools.skill_injector._get_source_dir") as mock_src:
            mock_src.side_effect = self._source_selector(agents_source, prompts_source)
            inject_skills(tmp_path)

        assert readme.exists()
        # The README is regenerated (not the old content)
        assert "old readme" not in readme.read_text(encoding="utf-8")

    def test_empty_source_creates_empty_manifest(self, tmp_path):
        """When no source files exist, README.md is created with an empty table."""
        agents_source = tmp_path / "source_agents"
        prompts_source = tmp_path / "source_prompts"
        agents_source.mkdir()
        prompts_source.mkdir()

        with patch("agentic_devtools.skill_injector._get_source_dir") as mock_src:
            mock_src.side_effect = self._source_selector(agents_source, prompts_source)
            inject_skills(tmp_path)

        readme = tmp_path / ".github" / "agents" / ".agdt" / "README.md"
        assert readme.exists()
        content = readme.read_text(encoding="utf-8")
        assert "File Manifest" in content

    def test_preserves_nested_directory_structure(self, tmp_path):
        """Files in subdirectories are copied preserving their relative path."""
        source = tmp_path / "source_agents"
        empty_prompts_source = tmp_path / "source_prompts"
        source.mkdir()
        empty_prompts_source.mkdir()
        subdir = source / "sub"
        subdir.mkdir()
        (source / "root.agent.md").write_text(
            "---\ndescription: root agent\n---\n",
            encoding="utf-8",
        )
        (subdir / "nested.agent.md").write_text(
            "---\ndescription: nested agent\n---\n",
            encoding="utf-8",
        )

        with patch("agentic_devtools.skill_injector._get_source_dir") as mock_src:
            mock_src.side_effect = self._source_selector(source, empty_prompts_source)
            inject_skills(tmp_path)

        target_dir = tmp_path / ".github" / "agents" / ".agdt"
        assert (target_dir / "root.agent.md").exists()
        assert (target_dir / "sub" / "nested.agent.md").exists()

    def test_removes_stale_files_in_subdirectories(self, tmp_path):
        """Stale files in subdirectories of .agdt/ are also removed."""
        agents_source = tmp_path / "source_agents"
        prompts_source = tmp_path / "source_prompts"
        agents_source.mkdir()
        prompts_source.mkdir()

        target_dir = tmp_path / ".github" / "agents" / ".agdt"
        stale_sub = target_dir / "old_sub"
        stale_sub.mkdir(parents=True)
        stale = stale_sub / "stale.agent.md"
        stale.write_text("stale", encoding="utf-8")

        with patch("agentic_devtools.skill_injector._get_source_dir") as mock_src:
            mock_src.side_effect = self._source_selector(agents_source, prompts_source)
            inject_skills(tmp_path)

        assert not stale.exists()

    def test_missing_prompts_source_returns_false_and_preserves_existing_files(self, tmp_path):
        """Missing prompts source returns False and preserves already injected prompt files."""
        agents_source = tmp_path / "source_agents"
        agents_source.mkdir()

        target_dir = tmp_path / ".github" / "prompts" / ".agdt"
        target_dir.mkdir(parents=True)
        stale = target_dir / "old.prompt.md"
        stale.write_text("stale", encoding="utf-8")
        readme = target_dir / "README.md"
        readme.write_text("old readme", encoding="utf-8")

        with patch("agentic_devtools.skill_injector._get_source_dir") as mock_src:
            mock_src.side_effect = self._source_selector(agents_source, None)
            result = inject_skills(tmp_path)

        assert result is False
        assert stale.exists()
        assert readme.exists()
        assert "old readme" in readme.read_text(encoding="utf-8")

    def test_missing_agents_source_returns_false_and_preserves_existing_files(self, tmp_path):
        """Missing agents source returns False and preserves already injected agent files."""
        prompts_source = tmp_path / "source_prompts"
        prompts_source.mkdir()

        target_dir = tmp_path / ".github" / "agents" / ".agdt"
        target_dir.mkdir(parents=True)
        existing = target_dir / "existing.agent.md"
        existing.write_text("existing", encoding="utf-8")
        readme = target_dir / "README.md"
        readme.write_text("old readme", encoding="utf-8")

        with patch("agentic_devtools.skill_injector._get_source_dir") as mock_src:
            mock_src.side_effect = self._source_selector(None, prompts_source)
            result = inject_skills(tmp_path)

        assert result is False
        assert existing.exists()
        assert "old readme" in readme.read_text(encoding="utf-8")

    def test_manifest_uses_relative_paths(self, tmp_path):
        """README manifest shows relative paths for nested files."""
        source = tmp_path / "source_agents"
        empty_prompts_source = tmp_path / "source_prompts"
        source.mkdir()
        empty_prompts_source.mkdir()
        subdir = source / "sub"
        subdir.mkdir()
        (subdir / "deep.agent.md").write_text(
            "---\ndescription: Deep agent\n---\n",
            encoding="utf-8",
        )

        with patch("agentic_devtools.skill_injector._get_source_dir") as mock_src:
            mock_src.side_effect = self._source_selector(source, empty_prompts_source)
            inject_skills(tmp_path)

        readme = tmp_path / ".github" / "agents" / ".agdt" / "README.md"
        content = readme.read_text(encoding="utf-8")
        assert "sub/deep.agent.md" in content
