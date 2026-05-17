"""Tests for process_speckit_label_event."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from agentic_devtools.cli.ci import speckit_trigger
from agentic_devtools.cli.ci.models import EventPayload
from agentic_devtools.cli.ci.speckit_trigger import (
    EXIT_FAILED,
    EXIT_MALFORMED_EVENT,
    EXIT_MISSING_CONFIG,
    EXIT_SUCCESS,
    process_speckit_label_event,
)


def _write_event_payload(payload: dict) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        return f.name


class TestProcessSpeckitLabelEvent:
    """Tests for SpecKit trigger processing logic."""

    def test_returns_success_when_action_is_not_labeled(self) -> None:
        payload = EventPayload(action="unlabeled", trigger_label="speckit")
        provider = MagicMock()

        result = process_speckit_label_event(provider, payload)

        assert result == EXIT_SUCCESS

    def test_returns_success_when_label_does_not_match(self) -> None:
        payload = EventPayload(action="labeled", trigger_label="not-speckit")
        provider = MagicMock()

        with patch.dict(os.environ, {"SPECKIT_TRIGGER_LABEL": "speckit"}):
            result = process_speckit_label_event(provider, payload)

        assert result == EXIT_SUCCESS

    def test_returns_malformed_event_when_issue_number_missing(self) -> None:
        event_path = _write_event_payload({"action": "labeled", "issue": {}, "label": {"name": "speckit"}})
        try:
            env = {
                "GITHUB_EVENT_PATH": event_path,
                "SPECKIT_TRIGGER_LABEL": "speckit",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                result = process_speckit_label_event(MagicMock(), EventPayload(action="labeled", trigger_label="speckit"))
            assert result == EXIT_MALFORMED_EVENT
        finally:
            os.unlink(event_path)

    def test_returns_missing_config_when_repo_env_missing(self) -> None:
        event_path = _write_event_payload(
            {
                "action": "labeled",
                "label": {"name": "speckit"},
                "issue": {"number": 42, "title": "Feature", "labels": [{"name": "speckit"}]},
            }
        )
        try:
            env = {"GITHUB_EVENT_PATH": event_path, "SPECKIT_TRIGGER_LABEL": "speckit"}
            with patch.dict(os.environ, env, clear=True):
                result = process_speckit_label_event(MagicMock(), EventPayload(action="labeled", trigger_label="speckit"))
            assert result == EXIT_MISSING_CONFIG
        finally:
            os.unlink(event_path)

    @patch("agentic_devtools.cli.ci.speckit_trigger._set_issue_labels")
    def test_duplicate_trigger_is_skipped(self, mock_set_labels) -> None:
        event_path = _write_event_payload(
            {
                "action": "labeled",
                "label": {"name": "speckit"},
                "issue": {"number": 42, "title": "Feature", "labels": [{"name": "speckit:processing"}]},
            }
        )
        try:
            env = {
                "GITHUB_EVENT_PATH": event_path,
                "SPECKIT_TRIGGER_LABEL": "speckit",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                result = process_speckit_label_event(MagicMock(), EventPayload(action="labeled", trigger_label="speckit"))
            assert result == EXIT_SUCCESS
            mock_set_labels.assert_not_called()
        finally:
            os.unlink(event_path)

    @patch("agentic_devtools.cli.ci.speckit_trigger._run_script_with_outputs", return_value={"skipped": "true"})
    @patch("agentic_devtools.cli.ci.speckit_trigger._set_issue_labels")
    def test_idempotent_phase_is_skipped(self, mock_set_labels, mock_run_script) -> None:
        event_path = _write_event_payload(
            {
                "action": "labeled",
                "label": {"name": "speckit"},
                "issue": {"number": 42, "title": "Feature", "labels": [{"name": "speckit"}]},
            }
        )
        try:
            env = {
                "GITHUB_EVENT_PATH": event_path,
                "SPECKIT_TRIGGER_LABEL": "speckit",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                result = process_speckit_label_event(MagicMock(), EventPayload(action="labeled", trigger_label="speckit"))
            assert result == EXIT_SUCCESS
            mock_run_script.assert_called_once()
            assert mock_set_labels.call_args_list == [
                call(42, add=["speckit:processing"], remove=["speckit", "speckit:failed"]),
                call(42, add=["speckit:phase-1-complete"], remove=["speckit:processing"]),
            ]
        finally:
            os.unlink(event_path)

    @patch("agentic_devtools.cli.ci.speckit_trigger._create_phase_pull_request")
    @patch("agentic_devtools.cli.ci.speckit_trigger._commit_and_push_phase_branch")
    @patch(
        "agentic_devtools.cli.ci.speckit_trigger._run_script_with_outputs",
        side_effect=[
            {"skipped": "false"},
            {"short_name": "my-feature"},
            {"spec_dir": "specs/42-my-feature"},
        ],
    )
    @patch("agentic_devtools.cli.ci.speckit_trigger._set_issue_labels")
    def test_happy_path_runs_pipeline(
        self,
        mock_set_labels,
        mock_run_script,
        mock_commit_push,
        mock_create_pr,
    ) -> None:
        event_path = _write_event_payload(
            {
                "action": "labeled",
                "label": {"name": "speckit"},
                "issue": {
                    "number": 42,
                    "title": "My feature",
                    "body": "Implement it",
                    "html_url": "https://github.com/owner/repo/issues/42",
                    "labels": [{"name": "speckit"}, {"name": "enhancement"}],
                },
            }
        )
        try:
            env = {
                "GITHUB_EVENT_PATH": event_path,
                "SPECKIT_TRIGGER_LABEL": "speckit",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                result = process_speckit_label_event(MagicMock(), EventPayload(action="labeled", trigger_label="speckit"))
            assert result == EXIT_SUCCESS
            mock_run_script.assert_called()
            mock_commit_push.assert_called_once_with(42, "specs/42-my-feature")
            mock_create_pr.assert_called_once()
            assert mock_set_labels.call_args_list[-1] == call(
                42,
                add=["speckit:phase-1"],
                remove=["speckit:processing"],
            )
        finally:
            os.unlink(event_path)

    @patch("agentic_devtools.cli.ci.speckit_trigger._run_script_with_outputs", side_effect=[{"skipped": "false"}, {}])
    @patch("agentic_devtools.cli.ci.speckit_trigger._set_issue_labels")
    def test_returns_failed_when_short_name_missing(self, mock_set_labels, mock_run_script) -> None:
        event_path = _write_event_payload(
            {
                "action": "labeled",
                "label": {"name": "speckit"},
                "issue": {"number": 42, "title": "Feature", "labels": [{"name": "speckit"}]},
            }
        )
        try:
            env = {
                "GITHUB_EVENT_PATH": event_path,
                "SPECKIT_TRIGGER_LABEL": "speckit",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                result = process_speckit_label_event(MagicMock(), EventPayload(action="labeled", trigger_label="speckit"))
            assert result == EXIT_FAILED
            assert mock_set_labels.call_count == 2
            assert mock_set_labels.call_args_list == [
                call(42, add=["speckit:processing"], remove=["speckit", "speckit:failed"]),
                call(42, add=["speckit:failed"], remove=["speckit:processing"]),
            ]
            assert mock_run_script.call_count == 2
        finally:
            os.unlink(event_path)

    @patch(
        "agentic_devtools.cli.ci.speckit_trigger._run_script_with_outputs",
        side_effect=[{"skipped": "false"}, {"short_name": "name"}, {}],
    )
    @patch("agentic_devtools.cli.ci.speckit_trigger._set_issue_labels")
    def test_returns_failed_when_spec_dir_missing(self, mock_set_labels, mock_run_script) -> None:
        event_path = _write_event_payload(
            {
                "action": "labeled",
                "label": {"name": "speckit"},
                "issue": {"number": 42, "title": "Feature", "labels": [{"name": "speckit"}]},
            }
        )
        try:
            env = {
                "GITHUB_EVENT_PATH": event_path,
                "SPECKIT_TRIGGER_LABEL": "speckit",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                result = process_speckit_label_event(MagicMock(), EventPayload(action="labeled", trigger_label="speckit"))
            assert result == EXIT_FAILED
            assert mock_set_labels.call_count == 2
            assert mock_set_labels.call_args_list == [
                call(42, add=["speckit:processing"], remove=["speckit", "speckit:failed"]),
                call(42, add=["speckit:failed"], remove=["speckit:processing"]),
            ]
            assert mock_run_script.call_count == 3
        finally:
            os.unlink(event_path)

    @patch("agentic_devtools.cli.ci.speckit_trigger._create_phase_pull_request", side_effect=RuntimeError("boom"))
    @patch("agentic_devtools.cli.ci.speckit_trigger._commit_and_push_phase_branch")
    @patch(
        "agentic_devtools.cli.ci.speckit_trigger._run_script_with_outputs",
        side_effect=[{"skipped": "false"}, {"short_name": "name"}, {"spec_dir": "specs/42-name"}],
    )
    @patch("agentic_devtools.cli.ci.speckit_trigger._set_issue_labels")
    def test_exception_marks_issue_failed(
        self,
        mock_set_labels,
        mock_run_script,
        mock_commit_push,
        mock_create_pr,
    ) -> None:
        event_path = _write_event_payload(
            {
                "action": "labeled",
                "label": {"name": "speckit"},
                "issue": {"number": 42, "title": "Feature", "labels": [{"name": "speckit"}]},
            }
        )
        try:
            env = {
                "GITHUB_EVENT_PATH": event_path,
                "SPECKIT_TRIGGER_LABEL": "speckit",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                result = process_speckit_label_event(MagicMock(), EventPayload(action="labeled", trigger_label="speckit"))
            assert result == EXIT_FAILED
            assert mock_set_labels.call_args_list[-1] == call(
                42,
                add=["speckit:failed"],
                remove=["speckit:processing"],
            )
            mock_run_script.assert_called()
            mock_commit_push.assert_called_once()
            mock_create_pr.assert_called_once()
        finally:
            os.unlink(event_path)


class TestSpeckitTriggerHelpers:
    """Tests for helper functions in speckit_trigger module."""

    def test_load_issue_context_requires_event_path(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            try:
                speckit_trigger._load_issue_context_from_event()
            except RuntimeError as exc:
                assert str(exc) == "GITHUB_EVENT_PATH is not set"
            else:  # pragma: no cover
                raise AssertionError("expected RuntimeError")

    def test_load_issue_context_invalid_json_raises(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{broken")
            event_path = f.name
        try:
            with patch.dict(os.environ, {"GITHUB_EVENT_PATH": event_path}, clear=True):
                try:
                    speckit_trigger._load_issue_context_from_event()
                except RuntimeError as exc:
                    assert "failed to read event payload" in str(exc)
                else:  # pragma: no cover
                    raise AssertionError("expected RuntimeError")
        finally:
            os.unlink(event_path)

    @patch("agentic_devtools.cli.ci.speckit_trigger._run_checked")
    def test_set_issue_labels_handles_add_and_remove(self, mock_run_checked) -> None:
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"}, clear=True):
            speckit_trigger._set_issue_labels(42, add=["x", "y", ""], remove=["a", "b"])
        assert mock_run_checked.call_args_list == [
            call(["gh", "issue", "edit", "42", "--repo", "owner/repo", "--add-label", "x"]),
            call(["gh", "issue", "edit", "42", "--repo", "owner/repo", "--add-label", "y"]),
            call(["gh", "issue", "edit", "42", "--repo", "owner/repo", "--remove-label", "a"]),
            call(["gh", "issue", "edit", "42", "--repo", "owner/repo", "--remove-label", "b"]),
        ]

    def test_run_script_with_outputs_requires_existing_script(self) -> None:
        try:
            speckit_trigger._run_script_with_outputs("does-not-exist.sh", [])
        except RuntimeError as exc:
            assert "script not found" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("expected RuntimeError")

    @patch("agentic_devtools.cli.ci.speckit_trigger._run_checked")
    def test_run_script_with_outputs_reads_output_file(self, mock_run_checked) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            script = Path(tmpdir) / "script.sh"
            script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

            def write_output(cmd, env=None):
                Path(env["GITHUB_OUTPUT"]).write_text("foo=bar\n", encoding="utf-8")

            mock_run_checked.side_effect = write_output
            outputs = speckit_trigger._run_script_with_outputs(str(script), ["--x"], extra_env={"A": "B"})
            assert outputs == {"foo": "bar"}

    @patch("agentic_devtools.cli.ci.speckit_trigger._run_checked")
    def test_run_script_with_outputs_ignores_unlink_errors(self, mock_run_checked) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            script = Path(tmpdir) / "script.sh"
            script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

            def write_output(cmd, env=None):
                Path(env["GITHUB_OUTPUT"]).write_text("foo=bar\n", encoding="utf-8")

            mock_run_checked.side_effect = write_output
            with patch("agentic_devtools.cli.ci.speckit_trigger.os.unlink", side_effect=OSError):
                outputs = speckit_trigger._run_script_with_outputs(str(script), ["--x"])
            assert outputs == {"foo": "bar"}

    def test_parse_key_value_file_handles_missing_and_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = str(Path(tmpdir) / f"agdt-nonexistent-{os.getpid()}.txt")
        assert speckit_trigger._parse_key_value_file(nonexistent) == {}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("a=1\nbroken\nb=2=3\n")
            path = f.name
        try:
            assert speckit_trigger._parse_key_value_file(path) == {"a": "1", "b": "2=3"}
        finally:
            os.unlink(path)

    @patch("agentic_devtools.cli.ci.speckit_trigger.run_safe")
    @patch("agentic_devtools.cli.ci.speckit_trigger._run_checked")
    def test_commit_and_push_phase_branch_existing_remote(self, mock_run_checked, mock_run_safe) -> None:
        mock_run_safe.return_value = subprocess.CompletedProcess(args=["git"], returncode=0, stdout="", stderr="")
        speckit_trigger._commit_and_push_phase_branch(42, "specs/42-feature")
        assert (
            call(
                [
                    "git",
                    "fetch",
                    "origin",
                    "refs/heads/speckit/42/phase-1-specify:refs/remotes/origin/speckit/42/phase-1-specify",
                ]
            )
            in mock_run_checked.call_args_list
        )

    @patch("agentic_devtools.cli.ci.speckit_trigger.run_safe")
    @patch("agentic_devtools.cli.ci.speckit_trigger._run_checked")
    def test_commit_and_push_phase_branch_new_remote(self, mock_run_checked, mock_run_safe) -> None:
        mock_run_safe.return_value = subprocess.CompletedProcess(args=["git"], returncode=2, stdout="", stderr="")
        speckit_trigger._commit_and_push_phase_branch(42, "specs/42-feature")
        assert call(["git", "checkout", "-b", "speckit/42/phase-1-specify"]) in mock_run_checked.call_args_list

    @patch("agentic_devtools.cli.ci.speckit_trigger.run_safe")
    @patch("agentic_devtools.cli.ci.speckit_trigger._run_checked")
    def test_commit_and_push_phase_branch_raises_on_ls_remote_error(self, mock_run_checked, mock_run_safe) -> None:
        mock_run_safe.return_value = subprocess.CompletedProcess(
            args=["git"], returncode=128, stdout="", stderr="fatal: could not read from remote"
        )
        try:
            speckit_trigger._commit_and_push_phase_branch(42, "specs/42-feature")
        except RuntimeError as exc:
            assert "git ls-remote failed (rc=128)" in str(exc)
            assert "could not read from remote" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("expected RuntimeError")

    @patch("agentic_devtools.cli.ci.speckit_trigger._run_script_with_outputs")
    def test_create_phase_pull_request_uses_script(self, mock_run_script) -> None:
        issue = speckit_trigger._IssueContext(
            issue_number=42,
            issue_title="Title",
            issue_body="Body",
            issue_url="url",
            labels=["enhancement"],
        )
        speckit_trigger._create_phase_pull_request(issue, "specs/42-title")
        mock_run_script.assert_called_once()

    @patch("agentic_devtools.cli.ci.speckit_trigger.run_safe")
    def test_run_checked_raises_on_failure(self, mock_run_safe) -> None:
        mock_run_safe.return_value = subprocess.CompletedProcess(args=["x"], returncode=1, stdout="", stderr="bad")
        try:
            speckit_trigger._run_checked(["cmd"])
        except RuntimeError as exc:
            assert str(exc) == "bad"
        else:  # pragma: no cover
            raise AssertionError("expected RuntimeError")

    def test_require_repository_validation(self) -> None:
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"}, clear=True):
            assert speckit_trigger._require_repository() == "owner/repo"
        with patch.dict(os.environ, {}, clear=True):
            try:
                speckit_trigger._require_repository()
            except RuntimeError as exc:
                assert str(exc) == "GITHUB_REPOSITORY is required"
            else:  # pragma: no cover
                raise AssertionError("expected RuntimeError")

    def test_load_issue_context_raises_when_issue_not_dict(self) -> None:
        event_path = _write_event_payload({"issue": "not-a-dict"})
        try:
            with patch.dict(os.environ, {"GITHUB_EVENT_PATH": event_path}, clear=True):
                try:
                    speckit_trigger._load_issue_context_from_event()
                except RuntimeError as exc:
                    assert "not a mapping" in str(exc)
                else:  # pragma: no cover
                    raise AssertionError("expected RuntimeError")
        finally:
            os.unlink(event_path)

    def test_load_issue_context_raises_when_labels_not_list(self) -> None:
        event_path = _write_event_payload({"issue": {"number": 42, "title": "T", "labels": "bad"}})
        try:
            with patch.dict(os.environ, {"GITHUB_EVENT_PATH": event_path}, clear=True):
                try:
                    speckit_trigger._load_issue_context_from_event()
                except RuntimeError as exc:
                    assert "not a list" in str(exc)
                else:  # pragma: no cover
                    raise AssertionError("expected RuntimeError")
        finally:
            os.unlink(event_path)

    @patch("agentic_devtools.cli.ci.speckit_trigger._create_phase_pull_request")
    @patch("agentic_devtools.cli.ci.speckit_trigger._commit_and_push_phase_branch")
    @patch(
        "agentic_devtools.cli.ci.speckit_trigger._run_script_with_outputs",
        side_effect=[
            {"skipped": "false"},
            {"short_name": "my-feature"},
            {"spec_dir": "specs/42-my-feature"},
        ],
    )
    @patch("agentic_devtools.cli.ci.speckit_trigger._set_issue_labels")
    def test_returns_failed_when_final_label_update_fails(
        self,
        mock_set_labels,
        mock_run_script,
        mock_commit_push,
        mock_create_pr,
    ) -> None:
        """Final _set_issue_labels failure returns EXIT_FAILED."""
        event_path = _write_event_payload(
            {
                "action": "labeled",
                "label": {"name": "speckit"},
                "issue": {
                    "number": 42,
                    "title": "My feature",
                    "body": "Implement it",
                    "html_url": "https://github.com/owner/repo/issues/42",
                    "labels": [{"name": "speckit"}],
                },
            }
        )
        # First call (processing label) succeeds, second call (phase label) fails
        mock_set_labels.side_effect = [None, RuntimeError("rate limited")]
        try:
            env = {
                "GITHUB_EVENT_PATH": event_path,
                "SPECKIT_TRIGGER_LABEL": "speckit",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                result = process_speckit_label_event(MagicMock(), EventPayload(action="labeled", trigger_label="speckit"))
            assert result == EXIT_FAILED
        finally:
            os.unlink(event_path)

    @patch("agentic_devtools.cli.ci.speckit_trigger._set_issue_labels", side_effect=RuntimeError("label api down"))
    @patch("agentic_devtools.cli.ci.speckit_trigger._run_script_with_outputs", side_effect=RuntimeError("script failed"))
    def test_returns_failed_when_failure_label_update_also_fails(self, mock_run_script, mock_set_labels) -> None:
        """Failure-label update errors are swallowed and EXIT_FAILED is still returned."""
        event_path = _write_event_payload(
            {
                "action": "labeled",
                "label": {"name": "speckit"},
                "issue": {
                    "number": 42,
                    "title": "My feature",
                    "body": "Implement it",
                    "html_url": "https://github.com/owner/repo/issues/42",
                    "labels": [{"name": "speckit"}],
                },
            }
        )
        try:
            env = {
                "GITHUB_EVENT_PATH": event_path,
                "SPECKIT_TRIGGER_LABEL": "speckit",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                result = process_speckit_label_event(MagicMock(), EventPayload(action="labeled", trigger_label="speckit"))
            assert result == EXIT_FAILED
        finally:
            os.unlink(event_path)
