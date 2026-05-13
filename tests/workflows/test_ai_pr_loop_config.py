"""Tests for .github/ai-pr-loop-config.json schema validation (T019).

Validates that the config file used by workflow-approval-monitor.yml
has the correct structure: non-empty array of string entries with no wildcards.
"""

import json
from pathlib import Path

# Path to the config file relative to repo root
CONFIG_PATH = Path(__file__).resolve().parents[2] / ".github" / "ai-pr-loop-config.json"


class TestAiPrLoopConfig:
    """Validate the structure of .github/ai-pr-loop-config.json (FR-007)."""

    def test_config_file_exists(self):
        """Config file must exist at the expected path."""
        assert CONFIG_PATH.exists(), f"Config file not found at {CONFIG_PATH}"

    def test_config_is_valid_json(self):
        """Config file must be valid JSON."""
        content = CONFIG_PATH.read_text(encoding="utf-8")
        config = json.loads(content)
        assert isinstance(config, dict)

    def test_config_has_trusted_bot_accounts(self):
        """Config must have a 'trusted_bot_accounts' key."""
        content = CONFIG_PATH.read_text(encoding="utf-8")
        config = json.loads(content)
        assert "trusted_bot_accounts" in config

    def test_trusted_bot_accounts_is_non_empty_array(self):
        """trusted_bot_accounts must be a non-empty array."""
        content = CONFIG_PATH.read_text(encoding="utf-8")
        config = json.loads(content)
        accounts = config["trusted_bot_accounts"]
        assert isinstance(accounts, list)
        assert len(accounts) > 0, "trusted_bot_accounts must not be empty"

    def test_trusted_bot_accounts_are_strings(self):
        """Each entry in trusted_bot_accounts must be a string."""
        content = CONFIG_PATH.read_text(encoding="utf-8")
        config = json.loads(content)
        for account in config["trusted_bot_accounts"]:
            assert isinstance(account, str), f"Expected string, got {type(account)}: {account}"

    def test_trusted_bot_accounts_no_wildcards(self):
        """No entry in trusted_bot_accounts may contain wildcard characters (NFR-004)."""
        content = CONFIG_PATH.read_text(encoding="utf-8")
        config = json.loads(content)
        for account in config["trusted_bot_accounts"]:
            assert "*" not in account, f"Wildcard found in account: {account}"
            assert "?" not in account, f"Wildcard found in account: {account}"

    def test_trusted_bot_accounts_no_empty_strings(self):
        """No entry in trusted_bot_accounts may be an empty string."""
        content = CONFIG_PATH.read_text(encoding="utf-8")
        config = json.loads(content)
        for account in config["trusted_bot_accounts"]:
            assert account.strip() != "", "Empty string found in trusted_bot_accounts"

    def test_config_contains_expected_bots(self):
        """Config should contain the standard trusted bot accounts."""
        content = CONFIG_PATH.read_text(encoding="utf-8")
        config = json.loads(content)
        accounts = config["trusted_bot_accounts"]
        assert "copilot-swe-agent[bot]" in accounts
        assert "github-actions[bot]" in accounts
