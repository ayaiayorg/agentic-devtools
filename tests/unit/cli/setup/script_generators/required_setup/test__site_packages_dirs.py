"""Tests for _site_packages_dirs."""

from unittest.mock import patch

from agentic_devtools.cli.setup.script_generators.required_setup import _site_packages_dirs

_MOD = "agentic_devtools.cli.setup.script_generators.required_setup"


class TestSitePackagesDirs:
    """Tests for _site_packages_dirs."""

    def test_returns_list_of_strings(self):
        """Returns a non-empty list of site-packages directories."""
        result = _site_packages_dirs()
        assert isinstance(result, list)
        assert all(isinstance(d, str) for d in result)

    def test_handles_list_result_then_string_result(self):
        """Handles getsitepackages returning a list then getusersitepackages a string."""
        fake_site = type("FakeSite", (), {})()
        fake_site.getsitepackages = lambda: ["/fake/sp1", "/fake/sp2"]
        fake_site.getusersitepackages = lambda: "/fake/user-sp"
        with patch(f"{_MOD}.site", fake_site):
            result = _site_packages_dirs()
        assert "/fake/sp1" in result
        assert "/fake/sp2" in result
        assert "/fake/user-sp" in result

    def test_skips_missing_attr(self):
        """Handles site module missing getsitepackages gracefully."""
        fake_site = type("FakeSite", (), {})()
        with patch(f"{_MOD}.site", fake_site):
            result = _site_packages_dirs()
        assert result == []

    def test_ignores_non_str_non_list_result(self):
        """Ignores results that are neither str nor list (e.g. tuple)."""
        fake_site = type("FakeSite", (), {})()
        fake_site.getsitepackages = lambda: ("/tuple/path",)
        with patch(f"{_MOD}.site", fake_site):
            result = _site_packages_dirs()
        assert result == []
