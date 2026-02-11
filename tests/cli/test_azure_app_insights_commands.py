"""Tests for azure/app_insights_commands.py module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from agentic_devtools.cli.azure.app_insights_commands import (
    FABRIC_DAP_ERROR_QUERY,
    FABRIC_DAP_PROVISIONING_QUERY,
    FABRIC_DAP_TIMELINE_QUERY,
    WORKBENCH_FABRIC_ROLE_PATTERNS,
    _build_combined_filter,
    _convert_sdk_response_to_dict,
    _format_query,
    _get_temp_output_dir,
    _print_query_results,
    _write_results_to_file,
    query_app_insights,
    query_app_insights_async,
    query_fabric_dap_errors,
    query_fabric_dap_errors_async,
    query_fabric_dap_provisioning,
    query_fabric_dap_provisioning_async,
    query_fabric_dap_timeline,
    query_fabric_dap_timeline_async,
)


class TestGetTempOutputDir:
    """Tests for _get_temp_output_dir function."""

    @patch("agentic_devtools.cli.azure.app_insights_commands.get_state_dir")
    def test_returns_path_from_get_state_dir(self, mock_get_state_dir):
        """Test that it delegates to get_state_dir."""
        mock_get_state_dir.return_value = Path("/some/temp/dir")
        result = _get_temp_output_dir()
        assert result == Path("/some/temp/dir")
        mock_get_state_dir.assert_called_once()


class TestWorkbenchPatterns:
    """Tests for WORKBENCH_FABRIC_ROLE_PATTERNS constant."""

    def test_stnd_pattern(self):
        """Test STND workbench pattern."""
        assert WORKBENCH_FABRIC_ROLE_PATTERNS["STND"] == "stndfabric"

    def test_known_workbenches_exist(self):
        """Test that all known workbenches have patterns."""
        assert "STND" in WORKBENCH_FABRIC_ROLE_PATTERNS
        assert "DEVA" in WORKBENCH_FABRIC_ROLE_PATTERNS
        assert "DEVB" in WORKBENCH_FABRIC_ROLE_PATTERNS


class TestBuildCombinedFilter:
    """Tests for _build_combined_filter function."""

    def test_basic_filter_with_timespan(self):
        """Test basic filter with only timespan."""
        result = _build_combined_filter("1h")
        assert "timestamp > ago(1h)" in result
        assert result.startswith("| where ")

    def test_filter_with_workbench(self):
        """Test filter includes workbench-specific role pattern."""
        result = _build_combined_filter("1h", workbench="STND")
        assert "stndfabric" in result

    def test_filter_with_unknown_workbench(self):
        """Test filter with unknown workbench uses lowercase key."""
        result = _build_combined_filter("1h", workbench="NEWWB")
        assert "newwbfabric" in result

    def test_filter_without_workbench_includes_generic_fabric(self):
        """Test filter without workbench uses generic fabric filter."""
        result = _build_combined_filter("1h")
        assert "cloud_RoleName contains 'fabric'" in result

    def test_filter_with_dataproduct_id(self):
        """Test filter includes dataproduct filter."""
        result = _build_combined_filter("1h", dataproduct_id="dp-test-123")
        assert "dp-test-123" in result
        assert "message contains" in result

    def test_filter_without_mgmt(self):
        """Test filter excludes management backend when include_mgmt=False."""
        result = _build_combined_filter("1h", include_mgmt=False)
        assert "app-restapi-mgmt" not in result

    def test_filter_with_mgmt(self):
        """Test filter includes management backend by default."""
        result = _build_combined_filter("1h", include_mgmt=True)
        assert "app-restapi-mgmt" in result

    def test_filter_combines_all_conditions(self):
        """Test filter combines all conditions with AND."""
        result = _build_combined_filter("2h", dataproduct_id="dp-x", workbench="STND")
        assert "timestamp > ago(2h)" in result
        assert "stndfabric" in result
        assert "dp-x" in result
        assert " and " in result


class TestFormatQuery:
    """Tests for _format_query function."""

    def test_formats_error_query(self):
        """Test formatting the error query template."""
        result = _format_query(FABRIC_DAP_ERROR_QUERY, timespan="1h", limit=50)
        assert "timestamp > ago(1h)" in result
        assert "take 50" in result
        assert "severityLevel >= 3" in result

    def test_formats_provisioning_query(self):
        """Test formatting the provisioning query template."""
        result = _format_query(FABRIC_DAP_PROVISIONING_QUERY, timespan="30m", limit=200)
        assert "timestamp > ago(30m)" in result
        assert "take 200" in result

    def test_formats_timeline_query(self):
        """Test formatting the timeline query template."""
        result = _format_query(FABRIC_DAP_TIMELINE_QUERY, timespan="4h", limit=500)
        assert "timestamp > ago(4h)" in result
        assert "take 500" in result
        assert "DataproductProvisioningService" in result


class TestConvertSdkResponseToDict:
    """Tests for _convert_sdk_response_to_dict function."""

    def test_converts_single_table(self):
        """Test conversion of single table response."""
        mock_table = MagicMock()
        mock_table.columns = ["timestamp", "message"]
        mock_table.rows = [["2024-01-01", "test message"], ["2024-01-02", "another"]]

        result = _convert_sdk_response_to_dict([mock_table])
        assert "tables" in result
        assert len(result["tables"]) == 1
        assert len(result["tables"][0]["columns"]) == 2
        assert len(result["tables"][0]["rows"]) == 2

    def test_converts_empty_tables(self):
        """Test conversion of empty response."""
        result = _convert_sdk_response_to_dict([])
        assert result == {"tables": []}

    def test_column_names_preserved(self):
        """Test that column names are preserved."""
        mock_table = MagicMock()
        mock_table.columns = ["timestamp", "severity", "message"]
        mock_table.rows = []

        result = _convert_sdk_response_to_dict([mock_table])
        col_names = [c["name"] for c in result["tables"][0]["columns"]]
        assert col_names == ["timestamp", "severity", "message"]


class TestWriteResultsToFile:
    """Tests for _write_results_to_file function."""

    def test_writes_results(self, tmp_path):
        """Test writing results to file."""
        output_file = tmp_path / "results.txt"
        data = {
            "tables": [
                {
                    "columns": [{"name": "timestamp"}, {"name": "message"}],
                    "rows": [["2024-01-01", "test message"]],
                }
            ]
        }
        _write_results_to_file(data, output_file)
        content = output_file.read_text()
        assert "Query Results" in content
        assert "test message" in content
        assert "Total: 1 rows" in content

    def test_writes_empty_results(self, tmp_path):
        """Test writing empty results."""
        output_file = tmp_path / "results.txt"
        data = {"tables": []}
        _write_results_to_file(data, output_file)
        content = output_file.read_text()
        assert "No results found" in content

    def test_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created."""
        output_file = tmp_path / "subdir" / "deep" / "results.txt"
        data = {"tables": []}
        _write_results_to_file(data, output_file)
        assert output_file.exists()


class TestPrintQueryResults:
    """Tests for _print_query_results function."""

    def test_prints_dry_run(self, capsys):
        """Test dry_run data is silently returned."""
        _print_query_results({"dry_run": True})
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_prints_no_results_empty_tables(self, capsys):
        """Test no results message for empty tables."""
        _print_query_results({"tables": []})
        assert "No results found" in capsys.readouterr().out

    def test_prints_no_results_empty_rows(self, capsys):
        """Test no results message for empty rows."""
        data = {"tables": [{"columns": [{"name": "a"}], "rows": []}]}
        _print_query_results(data)
        assert "No results found" in capsys.readouterr().out

    def test_prints_table_format(self, capsys):
        """Test table format output."""
        data = {
            "tables": [
                {
                    "columns": [{"name": "timestamp"}, {"name": "message"}],
                    "rows": [["2024-01-01", "hello"]],
                }
            ]
        }
        _print_query_results(data, format_type="table")
        output = capsys.readouterr().out
        assert "Found 1 results" in output
        assert "timestamp" in output

    def test_prints_block_format(self, capsys):
        """Test block format output."""
        data = {
            "tables": [
                {
                    "columns": [{"name": "timestamp"}, {"name": "message"}],
                    "rows": [["2024-01-01", "hello"]],
                }
            ]
        }
        _print_query_results(data, format_type="block")
        output = capsys.readouterr().out
        assert "Result 1" in output
        assert "timestamp: 2024-01-01" in output


class TestQueryAppInsights:
    """Tests for query_app_insights function."""

    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.is_dry_run",
        return_value=False,
    )
    @patch("agentic_devtools.cli.azure.app_insights_commands.get_value")
    def test_exits_when_no_query(self, mock_get, mock_dry):
        """Test exits with error when no query is set."""
        mock_get.side_effect = lambda k: None
        with pytest.raises(SystemExit) as exc:
            query_app_insights()
        assert exc.value.code == 1

    @patch("agentic_devtools.cli.azure.app_insights_commands._print_query_results")
    @patch("agentic_devtools.cli.azure.app_insights_commands._run_app_insights_query")
    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.is_dry_run", return_value=True
    )
    @patch("agentic_devtools.cli.azure.app_insights_commands.get_value")
    def test_dry_run(self, mock_get, mock_dry, mock_run, mock_print):
        """Test dry run mode."""
        mock_get.side_effect = lambda k: {"azure.query": "traces | take 10"}.get(k)
        mock_run.return_value = {"dry_run": True}
        query_app_insights()
        mock_run.assert_called_once()
        assert mock_run.call_args[1]["dry_run"] is True

    @patch("agentic_devtools.cli.azure.app_insights_commands._print_query_results")
    @patch("agentic_devtools.cli.azure.app_insights_commands._run_app_insights_query")
    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.is_dry_run",
        return_value=False,
    )
    @patch("agentic_devtools.cli.azure.app_insights_commands.get_value")
    def test_exits_on_none_result(self, mock_get, mock_dry, mock_run, mock_print):
        """Test exits when query returns None."""
        mock_get.side_effect = lambda k: {"azure.query": "traces | take 10"}.get(k)
        mock_run.return_value = None
        with pytest.raises(SystemExit) as exc:
            query_app_insights()
        assert exc.value.code == 1


class TestQueryFabricDapErrors:
    """Tests for query_fabric_dap_errors function."""

    @patch("agentic_devtools.cli.azure.app_insights_commands._print_query_results")
    @patch("agentic_devtools.cli.azure.app_insights_commands._run_app_insights_query")
    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.is_dry_run", return_value=True
    )
    @patch("agentic_devtools.cli.azure.app_insights_commands.get_value")
    def test_dry_run(self, mock_get, mock_dry, mock_run, mock_print):
        """Test dry run mode for error query."""
        mock_get.side_effect = lambda k: None
        mock_run.return_value = {"dry_run": True}
        query_fabric_dap_errors()
        mock_run.assert_called_once()

    @patch("agentic_devtools.cli.azure.app_insights_commands._run_app_insights_query")
    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.is_dry_run",
        return_value=False,
    )
    @patch("agentic_devtools.cli.azure.app_insights_commands.get_value")
    def test_exits_on_none_result(self, mock_get, mock_dry, mock_run):
        """Test exits when query returns None."""
        mock_get.side_effect = lambda k: None
        mock_run.return_value = None
        with pytest.raises(SystemExit) as exc:
            query_fabric_dap_errors()
        assert exc.value.code == 1


class TestQueryFabricDapProvisioning:
    """Tests for query_fabric_dap_provisioning function."""

    @patch(
        "agentic_devtools.cli.azure.app_insights_commands._query_fabric_dap_provisioning_sync"
    )
    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.is_dry_run",
        return_value=False,
    )
    @patch("agentic_devtools.cli.azure.app_insights_commands.get_value")
    def test_sync_mode(self, mock_get, mock_dry, mock_sync):
        """Test synchronous mode calls sync function."""
        mock_get.side_effect = lambda k: None
        query_fabric_dap_provisioning()
        mock_sync.assert_called_once()

    @patch("agentic_devtools.cli.azure.app_insights_commands.print_task_tracking_info")
    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.run_function_in_background"
    )
    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.is_dry_run",
        return_value=False,
    )
    @patch("agentic_devtools.cli.azure.app_insights_commands.get_value")
    def test_background_mode(self, mock_get, mock_dry, mock_bg, mock_print):
        """Test background mode starts background task."""
        mock_get.side_effect = lambda k: {"azure.background": "true"}.get(k)
        mock_bg.return_value = {"task_id": "123"}
        query_fabric_dap_provisioning()
        mock_bg.assert_called_once()
        assert (
            "agentic_devtools.cli.azure.app_insights_commands" in mock_bg.call_args[0]
        )

    @patch(
        "agentic_devtools.cli.azure.app_insights_commands._query_fabric_dap_provisioning_sync"
    )
    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.is_dry_run", return_value=True
    )
    @patch("agentic_devtools.cli.azure.app_insights_commands.get_value")
    def test_dry_run_skips_background(self, mock_get, mock_dry, mock_sync):
        """Test dry run skips background even if azure.background is true."""
        mock_get.side_effect = lambda k: {"azure.background": "true"}.get(k)
        query_fabric_dap_provisioning()
        mock_sync.assert_called_once()


class TestQueryFabricDapTimeline:
    """Tests for query_fabric_dap_timeline function."""

    @patch("agentic_devtools.cli.azure.app_insights_commands._print_query_results")
    @patch("agentic_devtools.cli.azure.app_insights_commands._run_app_insights_query")
    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.is_dry_run", return_value=True
    )
    @patch("agentic_devtools.cli.azure.app_insights_commands.get_value")
    def test_dry_run(self, mock_get, mock_dry, mock_run, mock_print):
        """Test dry run mode for timeline query."""
        mock_get.side_effect = lambda k: None
        mock_run.return_value = {"dry_run": True}
        query_fabric_dap_timeline()
        mock_run.assert_called_once()

    @patch("agentic_devtools.cli.azure.app_insights_commands._run_app_insights_query")
    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.is_dry_run",
        return_value=False,
    )
    @patch("agentic_devtools.cli.azure.app_insights_commands.get_value")
    def test_exits_on_none_result(self, mock_get, mock_dry, mock_run):
        """Test exits when query returns None."""
        mock_get.side_effect = lambda k: None
        mock_run.return_value = None
        with pytest.raises(SystemExit) as exc:
            query_fabric_dap_timeline()
        assert exc.value.code == 1


class TestRunAppInsightsQuery:
    """Tests for _run_app_insights_query function."""

    @patch("agentic_devtools.cli.azure.app_insights_commands.get_app_insights_config")
    def test_returns_none_for_unknown_env(self, mock_config):
        """Test returns None for unknown environment."""
        mock_config.return_value = None
        from agentic_devtools.cli.azure.app_insights_commands import (
            _run_app_insights_query,
        )

        result = _run_app_insights_query("UNKNOWN", "traces | take 10")
        assert result is None

    @patch("agentic_devtools.cli.azure.app_insights_commands.get_app_insights_config")
    def test_dry_run_returns_dict(self, mock_config):
        """Test dry run returns dry_run dict."""
        mock_config.return_value = MagicMock(
            name="test-ai",
            resource_id="/subscriptions/x/resourceGroups/rg/providers/microsoft.insights/components/test-ai",
        )
        from agentic_devtools.cli.azure.app_insights_commands import (
            _run_app_insights_query,
        )

        result = _run_app_insights_query("DEV", "traces | take 10", dry_run=True)
        assert result == {"dry_run": True}

    @patch("agentic_devtools.cli.azure.app_insights_commands.LogsQueryClient")
    @patch("agentic_devtools.cli.azure.app_insights_commands.AzureCliCredential")
    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.ensure_azure_account",
        return_value=True,
    )
    @patch("agentic_devtools.cli.azure.app_insights_commands.get_app_insights_config")
    def test_successful_query(self, mock_config, mock_ensure, mock_cred, mock_client):
        """Test successful query returns data."""
        mock_config.return_value = MagicMock(
            name="test-ai",
            resource_id="/subscriptions/x/resourceGroups/rg/providers/microsoft.insights/components/test-ai",
        )

        # Mock SDK response
        from azure.monitor.query import LogsQueryStatus

        mock_response = MagicMock()
        mock_response.status = LogsQueryStatus.SUCCESS
        mock_table = MagicMock()
        mock_table.columns = ["timestamp", "message"]
        mock_table.rows = [["2024-01-01", "test"]]
        mock_response.tables = [mock_table]
        mock_client.return_value.query_resource.return_value = mock_response

        from agentic_devtools.cli.azure.app_insights_commands import (
            _run_app_insights_query,
        )

        result = _run_app_insights_query("DEV", "traces | take 10")
        assert result is not None
        assert "tables" in result

    @patch("agentic_devtools.cli.azure.app_insights_commands.LogsQueryClient")
    @patch("agentic_devtools.cli.azure.app_insights_commands.AzureCliCredential")
    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.ensure_azure_account",
        return_value=True,
    )
    @patch("agentic_devtools.cli.azure.app_insights_commands.get_app_insights_config")
    def test_partial_results(self, mock_config, mock_ensure, mock_cred, mock_client):
        """Test partial results handled correctly."""
        mock_config.return_value = MagicMock(
            name="test-ai",
            resource_id="/subscriptions/x/resourceGroups/rg/providers/microsoft.insights/components/test-ai",
        )

        from azure.monitor.query import LogsQueryStatus

        mock_response = MagicMock()
        mock_response.status = LogsQueryStatus.PARTIAL
        mock_response.partial_error = "Some warning"
        mock_table = MagicMock()
        mock_table.columns = ["ts"]
        mock_table.rows = [["2024-01-01"]]
        mock_response.partial_data = [mock_table]
        mock_client.return_value.query_resource.return_value = mock_response

        from agentic_devtools.cli.azure.app_insights_commands import (
            _run_app_insights_query,
        )

        result = _run_app_insights_query("DEV", "traces | take 10")
        assert result is not None
        assert "tables" in result

    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.ensure_azure_account",
        return_value=False,
    )
    @patch("agentic_devtools.cli.azure.app_insights_commands.get_app_insights_config")
    def test_returns_none_on_account_failure(self, mock_config, mock_ensure):
        """Test returns None when account switching fails."""
        mock_config.return_value = MagicMock(
            name="test-ai",
            resource_id="/subscriptions/x/resourceGroups/rg/providers/microsoft.insights/components/test-ai",
        )

        from agentic_devtools.cli.azure.app_insights_commands import (
            _run_app_insights_query,
        )

        result = _run_app_insights_query("DEV", "traces | take 10")
        assert result is None

    @patch("agentic_devtools.cli.azure.app_insights_commands.LogsQueryClient")
    @patch("agentic_devtools.cli.azure.app_insights_commands.AzureCliCredential")
    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.ensure_azure_account",
        return_value=True,
    )
    @patch("agentic_devtools.cli.azure.app_insights_commands.get_app_insights_config")
    def test_handles_http_error(self, mock_config, mock_ensure, mock_cred, mock_client):
        """Test handles HttpResponseError gracefully."""
        mock_config.return_value = MagicMock(
            name="test-ai",
            resource_id="/subscriptions/x/resourceGroups/rg/providers/microsoft.insights/components/test-ai",
        )

        from azure.core.exceptions import HttpResponseError

        mock_client.return_value.query_resource.side_effect = HttpResponseError(
            message="Bad request"
        )

        from agentic_devtools.cli.azure.app_insights_commands import (
            _run_app_insights_query,
        )

        result = _run_app_insights_query("DEV", "invalid query")
        assert result is None

    @patch("agentic_devtools.cli.azure.app_insights_commands.LogsQueryClient")
    @patch("agentic_devtools.cli.azure.app_insights_commands.AzureCliCredential")
    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.ensure_azure_account",
        return_value=True,
    )
    @patch("agentic_devtools.cli.azure.app_insights_commands.get_app_insights_config")
    def test_handles_generic_exception(
        self, mock_config, mock_ensure, mock_cred, mock_client
    ):
        """Test handles generic exceptions gracefully."""
        mock_config.return_value = MagicMock(
            name="test-ai",
            resource_id="/subscriptions/x/resourceGroups/rg/providers/microsoft.insights/components/test-ai",
        )
        mock_client.return_value.query_resource.side_effect = Exception(
            "Connection timeout"
        )

        from agentic_devtools.cli.azure.app_insights_commands import (
            _run_app_insights_query,
        )

        result = _run_app_insights_query("DEV", "traces | take 10")
        assert result is None

    @patch("agentic_devtools.cli.azure.app_insights_commands._write_results_to_file")
    @patch("agentic_devtools.cli.azure.app_insights_commands.LogsQueryClient")
    @patch("agentic_devtools.cli.azure.app_insights_commands.AzureCliCredential")
    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.ensure_azure_account",
        return_value=True,
    )
    @patch("agentic_devtools.cli.azure.app_insights_commands.get_app_insights_config")
    def test_writes_to_output_file(
        self, mock_config, mock_ensure, mock_cred, mock_client, mock_write
    ):
        """Test writing results to output file when specified."""
        mock_config.return_value = MagicMock(
            name="test-ai",
            resource_id="/subscriptions/x/resourceGroups/rg/providers/microsoft.insights/components/test-ai",
        )

        from azure.monitor.query import LogsQueryStatus

        mock_response = MagicMock()
        mock_response.status = LogsQueryStatus.SUCCESS
        mock_table = MagicMock()
        mock_table.columns = ["ts"]
        mock_table.rows = [["val"]]
        mock_response.tables = [mock_table]
        mock_client.return_value.query_resource.return_value = mock_response

        from agentic_devtools.cli.azure.app_insights_commands import (
            _run_app_insights_query,
        )

        output = Path("/tmp/test-output.txt")
        result = _run_app_insights_query("DEV", "traces | take 10", output_file=output)
        assert result is not None
        mock_write.assert_called_once()


class TestAsyncCLIWrappers:
    """Tests for async CLI wrapper functions (argparse-based entry points)."""

    @patch("agentic_devtools.cli.azure.app_insights_commands.query_app_insights")
    @patch("agentic_devtools.cli.azure.app_insights_commands.set_value")
    def test_query_app_insights_async_with_args(self, mock_set, mock_query):
        """Test query_app_insights_async parses CLI args."""
        with patch(
            "sys.argv",
            ["agdt-query-app-insights", "-e", "DEV", "-q", "traces | take 5"],
        ):
            query_app_insights_async()
        mock_query.assert_called_once()

    @patch("agentic_devtools.cli.azure.app_insights_commands.query_app_insights")
    def test_query_app_insights_async_no_args(self, mock_query):
        """Test query_app_insights_async with no CLI args uses state."""
        with patch("sys.argv", ["agdt-query-app-insights"]):
            query_app_insights_async()
        mock_query.assert_called_once()

    @patch("agentic_devtools.cli.azure.app_insights_commands.query_fabric_dap_errors")
    def test_query_fabric_dap_errors_async_no_args(self, mock_query):
        """Test query_fabric_dap_errors_async with no args."""
        with patch("sys.argv", ["agdt-query-fabric-dap-errors"]):
            query_fabric_dap_errors_async()
        mock_query.assert_called_once()

    @patch("agentic_devtools.cli.azure.app_insights_commands.query_fabric_dap_errors")
    @patch("agentic_devtools.cli.azure.app_insights_commands.set_value")
    def test_query_fabric_dap_errors_async_with_args(self, mock_set, mock_query):
        """Test query_fabric_dap_errors_async parses CLI args."""
        with patch(
            "sys.argv",
            ["agdt-query-fabric-dap-errors", "-e", "INT", "-w", "STND", "-t", "4h"],
        ):
            query_fabric_dap_errors_async()
        mock_query.assert_called_once()

    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.query_fabric_dap_provisioning"
    )
    def test_query_fabric_dap_provisioning_async_no_args(self, mock_query):
        """Test query_fabric_dap_provisioning_async with no args."""
        with patch("sys.argv", ["agdt-query-fabric-dap-provisioning"]):
            query_fabric_dap_provisioning_async()
        mock_query.assert_called_once()

    @patch("agentic_devtools.cli.azure.app_insights_commands.query_fabric_dap_timeline")
    def test_query_fabric_dap_timeline_async_no_args(self, mock_query):
        """Test query_fabric_dap_timeline_async with no args."""
        with patch("sys.argv", ["agdt-query-fabric-dap-timeline"]):
            query_fabric_dap_timeline_async()
        mock_query.assert_called_once()

    @patch("agentic_devtools.cli.azure.app_insights_commands.query_fabric_dap_timeline")
    @patch("agentic_devtools.cli.azure.app_insights_commands.set_value")
    def test_query_fabric_dap_timeline_async_with_args(self, mock_set, mock_query):
        """Test query_fabric_dap_timeline_async parses CLI args."""
        with patch(
            "sys.argv",
            [
                "agdt-query-fabric-dap-timeline",
                "-e",
                "PROD",
                "-d",
                "dp-test",
                "-l",
                "1000",
            ],
        ):
            query_fabric_dap_timeline_async()
        mock_query.assert_called_once()


class TestSetIfProvided:
    """Tests for _set_if_provided helper."""

    @patch("agentic_devtools.cli.azure.app_insights_commands.set_value")
    def test_sets_value_when_provided(self, mock_set):
        """Test sets value when not None."""
        from agentic_devtools.cli.azure.app_insights_commands import _set_if_provided

        _set_if_provided("key", "value")
        mock_set.assert_called_once_with("key", "value")

    @patch("agentic_devtools.cli.azure.app_insights_commands.set_value")
    def test_skips_when_none(self, mock_set):
        """Test skips when value is None."""
        from agentic_devtools.cli.azure.app_insights_commands import _set_if_provided

        _set_if_provided("key", None)
        mock_set.assert_not_called()


class TestQueryFabricDapProvisioningSync:
    """Tests for _query_fabric_dap_provisioning_sync function."""

    @patch("agentic_devtools.cli.azure.app_insights_commands._run_app_insights_query")
    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.is_dry_run", return_value=True
    )
    @patch("agentic_devtools.cli.azure.app_insights_commands.get_value")
    def test_returns_zero_on_success(self, mock_get, mock_dry, mock_run):
        """Test returns 0 on successful query."""
        mock_get.side_effect = lambda k: None
        mock_run.return_value = {"tables": []}

        from agentic_devtools.cli.azure.app_insights_commands import (
            _query_fabric_dap_provisioning_sync,
        )

        result = _query_fabric_dap_provisioning_sync()
        assert result == 0

    @patch("agentic_devtools.cli.azure.app_insights_commands._run_app_insights_query")
    @patch(
        "agentic_devtools.cli.azure.app_insights_commands.is_dry_run",
        return_value=False,
    )
    @patch("agentic_devtools.cli.azure.app_insights_commands.get_value")
    def test_returns_one_on_failure(self, mock_get, mock_dry, mock_run):
        """Test returns 1 when query fails."""
        mock_get.side_effect = lambda k: None
        mock_run.return_value = None

        from agentic_devtools.cli.azure.app_insights_commands import (
            _query_fabric_dap_provisioning_sync,
        )

        result = _query_fabric_dap_provisioning_sync()
        assert result == 1
