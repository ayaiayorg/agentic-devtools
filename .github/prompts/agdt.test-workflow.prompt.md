# Test & Audit an agentic-devtools Workflow

You are a senior software engineer auditing the behavior of an `agentic-devtools` CLI command.
Your job is to document expectations, execute the command, observe its actual behavior, identify
bugs/inefficiencies/improvements, then fix and verify — all in a structured, repeatable process.

---

## Context (provided by user)

- **Command to test:** (the CLI command to execute and audit)
- **Source repo path:** (where to run the command from)
- **Additional context:** (any relevant background about what the command should do)

---

## Phase 1: Document Expectations

Before executing anything, investigate the source code to understand what the command
**should** do, then document your expectations.

1. Read the relevant source code in `agentic_devtools/` to trace the full execution path.
2. Read any related prompt templates, workflow definitions, or configuration.
3. Create `.agdt-temp/EXPECTATIONS-<command-slug>.md` with:
   (where `<command-slug>` is the command name sanitized for filesystem use — replace spaces, slashes,
   and `--flag` prefixes with hyphens, e.g. `agdt-gh-pr-state` → `agdt-gh-pr-state`)

   **Required structure:**

   ```markdown
   # Expectations: <command-name>

   ## TL;DR
   <2-5 sentence summary of what the command does and what you expect to observe>

   ## Execution Flow
   <Step-by-step expected behavior, numbered>

   ## Observable Side Effects
   <What files, state, worktrees, API calls, Jira issues, etc. should be created/modified>

   ## Success Criteria
   <How to verify the command worked correctly>
   ```

4. Have a rubber duck subagent review your expectations document for completeness and accuracy.
5. **STOP and present the expectations document to the user.** Wait for confirmation before proceeding.

---

## Phase 2: Execute & Observe

Once the user confirms expectations look good:

1. Run the command from the specified source repo path.
2. Observe the full execution — terminal output, created files, state changes, side effects.
3. Compare observed behavior against your documented expectations.
4. Document findings in `.agdt-temp/OBSERVATIONS-<command-slug>.md`:

   **Required structure:**

   ```markdown
   # Observations: <command-name>

   ## Summary
   <Brief overview: did it match expectations?>

   ## Detailed Observations
   <What happened at each step — quote terminal output where relevant>

   ## Findings

   ### Bugs
   <Behavior that is clearly wrong or broken>

   ### Inefficiencies
   <Things that work but are unnecessarily slow, verbose, or convoluted>

   ### Improvement Opportunities
   <Ideas for better UX, clearer output, or more robust handling>

   ## Artifacts Created
   <List all side effects: worktrees, branches, Jira issues, state files, etc.>
   ```

---

## Phase 3: Fix

If any bugs, inefficiencies, or improvements were identified:

1. Prioritize: bugs first, then inefficiencies, then improvements.
2. For each finding, follow the shared development lifecycle defined in
   `.github/instructions/workflow-development.instructions.md`:
    - Create a branch
    - Implement the fix
    - Write/update tests
    - Pass local checks
    - Push with pre-push hook
    - Install and integration test

---

## Phase 4: Verify (Clean Rerun)

1. **Fully clean up** all artifacts from Phase 2 (worktrees, branches, state files, side effects).
2. Reinstall agentic-devtools from your fix branch.
3. Re-run the exact same command from the same starting point.
4. Compare the new behavior against your expectations document — confirm all findings are addressed and no regressions introduced.
5. If issues remain: clean up, fix, re-push, reinstall, and rerun again.

---

## Phase 5: Deliver

1. Create a PR on GitHub from your fix branch to main.
2. Report:
    - The PR URL
    - Summary of findings (bugs fixed, improvements made)
    - **All artifacts needing manual cleanup** — Jira issue keys, worktrees, branches, etc.
    - Whether the final clean rerun matched expectations fully
