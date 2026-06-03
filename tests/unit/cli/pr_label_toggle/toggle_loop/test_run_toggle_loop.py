"""Tests for run_toggle_loop."""

from __future__ import annotations

from unittest.mock import patch

from agentic_devtools.cli.pr_label_toggle import PrInfo, PrLabelToggleProvider
from agentic_devtools.cli.pr_label_toggle.toggle_loop import (
    ToggleConfig,
    run_toggle_loop,
)

_MOD = "agentic_devtools.cli.pr_label_toggle.toggle_loop"


class FakeProvider(PrLabelToggleProvider):
    """A fake provider that records calls for testing."""

    def __init__(self):
        self.prs: list[PrInfo] = []
        self.open_prs: set[int] = set()
        self.labels: dict[int, set[str]] = {}
        self.calls: list[tuple[str, ...]] = []

    def get_newest_open_pr(self) -> PrInfo | None:
        self.calls.append(("get_newest_open_pr",))
        for pr in reversed(self.prs):
            if pr.number in self.open_prs:
                return pr
        return None

    def is_pr_open(self, pr_number: int) -> bool:
        self.calls.append(("is_pr_open", str(pr_number)))
        return pr_number in self.open_prs

    def has_label(self, pr_number: int, label: str) -> bool | None:
        self.calls.append(("has_label", str(pr_number), label))
        if pr_number not in self.labels:
            return None
        return label in self.labels[pr_number]

    def add_label(self, pr_number: int, label: str) -> None:
        self.calls.append(("add_label", str(pr_number), label))
        self.labels.setdefault(pr_number, set()).add(label)

    def remove_label(self, pr_number: int, label: str) -> None:
        self.calls.append(("remove_label", str(pr_number), label))
        self.labels.get(pr_number, set()).discard(label)


class TestRunToggleLoopMaxDuration:
    """Tests for max duration stop condition."""

    @patch(f"{_MOD}.time.time")
    @patch(f"{_MOD}.time.sleep")
    def test_stops_after_max_duration(self, mock_sleep, mock_time):
        """Loop stops when elapsed time exceeds max_hours."""
        # First call is start_time, second check exceeds duration
        mock_time.side_effect = [0.0, 3700.0]

        provider = FakeProvider()
        config = ToggleConfig(label="test-label", max_hours=1)

        result = run_toggle_loop(provider, config)

        assert result.stop_reason == "max_duration"
        assert result.cycles_completed == 0


class TestRunToggleLoopNoPrs:
    """Tests for no open PRs stop condition."""

    @patch(f"{_MOD}.time.time")
    @patch(f"{_MOD}.time.sleep")
    def test_stops_after_consecutive_no_pr(self, mock_sleep, mock_time):
        """Loop stops after max_consecutive_no_pr consecutive misses."""
        # Always return 0 for start, and < max for elapsed checks
        mock_time.return_value = 0.0

        provider = FakeProvider()
        # No PRs available
        config = ToggleConfig(
            label="test-label",
            interval_seconds=60,
            max_consecutive_no_pr=3,
        )

        result = run_toggle_loop(provider, config)

        assert result.stop_reason == "no_open_prs"
        assert result.cycles_completed == 0
        assert mock_sleep.call_count == 2  # sleeps between retries (3 checks, 2 sleeps)

    @patch(f"{_MOD}.time.time")
    @patch(f"{_MOD}.time.sleep")
    def test_resets_counter_when_pr_found(self, mock_sleep, mock_time):
        """Consecutive no-PR counter resets when a PR is found."""
        mock_time.return_value = 0.0

        provider = FakeProvider()
        # First call: no PR; second call: found a PR; then label check
        call_count = [0]

        def get_pr_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return None
            return PrInfo(number=42, is_open=True)

        provider.get_newest_open_pr = get_pr_side_effect
        provider.open_prs = {42}
        provider.labels = {42: set()}

        config = ToggleConfig(
            label="test-label",
            interval_seconds=60,
            max_consecutive_no_pr=2,
            max_hours=1,
        )

        # After adding label, next cycle will check for new PR (after remove).
        # But we added, so it will use cached. Force stop via KeyboardInterrupt.
        sleep_count = [0]

        def sleep_side_effect(seconds):
            sleep_count[0] += 1
            if sleep_count[0] >= 3:
                raise KeyboardInterrupt

        mock_sleep.side_effect = sleep_side_effect

        result = run_toggle_loop(provider, config)

        assert result.stop_reason == "interrupted"
        assert result.cycles_completed >= 1


class TestRunToggleLoopToggleBehavior:
    """Tests for label add/remove toggling."""

    @patch(f"{_MOD}.time.time")
    @patch(f"{_MOD}.time.sleep")
    def test_adds_label_when_missing(self, mock_sleep, mock_time):
        """Adds label when PR does not have it."""
        mock_time.return_value = 0.0

        provider = FakeProvider()
        provider.prs = [PrInfo(number=100, is_open=True)]
        provider.open_prs = {100}
        provider.labels = {100: set()}

        config = ToggleConfig(label="my-label", interval_seconds=60, max_hours=1)

        # Stop after first cycle
        mock_sleep.side_effect = KeyboardInterrupt

        result = run_toggle_loop(provider, config)

        assert result.cycles_completed == 1
        assert "my-label" in provider.labels[100]

    @patch(f"{_MOD}.time.time")
    @patch(f"{_MOD}.time.sleep")
    def test_removes_label_when_present(self, mock_sleep, mock_time):
        """Removes label when PR already has it."""
        mock_time.return_value = 0.0

        provider = FakeProvider()
        provider.prs = [PrInfo(number=100, is_open=True)]
        provider.open_prs = {100}
        provider.labels = {100: {"my-label"}}

        config = ToggleConfig(label="my-label", interval_seconds=60, max_hours=1)

        # Stop after first cycle
        mock_sleep.side_effect = KeyboardInterrupt

        result = run_toggle_loop(provider, config)

        assert result.cycles_completed == 1
        assert "my-label" not in provider.labels[100]

    @patch(f"{_MOD}.time.time")
    @patch(f"{_MOD}.time.sleep")
    def test_only_checks_new_pr_after_remove(self, mock_sleep, mock_time):
        """After add, uses cached PR. After remove, checks for newer PR."""
        mock_time.return_value = 0.0

        provider = FakeProvider()
        provider.prs = [PrInfo(number=50, is_open=True)]
        provider.open_prs = {50}
        provider.labels = {50: set()}

        config = ToggleConfig(label="lbl", interval_seconds=60, max_hours=1)

        cycle = [0]

        def sleep_side_effect(seconds):
            cycle[0] += 1
            if cycle[0] >= 2:
                raise KeyboardInterrupt

        mock_sleep.side_effect = sleep_side_effect

        run_toggle_loop(provider, config)

        # First cycle: add (get_newest_open_pr called)
        # Second cycle: remove (since add → cached, but label now present → remove)
        # But second cycle should NOT call get_newest_open_pr (cached after add)
        get_calls = [c for c in provider.calls if c[0] == "get_newest_open_pr"]
        # First cycle needs new PR, second does not (last action was add)
        assert len(get_calls) == 1


class TestRunToggleLoopClosedPr:
    """Tests for handling closed/merged PRs."""

    @patch(f"{_MOD}.time.time")
    @patch(f"{_MOD}.time.sleep")
    def test_removes_label_from_closed_pr_and_moves_on(self, mock_sleep, mock_time):
        """When cached PR is closed, removes label and looks for next PR."""
        mock_time.return_value = 0.0

        provider = FakeProvider()
        provider.prs = [PrInfo(number=10, is_open=True)]
        provider.open_prs = {10}  # Start open
        provider.labels = {10: set()}  # No label initially

        config = ToggleConfig(
            label="the-label",
            interval_seconds=60,
            max_hours=1,
            max_consecutive_no_pr=2,
        )

        call_count = [0]

        def sleep_side_effect(seconds):
            call_count[0] += 1
            if call_count[0] == 1:
                # After first cycle (label added), close the PR
                provider.open_prs.discard(10)

        mock_sleep.side_effect = sleep_side_effect

        result = run_toggle_loop(provider, config)

        assert result.stop_reason == "no_open_prs"
        # Label was removed from the closed PR
        assert "the-label" not in provider.labels[10]

    @patch(f"{_MOD}.time.time")
    @patch(f"{_MOD}.time.sleep")
    def test_closed_pr_without_label_skips_removal(self, mock_sleep, mock_time):
        """When cached PR is closed but has no label, skips removal."""
        mock_time.return_value = 0.0

        provider = FakeProvider()
        provider.prs = [PrInfo(number=20, is_open=True)]
        provider.open_prs = {20}
        provider.labels = {20: set()}  # No label

        config = ToggleConfig(
            label="lbl",
            interval_seconds=60,
            max_hours=1,
            max_consecutive_no_pr=2,
        )

        call_count = [0]

        def sleep_side_effect(seconds):
            call_count[0] += 1
            if call_count[0] == 1:
                # After first cycle (label added), close the PR
                provider.open_prs.discard(20)
                # Simulate external removal of label between cycles
                provider.labels[20].discard("lbl")

        mock_sleep.side_effect = sleep_side_effect

        result = run_toggle_loop(provider, config)

        assert result.stop_reason == "no_open_prs"
        # Verify remove_label was NOT called for the closed PR (label was already gone)
        remove_calls = [c for c in provider.calls if c[0] == "remove_label" and c[1] == "20"]
        assert len(remove_calls) == 0


class TestRunToggleLoopGenericException:
    """Tests for generic exception handling."""

    @patch(f"{_MOD}.time.time")
    @patch(f"{_MOD}.time.sleep")
    def test_returns_error_on_unexpected_exception(self, mock_sleep, mock_time):
        """Returns error stop_reason on unexpected exception."""
        mock_time.return_value = 0.0

        provider = FakeProvider()
        provider.prs = [PrInfo(number=1, is_open=True)]
        provider.open_prs = {1}
        provider.labels = {1: set()}

        # Make add_label raise an unexpected error
        def raise_error(pr_number, label):
            raise RuntimeError("network failure")

        provider.add_label = raise_error

        config = ToggleConfig(label="lbl", interval_seconds=60, max_hours=1)

        result = run_toggle_loop(provider, config)

        assert "error:" in result.stop_reason
        assert "network failure" in result.stop_reason

    """Tests for label parse failure handling."""

    @patch(f"{_MOD}.time.time")
    @patch(f"{_MOD}.time.sleep")
    def test_retries_on_parse_failure(self, mock_sleep, mock_time):
        """Retries next cycle when has_label returns None."""
        mock_time.return_value = 0.0

        provider = FakeProvider()
        provider.prs = [PrInfo(number=5, is_open=True)]
        provider.open_prs = {5}
        # Don't set labels[5] so has_label returns None

        config = ToggleConfig(label="lbl", interval_seconds=60, max_hours=1)

        cycle = [0]

        def sleep_side_effect(seconds):
            cycle[0] += 1
            if cycle[0] >= 2:
                raise KeyboardInterrupt

        mock_sleep.side_effect = sleep_side_effect

        result = run_toggle_loop(provider, config)

        assert result.stop_reason == "interrupted"
        assert result.cycles_completed == 0  # No successful toggle


class TestRunToggleLoopInterrupt:
    """Tests for keyboard interrupt handling."""

    @patch(f"{_MOD}.time.time")
    @patch(f"{_MOD}.time.sleep")
    def test_returns_interrupted_on_ctrl_c(self, mock_sleep, mock_time):
        """Returns interrupted stop_reason on KeyboardInterrupt."""
        mock_time.return_value = 0.0

        provider = FakeProvider()
        provider.prs = [PrInfo(number=1, is_open=True)]
        provider.open_prs = {1}
        provider.labels = {1: set()}

        config = ToggleConfig(label="lbl", interval_seconds=60, max_hours=1)

        mock_sleep.side_effect = KeyboardInterrupt

        result = run_toggle_loop(provider, config)

        assert result.stop_reason == "interrupted"
