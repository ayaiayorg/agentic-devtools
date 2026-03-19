"""Tests for agentic_devtools.skill_injector._extract_description."""

from agentic_devtools.skill_injector import _extract_description


class TestExtractDescription:
    """Tests for the _extract_description helper."""

    def test_agents_uses_description_key(self):
        """For agents, extracts the 'description' key."""
        fm = {"description": "My agent description"}
        assert _extract_description(fm, "agents") == "My agent description"

    def test_prompts_uses_agent_key(self):
        """For prompts, extracts the 'agent' key."""
        fm = {"agent": "my-agent-name"}
        assert _extract_description(fm, "prompts") == "my-agent-name"

    def test_fallback_when_key_missing(self):
        """Falls back to em dash when the expected key is missing."""
        assert _extract_description({}, "agents") == "\u2014"
        assert _extract_description({}, "prompts") == "\u2014"

    def test_fallback_when_value_is_none(self):
        """Falls back to em dash when the value is None."""
        assert _extract_description({"description": None}, "agents") == "\u2014"

    def test_fallback_when_value_is_empty_string(self):
        """Falls back to em dash when the value is an empty string."""
        assert _extract_description({"description": ""}, "agents") == "\u2014"
