"""Tests for pypi_version_exists function."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.release.helpers import ReleaseError, pypi_version_exists


class TestPypiVersionExists:
    """Tests for pypi_version_exists function."""

    def test_raises_for_unsupported_repository(self):
        """Should raise ValueError for unsupported repository names."""
        with pytest.raises(ValueError):
            pypi_version_exists("pkg", "1.0", repository="npmjs")

    def test_returns_true_for_200_response(self):
        """Should return True when the PyPI API responds with 200."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.release.helpers._get_requests",
            return_value=mock_requests,
        ):
            result = pypi_version_exists("my-package", "1.0.0")

        assert result is True

    def test_returns_false_for_404_response(self):
        """Should return False when the PyPI API responds with 404."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.release.helpers._get_requests",
            return_value=mock_requests,
        ):
            result = pypi_version_exists("my-package", "1.0.0")

        assert result is False

    def test_raises_release_error_for_non_200_404_status(self):
        """Should raise ReleaseError for unexpected HTTP status codes."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.release.helpers._get_requests",
            return_value=mock_requests,
        ):
            with pytest.raises(ReleaseError):
                pypi_version_exists("my-package", "1.0.0")

    def test_uses_testpypi_url_when_specified(self):
        """Should use test.pypi.org URL when repository='testpypi'."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.release.helpers._get_requests",
            return_value=mock_requests,
        ):
            pypi_version_exists("my-package", "1.0.0", repository="testpypi")

        call_url = mock_requests.get.call_args[0][0]
        assert "test.pypi.org" in call_url

    def test_uses_pypi_url_by_default(self):
        """Should use pypi.org URL by default."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.release.helpers._get_requests",
            return_value=mock_requests,
        ):
            pypi_version_exists("my-package", "1.0.0")

        call_url = mock_requests.get.call_args[0][0]
        assert "pypi.org" in call_url
        assert "test.pypi.org" not in call_url
