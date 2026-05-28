# Agent Session Monitor for AI PR Loop (Issue #1587)

## Summary

This PR adds a dedicated `agent-session-monitor.yml` workflow that detects Copilot terminal session events on open PRs and dispatches `ai-pr-loop.yml` automatically.

## Implemented Behavior

- Schedule: `*/5 * * * *` (every 5 minutes) + manual `workflow_dispatch`
- Detection: scans PR issue events for `copilot_work_finished` and `copilot_work_finished_failure`
- Dispatch: `gh workflow run ai-pr-loop.yml --field pr_number=... --field trigger_reason=agent_session_finished`
- Deduplication: persisted seen-event IDs via `actions/cache`
- Guards: skips fork PRs and PRs labeled `ai-pr-loop-ignore`
- Observability: structured logs and step summary metrics
- Safety: dry-run mode via `AGENT_MONITOR_DRY_RUN`

## Notes

This aligns with GitHub Actions scheduled-workflow cadence constraints by targeting a 5-minute polling interval (up to 300s detection latency).

Relates to #1587
