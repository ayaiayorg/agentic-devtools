# Fix an agentic-devtools Workflow

You are a senior software engineer diagnosing and fixing a bug in the `agentic-devtools` Python package.
The user has observed incorrect behavior when running a CLI command. Your job is to investigate, fix,
test, and deliver a PR — following the phased process below.

---

## Context (provided by user)

- **Command that failed:** (user will describe)
- **Source repo path:** (where the command was invoked from)
- **Observed behavior:** (what actually happened)
- **Expected behavior:** (what should have happened)
- **Test repo path:** (where to run the repro command during testing)
- **Test command:** (the command to use for integration testing)

---

## Phase 1: Investigate & Plan

1. Investigate the relevant source code in `agentic_devtools/` to trace the full execution path of the failing command.
2. Check for relevant logs in the source repo's `.agdt/` directory if they exist.
3. Identify the root cause — pinpoint the exact code path that diverges from expected behavior.
4. Save your findings to `.agdt-temp/FINDINGS-<descriptive-name>.md`.
5. Create a fix plan in `.agdt-temp/PLAN-<descriptive-name>.md` with the specific changes needed.

---

## Phase 2: Implement & Verify Locally

6. Create a new branch in agentic-devtools: `fix/<descriptive-name>`.
7. Implement the fix.
8. Update or create tests to cover the fixed code paths. Ensure any new branches (success AND failure) are tested.
9. Run targeted checks on your changed files:
   - `ruff check <files> --no-fix` (lint)
   - `ruff format --check <files>` (format — auto-fix with `ruff format <files>` if needed)
   - `python -m mypy <source-files> --ignore-missing-imports --follow-imports=silent` (type check)
   - `python -m pytest <test-files> --no-cov --tb=short` (unit tests pass)

---

## Phase 3: Push with Pre-Push Hook

10. Stage and commit your changes.
11. Push to origin. The pre-push hook will run targeted checks (lint, format, per-file 100% coverage, mypy, test structure validation).
12. If the hook fails, read the output from `check-output-condensed.txt` in the repo root, fix the issues, amend the commit, and push again.
13. Do NOT use `--no-verify` to bypass the hook. The hook must pass.

---

## Phase 4: Install & Integration Test

14. Install the fixed version: `pip install -e C:\repos\agentic-devtools`
15. Run the test command from the test repo path.
16. Verify the expected behavior occurs end-to-end.
17. If it doesn't work, **fully reset to a clean starting point** before retrying:
    - Delete any worktrees and branches created in the test repo during the failed run.
    - Remove any leftover state files (e.g., `.agdt/workflows/` state directories in the new worktree).
    - Clean up any side effects the workflow produced: PR comments, review threads, pipeline runs, Azure DevOps thread scaffolds, etc. — anything that would prevent the command from running as if invoked for the first time.
    - The goal is to restore the exact starting conditions so the rerun is a true test of the fix, not polluted by artifacts from the failed attempt.
    - Then: fix the code, amend the commit, re-push (hook must pass again), reinstall, and retest.
18. Track any side effects that **cannot** be automatically cleaned up (e.g., Jira issues — these cannot be deleted via API). You will report these to the user in Phase 5.

---

## Phase 5: Deliver

19. Create a PR on GitHub from your fix branch to main.
20. Report:
    - The PR URL
    - A brief summary of what was wrong and how you fixed it
    - **All artifacts that need manual cleanup** — Jira issue keys created during testing, any worktrees/branches left behind, PR comments that couldn't be deleted, etc. List these clearly so the user can clean them up.

---

## Guidelines

- Before pushing, ensure the pre-push hook passes. Do not bypass it.
- **CRITICAL: Do NOT send any commands to the terminal running `git push` while the pre-push hook is executing.** Sending any input to that terminal will interrupt the hook process and you will need to retry the push. To check on progress, read `check-output-condensed.txt` (or `check-output.txt` for full output) from the repo root using a file-read tool or a **separate** terminal. These files contain all the information you need about the hook's status, pass/fail result, and any error details.
- If you accidentally interrupt the push by sending commands to the same terminal, you must re-run `git push --force-with-lease` to retry.
- Use subagents generously for investigation, test-writing, and implementation if the scope is large.
- The single-commit-per-PR policy applies: always amend, never create additional commits on the branch.

---

## Quality Assurance: Rubber Duck Feedback

- **Before reporting your final result**, delegate to a "rubber duck" subagent: give it your findings, plan, or implementation and ask it to critically review for logical errors, missed edge cases, or flawed assumptions. Incorporate its feedback before proceeding.
- **When delegating to subagents**, instruct each subagent to also use a rubber duck agent to critically review its work before reporting back to you. This ensures each layer of work is validated independently.
- The goal is to catch mistakes early — before they compound across phases — and reduce the number of install-test-fix loops needed.

---

## Tips

- The pre-push hook runs 4 checks in parallel: (1) ruff lint, (2) mypy, (3) test structure validation, (4) per-file 100% branch coverage. Check 4 is the slowest (~25-40s).
- **Never poll the push terminal for status.** The hook writes its output to `check-output-condensed.txt` and `check-output.txt` in the repo root. Read those files to see results.
- If a test fails due to a Windows-specific issue (symlinks, path separators), use `pytest.skip()` with a try/except rather than `@pytest.mark.skipif` with fragile platform detection.
- Coverage failures show specific missing line numbers — read those lines to understand what branches need test coverage.
