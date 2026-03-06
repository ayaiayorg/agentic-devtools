"""Tests for build_commit_pr_url function."""

from agentic_devtools.cli.azure_devops.review_attribution import build_commit_pr_url


class TestBuildCommitPrUrl:
    """Tests for build_commit_pr_url."""

    def test_basic_url_construction(self):
        """Test basic URL is constructed with all parameters (no path param)."""
        url = build_commit_pr_url(
            organization="https://dev.azure.com/myorg",
            project="MyProject",
            repo_name="my-repo",
            pr_id=42,
            iteration=3,
            base=2,
        )
        assert url == ("https://dev.azure.com/myorg/MyProject/_git/my-repo/pullrequest/42?_a=files&base=2&iteration=3")

    def test_no_path_parameter_in_url(self):
        """Test that the URL does not include a 'path' query parameter."""
        url = build_commit_pr_url(
            organization="https://dev.azure.com/myorg",
            project="MyProject",
            repo_name="my-repo",
            pr_id=1,
            iteration=2,
            base=1,
        )
        assert "path=" not in url

    def test_base_defaults_to_iteration_minus_one(self):
        """Test that base defaults to iteration - 1 when not provided."""
        url = build_commit_pr_url(
            organization="https://dev.azure.com/myorg",
            project="MyProject",
            repo_name="my-repo",
            pr_id=42,
            iteration=5,
        )
        assert "base=4" in url
        assert "iteration=5" in url

    def test_iteration_one_base_defaults_to_zero(self):
        """Test that iteration=1 with no base gives base=0."""
        url = build_commit_pr_url(
            organization="https://dev.azure.com/myorg",
            project="MyProject",
            repo_name="my-repo",
            pr_id=1,
            iteration=1,
        )
        assert "base=0" in url
        assert "iteration=1" in url

    def test_organization_trailing_slash_stripped(self):
        """Test that a trailing slash on organization is removed."""
        url = build_commit_pr_url(
            organization="https://dev.azure.com/myorg/",
            project="MyProject",
            repo_name="my-repo",
            pr_id=1,
            iteration=2,
        )
        assert "myorg//" not in url
        assert url.startswith("https://dev.azure.com/myorg/")

    def test_explicit_base_zero(self):
        """Test that base=0 is used as-is (not replaced by iteration-1)."""
        url = build_commit_pr_url(
            organization="https://dev.azure.com/myorg",
            project="MyProject",
            repo_name="my-repo",
            pr_id=1,
            iteration=5,
            base=0,
        )
        assert "base=0" in url

    def test_project_and_repo_name_are_url_encoded(self):
        """Test that project and repo_name with special characters are URL-encoded."""
        url = build_commit_pr_url(
            organization="https://dev.azure.com/myorg",
            project="My Project#1",
            repo_name="my repo#1",
            pr_id=42,
            iteration=3,
            base=2,
        )
        assert url == (
            "https://dev.azure.com/myorg/My%20Project%231/_git/my%20repo%231/pullrequest/42"
            "?_a=files&base=2&iteration=3"
        )
