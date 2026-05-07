"""Tests for count_checkboxes() function."""

from __future__ import annotations

from agentic_devtools.cli.speckit.validate_checklists import count_checkboxes


class TestCountCheckboxesBasic:
    """Basic checkbox counting tests."""

    def test_empty_content(self) -> None:
        assert count_checkboxes("") == 0

    def test_whitespace_only(self) -> None:
        assert count_checkboxes("   \n\n  \n") == 0

    def test_single_unchecked(self) -> None:
        assert count_checkboxes("- [ ] Item 1") == 1

    def test_single_checked_lowercase(self) -> None:
        assert count_checkboxes("- [x] Item 1") == 1

    def test_single_checked_uppercase(self) -> None:
        assert count_checkboxes("- [X] Item 1") == 1

    def test_multiple_checkboxes(self) -> None:
        content = "- [ ] Item 1\n- [x] Item 2\n- [X] Item 3"
        assert count_checkboxes(content) == 3

    def test_asterisk_unchecked(self) -> None:
        assert count_checkboxes("* [ ] Item 1") == 1

    def test_asterisk_checked(self) -> None:
        assert count_checkboxes("* [x] Item 1") == 1

    def test_asterisk_checked_uppercase(self) -> None:
        assert count_checkboxes("* [X] Item 1") == 1

    def test_mixed_markers(self) -> None:
        content = "- [ ] Dash item\n* [x] Asterisk item"
        assert count_checkboxes(content) == 2

    def test_prose_no_checkboxes(self) -> None:
        content = "# Heading\n\nSome paragraph text.\n\n- Regular list item"
        assert count_checkboxes(content) == 0


class TestCountCheckboxesIndented:
    """Tests for indented/nested checkbox items."""

    def test_indented_two_spaces(self) -> None:
        assert count_checkboxes("  - [ ] Indented item") == 1

    def test_indented_four_spaces(self) -> None:
        assert count_checkboxes("    - [ ] Deeply indented") == 1

    def test_nested_mixed(self) -> None:
        content = "- [ ] Top\n  - [x] Nested\n    - [ ] Deep"
        assert count_checkboxes(content) == 3

    def test_tab_indented(self) -> None:
        assert count_checkboxes("\t- [ ] Tab indented") == 1


class TestCountCheckboxesFencedCodeBlocks:
    """Tests for fenced code block exclusion."""

    def test_checkbox_inside_backtick_fence_excluded(self) -> None:
        content = "```\n- [ ] Inside fence\n```"
        assert count_checkboxes(content) == 0

    def test_checkbox_outside_fence_counted(self) -> None:
        content = "- [ ] Outside\n```\n- [ ] Inside\n```\n- [ ] Also outside"
        assert count_checkboxes(content) == 2

    def test_tilde_fence_exclusion(self) -> None:
        content = "~~~\n- [ ] Inside tilde fence\n~~~"
        assert count_checkboxes(content) == 0

    def test_longer_opening_fence(self) -> None:
        content = "````\n- [ ] Inside\n````"
        assert count_checkboxes(content) == 0

    def test_closing_fence_must_match_length(self) -> None:
        # Closing fence shorter than opening does NOT close
        content = "````\n- [ ] Still inside\n```\n````"
        assert count_checkboxes(content) == 0

    def test_closing_fence_longer_is_valid(self) -> None:
        # Closing fence longer than opening DOES close
        content = "```\n- [ ] Inside\n````\n- [ ] Outside"
        assert count_checkboxes(content) == 1

    def test_tilde_closing_must_match_length(self) -> None:
        content = "~~~~\n- [ ] Inside\n~~~\n~~~~"
        assert count_checkboxes(content) == 0

    def test_mixed_fences_backtick_and_tilde(self) -> None:
        content = "```\n- [ ] In backtick\n```\n~~~\n- [ ] In tilde\n~~~\n- [ ] Free"
        assert count_checkboxes(content) == 1

    def test_nested_fence_outermost_boundary(self) -> None:
        # Inner fence is treated as text inside outer fence
        content = "```\n~~~\n- [ ] Nested\n~~~\n```"
        assert count_checkboxes(content) == 0

    def test_fence_with_info_string(self) -> None:
        content = "```python\n- [ ] Inside code\n```"
        assert count_checkboxes(content) == 0

    def test_indented_fence(self) -> None:
        content = "  ```\n  - [ ] Inside\n  ```"
        assert count_checkboxes(content) == 0

    def test_multiple_fenced_blocks(self) -> None:
        content = "- [ ] Before\n```\n- [ ] In first\n```\n- [ ] Between\n~~~\n- [ ] In second\n~~~\n- [ ] After"
        assert count_checkboxes(content) == 3
