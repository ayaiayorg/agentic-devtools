"""Tests for confirm_suggestion_addressed_async function."""

from agentic_devtools.cli.azure_devops.async_commands import confirm_suggestion_addressed_async
from tests.unit.cli.azure_devops.async_commands._helpers import assert_function_in_script, get_script_from_call


class TestConfirmSuggestionAddressedAsync:
    def test_spawns_background_task(self, mock_background_and_state, capsys):
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "12345")
        set_value("thread_id", "67890")
        set_value("suggestion.commit_hash", "abc1234")
        confirm_suggestion_addressed_async()
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(
            script, "agentic_devtools.cli.azure_devops.suggestion_commands", "confirm_suggestion_addressed"
        )

    def test_cli_args_override_state(self, mock_background_and_state, capsys):
        from agentic_devtools.state import get_value, set_value

        set_value("pull_request_id", "old")
        set_value("thread_id", "old")
        set_value("suggestion.commit_hash", "old")
        confirm_suggestion_addressed_async(pull_request_id="111", thread_id="222", commit_hash="new_hash")
        assert get_value("pull_request_id") == "111"
        assert get_value("thread_id") == "222"
        assert get_value("suggestion.commit_hash") == "new_hash"
