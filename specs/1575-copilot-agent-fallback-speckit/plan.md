# Implementation Plan: Copilot Agent Fallback on SpecKit Generation Failures

## Technical Context

**Stack**: GitHub Actions workflows (YAML), `actions/github-script@v7` (JavaScript), Bash shell scripts
**Key Dependencies**:

- Existing workflows: `speckit-issue-trigger.yml` (Phase 1), `speckit-phase-progression.yml` (Phases 2–5)
- Validation library: `.github/scripts/speckit-trigger/lib/spec-validation.sh` (defines structural error categories)
- Existing pattern: `speckit-implement-trigger.yml` uses `agent_assignment` PATCH API — this feature uses the REST `POST /repos/{owner}/{repo}/copilot/coding-agent/tasks` endpoint instead
- Token: `COPILOT_GITHUB_TOKEN` (already available in both workflows)

**Architecture Decision**: Shared reusable JavaScript module (loaded via `actions/github-script`) rather than a composite action, because the logic requires GitHub API calls (octokit), environment
variable access, and step output handling that composite actions handle poorly. The module lives at `.github/scripts/speckit-trigger/agent-fallback.js`.

## Research Summary

See [research.md](research.md) for detailed decisions on:

1. **Reusable component format**: GitHub Script module (not composite action)
2. **Failure detection mechanism**: `$GITHUB_OUTPUT` from orchestrator step + workspace file fallback
3. **API endpoint choice**: `POST /repos/{owner}/{repo}/copilot/coding-agent/tasks` with problem_statement
4. **Idempotency strategy**: Marker comment parsing + existing PR check
5. **Follow-up architecture**: Separate scheduled workflow + PR-opened event workflow

## Design Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│  speckit-issue-trigger.yml / speckit-phase-progression.yml          │
│                                                                     │
│  ┌──────────────────┐     ┌─────────────────────────────────────┐  │
│  │ Orchestrator Step │────▶│ Emit validation_errors to           │  │
│  │ (generate-spec)   │     │ $GITHUB_OUTPUT + workspace file     │  │
│  └───────┬───────────┘     └─────────────────────────────────────┘  │
│          │ if: failure()                                             │
│          ▼                                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Agent Fallback Step (actions/github-script)                   │   │
│  │  - Load .github/scripts/speckit-trigger/agent-fallback.js     │   │
│  │  - Detect structural vs infra failure                         │   │
│  │  - Check kill-switch (SPECKIT_AGENT_FALLBACK var)             │   │
│  │  - Check idempotency (existing PR / marker comment)           │   │
│  │  - Build problem statement (48KB truncation)                  │   │
│  │  - POST to Coding Agent API                                   │   │
│  │  - Label + comment + marker                                   │   │
│  │  - On API failure → fall through to standard failure handler  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│          │ if: steps.agent-fallback.outputs.triggered != 'true'     │
│          ▼                                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Standard Failure Handler (existing)                           │   │
│  │  - Post failure comment + speckit:failed label                │   │
│  │  - Remove speckit:processing                                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ speckit-agent-fallback-cleanup.yml (NEW)                            │
│                                                                     │
│  Trigger: pull_request [opened] where head matches speckit/*        │
│  Action: Remove speckit:processing from linked issue                │
│                                                                     │
│  Trigger: schedule (every 15 min) / workflow_dispatch               │
│  Action: Poll agent tasks for issues with speckit:agent-fallback    │
│          Remove speckit:processing on terminal failure              │
└─────────────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Upstream Signal Emission (FR-001)

**Goal**: Make the orchestrator step emit machine-readable validation error output.

**Deliverables**:

1. Modify `generate-spec-from-issue.sh` to write `validation_errors` to `$GITHUB_OUTPUT` when structural validation fails (specify phase and clarify phase)
2. Also write a `validation-errors.json` workspace file as fallback
3. Ensure non-structural failures do NOT emit these markers

**Files Modified**:

- `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` — add output emission at failure points
- `.github/scripts/speckit-trigger/lib/spec-validation.sh` — no changes needed (already outputs structured categories)

**Output format** (`validation_errors` in `$GITHUB_OUTPUT`):

```text
validation_errors=MISSING_SECTIONS: ## Problem Statement, ## Requirements;INSUFFICIENT_REQUIREMENTS: found=2, minimum=5
```

**Workspace file** (`validation-errors.json`):

```json
{
  "phase": 1,
  "phase_name": "specify",
  "errors": [
    {"category": "MISSING_SECTIONS", "detail": "## Problem Statement, ## Requirements"},
    {"category": "INSUFFICIENT_REQUIREMENTS", "detail": "found=2, minimum=5"}
  ]
}
```

### Phase 2: Shared Fallback Module (FR-001–FR-011)

**Goal**: Implement the core fallback logic as a reusable JavaScript module.

**Deliverables**:

1. Create `.github/scripts/speckit-trigger/agent-fallback.js` with exported `run()` function
2. Functions: `detectStructuralFailure()`, `checkIdempotency()`, `buildProblemStatement()`, `triggerCodingAgent()`, `applyLabelsAndComment()`

**File Created**:

- `.github/scripts/speckit-trigger/agent-fallback.js`

**Key logic**:

```javascript
// Structural validation signatures (co-located with spec-validation.sh categories)
const STRUCTURAL_ERROR_SIGNATURES = [
  'MISSING_SECTIONS',
  'INSUFFICIENT_REQUIREMENTS',
  'INSUFFICIENT_USER_STORIES',
  'MISSING_SUCCESS_CRITERIA',
  'NON_MEASURABLE_CRITERIA',
  'BELOW_SIZE_THRESHOLD',
  'BULLET_SUMMARY_DETECTED',
  'MISSING_FILE',
];
```

### Phase 3: Workflow Integration (FR-009, FR-010)

**Goal**: Wire the fallback module into both workflow files.

**Deliverables**:

1. Add `id: generate` to the orchestrator step in `speckit-issue-trigger.yml` (already named but needs id for output access)
2. Add "Agent Fallback" step (`if: failure()`) before the existing "Handle Failure" step in both workflows
3. Modify existing "Handle Failure" step condition to `if: failure() && steps.agent-fallback.outputs.triggered != 'true'`
4. Wire `SPECKIT_AGENT_FALLBACK` repository variable as kill-switch

**Files Modified**:

- `.github/workflows/speckit-issue-trigger.yml`
- `.github/workflows/speckit-phase-progression.yml`

**Workflow-specific code per file**: ~20–30 lines (step definition + env vars + condition), well under 50-line target.

### Phase 4: Idempotency Guards (FR-008, FR-013)

**Goal**: Prevent duplicate agent tasks.

**Deliverables**:

1. Check for existing open PR on expected `speckit/{issue}/phase-{N}-{name}` branch
2. Check for existing marker comment `<!-- speckit:agent-fallback task_id=... issue=<N> phase=<N> -->`
3. Both checks integrated into the shared module's `checkIdempotency()` function

### Phase 5: Follow-up Workflows (FR-012)

**Goal**: Manage `speckit:processing` label lifecycle after async agent execution.

**Deliverables**:

1. Create `.github/workflows/speckit-agent-fallback-cleanup.yml`:
   - **Job 1** (`on: pull_request [opened]`): If PR head branch matches `speckit/*/phase-*`, find linked issue, remove `speckit:processing`
   - **Job 2** (`on: schedule` every 15 min + `workflow_dispatch`): Scan issues with `speckit:agent-fallback` label, parse marker comments, poll Coding Agent API status, remove `speckit:processing` on
     terminal failure

**Files Created**:

- `.github/workflows/speckit-agent-fallback-cleanup.yml`

### Phase 6: Testing & Validation

**Goal**: Verify all acceptance criteria.

**Deliverables**:

1. Manual workflow_dispatch test with a mock structural failure
2. Verify idempotency (re-run → no duplicate task)
3. Verify kill-switch (`SPECKIT_AGENT_FALLBACK=false`)
4. Verify non-structural failure → no fallback triggered
5. Verify graceful degradation (mock API failure)
6. Document in PR description with test evidence

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Coding Agent API schema differs from documented | Medium | High | Validate response schema defensively; graceful degradation on unexpected response |
| `COPILOT_GITHUB_TOKEN` lacks Coding Agent API scope | Low | High | Token already has Copilot access for SDK; test early. Graceful degradation on 403 |
| Race condition: concurrent workflow runs trigger multiple fallbacks | Low | Medium | Idempotency guards (marker comment + PR check) execute atomically per concurrency group |
| Validation error format changes in `spec-validation.sh` | Low | Medium | Error signatures defined as constants in fallback module; co-located documentation |
| Issue body > 48KB causing API rejection | Low | Low | Truncation logic with `[truncated]` marker within byte budget |
| Scheduled polling job adds API cost | Low | Low | 15-min interval; only scans issues with specific label; exits early when no work |

## Dependencies

**External**:

- GitHub Copilot Coding Agent API (`POST /repos/{owner}/{repo}/copilot/coding-agent/tasks`)
- `COPILOT_GITHUB_TOKEN` secret with Coding Agent API scope
- GitHub Actions runner environment

**Internal**:

- `.github/scripts/speckit-trigger/lib/spec-validation.sh` — error category definitions
- `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` — validation failure output points
- Existing failure handlers in both workflow files
- `SPECKIT_AGENT_FALLBACK` repository variable (new, opt-out)
- `SPECKIT_REFERENCE_SPEC_PATH` repository variable (new, optional override)

**Labels Required** (create if not existing):

- `speckit:agent-fallback` — applied when fallback triggers

---
*Generated by Copilot SDK (claude-opus-4.6)*
