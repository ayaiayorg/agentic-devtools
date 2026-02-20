"""
Tests for role_commands module - Jira project role management.
"""

import re
from unittest.mock import MagicMock

from agdt_ai_helpers.cli.jira.role_commands import (
    _check_user_exists,
)


class TestRoleIdExtraction:
    """Tests for role ID extraction from URLs."""

    def test_extract_role_id_from_url(self):
        """Test extracting role ID from Jira role URL."""
        role_url = "https://jira.example.com/rest/api/2/project/PROJ/role/12345"
        pattern = re.compile(r"/role/(\d+)$")
        match = pattern.search(role_url)

        assert match is not None
        assert match.group(1) == "12345"

    def test_extract_role_id_different_numbers(self):
        """Test extracting various role IDs."""
        test_cases = [
            ("https://jira.example.com/rest/api/2/project/KEY/role/10100", "10100"),
            ("https://jira.example.com/rest/api/2/project/KEY/role/99999", "99999"),
            ("https://jira.example.com/rest/api/2/project/KEY/role/1", "1"),
        ]

        pattern = re.compile(r"/role/(\d+)$")
        for url, expected_id in test_cases:
            match = pattern.search(url)
            assert match is not None
            assert match.group(1) == expected_id

    def test_no_role_id_in_url(self):
        """Test URL without role ID."""
        url = "https://jira.example.com/rest/api/2/project/KEY"
        pattern = re.compile(r"/role/(\d+)$")
        match = pattern.search(url)

        assert match is None
