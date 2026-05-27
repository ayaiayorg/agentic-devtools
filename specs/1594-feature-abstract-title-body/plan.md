# Implementation Plan: Abstract PR Title/Body Change Event Filtering as a Provider-Agnostic Guard

**Branch**: `speckit/1594/phase-3-plan` | **Date**: 2026-05-27 | **Spec**: `specs/1594-feature-abstract-title-body/spec.md`  
**Input**: Feature specification from `/specs/1594-feature-abstract-title-body/spec.md`

## Summary

Introduce provider-agnostic edit-change metadata on `EventPayload` and a pure preflight guard in
`ai_pr_loop_command()` so body-only PR edits are skipped while title/base edits continue through
normal CI evaluation across GitHub and Azure DevOps providers.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- ✅ Auto-Approval Friendly Design: no new CLI patterns; change is internal to CI event handling.
- ✅ Single Source of Truth / Background Task Architecture: no workflow-state model changes.
- ✅ TDD & Coverage / Code Quality: plan includes unit tests for all new model/guard/provider branches.
- ✅ UX & Performance: skips irrelevant body-only edits early, reducing unnecessary pipeline work.

## Project Structure

### Documentation (this feature)

```text
specs/1594-feature-abstract-title-body/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    └── .gitkeep
```

### Source Code (repository root)

```text
agentic_devtools/cli/ci/
├── models.py
├── guards.py
├── commands.py
├── github_provider.py
└── ado_provider.py

tests/unit/cli/ci/
├── models/
├── guards/
├── commands/
├── github_provider/
└── ado_provider/
```

**Structure Decision**: Keep changes scoped to existing CI provider/guard modules and mirrored unit
test paths under `tests/unit/cli/ci/`.

## Complexity Tracking

No constitution violations or complexity exemptions identified for this plan.

## Technical Context

- **Stack**: Python >=3.10, frozen dataclasses, `logging` module, `gh` CLI for GitHub API
- **Key Files**:
  - `agentic_devtools/cli/ci/models.py` — `EventPayload` dataclass (frozen, all fields have defaults)
  - `agentic_devtools/cli/ci/guards.py` — Guard functions (`check_*` pattern, returns tuples)
  - `agentic_devtools/cli/ci/commands.py` — `ai_pr_loop_command()` entry point with v1/v2 routing
  - `agentic_devtools/cli/ci/github_provider.py` — `_parse_pull_request_event()` parses raw GitHub payloads
  - `agentic_devtools/cli/ci/ado_provider.py` — `AzureDevOpsProvider.parse_event()` stub
  - `.github/workflows/ai-pr-loop.yml` — workflow triggers (currently `opened`, `reopened` only for PR)
- **Architecture**: Provider-agnostic model (`EventPayload`) consumed by guards; providers normalize platform payloads into this model
- **Test Policy**: 1:1:1 structure under `tests/unit/`, 100% coverage required

## Research Summary

Research decisions are documented in `research.md`. Key choices: place the edit-relevance guard
before downstream routing/guards, keep the guard return signature consistent with the existing
`check_*` tuple pattern, and have providers populate the new change-tracking fields from their
platform-specific payloads, including the ADO event mapping.

Design artifacts: `data-model.md` (entity/field definitions), `quickstart.md` (implementation
steps), and `contracts/.gitkeep` (no external API contracts for this internal guard).

## Design Overview

```text
┌───────────────────────────────────────────────────┐
│ ai_pr_loop_command() in commands.py               │
│  1. Parse event → EventPayload (with new fields)  │
│  2. ★ check_edit_relevance(event) → skip/proceed  │
│  3. Route to v1 or v2 pipeline                    │
└───────────────────────────────────────────────────┘
         ▲                          │
         │                          ▼
┌────────┴─────────┐     ┌─────────────────────┐
│ Providers        │     │ Downstream guards   │
│ (GitHub, ADO)    │     │ (WIP, fork, docker) │
│ populate new     │     │ run only if edit-    │
│ fields on parse  │     │ relevance passes    │
└──────────────────┘     └─────────────────────┘
```

The four new `EventPayload` fields (`title_changed`, `body_changed`, `base_changed`, `edit_changes_known`) are populated by each provider's `parse_event()`. The guard is a pure function with no I/O.

## Implementation Phases

### Phase 1: Extend `EventPayload` Model

**Deliverable**: Four new boolean fields on the frozen dataclass with `False` defaults.

**Files**:

- `agentic_devtools/cli/ci/models.py` — Add fields after `sender_login`
- `tests/unit/cli/ci/models/test_eventpayload.py` — Extend with tests for new fields + backward compat

**Tasks**:

1. Add `title_changed: bool = False` to `EventPayload`
2. Add `body_changed: bool = False` to `EventPayload`
3. Add `base_changed: bool = False` to `EventPayload`
4. Add `edit_changes_known: bool = False` to `EventPayload`
5. Update docstring to document all four fields
6. Add tests: construction with/without new fields, frozen enforcement, equality

### Phase 2: Implement `check_edit_relevance` Guard

**Deliverable**: Standalone guard function following existing `check_*` pattern.

**Files**:

- `agentic_devtools/cli/ci/guards.py` — Add `check_edit_relevance(event: EventPayload) -> tuple[bool, str]`
- `tests/unit/cli/ci/guards/test_check_edit_relevance.py` — Comprehensive tests

**Tasks**:

1. Add import of `EventPayload` to `guards.py` (currently only imports `CIPlatformProvider`)
2. Implement `check_edit_relevance`:
   - If `event.action != "edited"` → return `(False, "")`
   - If `event.edit_changes_known is False` → return `(False, "")` (fail-open)
   - If `event.title_changed is True` → return `(False, "")`
   - If `event.base_changed is True` → return `(False, "")`
   - Otherwise → return `(True, "edited event with no title or base change")`
3. Keep `check_edit_relevance` side-effect-free (no logging/I/O); only return skip/proceed tuple
4. Write tests for all branches: non-edited action, edited+unknown metadata, title change, base change, body-only, simultaneous title+body, empty changes dict

### Phase 3: Update GitHub Provider

**Deliverable**: `_parse_pull_request_event` populates new fields from `changes` dict.

**Files**:

- `agentic_devtools/cli/ci/github_provider.py` — Modify `_parse_pull_request_event()`
- `tests/unit/cli/ci/github_provider/test_parse_event.py` — Extend with edited event tests

**Tasks**:

1. In `_parse_pull_request_event`, check if `raw.get("action") == "edited"` and `"changes" in raw`
2. When both conditions met: set `edit_changes_known=True`
3. Set `title_changed = "title" in raw.get("changes", {})`
4. Set `body_changed = "body" in raw.get("changes", {})`
5. Set `base_changed = "base" in raw.get("changes", {})`
6. Pass these to the `EventPayload` constructor
7. Write tests: payload with `changes.title`, `changes.body`, `changes.base`, empty changes, no changes key, non-edited action

### Phase 4: Update Azure DevOps Provider

**Deliverable**: ADO provider populates fields when payload has change metadata.

**Files**:

- `agentic_devtools/cli/ci/ado_provider.py` — Enhance `parse_event()`
- `tests/unit/cli/ci/ado_provider/test_azuredevopsprovider.py` — Extend tests

**Tasks**:

1. For ADO `git.pullrequest.updated` events, check for field-level change indicators in the `resource` dict
2. Normalize `action` to `"edited"` for PR update events that modify title/description/target
3. Set `edit_changes_known=True` when payload structure reliably conveys what changed
4. Set `title_changed`, `body_changed`, `base_changed` based on ADO-specific fields (`resource.title` vs `resource.description` deltas, `targetRefName` changes)
5. Fail-open when metadata unavailable (keep defaults)
6. Write tests for ADO payloads with/without change metadata

### Phase 5: Wire Guard into `ai_pr_loop_command()`

**Deliverable**: Preflight runs after event parsing, before v1/v2 routing.

**Files**:

- `agentic_devtools/cli/ci/commands.py` — Insert guard call between parse and route
- `tests/unit/cli/ci/commands/test_ai_pr_loop_command.py` — Add edited event tests

**Tasks**:

1. Import `logging` and `check_edit_relevance` from `guards`
2. After line 94 (`event_payload = provider.parse_event(...)`) and before line 100 (`if _pipeline_v2_enabled():`), insert:

   ```python
   should_skip, skip_reason = check_edit_relevance(event_payload)
   if should_skip:
       logging.info("PR #%d: %s", event_payload.pr_number, skip_reason)
       sys.exit(0)
   ```

3. Add tests: body-only edit exits 0, title change proceeds, non-edited proceeds

### Phase 6: Post-Release Workflow YAML Update

**Deliverable**: `edited` added to `pull_request` event types in a gated, post-release follow-up.

**Files**:

- `.github/workflows/ai-pr-loop.yml` — Add `edited` to types list

**Tasks**:

1. Treat this phase as a post-release follow-up, not part of the same implementation merge train
2. Gate this change on a published PyPI release that contains Phases 1-5 and is installable by `ai-pr-loop`
3. Change line 5 from `types: [opened, reopened]` to `types: [opened, reopened, edited]`
4. No `if:` conditions for title/body — filtering is in Python

### Phase 7: Documentation

**Deliverable**: Updated docs clarifying the edit-relevance guard approach.

**Tasks**:

1. Add inline docstring to `check_edit_relevance` explaining the guard's purpose and return semantics
2. Add a comment in the YAML explaining that PR edit filtering is handled in Python

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Body-only edits still trigger full pipeline (guard bug) | Low | Medium | Comprehensive test coverage for all branches |
| ADO payload structure differs from expectations | Medium | Low | Fail-open design; ADO is stub-only today |
| Existing tests break due to new fields | Very Low | High | All fields have `False` defaults; frozen dataclass pattern preserved |
| `edited` trigger causes unwanted runs before guard code is available to the workflow | Medium | Low | Merge Phases 1-5, publish/release the updated `agentic-devtools` package consumed by `ai-pr-loop`, verify the workflow can install that release from PyPI, then update YAML |

## Dependencies

- **Internal**: `EventPayload` dataclass consumed by ~10+ files; backward compat is critical
- **External**: GitHub webhook schema (`pull_request` `edited` event with `changes` dict) — stable, well-documented
- **Deploy Order**: Python code (Phases 1-5) MUST be merged and the corresponding
  `agentic-devtools` package release MUST be published/deployed to PyPI before the YAML change
  (Phase 6), because `ai-pr-loop` installs from PyPI rather than the checked-out source

---
*Generated by Copilot SDK (claude-opus-4.6)*
