"""Tests for build_commit_file_url function."""

from agentic_devtools.cli.azure_devops.review_attribution import build_commit_file_url


class TestBuildCommitFileUrl:
    """Tests for build_commit_file_url."""

    def test_basic_url_construction(self):
        """Test basic URL is constructed with all parameters."""
        url = build_commit_file_url(
            organization="https://dev.azure.com/myorg",
            project="MyProject",
            repo_name="my-repo",
            pr_id=42,
            file_path="/src/app.py",
            iteration=3,
            base=2,
        )
        assert url == (
            "https://dev.azure.com/myorg/MyProject/_git/my-repo/pullrequest/42"
            "?_a=files&base=2&iteration=3&path=/src/app.py"
        )

    def test_base_defaults_to_iteration_minus_one(self):
        """Test that base defaults to iteration - 1 when not provided."""
        url = build_commit_file_url(
            organization="https://dev.azure.com/myorg",
            project="MyProject",
            repo_name="my-repo",
            pr_id=42,
            file_path="/src/app.py",
            iteration=5,
        )
        assert "base=4" in url
        assert "iteration=5" in url

    def test_iteration_one_base_defaults_to_zero(self):
        """Test that iteration=1 with no base gives base=0 (ADO PR base)."""
        url = build_commit_file_url(
            organization="https://dev.azure.com/myorg",
            project="MyProject",
            repo_name="my-repo",
            pr_id=1,
            file_path="/file.ts",
            iteration=1,
        )
        assert "base=0" in url
        assert "iteration=1" in url

    def test_file_path_without_leading_slash_is_normalized(self):
        """Test that a file path without a leading slash gets one prepended."""
        url = build_commit_file_url(
            organization="https://dev.azure.com/myorg",
            project="MyProject",
            repo_name="my-repo",
            pr_id=1,
            file_path="src/utils.py",
            iteration=2,
        )
        assert "path=/src/utils.py" in url

    def test_file_path_with_leading_slash_unchanged(self):
        """Test that a file path with a leading slash is not double-slashed."""
        url = build_commit_file_url(
            organization="https://dev.azure.com/myorg",
            project="MyProject",
            repo_name="my-repo",
            pr_id=1,
            file_path="/src/utils.py",
            iteration=2,
        )
        assert "path=/src/utils.py" in url
        assert "path=//src" not in url

    def test_organization_trailing_slash_stripped(self):
        """Test that a trailing slash on organization is removed."""
        url = build_commit_file_url(
            organization="https://dev.azure.com/myorg/",
            project="MyProject",
            repo_name="my-repo",
            pr_id=1,
            file_path="/file.py",
            iteration=2,
        )
        assert "myorg//" not in url
        assert url.startswith("https://dev.azure.com/myorg/")

    def test_explicit_base_zero(self):
        """Test that base=0 is used as-is (not replaced by iteration-1)."""
        url = build_commit_file_url(
            organization="https://dev.azure.com/myorg",
            project="MyProject",
            repo_name="my-repo",
            pr_id=1,
            file_path="/file.py",
            iteration=5,
            base=0,
        )
        assert "base=0" in url

    def test_special_characters_in_path_are_url_encoded(self):
        """Test that spaces, #, ? and other special chars in file path are URL-encoded."""
        url = build_commit_file_url(
            organization="https://dev.azure.com/myorg",
            project="MyProject",
            repo_name="my-repo",
            pr_id=1,
            file_path="/src/my file#2.py",
            iteration=2,
        )
        assert "path=/src/my%20file%232.py" in url

    def test_backslashes_normalized_to_forward_slashes(self):
        """Test that backslashes in file path are replaced with forward slashes."""
        url = build_commit_file_url(
            organization="https://dev.azure.com/myorg",
            project="MyProject",
            repo_name="my-repo",
            pr_id=1,
            file_path="src\\utils\\app.py",
            iteration=2,
        )
        assert "path=/src/utils/app.py" in url
        assert "\\" not in url

    def test_project_and_repo_name_are_url_encoded(self):
        """Test that project and repo_name with special chars are URL-encoded."""
        url = build_commit_file_url(
            organization="https://dev.azure.com/myorg",
            project="My Project",
            repo_name="my repo#1",
            pr_id=1,
            file_path="/file.py",
            iteration=2,
        )
        assert "My%20Project/_git/my%20repo%231" in url
