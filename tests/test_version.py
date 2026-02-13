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
        """Test that version is not the old hardcoded value."""
        import agentic_devtools
        
        # After the fix, version should not be the stale "0.1.0"
        # It should be from _version.py which is auto-generated
        # We can't assert the exact value, but we can check it's not "0.1.0"
        # unless that's actually the git tag (unlikely given the problem statement)
        from agentic_devtools import _version
        
        # If _version has a different value than "0.1.0", 
        # then __init__ should match _version, not "0.1.0"
        if _version.__version__ != "0.1.0":
            assert agentic_devtools.__version__ != "0.1.0"
