"""Tests for agentic_devtools.tools.git._capture."""

from agentic_devtools.tools.git import _capture


class TestCapture:
    """Tests for the _capture helper function."""

    def test_captures_stdout(self):
        def greet():
            print("Hello, world!")

        output = _capture(greet)
        assert output == "Hello, world!\n"

    def test_captures_with_args(self):
        def greet(name):
            print(f"Hello, {name}!")

        output = _capture(greet, "Alice")
        assert output == "Hello, Alice!\n"

    def test_empty_output(self):
        def noop():
            pass

        output = _capture(noop)
        assert output == ""
