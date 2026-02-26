"""Tests for DependencyStatus dataclass."""

from agentic_devtools.cli.setup.dependency_checker import DependencyStatus


class TestDependencyStatus:
    """Tests for DependencyStatus dataclass."""

    def test_default_fields(self):
        """Default optional fields are None/False/empty."""
        status = DependencyStatus(name="git", found=True)
        assert status.name == "git"
        assert status.found is True
        assert status.path is None
        assert status.version is None
        assert status.required is False
        assert status.install_hint == ""
        assert status.category == "Optional"

    def test_all_fields_set(self):
        """All fields can be set explicitly."""
        status = DependencyStatus(
            name="gh",
            found=True,
            path="/usr/bin/gh",
            version="2.65.0",
            required=False,
            install_hint="run: agdt-setup-gh-cli",
            category="Recommended",
        )
        assert status.path == "/usr/bin/gh"
        assert status.version == "2.65.0"
        assert status.category == "Recommended"

    def test_not_found(self):
        """A missing dependency has found=False and no path/version."""
        status = DependencyStatus(name="copilot", found=False)
        assert not status.found
        assert status.path is None
