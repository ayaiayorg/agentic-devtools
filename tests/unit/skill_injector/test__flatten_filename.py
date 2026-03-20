"""Tests for agentic_devtools.skill_injector._flatten_filename."""

from pathlib import Path

from agentic_devtools.skill_injector import _flatten_filename


class TestFlattenFilename:
    """Tests for the _flatten_filename helper."""

    def test_root_level_file_unchanged(self):
        """Root-level files keep their name unchanged."""
        assert _flatten_filename(Path("foo.agent.md")) == "foo.agent.md"

    def test_single_subdirectory(self):
        """Files in a subdirectory get agdt.<dir>.<name>."""
        assert _flatten_filename(Path("sub/nested.agent.md")) == "agdt.sub.nested.agent.md"

    def test_multi_level_nesting(self):
        """Multi-level nesting joins each sanitized segment with dots."""
        assert _flatten_filename(Path("foo/bar/baz.agent.md")) == "agdt.foo.bar.baz.agent.md"

    def test_sanitizes_non_alpha_characters(self):
        """Non-alpha characters are stripped from directory names."""
        assert _flatten_filename(Path("My Dir 123/file.agent.md")) == "agdt.MyDir.file.agent.md"

    def test_empty_after_sanitization_fallback(self):
        """Directory name consisting entirely of non-alpha chars falls back to filename only."""
        assert _flatten_filename(Path("123/file.agent.md")) == "file.agent.md"

    def test_agdt_prefix_not_deduplicated(self):
        """agdt. prefix is NOT deduplicated for files already prefixed with agdt."""
        result = _flatten_filename(Path("sub/agdt.cool.agent.md"))
        assert result == "agdt.sub.agdt.cool.agent.md"
