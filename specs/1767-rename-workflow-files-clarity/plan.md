# Implementation Plan: Rename Workflow Files for Clarity

## Technical Context

- **Stack**: GitHub Actions YAML workflows, Python (agentic-devtools package), pytest
- **Repository**: `ayaiayorg/agentic-devtools`
- **Branch**: Feature work on `speckit/1767/phase-3-plan`
- **Issue**: [#1767](https://github.com/ayaiayorg/agentic-devtools/issues/1767)

## Research Summary

No technology decisions needed — this is a pure rename/refactor. See research.md for the
complete file inventory and reference mapping.

## Design Overview

This is a mechanical rename with two workflow files being renamed and all cross-references
updated. No logic changes, no new features. The rename makes the dispatch chain self-documenting:

```text
ai-pr-loop-dispatcher (cold-start on PR events)
  → ai-pr-loop-throttler (selects oldest eligible PR)
      → ai-pr-loop (executes)
          → ai-pr-loop-redispatch → ai-pr-loop-throttler → ...
```

## Implementation Phases

### Phase 1: File Renames (git mv)

1. `git mv .github/workflows/agent-session-monitor.yml .github/workflows/ai-pr-loop-throttler.yml`
2. `git mv .github/workflows/pr-activity-dispatch.yml .github/workflows/ai-pr-loop-dispatcher.yml`
3. `git mv tests/workflows/test_agent_session_monitor.py tests/workflows/test_ai_pr_loop_throttler.py`

### Phase 2: Update `ai-pr-loop-throttler.yml` (formerly agent-session-monitor.yml)

| Line | Old | New |
|------|-----|-----|
| 5 | `pr-activity-dispatch cold-starts` | `ai-pr-loop-dispatcher cold-starts` |
| 26 | `pr-activity-dispatch.yml — cold-start trigger` | `ai-pr-loop-dispatcher.yml — cold-start trigger` |
| 28 | `name: Agent Session Monitor` | `name: ai-pr-loop-throttler` |
| 44 | `group: agent-session-monitor` | `group: ai-pr-loop-throttler` |
| 72 | structured log prefix: `[agent-session-monitor]` | `[ai-pr-loop-throttler]` |

### Phase 3: Update `ai-pr-loop-dispatcher.yml` (formerly pr-activity-dispatch.yml)

| Line | Old | New |
|------|-----|-----|
| 1 | `# PR Activity → Agent Session Monitor Dispatch` | `# PR Activity → AI PR Loop Throttler Dispatch` |
| 3 | `triggers the Agent Session Monitor` | `triggers the AI PR Loop Throttler` |
| 8 | `name: PR Activity Dispatch` | `name: ai-pr-loop-dispatcher` |
| 26 | `group: pr-activity-dispatch` | `group: ai-pr-loop-dispatcher` |
| 44 | comment: `agent-session-monitor` | `ai-pr-loop-throttler` |
| 45 | API path: `agent-session-monitor.yml` | `ai-pr-loop-throttler.yml` |
| 53 | echo: `agent-session-monitor` | `ai-pr-loop-throttler` |
| 83 | step name: `Dispatch Agent Session Monitor` | `Dispatch AI PR Loop Throttler` |
| 88 | `gh workflow run agent-session-monitor.yml` | `gh workflow run ai-pr-loop-throttler.yml` |

### Phase 4: Update `ai-pr-loop-redispatch.yml`

All references to `agent-session-monitor` → `ai-pr-loop-throttler`:

| Line | Context | Change |
|------|---------|--------|
| 5 | Comment | `agent-session-monitor` → `ai-pr-loop-throttler` |
| 7 | Comment: `pr-activity-dispatch` | `ai-pr-loop-dispatcher` |
| 13 | Comment | `agent-session-monitor` → `ai-pr-loop-throttler` |
| 14 | Comment: `pr-activity-dispatch's` | `ai-pr-loop-dispatcher's` |
| 15 | Comment | `agent-session-monitor.yml` → `ai-pr-loop-throttler.yml` |
| 98 | Comment: `pr-activity-dispatch's 60 s cooldown` | `ai-pr-loop-dispatcher's 60 s cooldown` |
| 103 | API path | `agent-session-monitor.yml` → `ai-pr-loop-throttler.yml` |
| 111 | echo string | `agent-session-monitor` → `ai-pr-loop-throttler` |
| 119 | echo string | `agent-session-monitor` → `ai-pr-loop-throttler` |
| 126 | echo string | `agent-session-monitor` → `ai-pr-loop-throttler` |
| 137 | echo string | `agent-session-monitor` → `ai-pr-loop-throttler` |
| 145 | step name | `Dispatch agent-session-monitor` → `Dispatch ai-pr-loop-throttler` |
| 150 | `gh workflow run` | `agent-session-monitor.yml` → `ai-pr-loop-throttler.yml` |

### Phase 5: Update `.github/workflows/README.md`

All instances of:

- `agent-session-monitor` → `ai-pr-loop-throttler`
- `pr-activity-dispatch` → `ai-pr-loop-dispatcher`

(~12 references across the README)

### Phase 6: Update Python source

**`agentic_devtools/cli/ci/guards.py`** (line 469):

- `agent-session-monitor no longer re-triggers` → `ai-pr-loop-throttler no longer re-triggers`

### Phase 7: Update test files

**`tests/workflows/test_ai_pr_loop_throttler.py`** (renamed file):

- Line 1 docstring: `agent-session-monitor.yml` → `ai-pr-loop-throttler.yml`
- Line 8 path constant: `"agent-session-monitor.yml"` → `"ai-pr-loop-throttler.yml"`
- Line 11 class name: `TestAgentSessionMonitor` → `TestAiPrLoopThrottler`
- Line 12 docstring: `agent-session-monitor` → `ai-pr-loop-throttler`
- Lines 14-153: All `AGENT_SESSION_MONITOR` variable refs → `AI_PR_LOOP_THROTTLER`
- Line 39 assertion: `"agent-session-monitor"` → `"ai-pr-loop-throttler"`
- Line 74 job key assertion: `"monitor-agent-sessions"` stays (job key in YAML — update if renamed in Phase 2)

**`tests/workflows/test_ai_pr_loop_redispatch.py`**:

- Line 64: `"agent-session-monitor.yml/runs"` → `"ai-pr-loop-throttler.yml/runs"`
- Line 73: `"gh workflow run agent-session-monitor.yml"` → `"gh workflow run ai-pr-loop-throttler.yml"`

### Phase 8: Update PR_DESCRIPTION.md

- Line 5: `agent-session-monitor.yml` → `ai-pr-loop-throttler.yml` (active repo doc, not historical spec)

### Phase 9: Verification

1. Run `grep -r "agent-session-monitor" --include="*.yml" --include="*.yaml" --include="*.py" --include="*.md" --exclude-dir=specs .` — expect zero results (excluding specs/)
2. Run `grep -r "pr-activity-dispatch" --include="*.yml" --include="*.yaml" --include="*.py" --include="*.md" --exclude-dir=specs .` — expect zero results (excluding specs/)
3. Run `agdt-test-pattern tests/workflows/ -v` — all workflow tests pass
4. Run `agdt-test` and `agdt-task-wait` — canonical full-suite validation for agents
5. Run `bash scripts/run-pr-checks.sh --full` — local comprehensive checks pass
6. Validate YAML syntax: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ai-pr-loop-throttler.yml'))"` (and dispatcher)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| GitHub Actions history split across old/new workflow entries after rename | Medium | Low | Expected behavior: filename rename creates a new workflow ID/history entry. Keep old workflow history for reference and validate both entries during rollout. |
| External automation referencing old filenames | Low | Medium | Only internal `gh workflow run` calls reference these; all updated in this PR. |
| Missed reference in an untracked file | Low | Low | Comprehensive grep verification in Phase 9 catches any misses. |
| Job key rename (`monitor-agent-sessions`) breaks external references | Low | Low | Keep job key unchanged unless explicitly required — it's internal to the YAML. |

## Dependencies

- No external dependencies
- No package version changes
- No new tooling required
- Blocked by: nothing (pure rename)

---
*Generated by Copilot SDK (claude-opus-4.6)*
