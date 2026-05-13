"""Tests for check_docker_files() guard."""

from agentic_devtools.cli.ci.guards import check_docker_files


class TestCheckDockerFiles:
    """Tests for the Docker files guard."""

    def test_dockerfile_triggers(self) -> None:
        assert check_docker_files(["Dockerfile"]) is True

    def test_docker_compose_yml_triggers(self) -> None:
        assert check_docker_files(["docker-compose.yml"]) is True

    def test_docker_compose_yaml_triggers(self) -> None:
        assert check_docker_files(["docker-compose.yaml"]) is True

    def test_dockerignore_triggers(self) -> None:
        assert check_docker_files([".dockerignore"]) is True

    def test_dockerfile_with_suffix_triggers(self) -> None:
        assert check_docker_files(["Dockerfile.prod"]) is True

    def test_dockerfile_in_subdirectory(self) -> None:
        assert check_docker_files(["services/api/Dockerfile"]) is True

    def test_non_docker_files(self) -> None:
        assert check_docker_files(["src/main.py", "package.json"]) is False

    def test_empty_file_list(self) -> None:
        assert check_docker_files([]) is False

    def test_similar_but_not_docker(self) -> None:
        """Files with 'docker' in the name but not matching patterns."""
        assert check_docker_files(["docs/docker-guide.md"]) is False

    def test_mixed_docker_and_normal(self) -> None:
        files = ["src/app.py", "docker-compose.yml", "README.md"]
        assert check_docker_files(files) is True
