"""Tests for is_binary_file function."""


class TestIsBinaryFile:
    """Tests for is_binary_file function."""

    def test_png_is_binary(self):
        """Test .png is identified as binary."""
        from agentic_devtools.cli.azure_devops.review_helpers import is_binary_file

        assert is_binary_file("image.png") is True

    def test_jpg_is_binary(self):
        """Test .jpg is identified as binary."""
        from agentic_devtools.cli.azure_devops.review_helpers import is_binary_file

        assert is_binary_file("photo.jpg") is True

    def test_exe_is_binary(self):
        """Test .exe is identified as binary."""
        from agentic_devtools.cli.azure_devops.review_helpers import is_binary_file

        assert is_binary_file("program.exe") is True

    def test_python_is_not_binary(self):
        """Test .py is not identified as binary."""
        from agentic_devtools.cli.azure_devops.review_helpers import is_binary_file

        assert is_binary_file("script.py") is False

    def test_typescript_is_not_binary(self):
        """Test .ts is not identified as binary."""
        from agentic_devtools.cli.azure_devops.review_helpers import is_binary_file

        assert is_binary_file("app.ts") is False

    def test_uppercase_extension(self):
        """Test uppercase extension is handled case-insensitively."""
        from agentic_devtools.cli.azure_devops.review_helpers import is_binary_file

        assert is_binary_file("IMAGE.PNG") is True

    def test_empty_string(self):
        """Test empty string returns False."""
        from agentic_devtools.cli.azure_devops.review_helpers import is_binary_file

        assert is_binary_file("") is False

    def test_no_extension(self):
        """Test file with no extension returns False."""
        from agentic_devtools.cli.azure_devops.review_helpers import is_binary_file

        assert is_binary_file("Makefile") is False
