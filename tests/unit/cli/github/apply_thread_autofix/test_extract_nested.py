"""Tests for _extract_nested."""

from agentic_devtools.cli.github.apply_thread_autofix import _extract_nested


class TestExtractNested:
    """Tests for _extract_nested."""

    def test_traverses_valid_keys(self) -> None:
        data = {"a": {"b": {"c": 42}}}
        assert _extract_nested(data, ["a", "b", "c"]) == 42

    def test_returns_none_on_missing_key(self) -> None:
        data = {"a": {"b": 1}}
        assert _extract_nested(data, ["a", "x"]) is None

    def test_returns_none_when_intermediate_is_not_dict(self) -> None:
        data = {"a": "not_a_dict"}
        assert _extract_nested(data, ["a", "b"]) is None

    def test_empty_keys_returns_data(self) -> None:
        data = {"a": 1}
        assert _extract_nested(data, []) == data

    def test_returns_none_when_value_is_none(self) -> None:
        data = {"a": None}
        assert _extract_nested(data, ["a", "b"]) is None
