"""Tests for agentic_devtools.skill_injector._generate_readme."""

from agentic_devtools.skill_injector import _generate_readme


class TestGenerateReadme:
    """Tests for the _generate_readme helper."""

    def test_contains_managed_header_for_agents(self):
        """README for agents contains 'Managed Agent Skills' header."""
        result = _generate_readme([], "agents")
        assert "# Managed Agent Skills" in result

    def test_contains_managed_header_for_prompts(self):
        """README for prompts contains 'Managed Prompt Skills' header."""
        result = _generate_readme([], "prompts")
        assert "# Managed Prompt Skills" in result

    def test_contains_do_not_edit_warning(self):
        """README contains a warning not to edit files manually."""
        result = _generate_readme([], "agents")
        assert "Do **not** edit" in result

    def test_contains_file_manifest_table(self):
        """README contains a file manifest table with provided entries."""
        files = [("test.agent.md", "A test agent")]
        result = _generate_readme(files, "agents")
        assert "| `test.agent.md` | A test agent |" in result

    def test_contains_regeneration_instructions(self):
        """README contains regeneration instructions mentioning agdt-setup."""
        result = _generate_readme([], "agents")
        assert "agdt-setup" in result

    def test_empty_file_list_produces_empty_table_body(self):
        """An empty file list produces a table with only the header row."""
        result = _generate_readme([], "agents")
        lines = result.split("\n")
        # The table header and separator are present but no data rows
        table_start = next(i for i, line in enumerate(lines) if "| File |" in line)
        separator_line = lines[table_start + 1]
        assert "----" in separator_line
        # Next line should be empty (no data rows)
        assert lines[table_start + 2] == ""

    def test_multiple_files_in_manifest(self):
        """Multiple files are listed in the manifest table."""
        files = [
            ("a.agent.md", "Agent A"),
            ("b.agent.md", "Agent B"),
        ]
        result = _generate_readme(files, "agents")
        assert "| `a.agent.md` | Agent A |" in result
        assert "| `b.agent.md` | Agent B |" in result
