"""Tests for agentic_devtools.context.retriever.IssueContextRetriever."""

import json
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.context.retriever import IssueContextRetriever
from agentic_devtools.tools.jira import JiraConfig


def _make_config():
    """Create a JiraConfig suitable for unit tests."""
    return JiraConfig(
        base_url="https://jira.example.com",
        headers={"Authorization": "Basic xxx"},
        ssl_verify=False,
        requests_module=MagicMock(),
    )


class TestIssueContextRetrieverInit:
    """Tests for IssueContextRetriever constructor."""

    def test_raises_on_invalid_repo_path(self, tmp_path):
        """Constructor raises ValueError for non-existent repo_path."""
        config = _make_config()
        with pytest.raises(ValueError, match="repo_path must be a valid directory"):
            IssueContextRetriever(jira_config=config, repo_path=str(tmp_path / "nonexistent"))

    def test_accepts_valid_directory(self, tmp_path):
        """Constructor succeeds with a valid directory."""
        config = _make_config()
        r = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        assert r._repo_path == tmp_path

    def test_default_coverage_path(self, tmp_path):
        """Default coverage path is {repo_path}/coverage.json."""
        config = _make_config()
        r = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        assert r._coverage_path == tmp_path / "coverage.json"

    def test_explicit_coverage_path(self, tmp_path):
        """Explicit coverage_path overrides default."""
        config = _make_config()
        custom = str(tmp_path / "custom_cov.json")
        r = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path), coverage_path=custom)
        assert r._coverage_path.name == "custom_cov.json"

    def test_relative_coverage_path_resolved_against_repo(self, tmp_path):
        """Relative coverage_path is resolved against repo_path."""
        config = _make_config()
        r = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path), coverage_path="subdir/cov.json")
        assert r._coverage_path == tmp_path / "subdir" / "cov.json"

    def test_absolute_coverage_path_used_directly(self, tmp_path):
        """Absolute coverage_path is used as-is."""
        config = _make_config()
        abs_path = str(tmp_path / "abs_cov.json")
        r = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path), coverage_path=abs_path)
        assert str(r._coverage_path) == abs_path


class TestRetrieve:
    """Tests for IssueContextRetriever.retrieve()."""

    @pytest.mark.asyncio
    @patch("agentic_devtools.context.retriever.get_recent_changes")
    @patch("agentic_devtools.context.retriever.fetch_issue_context")
    async def test_happy_path(self, mock_fetch, mock_git, tmp_path):
        """All subsystems succeed and populate the AgentContext."""
        # Jira mock
        mock_fetch.return_value = {
            "issue": {"key": "T-1", "fields": {"summary": "test"}},
            "parent_issue": {"key": "T-0"},
            "epic_issue": None,
            "remote_links": [{"url": "https://example.com"}],
        }
        # Git mock
        mock_git.return_value = {"commits": [{"sha": "abc", "message": "init"}]}

        # Create an affected file and coverage.json
        affected = tmp_path / "src" / "main.py"
        affected.parent.mkdir(parents=True)
        affected.write_text("print('hi')")

        cov_data = {"files": {"src/main.py": {"summary": {"percent_covered": 95.0}}}}
        (tmp_path / "coverage.json").write_text(json.dumps(cov_data))

        # Create a README
        (tmp_path / "README.md").write_text("# Readme")

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        ctx = await retriever.retrieve("T-1", affected_paths=["src/main.py"])

        assert ctx.issue_key == "T-1"
        assert ctx.issue_details == {"key": "T-1", "fields": {"summary": "test"}}
        assert ctx.parent_issue == {"key": "T-0"}
        assert ctx.remote_links == [{"url": "https://example.com"}]
        assert "src/main.py" in ctx.relevant_files
        assert ctx.recent_changes == [{"sha": "abc", "message": "init"}]
        assert "src/main.py" in ctx.test_coverage
        assert any(d["path"] == "README.md" for d in ctx.documentation)
        assert ctx.errors == []

    @pytest.mark.asyncio
    @patch("agentic_devtools.context.retriever.get_recent_changes")
    @patch("agentic_devtools.context.retriever.fetch_issue_context")
    async def test_jira_failure(self, mock_fetch, mock_git, tmp_path):
        """Jira fetch failure is non-fatal — logged to errors."""
        mock_fetch.side_effect = Exception("connection refused")
        mock_git.return_value = {"commits": []}

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        ctx = await retriever.retrieve("T-1")

        assert ctx.issue_details is None
        assert any("connection refused" in e for e in ctx.errors)

    @pytest.mark.asyncio
    @patch("agentic_devtools.context.retriever.get_recent_changes")
    @patch("agentic_devtools.context.retriever.fetch_issue_context")
    async def test_git_failure(self, mock_fetch, mock_git, tmp_path):
        """Git fetch failure is non-fatal — logged to errors."""
        mock_fetch.return_value = {
            "issue": None,
            "parent_issue": None,
            "epic_issue": None,
            "remote_links": [],
        }
        mock_git.side_effect = Exception("not a git repo")

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        ctx = await retriever.retrieve("T-1")

        assert ctx.recent_changes == []
        assert any("not a git repo" in e for e in ctx.errors)

    @pytest.mark.asyncio
    @patch("agentic_devtools.context.retriever.get_recent_changes")
    @patch("agentic_devtools.context.retriever.fetch_issue_context")
    async def test_affected_paths_none(self, mock_fetch, mock_git, tmp_path):
        """affected_paths=None leaves relevant_files empty."""
        mock_fetch.return_value = {
            "issue": None,
            "parent_issue": None,
            "epic_issue": None,
            "remote_links": [],
        }
        mock_git.return_value = {"commits": []}

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        ctx = await retriever.retrieve("T-1", affected_paths=None)

        assert ctx.relevant_files == []
        # With no relevant files, coverage parsing should be skipped entirely
        # (no noisy "Failed to parse coverage data" error).
        assert not any("coverage" in e.lower() for e in ctx.errors)

    @pytest.mark.asyncio
    @patch("agentic_devtools.context.retriever.get_recent_changes")
    @patch("agentic_devtools.context.retriever.fetch_issue_context")
    async def test_invalid_affected_paths_logged(self, mock_fetch, mock_git, tmp_path):
        """Affected paths that don't exist are dropped and logged to errors."""
        mock_fetch.return_value = {
            "issue": None,
            "parent_issue": None,
            "epic_issue": None,
            "remote_links": [],
        }
        mock_git.return_value = {"commits": []}

        # Create one valid file
        valid = tmp_path / "real.py"
        valid.write_text("x = 1")

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        ctx = await retriever.retrieve("T-1", affected_paths=["real.py", "ghost.py"])

        assert "real.py" in ctx.relevant_files
        assert "ghost.py" not in ctx.relevant_files
        assert any("ghost.py" in e for e in ctx.errors)

    @pytest.mark.asyncio
    @patch("agentic_devtools.context.retriever.get_recent_changes")
    @patch("agentic_devtools.context.retriever.fetch_issue_context")
    async def test_absolute_path_rejected(self, mock_fetch, mock_git, tmp_path):
        """Absolute paths are rejected during affected_paths validation."""
        mock_fetch.return_value = {
            "issue": None,
            "parent_issue": None,
            "epic_issue": None,
            "remote_links": [],
        }
        mock_git.return_value = {"commits": []}

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        ctx = await retriever.retrieve("T-1", affected_paths=["/etc/passwd"])

        assert ctx.relevant_files == []
        assert any("/etc/passwd" in e for e in ctx.errors)

    @pytest.mark.asyncio
    @patch("agentic_devtools.context.retriever.get_recent_changes")
    @patch("agentic_devtools.context.retriever.fetch_issue_context")
    async def test_dotdot_traversal_rejected(self, mock_fetch, mock_git, tmp_path):
        """Paths with .. components are rejected during validation."""
        mock_fetch.return_value = {
            "issue": None,
            "parent_issue": None,
            "epic_issue": None,
            "remote_links": [],
        }
        mock_git.return_value = {"commits": []}

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        ctx = await retriever.retrieve("T-1", affected_paths=["../../../etc/passwd"])

        assert ctx.relevant_files == []
        assert any("../../../etc/passwd" in e for e in ctx.errors)

    @pytest.mark.asyncio
    @patch("agentic_devtools.context.retriever.get_recent_changes")
    @patch("agentic_devtools.context.retriever.fetch_issue_context")
    async def test_paths_normalized_to_posix(self, mock_fetch, mock_git, tmp_path):
        """Validated paths are stored as normalized, repo-relative POSIX strings."""
        mock_fetch.return_value = {
            "issue": None,
            "parent_issue": None,
            "epic_issue": None,
            "remote_links": [],
        }
        mock_git.return_value = {"commits": []}

        # Create a file at src/main.py
        affected = tmp_path / "src" / "main.py"
        affected.parent.mkdir(parents=True)
        affected.write_text("x = 1")

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        ctx = await retriever.retrieve("T-1", affected_paths=["./src/main.py"])

        # The path should be normalized to "src/main.py" (no leading "./")
        assert ctx.relevant_files == ["src/main.py"]

    @pytest.mark.asyncio
    @patch("agentic_devtools.context.retriever.get_recent_changes")
    @patch("agentic_devtools.context.retriever.fetch_issue_context")
    async def test_directory_path_rejected(self, mock_fetch, mock_git, tmp_path):
        """Directories are rejected during affected_paths validation."""
        mock_fetch.return_value = {
            "issue": None,
            "parent_issue": None,
            "epic_issue": None,
            "remote_links": [],
        }
        mock_git.return_value = {"commits": []}

        (tmp_path / "mydir").mkdir()

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        ctx = await retriever.retrieve("T-1", affected_paths=["mydir"])

        assert ctx.relevant_files == []
        assert any("mydir" in e for e in ctx.errors)

    @pytest.mark.asyncio
    @patch("agentic_devtools.context.retriever.get_recent_changes")
    @patch("agentic_devtools.context.retriever.fetch_issue_context")
    async def test_doc_discovery_uses_validated_paths(self, mock_fetch, mock_git, tmp_path):
        """Documentation discovery uses validated paths, not raw input."""
        mock_fetch.return_value = {
            "issue": None,
            "parent_issue": None,
            "epic_issue": None,
            "remote_links": [],
        }
        mock_git.return_value = {"commits": []}

        # Create a valid file and its docs
        affected = tmp_path / "src" / "mymodule.py"
        affected.parent.mkdir(parents=True)
        affected.write_text("x = 1")
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "mymodule.md").write_text("# Module docs")
        (tmp_path / "README.md").write_text("# Root")

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        # Pass with "./" prefix — doc discovery should still work after normalization
        ctx = await retriever.retrieve("T-1", affected_paths=["./src/mymodule.py"])

        doc_paths = [d["path"] for d in ctx.documentation]
        assert "docs/mymodule.md" in doc_paths
        assert "README.md" in doc_paths

    @pytest.mark.asyncio
    @patch("agentic_devtools.context.retriever.get_recent_changes")
    @patch("agentic_devtools.context.retriever.fetch_issue_context")
    async def test_documentation_failure(self, mock_fetch, mock_git, tmp_path):
        """Documentation scan failure is non-fatal — logged to errors."""
        mock_fetch.return_value = {
            "issue": None,
            "parent_issue": None,
            "epic_issue": None,
            "remote_links": [],
        }
        mock_git.return_value = {"commits": []}

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        with patch.object(IssueContextRetriever, "_find_documentation", side_effect=PermissionError("denied")):
            ctx = await retriever.retrieve("T-1", affected_paths=[])

        assert ctx.documentation == []
        assert any("Failed to find documentation" in e for e in ctx.errors)

    @pytest.mark.asyncio
    @patch("agentic_devtools.context.retriever.get_recent_changes")
    @patch("agentic_devtools.context.retriever.fetch_issue_context")
    async def test_validate_path_exception_is_nonfatal(self, mock_fetch, mock_git, tmp_path):
        """An exception inside _validate_path() is caught and logged, not propagated."""
        mock_fetch.return_value = {
            "issue": None,
            "parent_issue": None,
            "epic_issue": None,
            "remote_links": [],
        }
        mock_git.return_value = {"commits": []}

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        with patch.object(IssueContextRetriever, "_validate_path", side_effect=OSError("filesystem error")):
            ctx = await retriever.retrieve("T-1", affected_paths=["some/file.py"])

        assert ctx.relevant_files == []
        assert any("Error validating path some/file.py" in e for e in ctx.errors)


class TestParseCoverage:
    """Tests for IssueContextRetriever._parse_coverage()."""

    def test_valid_coverage_json(self, tmp_path):
        """Extracts per-file data for affected paths."""
        cov_data = {
            "files": {
                "src/a.py": {"summary": {"percent_covered": 100}},
                "src/b.py": {"summary": {"percent_covered": 50}},
            }
        }
        cov_file = tmp_path / "coverage.json"
        cov_file.write_text(json.dumps(cov_data))

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path), coverage_path=str(cov_file))
        result = retriever._parse_coverage(["src/a.py", "src/c.py"])

        assert "src/a.py" in result
        assert result["src/a.py"]["summary"]["percent_covered"] == 100
        assert "src/c.py" not in result

    def test_missing_coverage_json(self, tmp_path):
        """Raises FileNotFoundError when coverage.json is absent."""
        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            retriever._parse_coverage(["a.py"])

    def test_malformed_json(self, tmp_path):
        """Raises json.JSONDecodeError for malformed coverage.json."""
        cov_file = tmp_path / "coverage.json"
        cov_file.write_text("{invalid json")

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path), coverage_path=str(cov_file))
        with pytest.raises(json.JSONDecodeError):
            retriever._parse_coverage(["a.py"])


class TestFindDocumentation:
    """Tests for IssueContextRetriever._find_documentation()."""

    def test_finds_readme_and_docs(self, tmp_path):
        """Finds README.md and docs matching affected path stems."""
        (tmp_path / "README.md").write_text("# Root readme")
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "tools.md").write_text("# Tools docs")

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        result = retriever._find_documentation(["agentic_devtools/tools/jira.py"])

        paths = [d["path"] for d in result]
        assert "README.md" in paths

    def test_no_matching_docs(self, tmp_path):
        """Returns empty list when no docs match."""
        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        result = retriever._find_documentation(["src/nonexistent.py"])

        assert result == []

    def test_none_affected_paths(self, tmp_path):
        """Returns empty list when affected_paths is None."""
        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        result = retriever._find_documentation(None)

        assert result == []

    def test_empty_affected_paths(self, tmp_path):
        """Returns empty list when affected_paths is empty."""
        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        result = retriever._find_documentation([])

        assert result == []

    def test_doc_content_limited_to_200_lines(self, tmp_path):
        """Documentation content is limited to 200 lines."""
        readme = tmp_path / "README.md"
        readme.write_text("\n".join(f"Line {i}" for i in range(300)))

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        result = retriever._find_documentation(["some/file.py"])

        # Should include README.md
        readme_entry = [d for d in result if d["path"] == "README.md"]
        if readme_entry:
            lines = readme_entry[0]["content"].strip().split("\n")
            assert len(lines) == 200

    def test_finds_stem_doc_in_docs_directory(self, tmp_path):
        """Finds docs/<stem>.md when it exists."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "mymodule.md").write_text("# Module docs")

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        result = retriever._find_documentation(["src/mymodule.py"])

        paths = [d["path"] for d in result]
        assert "docs/mymodule.md" in paths

    def test_finds_nested_stem_doc(self, tmp_path):
        """Finds docs/<parent>/<stem>.md for nested paths."""
        nested = tmp_path / "docs" / "tools"
        nested.mkdir(parents=True)
        (nested / "jira.md").write_text("# Jira docs")

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        result = retriever._find_documentation(["agentic_devtools/tools/jira.py"])

        paths = [d["path"] for d in result]
        assert "docs/tools/jira.md" in paths

    def test_finds_directory_readme(self, tmp_path):
        """Finds README.md in the affected file's directory."""
        pkg_dir = tmp_path / "src" / "pkg"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "README.md").write_text("# Package README")

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        result = retriever._find_documentation(["src/pkg/module.py"])

        paths = [d["path"] for d in result]
        assert "src/pkg/README.md" in paths

    def test_read_error_raises(self, tmp_path):
        """File read errors propagate as exceptions from the inner try/except."""
        # Create a doc file that the loop will find (inside the for-candidate loop)
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "mymod.md").write_text("# Docs")

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))

        with patch.object(IssueContextRetriever, "_read_lines", side_effect=PermissionError("denied")):
            with pytest.raises(PermissionError, match="denied"):
                retriever._find_documentation(["src/mymod.py"])

    def test_candidate_outside_repo_skipped(self, tmp_path):
        """Documentation candidates that resolve outside repo are silently skipped."""
        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        # Use a path with ".." that would produce candidates escaping the repo
        result = retriever._find_documentation(["../../etc/secret.py"])

        # Should not crash and should not include paths outside repo
        for doc in result:
            assert ".." not in doc["path"]

    def test_candidate_relative_to_failure_skipped(self, tmp_path):
        """Candidates where relative_to raises ValueError are silently skipped."""
        # Create a doc file that would normally be found
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "mymod.md").write_text("# Docs")

        config = _make_config()
        retriever = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))

        from pathlib import Path

        original_relative_to = Path.relative_to

        def failing_relative_to(self_path, *args, **kwargs):
            # Only fail for doc candidate paths (not root readme or _is_within_repo calls)
            if "docs" in str(self_path) and str(self_path).endswith(".md"):
                raise ValueError("forced failure")
            return original_relative_to(self_path, *args, **kwargs)

        with (
            patch.object(IssueContextRetriever, "_is_within_repo", return_value=True),
            patch.object(Path, "relative_to", failing_relative_to),
        ):
            result = retriever._find_documentation(["src/mymod.py"])

        # Should not crash — docs/mymod.md is skipped due to ValueError
        for doc in result:
            assert "docs/" not in doc["path"]


class TestValidatePath:
    """Tests for IssueContextRetriever._validate_path()."""

    def test_rejects_absolute_path(self, tmp_path):
        """Absolute paths are rejected."""
        config = _make_config()
        r = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        assert r._validate_path("/etc/passwd") is None

    def test_rejects_dotdot_traversal(self, tmp_path):
        """Paths containing .. components are rejected."""
        config = _make_config()
        r = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        assert r._validate_path("../../../etc/passwd") is None

    def test_rejects_nonexistent_file(self, tmp_path):
        """Paths that don't exist on disk are rejected."""
        config = _make_config()
        r = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        assert r._validate_path("nonexistent.py") is None

    def test_accepts_valid_relative_path(self, tmp_path):
        """Valid relative paths within the repo are accepted."""
        (tmp_path / "valid.py").write_text("x = 1")
        config = _make_config()
        r = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        result = r._validate_path("valid.py")
        assert result is not None

    def test_rejects_directory(self, tmp_path):
        """Directories are rejected — only regular files are accepted."""
        (tmp_path / "subdir").mkdir()
        config = _make_config()
        r = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        assert r._validate_path("subdir") is None

    def test_rejects_path_resolving_outside_repo(self, tmp_path):
        """Paths that resolve outside repo via symlink are rejected."""
        # Create a symlink that points outside the repo
        outside = tmp_path.parent / "outside_file.py"
        outside.write_text("secret")
        link = tmp_path / "sneaky_link.py"
        try:
            link.symlink_to(outside)
        except OSError:
            pytest.skip("Symlink creation not permitted on this platform/configuration")

        config = _make_config()
        r = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        result = r._validate_path("sneaky_link.py")
        assert result is None


class TestIsWithinRepo:
    """Tests for IssueContextRetriever._is_within_repo()."""

    def test_path_within_repo(self, tmp_path):
        """Returns True for paths inside the repo."""
        config = _make_config()
        r = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        assert r._is_within_repo((tmp_path / "subdir" / "file.py").resolve()) is True

    def test_path_outside_repo(self, tmp_path):
        """Returns False for paths outside the repo."""
        config = _make_config()
        r = IssueContextRetriever(jira_config=config, repo_path=str(tmp_path))
        from pathlib import Path

        assert r._is_within_repo(Path("/etc/passwd").resolve()) is False


class TestReadLines:
    """Tests for IssueContextRetriever._read_lines static method."""

    def test_reads_limited_lines(self, tmp_path):
        """Reads up to max_lines from a file."""
        f = tmp_path / "test.txt"
        f.write_text("line1\nline2\nline3\nline4\nline5\n")

        result = IssueContextRetriever._read_lines(f, 3)
        assert result.count("\n") == 3
        assert "line1" in result
        assert "line4" not in result

    def test_reads_entire_short_file(self, tmp_path):
        """Reads the full content if file has fewer lines than max_lines."""
        f = tmp_path / "short.txt"
        f.write_text("only one line\n")

        result = IssueContextRetriever._read_lines(f, 200)
        assert result == "only one line\n"
