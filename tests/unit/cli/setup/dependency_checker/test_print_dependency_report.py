"""Tests for print_dependency_report."""

from agentic_devtools.cli.setup.dependency_checker import DependencyStatus, print_dependency_report


class TestPrintDependencyReport:
    """Tests for print_dependency_report."""

    def test_prints_found_tool_with_checkmark(self, capsys):
        """Found tools are displayed with ✅."""
        statuses = [
            DependencyStatus(
                name="git",
                found=True,
                path="/usr/bin/git",
                version="2.43.0",
                required=True,
                category="Required",
            )
        ]
        print_dependency_report(statuses)
        captured = capsys.readouterr()
        assert "✅" in captured.out
        assert "git" in captured.out
        assert "2.43.0" in captured.out
        assert "/usr/bin/git" in captured.out

    def test_prints_missing_tool_with_cross(self, capsys):
        """Missing tools are displayed with ❌ and install hint."""
        statuses = [
            DependencyStatus(
                name="copilot",
                found=False,
                required=False,
                install_hint="run: agdt-setup-copilot-cli",
                category="Recommended",
            )
        ]
        print_dependency_report(statuses)
        captured = capsys.readouterr()
        assert "❌" in captured.out
        assert "copilot" in captured.out
        assert "agdt-setup-copilot-cli" in captured.out

    def test_missing_tool_without_hint_no_install_line(self, capsys):
        """Missing tools with no install hint don't print an Install line."""
        statuses = [DependencyStatus(name="az", found=False, install_hint="", category="Optional")]
        print_dependency_report(statuses)
        captured = capsys.readouterr()
        assert "Install:" not in captured.out

    def test_multiple_tools_all_printed(self, capsys):
        """All tools in the list are printed."""
        statuses = [
            DependencyStatus(name="git", found=True, path="/usr/bin/git", version="2.43.0", category="Required"),
            DependencyStatus(name="gh", found=False, install_hint="https://cli.github.com/", category="Recommended"),
        ]
        print_dependency_report(statuses)
        captured = capsys.readouterr()
        assert "git" in captured.out
        assert "gh" in captured.out

    def test_version_dash_when_missing(self, capsys):
        """Version shows '—' when not available."""
        statuses = [DependencyStatus(name="az", found=False, category="Optional")]
        print_dependency_report(statuses)
        captured = capsys.readouterr()
        assert "—" in captured.out

    def test_not_found_location(self, capsys):
        """'not found' appears for missing tools."""
        statuses = [DependencyStatus(name="code", found=False, category="Optional")]
        print_dependency_report(statuses)
        captured = capsys.readouterr()
        assert "not found" in captured.out
