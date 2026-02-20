"""
Tests for run_details_commands module.
"""

from agentic_devtools.cli.azure_devops.run_details_commands import (
    _print_parameters,
)


class TestPrintParameters:
    """Tests for _print_parameters helper."""

    def test_pipeline_template_parameters(self, capsys):
        """Should print templateParameters for pipeline source."""
        data = {"templateParameters": {"env": "dev", "deploy": "true"}}
        _print_parameters(data, "pipeline")

        captured = capsys.readouterr()
        assert "env: dev" in captured.out
        assert "deploy: true" in captured.out

    def test_build_json_parameters(self, capsys):
        """Should parse JSON parameters for build source."""
        data = {"parameters": '{"env": "prod", "version": "1.0"}'}
        _print_parameters(data, "build")

        captured = capsys.readouterr()
        assert "env: prod" in captured.out
        assert "version: 1.0" in captured.out

    def test_no_parameters(self, capsys):
        """Should print (none) when no parameters present."""
        data = {}
        _print_parameters(data, "build")

        captured = capsys.readouterr()
        assert "(none)" in captured.out

    def test_invalid_json_parameters(self, capsys):
        """Should handle invalid JSON in build parameters."""
        data = {"parameters": "not-valid-json"}
        _print_parameters(data, "build")

        captured = capsys.readouterr()
        assert "raw" in captured.out
