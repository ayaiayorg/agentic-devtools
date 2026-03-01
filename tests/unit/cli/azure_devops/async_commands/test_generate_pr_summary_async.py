"""Tests for generate_pr_summary_async function."""

import warnings

from agentic_devtools.cli.azure_devops.async_commands import generate_pr_summary_async
from tests.unit.cli.azure_devops.async_commands._helpers import assert_function_in_script, get_script_from_call


class TestGeneratePrSummaryAsync:
    def test_spawns_background_task(self, mock_background_and_state, capsys):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            generate_pr_summary_async()
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(
            script, "agentic_devtools.cli.azure_devops.pr_summary_commands", "generate_overarching_pr_comments_cli"
        )

    def test_emits_deprecation_warning(self, mock_background_and_state):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            generate_pr_summary_async()
        assert any(issubclass(w.category, DeprecationWarning) for w in caught)
        messages = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
        assert any("deprecated" in m.lower() for m in messages)

    def test_prints_deprecation_message(self, mock_background_and_state, capsys):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            generate_pr_summary_async()
        captured = capsys.readouterr()
        dep_messages = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
        assert dep_messages, "Expected at least one DeprecationWarning"
        for message in dep_messages:
            assert message in captured.out
