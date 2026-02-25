"""Tests for normalize_package_name function."""

from agentic_devtools.cli.release.helpers import normalize_package_name


class TestNormalizePackageName:
    """Tests for normalize_package_name function."""

    def test_converts_underscores_to_hyphens(self):
        """Underscores should be replaced with hyphens."""
        assert normalize_package_name("my_package") == "my-package"

    def test_lowercases_name(self):
        """Name should be lowercased."""
        assert normalize_package_name("MyPackage") == "mypackage"

    def test_converts_dots_to_hyphens(self):
        """Dots should be replaced with hyphens."""
        assert normalize_package_name("my.package") == "my-package"

    def test_collapses_consecutive_separators(self):
        """Multiple consecutive separators should collapse to a single hyphen."""
        assert normalize_package_name("my--package") == "my-package"

    def test_strips_leading_trailing_hyphens(self):
        """Leading and trailing hyphens should be stripped."""
        assert normalize_package_name("-package-") == "package"

    def test_handles_mixed_separators(self):
        """Mixed separators (underscores, dots, hyphens) should collapse to one."""
        assert normalize_package_name("my_.-package") == "my-package"

    def test_already_normalized_name_unchanged(self):
        """An already-normalised name should be returned as-is."""
        assert normalize_package_name("my-package") == "my-package"
