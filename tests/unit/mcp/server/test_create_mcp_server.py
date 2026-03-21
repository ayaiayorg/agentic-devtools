"""Tests for agentic_devtools.mcp.server.create_mcp_server."""

import asyncio
import os
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP

from agentic_devtools.mcp.server import (
    _AZURE_DEVOPS_MISSING_MSG,
    _JIRA_MISSING_MSG,
    create_mcp_server,
)


def get_tool_names(server: FastMCP) -> set[str]:
    """Return the set of tool names registered on *server*."""
    tools = asyncio.run(server.list_tools())
    return {t.name for t in tools}


class TestCreateMcpServer:
    """Tests for the create_mcp_server factory function."""

    def test_returns_fastmcp_instance(self):
        with patch.dict(os.environ, {}, clear=True):
            server = create_mcp_server()
        assert isinstance(server, FastMCP)

    def test_registers_jira_tools(self):
        with patch.dict(os.environ, {}, clear=True):
            server = create_mcp_server()
        names = get_tool_names(server)
        expected = {
            "jira_create_issue",
            "jira_create_epic",
            "jira_create_subtask",
            "jira_add_comment",
            "jira_fetch_issue_context",
        }
        assert expected.issubset(names)

    def test_registers_git_tools(self):
        with patch.dict(os.environ, {}, clear=True):
            server = create_mcp_server()
        names = get_tool_names(server)
        expected = {
            "git_stage_changes",
            "git_create_commit",
            "git_amend_commit",
            "git_push",
            "git_force_push",
            "git_publish_branch",
            "git_save_work",
            "git_get_recent_changes",
        }
        assert expected.issubset(names)

    def test_registers_azure_devops_tools(self):
        with patch.dict(os.environ, {}, clear=True):
            server = create_mcp_server()
        names = get_tool_names(server)
        expected = {
            "azure_devops_create_pull_request",
            "azure_devops_reply_to_thread",
            "azure_devops_add_comment",
            "azure_devops_update_review_narrative",
        }
        assert expected.issubset(names)

    def test_does_not_register_stub_tools(self):
        with patch.dict(os.environ, {}, clear=True):
            server = create_mcp_server()
        names = get_tool_names(server)
        # Stubs that raise NotImplementedError must NOT be registered
        assert "add_reviewer" not in names
        assert "complete_pull_request" not in names
        assert "file_review" not in names
        # Also check with azure_devops_ prefix
        assert "azure_devops_add_reviewer" not in names
        assert "azure_devops_complete_pull_request" not in names
        assert "azure_devops_file_review" not in names

    def test_total_tool_count(self):
        with patch.dict(os.environ, {}, clear=True):
            server = create_mcp_server()
        names = get_tool_names(server)
        # 5 Jira + 8 Git + 4 Azure DevOps = 17
        assert len(names) == 17


class TestMcpToolHandlersJira:
    """Test Jira MCP tool handlers delegate correctly."""

    _JIRA_ENV = {
        "JIRA_BASE_URL": "https://jira.example.com",
        "JIRA_API_TOKEN": "tok123",
    }

    def test_jira_create_issue_delegates(self):
        mock_result = {"issue_key": "PROJ-1", "url": "https://x/browse/PROJ-1", "raw_response": {}}
        with (
            patch.dict(os.environ, self._JIRA_ENV, clear=True),
            patch("agentic_devtools.mcp.server.tools_jira.create_issue", return_value=mock_result) as mock_fn,
        ):
            server = create_mcp_server()
            asyncio.run(
                server.call_tool(
                    "jira_create_issue",
                    {
                        "project_key": "PROJ",
                        "summary": "Test",
                        "issue_type": "Task",
                        "description": "Desc",
                        "labels": ["a"],
                    },
                )
            )
        mock_fn.assert_called_once()

    def test_jira_create_issue_returns_error_when_no_config(self):
        with patch.dict(os.environ, {}, clear=True):
            server = create_mcp_server()
            result = asyncio.run(
                server.call_tool(
                    "jira_create_issue",
                    {
                        "project_key": "PROJ",
                        "summary": "Test",
                        "issue_type": "Task",
                        "description": "Desc",
                        "labels": [],
                    },
                )
            )
        # call_tool returns a list of content items
        assert any(_JIRA_MISSING_MSG in str(item) for item in result)

    def test_jira_create_issue_returns_error_on_exception(self):
        with (
            patch.dict(os.environ, self._JIRA_ENV, clear=True),
            patch(
                "agentic_devtools.mcp.server.tools_jira.create_issue",
                side_effect=ValueError("bad input"),
            ),
        ):
            server = create_mcp_server()
            result = asyncio.run(
                server.call_tool(
                    "jira_create_issue",
                    {
                        "project_key": "PROJ",
                        "summary": "Test",
                        "issue_type": "Task",
                        "description": "Desc",
                        "labels": [],
                    },
                )
            )
        assert any("bad input" in str(item) for item in result)

    def test_jira_create_epic_delegates(self):
        mock_result = {"issue_key": "PROJ-2", "url": "", "raw_response": {}}
        with (
            patch.dict(os.environ, self._JIRA_ENV, clear=True),
            patch("agentic_devtools.mcp.server.tools_jira.create_epic", return_value=mock_result) as mock_fn,
        ):
            server = create_mcp_server()
            asyncio.run(
                server.call_tool(
                    "jira_create_epic",
                    {
                        "project_key": "PROJ",
                        "summary": "Epic",
                        "epic_name": "MyEpic",
                        "description": "Desc",
                        "labels": [],
                    },
                )
            )
        mock_fn.assert_called_once()

    def test_jira_create_epic_error_no_config(self):
        with patch.dict(os.environ, {}, clear=True):
            server = create_mcp_server()
            result = asyncio.run(
                server.call_tool(
                    "jira_create_epic",
                    {
                        "project_key": "PROJ",
                        "summary": "Epic",
                        "epic_name": "MyEpic",
                        "description": "Desc",
                        "labels": [],
                    },
                )
            )
        assert any(_JIRA_MISSING_MSG in str(item) for item in result)

    def test_jira_create_epic_exception(self):
        with (
            patch.dict(os.environ, self._JIRA_ENV, clear=True),
            patch("agentic_devtools.mcp.server.tools_jira.create_epic", side_effect=RuntimeError("fail")),
        ):
            server = create_mcp_server()
            result = asyncio.run(
                server.call_tool(
                    "jira_create_epic",
                    {
                        "project_key": "P",
                        "summary": "E",
                        "epic_name": "N",
                        "description": "D",
                        "labels": [],
                    },
                )
            )
        assert any("fail" in str(item) for item in result)

    def test_jira_create_subtask_delegates(self):
        mock_result = {"issue_key": "PROJ-3", "url": "", "raw_response": {}}
        with (
            patch.dict(os.environ, self._JIRA_ENV, clear=True),
            patch("agentic_devtools.mcp.server.tools_jira.create_subtask", return_value=mock_result) as mock_fn,
        ):
            server = create_mcp_server()
            asyncio.run(
                server.call_tool(
                    "jira_create_subtask",
                    {
                        "project_key": "PROJ",
                        "summary": "Sub",
                        "description": "D",
                        "labels": [],
                        "parent_key": "PROJ-1",
                    },
                )
            )
        mock_fn.assert_called_once()

    def test_jira_create_subtask_error_no_config(self):
        with patch.dict(os.environ, {}, clear=True):
            server = create_mcp_server()
            result = asyncio.run(
                server.call_tool(
                    "jira_create_subtask",
                    {
                        "project_key": "P",
                        "summary": "S",
                        "description": "D",
                        "labels": [],
                        "parent_key": "P-1",
                    },
                )
            )
        assert any(_JIRA_MISSING_MSG in str(item) for item in result)

    def test_jira_create_subtask_exception(self):
        with (
            patch.dict(os.environ, self._JIRA_ENV, clear=True),
            patch("agentic_devtools.mcp.server.tools_jira.create_subtask", side_effect=RuntimeError("err")),
        ):
            server = create_mcp_server()
            result = asyncio.run(
                server.call_tool(
                    "jira_create_subtask",
                    {
                        "project_key": "P",
                        "summary": "S",
                        "description": "D",
                        "labels": [],
                        "parent_key": "P-1",
                    },
                )
            )
        assert any("err" in str(item) for item in result)

    def test_jira_add_comment_delegates(self):
        mock_result = {"comment_id": "100", "raw_response": {}}
        with (
            patch.dict(os.environ, self._JIRA_ENV, clear=True),
            patch("agentic_devtools.mcp.server.tools_jira.add_comment", return_value=mock_result) as mock_fn,
        ):
            server = create_mcp_server()
            asyncio.run(
                server.call_tool(
                    "jira_add_comment",
                    {
                        "issue_key": "PROJ-1",
                        "comment": "Hello",
                    },
                )
            )
        mock_fn.assert_called_once()

    def test_jira_add_comment_error_no_config(self):
        with patch.dict(os.environ, {}, clear=True):
            server = create_mcp_server()
            result = asyncio.run(
                server.call_tool(
                    "jira_add_comment",
                    {
                        "issue_key": "X-1",
                        "comment": "Hi",
                    },
                )
            )
        assert any(_JIRA_MISSING_MSG in str(item) for item in result)

    def test_jira_add_comment_exception(self):
        with (
            patch.dict(os.environ, self._JIRA_ENV, clear=True),
            patch("agentic_devtools.mcp.server.tools_jira.add_comment", side_effect=RuntimeError("oops")),
        ):
            server = create_mcp_server()
            result = asyncio.run(
                server.call_tool(
                    "jira_add_comment",
                    {
                        "issue_key": "X-1",
                        "comment": "Hi",
                    },
                )
            )
        assert any("oops" in str(item) for item in result)

    def test_jira_fetch_issue_context_delegates(self):
        mock_result = {"issue": {}, "parent_issue": None, "epic_issue": None, "remote_links": []}
        with (
            patch.dict(os.environ, self._JIRA_ENV, clear=True),
            patch("agentic_devtools.mcp.server.tools_jira.fetch_issue_context", return_value=mock_result) as mock_fn,
        ):
            server = create_mcp_server()
            asyncio.run(
                server.call_tool(
                    "jira_fetch_issue_context",
                    {
                        "issue_key": "PROJ-1",
                    },
                )
            )
        mock_fn.assert_called_once()

    def test_jira_fetch_issue_context_error_no_config(self):
        with patch.dict(os.environ, {}, clear=True):
            server = create_mcp_server()
            result = asyncio.run(
                server.call_tool(
                    "jira_fetch_issue_context",
                    {
                        "issue_key": "X-1",
                    },
                )
            )
        assert any(_JIRA_MISSING_MSG in str(item) for item in result)

    def test_jira_fetch_issue_context_exception(self):
        with (
            patch.dict(os.environ, self._JIRA_ENV, clear=True),
            patch("agentic_devtools.mcp.server.tools_jira.fetch_issue_context", side_effect=RuntimeError("fail")),
        ):
            server = create_mcp_server()
            result = asyncio.run(
                server.call_tool(
                    "jira_fetch_issue_context",
                    {
                        "issue_key": "X-1",
                    },
                )
            )
        assert any("fail" in str(item) for item in result)


class TestMcpToolHandlersGit:
    """Test Git MCP tool handlers delegate correctly."""

    def test_git_stage_changes_delegates(self):
        mock_result = {"success": True, "message": "staged"}
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("agentic_devtools.mcp.server.tools_git.stage_changes", return_value=mock_result) as mock_fn,
        ):
            server = create_mcp_server()
            asyncio.run(server.call_tool("git_stage_changes", {}))
        mock_fn.assert_called_once_with(dry_run=False)

    def test_git_stage_changes_exception(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("agentic_devtools.mcp.server.tools_git.stage_changes", side_effect=RuntimeError("git err")),
        ):
            server = create_mcp_server()
            result = asyncio.run(server.call_tool("git_stage_changes", {}))
        assert any("git err" in str(item) for item in result)

    def test_git_create_commit_delegates(self):
        mock_result = {"success": True, "message": "committed"}
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("agentic_devtools.mcp.server.tools_git.create_commit", return_value=mock_result) as mock_fn,
        ):
            server = create_mcp_server()
            asyncio.run(server.call_tool("git_create_commit", {"message": "msg"}))
        mock_fn.assert_called_once_with(message="msg", dry_run=False)

    def test_git_create_commit_exception(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("agentic_devtools.mcp.server.tools_git.create_commit", side_effect=RuntimeError("err")),
        ):
            server = create_mcp_server()
            result = asyncio.run(server.call_tool("git_create_commit", {"message": "m"}))
        assert any("err" in str(item) for item in result)

    def test_git_amend_commit_delegates(self):
        mock_result = {"success": True, "message": "amended"}
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("agentic_devtools.mcp.server.tools_git.amend_commit", return_value=mock_result) as mock_fn,
        ):
            server = create_mcp_server()
            asyncio.run(server.call_tool("git_amend_commit", {"message": "new msg"}))
        mock_fn.assert_called_once_with(message="new msg", dry_run=False)

    def test_git_amend_commit_exception(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("agentic_devtools.mcp.server.tools_git.amend_commit", side_effect=RuntimeError("err")),
        ):
            server = create_mcp_server()
            result = asyncio.run(server.call_tool("git_amend_commit", {"message": "m"}))
        assert any("err" in str(item) for item in result)

    def test_git_push_delegates(self):
        mock_result = {"success": True, "message": "pushed"}
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("agentic_devtools.mcp.server.tools_git.push", return_value=mock_result) as mock_fn,
        ):
            server = create_mcp_server()
            asyncio.run(server.call_tool("git_push", {}))
        mock_fn.assert_called_once_with(dry_run=False)

    def test_git_push_exception(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("agentic_devtools.mcp.server.tools_git.push", side_effect=RuntimeError("err")),
        ):
            server = create_mcp_server()
            result = asyncio.run(server.call_tool("git_push", {}))
        assert any("err" in str(item) for item in result)

    def test_git_force_push_delegates(self):
        mock_result = {"success": True, "message": "force pushed"}
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("agentic_devtools.mcp.server.tools_git.force_push", return_value=mock_result) as mock_fn,
        ):
            server = create_mcp_server()
            asyncio.run(server.call_tool("git_force_push", {}))
        mock_fn.assert_called_once_with(dry_run=False)

    def test_git_force_push_exception(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("agentic_devtools.mcp.server.tools_git.force_push", side_effect=RuntimeError("err")),
        ):
            server = create_mcp_server()
            result = asyncio.run(server.call_tool("git_force_push", {}))
        assert any("err" in str(item) for item in result)

    def test_git_publish_branch_delegates(self):
        mock_result = {"success": True, "message": "published"}
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("agentic_devtools.mcp.server.tools_git.publish_branch", return_value=mock_result) as mock_fn,
        ):
            server = create_mcp_server()
            asyncio.run(server.call_tool("git_publish_branch", {}))
        mock_fn.assert_called_once_with(dry_run=False)

    def test_git_publish_branch_exception(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("agentic_devtools.mcp.server.tools_git.publish_branch", side_effect=RuntimeError("err")),
        ):
            server = create_mcp_server()
            result = asyncio.run(server.call_tool("git_publish_branch", {}))
        assert any("err" in str(item) for item in result)

    def test_git_save_work_delegates(self):
        mock_result = {"success": True, "message": "saved", "operations": ["stage", "commit", "push"]}
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("agentic_devtools.mcp.server.tools_git.save_work", return_value=mock_result) as mock_fn,
        ):
            server = create_mcp_server()
            asyncio.run(server.call_tool("git_save_work", {"commit_message": "fix"}))
        mock_fn.assert_called_once_with(
            commit_message="fix",
            amend=False,
            skip_stage=False,
            skip_push=False,
            dry_run=False,
        )

    def test_git_save_work_exception(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("agentic_devtools.mcp.server.tools_git.save_work", side_effect=RuntimeError("err")),
        ):
            server = create_mcp_server()
            result = asyncio.run(server.call_tool("git_save_work", {"commit_message": "m"}))
        assert any("err" in str(item) for item in result)

    def test_git_get_recent_changes_delegates(self):
        mock_result = {"commits": [{"sha": "abc"}]}
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("agentic_devtools.mcp.server.tools_git.get_recent_changes", return_value=mock_result) as mock_fn,
        ):
            server = create_mcp_server()
            asyncio.run(server.call_tool("git_get_recent_changes", {}))
        mock_fn.assert_called_once_with(num_commits=10)

    def test_git_get_recent_changes_exception(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("agentic_devtools.mcp.server.tools_git.get_recent_changes", side_effect=RuntimeError("err")),
        ):
            server = create_mcp_server()
            result = asyncio.run(server.call_tool("git_get_recent_changes", {}))
        assert any("err" in str(item) for item in result)


class TestMcpToolHandlersAzureDevOps:
    """Test Azure DevOps MCP tool handlers delegate correctly."""

    _ADO_ENV = {
        "AZURE_DEVOPS_ORG": "https://dev.azure.com/myorg",
        "AZURE_DEVOPS_PROJECT": "MyProject",
        "AZURE_DEVOPS_PAT": "mypat",
        "AZURE_DEVOPS_REPOSITORY": "my-repo",
    }

    def test_azure_devops_create_pull_request_delegates(self):
        mock_result = {"pull_request_id": 123, "url": "https://x", "raw_output": ""}
        with (
            patch.dict(os.environ, self._ADO_ENV, clear=True),
            patch(
                "agentic_devtools.mcp.server.tools_azure_devops.create_pull_request",
                return_value=mock_result,
            ) as mock_fn,
        ):
            server = create_mcp_server()
            asyncio.run(
                server.call_tool(
                    "azure_devops_create_pull_request",
                    {
                        "source_branch": "feature/x",
                        "title": "My PR",
                    },
                )
            )
        mock_fn.assert_called_once()

    def test_azure_devops_create_pull_request_error_no_config(self):
        with patch.dict(os.environ, {}, clear=True):
            server = create_mcp_server()
            result = asyncio.run(
                server.call_tool(
                    "azure_devops_create_pull_request",
                    {
                        "source_branch": "feature/x",
                        "title": "PR",
                    },
                )
            )
        assert any(_AZURE_DEVOPS_MISSING_MSG in str(item) for item in result)

    def test_azure_devops_create_pull_request_exception(self):
        with (
            patch.dict(os.environ, self._ADO_ENV, clear=True),
            patch(
                "agentic_devtools.mcp.server.tools_azure_devops.create_pull_request",
                side_effect=RuntimeError("az fail"),
            ),
        ):
            server = create_mcp_server()
            result = asyncio.run(
                server.call_tool(
                    "azure_devops_create_pull_request",
                    {
                        "source_branch": "f/x",
                        "title": "PR",
                    },
                )
            )
        assert any("az fail" in str(item) for item in result)

    def test_azure_devops_reply_to_thread_delegates(self):
        mock_result = {"comment_id": 1, "thread_resolved": False}
        with (
            patch.dict(os.environ, self._ADO_ENV, clear=True),
            patch(
                "agentic_devtools.mcp.server.tools_azure_devops.reply_to_pull_request_thread",
                return_value=mock_result,
            ) as mock_fn,
        ):
            server = create_mcp_server()
            asyncio.run(
                server.call_tool(
                    "azure_devops_reply_to_thread",
                    {
                        "pull_request_id": 100,
                        "thread_id": 200,
                        "content": "Reply",
                    },
                )
            )
        mock_fn.assert_called_once()

    def test_azure_devops_reply_to_thread_error_no_config(self):
        with patch.dict(os.environ, {}, clear=True):
            server = create_mcp_server()
            result = asyncio.run(
                server.call_tool(
                    "azure_devops_reply_to_thread",
                    {
                        "pull_request_id": 1,
                        "thread_id": 2,
                        "content": "x",
                    },
                )
            )
        assert any(_AZURE_DEVOPS_MISSING_MSG in str(item) for item in result)

    def test_azure_devops_reply_to_thread_exception(self):
        with (
            patch.dict(os.environ, self._ADO_ENV, clear=True),
            patch(
                "agentic_devtools.mcp.server.tools_azure_devops.reply_to_pull_request_thread",
                side_effect=RuntimeError("err"),
            ),
        ):
            server = create_mcp_server()
            result = asyncio.run(
                server.call_tool(
                    "azure_devops_reply_to_thread",
                    {
                        "pull_request_id": 1,
                        "thread_id": 2,
                        "content": "x",
                    },
                )
            )
        assert any("err" in str(item) for item in result)

    def test_azure_devops_add_comment_delegates(self):
        mock_result = {"thread_id": 10, "comment_id": 20}
        with (
            patch.dict(os.environ, self._ADO_ENV, clear=True),
            patch(
                "agentic_devtools.mcp.server.tools_azure_devops.add_pull_request_comment",
                return_value=mock_result,
            ) as mock_fn,
        ):
            server = create_mcp_server()
            asyncio.run(
                server.call_tool(
                    "azure_devops_add_comment",
                    {
                        "pull_request_id": 100,
                        "content": "Comment text",
                    },
                )
            )
        mock_fn.assert_called_once()

    def test_azure_devops_add_comment_error_no_config(self):
        with patch.dict(os.environ, {}, clear=True):
            server = create_mcp_server()
            result = asyncio.run(
                server.call_tool(
                    "azure_devops_add_comment",
                    {
                        "pull_request_id": 1,
                        "content": "x",
                    },
                )
            )
        assert any(_AZURE_DEVOPS_MISSING_MSG in str(item) for item in result)

    def test_azure_devops_add_comment_exception(self):
        with (
            patch.dict(os.environ, self._ADO_ENV, clear=True),
            patch(
                "agentic_devtools.mcp.server.tools_azure_devops.add_pull_request_comment",
                side_effect=RuntimeError("err"),
            ),
        ):
            server = create_mcp_server()
            result = asyncio.run(
                server.call_tool(
                    "azure_devops_add_comment",
                    {
                        "pull_request_id": 1,
                        "content": "x",
                    },
                )
            )
        assert any("err" in str(item) for item in result)

    def test_azure_devops_update_review_narrative_delegates(self):
        mock_result = {"success": True, "message": "updated"}
        with (
            patch.dict(os.environ, self._ADO_ENV, clear=True),
            patch(
                "agentic_devtools.mcp.server.tools_azure_devops.update_review_narrative",
                return_value=mock_result,
            ) as mock_fn,
        ):
            server = create_mcp_server()
            asyncio.run(
                server.call_tool(
                    "azure_devops_update_review_narrative",
                    {
                        "pull_request_id": 100,
                        "content": "Narrative text",
                    },
                )
            )
        mock_fn.assert_called_once()

    def test_azure_devops_update_review_narrative_error_no_config(self):
        with patch.dict(os.environ, {}, clear=True):
            server = create_mcp_server()
            result = asyncio.run(
                server.call_tool(
                    "azure_devops_update_review_narrative",
                    {
                        "pull_request_id": 1,
                        "content": "x",
                    },
                )
            )
        assert any(_AZURE_DEVOPS_MISSING_MSG in str(item) for item in result)

    def test_azure_devops_update_review_narrative_exception(self):
        with (
            patch.dict(os.environ, self._ADO_ENV, clear=True),
            patch(
                "agentic_devtools.mcp.server.tools_azure_devops.update_review_narrative",
                side_effect=RuntimeError("err"),
            ),
        ):
            server = create_mcp_server()
            result = asyncio.run(
                server.call_tool(
                    "azure_devops_update_review_narrative",
                    {
                        "pull_request_id": 1,
                        "content": "x",
                    },
                )
            )
        assert any("err" in str(item) for item in result)
