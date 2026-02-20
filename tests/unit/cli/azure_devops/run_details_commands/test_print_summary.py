"""
Tests for run_details_commands module.
"""



from agentic_devtools.cli.azure_devops.run_details_commands import (
    _print_summary,
)


class TestPrintSummary:
    """Tests for _print_summary helper."""

    def test_pipeline_summary_output(self, capsys):
        """Should print formatted summary for pipeline data."""
        data = {
            "state": "completed",
            "result": "succeeded",
            "pipeline": {"name": "my-pipeline"},
            "resources": {"repositories": {"self": {"refName": "refs/heads/feature"}}},
            "_links": {"web": {"href": "https://example.com/run/123"}},
            "templateParameters": {"stage": "INT"},
        }
        _print_summary(data, "pipeline")

        captured = capsys.readouterr()
        assert "pipeline API" in captured.out
        assert "completed" in captured.out
        assert "succeeded" in captured.out
        assert "my-pipeline" in captured.out
        assert "refs/heads/feature" in captured.out
        assert "https://example.com/run/123" in captured.out
        assert "stage: INT" in captured.out

    def test_build_summary_output(self, capsys):
        """Should print formatted summary for build data."""
        data = {
            "status": "inProgress",
            "result": None,
            "sourceBranch": "refs/heads/main",
            "definition": {"name": "CI-Build"},
            "_links": {"web": {"href": "https://example.com/build/456"}},
            "parameters": '{"clean": "true"}',
        }
        _print_summary(data, "build")

        captured = capsys.readouterr()
        assert "build API" in captured.out
        assert "inProgress" in captured.out
        assert "refs/heads/main" in captured.out
        assert "CI-Build" in captured.out
