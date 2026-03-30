"""Tests for agentic_devtools.submission_manager.TransientSubmissionError."""

from agentic_devtools.submission_manager import TransientSubmissionError


class TestTransientSubmissionError:
    """Tests for TransientSubmissionError exception class."""

    def test_is_exception_subclass(self):
        """TransientSubmissionError inherits from Exception."""
        assert issubclass(TransientSubmissionError, Exception)

    def test_can_be_raised_and_caught(self):
        """TransientSubmissionError can be raised and caught."""
        try:
            raise TransientSubmissionError("rate limited")
        except TransientSubmissionError as exc:
            assert str(exc) == "rate limited"

    def test_not_caught_by_other_exception_types(self):
        """TransientSubmissionError is not caught by ValueError handler."""
        try:
            raise TransientSubmissionError("503")
        except ValueError:
            raise AssertionError("Should not be caught by ValueError")
        except TransientSubmissionError:
            pass

    def test_importable_from_module(self):
        """TransientSubmissionError is importable from submission_manager."""
        from agentic_devtools.submission_manager import TransientSubmissionError as TSE

        assert TSE is TransientSubmissionError
