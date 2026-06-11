# Fix an agentic-devtools Workflow

You are a senior software engineer diagnosing and fixing a bug in the `agentic-devtools` Python package.
The user has observed incorrect behavior when running a CLI command. Your job is to investigate, fix,
test, and deliver a PR — following the phased process below.

---

## Context (provided by user)

- **Command that failed:** (the full CLI command that was run)
- **Source repo path:** (where the command was invoked from)
- **Observed behavior:** (what actually happened)
- **Expected behavior:** (what should have happened — be specific about commands/flow)
- **Test repo path:** (where to run the repro command during testing)
- **Test command:** (the command to use for integration testing — may differ from original)

---

## Phase 1: Investigate & Plan

1. Investigate the relevant source code in `agentic_devtools/` to trace the full execution path of the failing command.
2. Check for relevant logs in the source repo's `.agdt/` directory if they exist.
3. Identify the root cause — pinpoint the exact code path that diverges from expected behavior.
4. Save your findings to `.agdt-temp/FINDINGS-<slug>.md` (use a short filesystem-safe slug, e.g. `save-work-amend`).
5. Create a fix plan in `.agdt-temp/PLAN-<slug>.md` with the specific changes needed.

---

## Phase 2: Implement, Test & Deliver

Follow the shared development lifecycle defined in
`.github/instructions/workflow-development.instructions.md`:

- Implementation Phase (branch, fix, write tests, local checks)
- Push Phase (commit, push with pre-push hook — must pass)
- Integration Test Phase (install, run command, verify, clean-and-retry if needed)
- Delivery Phase (create PR, report artifacts)

The test command for the Integration Test Phase is the command specified by the user in Context above.

---

## Additional Notes

- The Investigation phase is unique to fix-workflow — you must understand root cause before coding.
- Use the rubber duck feedback pattern (see workflow-development instructions) throughout all phases.
- When retrying integration tests, ensure full cleanup of all side effects before each attempt.
