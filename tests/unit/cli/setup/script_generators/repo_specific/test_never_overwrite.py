"""Tests for repo-specific script never being overwritten."""

from agentic_devtools.cli.setup.script_generators.repo_specific import generate_repo_specific_stub


class TestNeverOverwrite:
    """Tests for repo-specific stub generation and preservation."""

    def test_stub_content(self):
        """Stub contains informational message."""
        stub = generate_repo_specific_stub()
        assert "No repo-specific dev tools configured" in stub

    def test_stub_is_valid_python(self):
        """Stub is valid Python source."""
        stub = generate_repo_specific_stub()
        compile(stub, "<stub>", "exec")

    def test_stub_has_shebang(self):
        """Stub starts with shebang."""
        stub = generate_repo_specific_stub()
        assert stub.startswith("#!/usr/bin/env python3")

    def test_stub_has_foreground_flag(self):
        """Stub supports --foreground."""
        stub = generate_repo_specific_stub()
        assert "--foreground" in stub

    def test_stub_has_guidance_comment(self):
        """Stub includes guidance for customization."""
        stub = generate_repo_specific_stub()
        assert "YOURS" in stub or "never overwrite" in stub.lower()

    def test_stdlib_only(self):
        """Stub does not import agentic_devtools."""
        stub = generate_repo_specific_stub()
        assert "import agentic_devtools" not in stub
        assert "from agentic_devtools" not in stub
