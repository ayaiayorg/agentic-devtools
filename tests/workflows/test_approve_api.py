"""Tests for approve API call handling (T023).

Tests the expected behavior for different HTTP response codes from the
GitHub approve workflow run API.
"""


class TestApproveApi:
    """Test approve API response handling (FR-003)."""

    def _classify_response(self, status_code, headers=None):
        """Replicate the response classification logic from the workflow.

        Returns a tuple of (result, reason) matching the workflow's behavior.

        Args:
            status_code: HTTP status code from the approve API.
            headers: Optional dict of response headers. Used to detect
                rate-limited 403 responses (x-ratelimit-remaining=0 or
                retry-after present).
        """
        if headers is None:
            headers = {}
        if status_code in (201, 202):
            return ("success", None)
        elif status_code == 403:
            ratelimit_remaining = headers.get("x-ratelimit-remaining")
            retry_after = headers.get("retry-after")
            if ratelimit_remaining == "0" or retry_after:
                return (
                    "skipped",
                    f"Rate-limited (403) — retry-after: {retry_after or 'n/a'}, will retry next cycle",
                )
            return (
                "failure",
                "Permission denied (403)",
            )
        elif status_code == 429:
            return (
                "skipped",
                "Rate-limited (429) — retry-after: n/a, will retry next cycle",
            )
        elif status_code in (404, 409):
            return ("skipped", f"Run not approvable (HTTP {status_code})")
        else:
            return ("failure", f"Unexpected HTTP {status_code}")

    def test_201_success(self):
        """HTTP 201 indicates successful approval."""
        result, reason = self._classify_response(201)
        assert result == "success"
        assert reason is None

    def test_202_success(self):
        """HTTP 202 (accepted) also indicates successful approval."""
        result, reason = self._classify_response(202)
        assert result == "success"
        assert reason is None

    def test_403_permission_denied(self):
        """HTTP 403 without rate-limit headers indicates permission denied."""
        result, reason = self._classify_response(403)
        assert result == "failure"
        assert "Permission denied (403)" in reason

    def test_403_rate_limited_via_ratelimit_remaining(self):
        """HTTP 403 with x-ratelimit-remaining=0 is skipped (rate-limited)."""
        headers = {"x-ratelimit-remaining": "0"}
        result, reason = self._classify_response(403, headers=headers)
        assert result == "skipped"
        assert "Rate-limited" in reason
        assert "will retry next cycle" in reason

    def test_403_rate_limited_via_retry_after(self):
        """HTTP 403 with retry-after header is skipped (rate-limited)."""
        headers = {"retry-after": "60"}
        result, reason = self._classify_response(403, headers=headers)
        assert result == "skipped"
        assert "Rate-limited" in reason
        assert "retry-after: 60" in reason

    def test_403_rate_limited_via_both_headers(self):
        """HTTP 403 with both rate-limit headers is skipped."""
        headers = {"x-ratelimit-remaining": "0", "retry-after": "30"}
        result, reason = self._classify_response(403, headers=headers)
        assert result == "skipped"
        assert "Rate-limited" in reason

    def test_403_with_nonzero_ratelimit_remaining(self):
        """HTTP 403 with x-ratelimit-remaining > 0 is still a failure."""
        headers = {"x-ratelimit-remaining": "50"}
        result, reason = self._classify_response(403, headers=headers)
        assert result == "failure"
        assert "Permission denied" in reason

    def test_404_not_approvable(self):
        """HTTP 404 indicates run is not in an approvable state."""
        result, reason = self._classify_response(404)
        assert result == "skipped"
        assert "not approvable" in reason

    def test_409_conflict(self):
        """HTTP 409 indicates run is not in an approvable state (conflict)."""
        result, reason = self._classify_response(409)
        assert result == "skipped"
        assert "not approvable" in reason

    def test_500_unexpected_error(self):
        """HTTP 500 is treated as an unexpected failure."""
        result, reason = self._classify_response(500)
        assert result == "failure"
        assert "Unexpected HTTP 500" in reason

    def test_429_rate_limit(self):
        """HTTP 429 (rate limit) is skipped — does not consume a retry."""
        result, reason = self._classify_response(429)
        assert result == "skipped"
        assert "Rate-limited" in reason
        assert "will retry next cycle" in reason
