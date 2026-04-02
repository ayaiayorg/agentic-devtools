"""Tests for get_language_from_extension function."""


class TestGetLanguageFromExtension:
    """Tests for get_language_from_extension function."""

    def test_python_extension(self):
        """Test .py maps to python."""
        from agentic_devtools.cli.azure_devops.review_helpers import get_language_from_extension

        assert get_language_from_extension("src/app.py") == "python"

    def test_typescript_extension(self):
        """Test .ts maps to typescript."""
        from agentic_devtools.cli.azure_devops.review_helpers import get_language_from_extension

        assert get_language_from_extension("src/app.ts") == "typescript"

    def test_json_extension(self):
        """Test .json maps to json."""
        from agentic_devtools.cli.azure_devops.review_helpers import get_language_from_extension

        assert get_language_from_extension("config.json") == "json"

    def test_unknown_extension_returns_empty(self):
        """Test unknown extension returns empty string."""
        from agentic_devtools.cli.azure_devops.review_helpers import get_language_from_extension

        assert get_language_from_extension("file.xyz") == ""

    def test_empty_string_returns_empty(self):
        """Test empty string returns empty string."""
        from agentic_devtools.cli.azure_devops.review_helpers import get_language_from_extension

        assert get_language_from_extension("") == ""

    def test_uppercase_extension(self):
        """Test uppercase extension is handled case-insensitively."""
        from agentic_devtools.cli.azure_devops.review_helpers import get_language_from_extension

        assert get_language_from_extension("FILE.PY") == "python"

    def test_no_extension_returns_empty(self):
        """Test file with no extension returns empty string."""
        from agentic_devtools.cli.azure_devops.review_helpers import get_language_from_extension

        assert get_language_from_extension("Makefile") == ""

    def test_dockerfile_extension(self):
        """Test .dockerfile extension maps to dockerfile."""
        from agentic_devtools.cli.azure_devops.review_helpers import get_language_from_extension

        assert get_language_from_extension("app.dockerfile") == "dockerfile"

    def test_yaml_extension(self):
        """Test .yaml and .yml map to yaml."""
        from agentic_devtools.cli.azure_devops.review_helpers import get_language_from_extension

        assert get_language_from_extension("config.yaml") == "yaml"
        assert get_language_from_extension("config.yml") == "yaml"

    def test_bash_extension(self):
        """Test .sh and .bash map to bash."""
        from agentic_devtools.cli.azure_devops.review_helpers import get_language_from_extension

        assert get_language_from_extension("script.sh") == "bash"
        assert get_language_from_extension("script.bash") == "bash"

    def test_cpp_extensions(self):
        """Test C++ related extensions map to cpp."""
        from agentic_devtools.cli.azure_devops.review_helpers import get_language_from_extension

        assert get_language_from_extension("main.cpp") == "cpp"
        assert get_language_from_extension("main.cc") == "cpp"
        assert get_language_from_extension("main.h") == "cpp"
        assert get_language_from_extension("main.hpp") == "cpp"
