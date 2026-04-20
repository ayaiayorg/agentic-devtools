"""Tests for the wrap_markdown_lines.py CLI helper script."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "scripts"
    / "speckit-trigger"
    / "wrap_markdown_lines.py"
)


def _load_module():
    """Load wrap_markdown_lines.py as a module without executing __main__."""
    spec = importlib.util.spec_from_file_location("wrap_markdown_lines", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {SCRIPT_PATH!s}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestWrapMarkdownText:
    """Verify wrap_markdown_text() behaviour against MD013 preservation rules."""

    def test_short_lines_pass_through_unchanged(self):
        module = _load_module()
        text = "Short line.\n\nAnother short line.\n"
        assert module.wrap_markdown_text(text, width=200) == text

    def test_long_paragraph_is_wrapped(self):
        module = _load_module()
        long_line = (
            "This is a very long line that exceeds the limit and must be wrapped "
            "at word boundaries so the result contains multiple lines each within "
            "the configured width."
        )
        wrapped = module.wrap_markdown_text(long_line, width=60)
        lines = wrapped.splitlines()
        assert len(lines) > 1
        for line in lines:
            assert len(line) <= 60 or " " not in line  # single oversize word allowed

    def test_long_list_item_preserves_marker_and_indent(self):
        module = _load_module()
        line = (
            "- This is a very long bullet item that exceeds the configured limit "
            "and must be wrapped with continuation indent aligning past the marker."
        )
        wrapped = module.wrap_markdown_text(line, width=60).splitlines()
        assert len(wrapped) > 1
        assert wrapped[0].startswith("- ")
        for cont in wrapped[1:]:
            assert cont.startswith("  "), f"continuation not indented: {cont!r}"

    def test_ordered_list_item_uses_correct_indent(self):
        module = _load_module()
        line = (
            "1. This is a very long numbered list item that should wrap and whose "
            "continuation lines must be indented three spaces to match the marker."
        )
        wrapped = module.wrap_markdown_text(line, width=60).splitlines()
        assert wrapped[0].startswith("1. ")
        # "1. " is 3 chars; continuation indent must be at least 3 spaces.
        for cont in wrapped[1:]:
            assert cont.startswith("   "), f"continuation not 3-space indented: {cont!r}"

    def test_fenced_code_block_is_preserved_verbatim(self):
        module = _load_module()
        long_code = "x" * 300
        text = f"Intro.\n\n```\n{long_code}\n```\n\nOutro.\n"
        wrapped = module.wrap_markdown_text(text, width=80)
        assert long_code in wrapped
        # Make sure nothing was injected inside the fence.
        assert f"```\n{long_code}\n```" in wrapped

    def test_tilde_fenced_code_block_is_preserved(self):
        module = _load_module()
        long_code = "y" * 300
        text = f"Intro.\n\n~~~\n{long_code}\n~~~\n\nOutro.\n"
        wrapped = module.wrap_markdown_text(text, width=80)
        assert long_code in wrapped

    def test_fence_closing_rules_must_match(self):
        module = _load_module()
        # Opening fence has 4 backticks; a 3-backtick fence should not close it.
        # Also testing that a fence indented 4 spaces shouldn't close it,
        # but 3-space indentation should be accepted eventually by a valid 4-backtick fence.
        long_code = "long_line_inside_fence_that_would_be_wrapped_if_outside " * 10
        text = (
            "````\n"
            "```\n"  # Too short; should not close
            f"{long_code}\n"
            "    ````\n"  # Indented 4 spaces; should not close
            "   ````\n"  # Valid closing fence (same character, length >= 4, indent <= 3)
            "```\n"  # Regular outside prose fence-like element? No wait, this starts a new fence!
        )
        wrapped = module.wrap_markdown_text(text, width=80)
        lines = wrapped.splitlines()
        # The long line should be preserved exactly as-is
        assert long_code.strip() in [l.strip() for l in lines]
        # Make sure the lines are present without wrapping
        assert wrapped == text

    def test_table_rows_are_preserved_even_when_long(self):
        module = _load_module()
        table = "| " + " | ".join(f"col{i}" for i in range(25)) + " |"
        assert len(table) > 80
        wrapped = module.wrap_markdown_text(table, width=80)
        assert wrapped.splitlines() == [table]

    def test_indented_code_block_is_preserved(self):
        module = _load_module()
        line = "    " + "z" * 300
        wrapped = module.wrap_markdown_text(line, width=80)
        assert wrapped == line

    def test_heading_is_not_wrapped(self):
        module = _load_module()
        heading = "## " + "a very long heading " * 20
        wrapped = module.wrap_markdown_text(heading, width=80)
        assert wrapped.splitlines() == [heading]

    def test_yaml_front_matter_is_preserved(self):
        module = _load_module()
        long_val = "very long value " * 30
        text = f"---\ntitle: {long_val}\n---\n\nBody {long_val}\n"
        wrapped = module.wrap_markdown_text(text, width=60)
        # Front matter key/value line must appear unchanged.
        assert f"title: {long_val}" in wrapped
        # Body content should have been wrapped.
        body_lines = [
            line
            for line in wrapped.splitlines()
            if line and not line.startswith(("---", "title:"))
        ]
        assert len(body_lines) > 1

    def test_blockquote_preserves_prefix(self):
        module = _load_module()
        line = "> " + "this is a long quote that really needs wrapping " * 5
        wrapped = module.wrap_markdown_text(line, width=60).splitlines()
        assert len(wrapped) > 1
        for out_line in wrapped:
            assert out_line.startswith(">"), f"missing blockquote prefix: {out_line!r}"

    def test_link_reference_definition_is_preserved(self):
        module = _load_module()
        url = "https://example.com/" + "path/" * 50
        line = f"[ref]: {url}"
        assert len(line) > 200
        wrapped = module.wrap_markdown_text(line, width=80)
        assert wrapped.splitlines() == [line]

    def test_markdownlint_disable_comment_is_preserved(self):
        module = _load_module()
        line = "<!-- markdownlint-disable MD013 MD041 --> " + "x" * 300
        wrapped = module.wrap_markdown_text(line, width=80)
        assert wrapped.splitlines() == [line]

    def test_trailing_newline_is_preserved(self):
        module = _load_module()
        assert module.wrap_markdown_text("short\n", width=80).endswith("\n")
        assert not module.wrap_markdown_text("short", width=80).endswith("\n")

    def test_width_validation(self):
        module = _load_module()
        try:
            module.wrap_markdown_text("x", width=0)
        except ValueError:
            return
        raise AssertionError("ValueError was not raised for width=0")

    def test_wrapped_list_item_respects_width_including_marker(self):
        """Each wrapped list-item line must fit within width, marker included."""
        module = _load_module()
        line = (
            "- This is a long bullet item that must wrap with every resulting "
            "line kept at or below the configured width including the marker."
        )
        wrapped = module.wrap_markdown_text(line, width=60).splitlines()
        for out_line in wrapped:
            # Allow a single over-width line only when it contains no space
            # (a lone long word we cannot split safely).
            if len(out_line) > 60:
                assert " " not in out_line.strip(), f"line too long: {out_line!r}"

    def test_wrapped_blockquote_respects_width_including_prefix(self):
        """Each wrapped blockquote line must fit within width, prefix included."""
        module = _load_module()
        line = "> " + "a quoted sentence that really runs on " * 5
        wrapped = module.wrap_markdown_text(line, width=60).splitlines()
        for out_line in wrapped:
            if len(out_line) > 60:
                assert " " not in out_line.strip(), f"line too long: {out_line!r}"

    def test_horizontal_rule_outside_front_matter_is_not_treated_as_front_matter(self):
        """A ``---`` on line 2+ is a horizontal rule, not front-matter delimiter."""
        module = _load_module()
        long_line = "Paragraph before rule that exceeds the width " * 5
        text = f"# Heading\n\n{long_line}\n\n---\n\nMore body.\n"
        wrapped = module.wrap_markdown_text(text, width=80)
        # The long line should have been wrapped.
        assert any(
            len(out_line) <= 80 and "Paragraph before rule" in out_line
            for out_line in wrapped.splitlines()
        )

    def test_wrap_markdown_lines_preserves_whitespace(self):
        """Tokenization should not collapse repeated spaces or strip trailing ones."""
        module = _load_module()
        # "Intro" followed by double space: a markdown hard line break.
        # "code  here" with inner double space.
        long_line = (
            "Intro  This is an overlong paragraph with `inline  code` that goes on "
            "and on and eventually needs to wrap."
        )
        wrapped = module.wrap_markdown_text(long_line, width=100)
        # Should be wrapped but space after Intro etc. preserved.
        assert "Intro  This " in wrapped or "Intro  \n" in wrapped
        assert "`inline  code`" in wrapped

    def test_whitespace_segment_respects_width_budget(self):
        """Whitespace segments must not silently push lines beyond width."""
        module = _load_module()
        # Build a line where the whitespace segment at the boundary would
        # overflow: "aaa...a  bbb" where 'a' block is exactly at width,
        # so appending "  " would exceed it.
        filler = "a" * 58  # 58 chars
        line = filler + "  overflow"  # 58 + 2 + 8 = 68
        wrapped = module.wrap_markdown_text(line, width=60).splitlines()
        for out_line in wrapped:
            if len(out_line) > 60:
                assert " " not in out_line.strip(), (
                    f"line too long: {out_line!r}"
                )

    def test_blockquote_list_item_with_small_width(self):
        """Zero/negative derived width must not crash _wrap_list_item."""
        module = _load_module()
        # A deeply-nested blockquote prefix (10 chars) with a tiny width
        # would produce a negative adjusted width without clamping.
        line = "> > > - item content that needs wrapping eventually"
        # Even with very small width, should not raise or produce garbage.
        wrapped = module.wrap_markdown_text(line, width=15)
        assert wrapped.startswith("> > > - ")

    def test_list_item_inside_blockquote(self):
        """
        A list item inside a blockquote should be wrapped keeping both the
        blockquote prefix and list marker/indent.
        """
        module = _load_module()
        line = (
            "> - This is a very long bullet item inside a blockquote that "
            "exceeds the configured limit and must be wrapped with continuation "
            "indent."
        )
        wrapped = module.wrap_markdown_text(line, width=60).splitlines()
        assert len(wrapped) > 1
        assert wrapped[0].startswith("> - ")
        for cont in wrapped[1:]:
            assert cont.startswith(">   "), f"continuation not correctly prefixed/indented: {cont!r}"


class TestWrapFile:
    """Verify wrap_file() in-place behaviour."""

    def test_file_is_modified_when_wrapping_applies(self, tmp_path: Path):
        module = _load_module()
        target = tmp_path / "spec.md"
        long_line = "This is an overlong paragraph line " * 20
        target.write_text(f"# Heading\n\n{long_line}\n", encoding="utf-8")
        changed = module.wrap_file(target, width=80)
        assert changed is True
        content = target.read_text(encoding="utf-8")
        for line in content.splitlines():
            # Heading / blank / wrapped paragraph lines all <= 80 (ignoring trailing whitespace)
            assert len(line.rstrip()) <= 80

    def test_file_is_untouched_when_no_wrapping_applies(self, tmp_path: Path):
        module = _load_module()
        target = tmp_path / "spec.md"
        original = "# Heading\n\nShort paragraph.\n"
        target.write_text(original, encoding="utf-8")
        changed = module.wrap_file(target, width=200)
        assert changed is False
        assert target.read_text(encoding="utf-8") == original


class TestCli:
    """Verify the CLI entry point."""

    def test_cli_skips_missing_files(self, tmp_path: Path):
        module = _load_module()
        rc = module.main(["--quiet", str(tmp_path / "does-not-exist.md")])
        assert rc == 0

    def test_cli_wraps_a_real_file(self, tmp_path: Path):
        module = _load_module()
        target = tmp_path / "spec.md"
        long_line = "This is an overlong paragraph line " * 20
        target.write_text(f"# Heading\n\n{long_line}\n", encoding="utf-8")
        rc = module.main(["--max-line-length", "80", "--quiet", str(target)])
        assert rc == 0
        for line in target.read_text(encoding="utf-8").splitlines():
            assert len(line.rstrip()) <= 80

    def test_cli_rejects_nonpositive_width(self, tmp_path: Path):
        module = _load_module()
        target = tmp_path / "spec.md"
        target.write_text("x\n", encoding="utf-8")
        rc = module.main(["--max-line-length", "0", str(target)])
        assert rc == 2
