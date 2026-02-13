"""
Tests for agentic_devtools version management.

This test ensures that the package version is correctly imported from the
auto-generated _version.py file (created by hatch-vcs) rather than being
hardcoded in __init__.py.
"""

import pytest


class TestVersionManagement:
    """Tests for version import."""

    def test_version_is_imported_from_version_module(self):
        """Test that __version__ is available in the package."""
        import agentic_devtools

        # Version should be a string
        assert isinstance(agentic_devtools.__version__, str)
        # Version should not be empty
        assert agentic_devtools.__version__
        # Version should follow semantic versioning pattern (basic check)
        assert "." in agentic_devtools.__version__

    def test_version_matches_version_module(self):
        """Test that package __version__ matches _version.py."""
        import agentic_devtools
        from agentic_devtools import _version

        # The version in __init__.py should match _version.py
        assert agentic_devtools.__version__ == _version.__version__

    def test_version_is_not_hardcoded_0_1_0(self):
        """Test that version comes from _version.py, not hardcoded."""
        import agentic_devtools
        from agentic_devtools import _version

        # The key test: both should use the same object from _version.py
        # If __init__.py had a hardcoded string, this would fail
        # because they'd be different string objects
        assert agentic_devtools.__version__ is _version.__version__
