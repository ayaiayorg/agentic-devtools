"""Tests for _verify_comment_via_sdk()."""

import os
import sys
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.models import VerificationVerdict


class TestVerifyCommentViaSdk:
    """Tests for _verify_comment_via_sdk edge cases."""

    def test_sdk_import_failure_defaults_unresolve(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")

        with patch.dict(os.environ, {"COPILOT_GITHUB_TOKEN": "test-token"}, clear=False):
            with patch.dict(sys.modules, {"copilot": None, "copilot.session": None}):
                result = provider._verify_comment_via_sdk("fix this", "diff --git a/x b/x")

        assert result == VerificationVerdict.COMMENT_UNRESOLVE
