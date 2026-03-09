"""Tests for agentic_devtools.cli.git.agdt_branch.GitPlumbingError."""

from agentic_devtools.cli.git.agdt_branch import GitPlumbingError


class TestGitPlumbingError:
    """Tests for the GitPlumbingError exception class."""

    def test_is_exception(self):
        """GitPlumbingError is a subclass of Exception."""
        assert issubclass(GitPlumbingError, Exception)

    def test_message_preserved(self):
        """The error message is accessible via str()."""
        err = GitPlumbingError("something went wrong")
        assert str(err) == "something went wrong"

    def test_can_be_raised_and_caught(self):
        """GitPlumbingError can be raised and caught."""
        try:
            raise GitPlumbingError("fail")
        except GitPlumbingError as exc:
            assert str(exc) == "fail"
