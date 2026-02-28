"""Tests for _print_dry_run_plan helper."""

from agentic_devtools.cli.azure_devops.review_scaffold import _print_dry_run_plan


class TestPrintDryRunPlan:
    """Tests for _print_dry_run_plan helper."""

    def test_prints_pr_id(self, capsys):
        """Prints the PR ID in the plan header."""
        _print_dry_run_plan(999, [], {})
        out = capsys.readouterr().out
        assert "[DRY RUN] Scaffolding plan for PR 999:" in out

    def test_prints_file_entries(self, capsys):
        """Prints a line for each file."""
        _print_dry_run_plan(1, ["/src/a.ts", "/src/b.ts"], {"src": ["/src/a.ts", "/src/b.ts"]})
        out = capsys.readouterr().out
        assert "Would create file summary thread for /src/a.ts" in out
        assert "Would create file summary thread for /src/b.ts" in out

    def test_prints_folder_entries(self, capsys):
        """Prints a line for each folder."""
        _print_dry_run_plan(1, ["/src/a.ts"], {"src": ["/src/a.ts"]})
        out = capsys.readouterr().out
        assert "Would create folder summary thread for src" in out

    def test_prints_overall_thread(self, capsys):
        """Prints a line for the overall PR summary thread."""
        _print_dry_run_plan(1, [], {})
        out = capsys.readouterr().out
        assert "Would create overall PR summary thread" in out

    def test_prints_total_api_calls(self, capsys):
        """Prints total API call count (N files + F folders + 1 overall)."""
        files = ["/a/x.ts", "/a/y.ts", "/b/z.ts"]
        folders = {"a": ["/a/x.ts", "/a/y.ts"], "b": ["/b/z.ts"]}
        _print_dry_run_plan(1, files, folders)
        out = capsys.readouterr().out
        # 3 files + 2 folders + 1 overall = 6
        assert "Total API calls: 6" in out
