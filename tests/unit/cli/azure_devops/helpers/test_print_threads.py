"""Tests for print_threads function."""

from agentic_devtools.cli.azure_devops.helpers import print_threads


class TestPrintThreads:
    """Tests for print_threads function."""

    def test_prints_thread_count(self, capsys):
        """Should print the number of threads found."""
        threads = [
            {
                "id": 1,
                "status": "active",
                "comments": [{"id": 1, "author": {"displayName": "User"}, "content": "Test"}],
            }
        ]

        print_threads(threads)

        captured = capsys.readouterr()
        assert "1" in captured.out

    def test_prints_empty_threads(self, capsys):
        """Should handle empty thread list without error."""
        print_threads([])

        captured = capsys.readouterr()
        assert "0" in captured.out

    def test_prints_thread_status(self, capsys):
        """Should print thread status in the output."""
        threads = [
            {
                "id": 5,
                "status": "closed",
                "threadContext": {"filePath": "src/main.py"},
                "comments": [],
            }
        ]

        print_threads(threads)

        captured = capsys.readouterr()
        assert "closed" in captured.out
