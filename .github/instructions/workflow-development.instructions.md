---
applyTo: ".github/prompts/agdt.*-workflow.prompt.md"
---

# Shared: agentic-devtools Workflow Development Lifecycle

This instructions file contains the shared phases used by both the `fix-workflow` and `test-workflow`
agents. Both agents implement, test, and deliver changes to the agentic-devtools codebase using
the identical process below.

---

## Implementation Phase

1. Create a new branch in agentic-devtools following the repo convention: `type/ISSUE-KEY/description`
   (e.g. `fix/1234/fix-save-work-amend` or `feature/1234/add-webhook-support`).
2. Implement the changes.
3. Update or create tests to cover all modified code paths. Ensure both success AND failure branches are tested.
4. Do NOT manually run `ruff`, `mypy`, or the full test suite before pushing —
   the pre-push hook runs **targeted** checks based on changed files (lint/format/mypy/coverage as applicable).
   See `.github/instructions/pre-push-hook.instructions.md` for the push-fix-push loop pattern.

---

## Push Phase (Pre-Push Hook)

1. Commit and push using `agdt-git-save-work` (stages, commits/amends, AND pushes — all
   in one smart command based on branch history), then wait with `agdt-task-wait`. Never use `git commit` or `git push` directly.
   Ensure hooks are enabled (`git config core.hooksPath .githooks`) so the push runs the pre-push hook checks.
2. If the hook fails, read `check-output-condensed.txt` (or `check-output.txt` / `.pre-push-output.log`)
   from the repo root to see what failed. Fix the issues and rerun `agdt-git-save-work`, then `agdt-task-wait`.
3. Do NOT use `--no-verify` to bypass the hook. The hook must pass.
4. Do NOT run `agdt-git-force-push` after `agdt-git-save-work` — it already handles force-push
   when amending an existing commit.

See `.github/instructions/pre-push-hook.instructions.md` for the full push-fix-push loop pattern.

### Terminal Rules for Push

- **CRITICAL: Do NOT cancel the push (e.g., Ctrl+C) or close the terminal running `git push` while the pre-push hook is executing.** If interrupted, rerun the push.
- To check progress: read `.pre-push-output.log` from the repo root using a file-read tool or a **separate** terminal.
- If you accidentally interrupt the push, rerun `agdt-git-save-work` to retry (never use raw `git push`/`git push --force-with-lease`).

---

## Integration Test Phase

1. Install the fixed version: `pip install -e <path-to-agentic-devtools-repo>`
   (e.g. `pip install -e /home/user/repos/agentic-devtools` on Linux/macOS or
   `pip install -e C:\repos\agentic-devtools` on Windows).
2. Run the test command from the test repo.
3. Verify the expected behavior occurs end-to-end.
4. If it doesn't work, **fully reset to a clean starting point** before retrying:
    - Delete any worktrees and branches created in the test repo during the failed run.
    - Remove any leftover state files (e.g., `.agdt/workflows/` state directories in new worktrees).
    - Clean up any side effects the workflow produced: PR comments, review threads, pipeline runs,
      Azure DevOps thread scaffolds, etc. — anything that would prevent the command from running
      as if invoked for the first time.
    - The goal is to restore the exact starting conditions so the rerun is a true test, not polluted by prior artifacts.
    - Then: fix the code, amend the commit, re-push (hook must pass again), reinstall, and retest.
5. Track any side effects that **cannot** be automatically cleaned up (e.g., Jira issues cannot be deleted via API).

---

## Delivery Phase

1. Create a PR on GitHub from your branch to main.
2. Report:
    - The PR URL
    - A brief summary of what was changed and why
    - **All artifacts needing manual cleanup** — Jira issue keys, leftover worktrees/branches, PR comments that couldn't be deleted, etc.

---

## Quality Assurance: Rubber Duck Feedback

- **Before reporting your final result**, delegate to a "rubber duck" subagent: give it your findings, plan, or implementation and ask it to critically review
  for logical errors, missed edge cases, or flawed assumptions. Incorporate its feedback before proceeding.
- **When delegating to subagents**, instruct each subagent to also use a rubber duck agent to critically review its work before reporting back to you.
  This ensures each layer of work is validated independently.
- The goal is to catch mistakes early — before they compound across phases — and reduce the number of install-test-fix loops needed.

---

## General Guidelines

- Use subagents generously for investigation, test-writing, and implementation if the scope is large.
- The single-commit-per-PR policy applies: always amend, never create additional commits on the branch.
- If a test fails due to a Windows-specific issue (symlinks, path separators), use `pytest.skip()` with a try/except rather than `@pytest.mark.skipif` with fragile platform detection.

---

## Tips

- The pre-push hook runs a variable set of checks via
  `python -m agentic_devtools.cli.checks` based on changed files (always test structure
  validation, plus lint/format/mypy for Python changes, plus per-file coverage checks and
  possible extra test runs).
- **Never poll the push terminal for status.** Read `.pre-push-output.log` instead.
- Coverage failures show specific missing line numbers — read those lines to understand what branches need test coverage.
