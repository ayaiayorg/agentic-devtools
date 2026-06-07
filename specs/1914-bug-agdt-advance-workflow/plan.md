# Implementation Plan: Prevent @agdt.advance-workflow from Re-initiating Workflows

## Tracked Artifacts

The following artifacts are committed to this branch under `specs/1914-bug-agdt-advance-workflow/`:

| Artifact | Status |
|----------|--------|
| `plan.md` | Tracked (this file) |
| `spec.md` | Tracked |
| `checklists/` | Tracked (directory) |
| `contracts/` | Tracked (directory) |

> **Note:** The PR description may reference additional optional artifacts (`quickstart.md`,
> `research.md`) that are **not** present in this branch. Those files are gitignored and only
> produced locally during spec generation. Only the artifacts listed above are committed and
> reviewable in-branch.

## 1. Technical Context

| Aspect | Detail |
|--------|--------|
| Technology | GitHub Copilot Chat agent prompt (Markdown) |
| Target file | `.github/agents/agdt.advance-workflow.agent.md` |
| Related CLI | `agdt-advance-workflow` (Python, already exits with code 1 on no workflow) |
| Scope | Prompt-only change — no Python code modifications |
| Branch | `speckit/1914/phase-3-plan` |
| Issue | [#1914](https://github.com/ayaiayorg/agentic-devtools/issues/1914) |

### Architecture Context

The `@agdt.advance-workflow` Copilot Chat agent delegates to the `agdt-advance-workflow` CLI command.
The CLI already handles the "no active workflow" case correctly (prints `ERROR: No workflow is currently active.`
to stderr and exits with code 1). The bug is that the agent prompt's **Prerequisites** section explicitly
suggests running initiation commands (`agdt-initiate-work-on-jira-issue-workflow`,
`agdt-initiate-pull-request-review-workflow`) when no workflow is active — causing the LLM to invoke them
on failure. The fix must remove this initiation guidance and replace it with an explicit prohibition.

### Key Dependencies

- `agdt-advance-workflow` CLI — exits 1 on no workflow (unchanged)
- `agdt-get-workflow` CLI — displays current workflow state (used in diagnostics)
- `agdt-show` CLI — displays all state (used in diagnostics)
- `@agdt.pull-request-review.initiate` — the agent that MUST NOT be invoked

## 2. Research Summary

Key decisions:

1. **Retry mechanism in prompt**: Implemented as a two-step `agdt-get-workflow` call with a
   4-second delay between attempts. Delay command fallback is sequential and shell-agnostic:
   attempt `python3 -c "import time; time.sleep(4)"`; if that attempt fails, attempt
   `python -c "import time; time.sleep(4)"`; if that fails, attempt
   `py -c "import time; time.sleep(4)"`. The eventual agent prompt should run those commands as
   separate sequential attempts and only try the next Python launcher if the previous one fails.
2. **Error output format**: Plain text console output matching existing `agdt-*` agent error patterns (no markdown formatting).
3. **State directory path**: Always obtained via Python by printing
   `get_state_dir().resolve()` with launcher fallback attempts in order:
   `python3 -c "from agentic_devtools.state import get_state_dir; print(get_state_dir().resolve())"`,
   then `python -c "from agentic_devtools.state import get_state_dir; print(get_state_dir().resolve())"`,
   then `py -c "from agentic_devtools.state import get_state_dir; print(get_state_dir().resolve())"`.
   `agdt-show` only prints JSON key-value pairs (no state-dir header).

## 3. Design Overview

The fix replaces the minimal 39-line agent prompt with a comprehensive prompt that includes:

```text
┌─────────────────────────────────────────────┐
│  @agdt.advance-workflow invoked             │
├─────────────────────────────────────────────┤
│  Step 1: Run agdt-get-workflow              │
│          ↓ (active found?)                  │
│    YES → Run agdt-advance-workflow [step]   │
│    NO  → Step 2: Wait 4 seconds            │
│          ↓                                  │
│  Step 3: Retry agdt-get-workflow            │
│          ↓ (active found?)                  │
│    YES → Run agdt-advance-workflow [step]   │
│    NO  → Step 4: Output diagnostic error   │
│          STOP (no re-initiation)            │
└─────────────────────────────────────────────┘
```

### Explicit Prohibitions (Safety Guardrails)

The prompt will contain an explicit `## PROHIBITED ACTIONS` section that:

1. Lists all initiation commands/agents that MUST NOT be invoked
2. States the prohibition applies regardless of CLI exit code or error output
3. Makes clear the only permitted output on failure is diagnostic text

## 4. Implementation Phases

### Phase 1: Rewrite Agent Prompt (Single Phase — Complete Fix)

**Deliverable**: Updated `.github/agents/agdt.advance-workflow.agent.md`

**Tasks**:

1. Replace the current minimal prompt with the comprehensive version containing:
   - **Purpose** section (unchanged intent)
   - **User Input** section (preserves step-name argument)
   - **PROHIBITED ACTIONS** section (FR-001, FR-004)
   - **Actions** section with retry logic (FR-006):
     - Step 1: `agdt-get-workflow` to check for active workflow
     - Step 2: If no active workflow, run a 4-second delay using sequential fallback attempts:
       `python3 -c "import time; time.sleep(4)"`, else `python -c "import time; time.sleep(4)"`,
       else `py -c "import time; time.sleep(4)"`; then retry `agdt-get-workflow`
     - Step 3: If retry succeeds, proceed with `agdt-advance-workflow [step]`
     - Step 4: If retry fails, output diagnostic error and STOP
   - **Failure Output** section specifying exact error format (FR-002, FR-003, FR-007):
     - "No active workflow found" phrase
     - Full state directory path (from Python `get_state_dir().resolve()` with launcher fallback
       attempts in order: `python3 -c "from agentic_devtools.state import get_state_dir; print(get_state_dir().resolve())"`,
       then `python -c "from agentic_devtools.state import get_state_dir; print(get_state_dir().resolve())"`,
       then `py -c "from agentic_devtools.state import get_state_dir; print(get_state_dir().resolve())"` —
       not from `agdt-show`, which prints only JSON key-value pairs)
     - Diagnostic commands to suggest
     - Mention of state directory mismatch possibility
     - Preserved step-name in error context
   - **Corrupted State** section for invalid `workflow` data
   - **Completed Workflow** handling (FR-005)

2. Validate prompt structure matches other agent prompts in the repository (YAML frontmatter, section hierarchy).

3. Run existing tests to ensure no regressions:

   ```bash
   agdt-test-pattern tests/unit/cli/workflows/commands/test_advance_workflow_cmd.py -v
   ```

4. Commit via `agdt-git-save-work`.

### Phase 1 Implementation Details

The new prompt structure:

```markdown
---
description: "Advance Workflow: Advance to next workflow step"
---

## User Input
## Purpose
## PROHIBITED ACTIONS
## Actions (with retry logic)
## Failure Output Format
## Edge Cases
## Expected Outcome
## Next Step
```

**Key content for PROHIBITED ACTIONS section**:

- Explicit list: `@agdt.pull-request-review.initiate`, `agdt-initiate-pull-request-review-workflow`,
  `agdt-initiate-work-on-jira-issue-workflow`, and any other `initiate` command/agent
- Applies when CLI exits with non-zero code OR reports no active workflow
- Applies regardless of user input or context
- No direct invocation exceptions: the agent MUST NOT run/initiate any initiate command or
  initiate agent when no active workflow is found. It MAY suggest that the user manually run
  initiation commands as diagnostics when explicitly framed as user action.

**Key content for retry logic**:

```text
1. Run: agdt-get-workflow
2. If output shows an active workflow → proceed to agdt-advance-workflow
3. If output shows NO active workflow or "completed" status:
   a. Log: "No active workflow detected. Retrying in 4 seconds..."
   b. Run delay with sequential fallback attempts as separate commands, only
      trying the next launcher when the previous attempt fails:
      - `python3 -c "import time; time.sleep(4)"`
      - if the prior attempt fails: `python -c "import time; time.sleep(4)"`
      - if the prior attempt fails: `py -c "import time; time.sleep(4)"`
   c. Run: agdt-get-workflow (second attempt)
   d. If now active → proceed to agdt-advance-workflow
   e. If still not active → output failure diagnostics and STOP
```

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM ignores prohibition in edge cases | Low | High | Use explicit language (MUST NOT, DO NOT, PROHIBITED) and redundant placement |
| Retry delay too short for slow state writes | Low | Low | 4 seconds covers observed write times; if insufficient, root cause is #1913 |
| Prompt length causes LLM context issues | Very Low | Medium | New prompt is ~80 lines — well within agent prompt norms |
| Other agents still trigger re-initiation | N/A | N/A | Out of scope — this fix only addresses `@agdt.advance-workflow` |

## 6. Dependencies

| Dependency | Type | Status |
|-----------|------|--------|
| `agdt-advance-workflow` CLI (exit 1 on no workflow) | Internal | ✅ Already implemented |
| `agdt-get-workflow` CLI | Internal | ✅ Already implemented |
| `agdt-show` CLI | Internal | ✅ Already implemented |
| Issue #1913 (state directory mismatch) | Related | 🔄 Separate fix — this prompt change is a defense-in-depth measure |

---
*Generated by Copilot SDK (claude-opus-4.6)*
