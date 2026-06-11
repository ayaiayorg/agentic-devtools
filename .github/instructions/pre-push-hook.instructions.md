---
applyTo: ".github/prompts/**,.github/agents/**"
---

# Pre-Push Hook: Push-Fix-Push Loop

This repo uses a `.githooks/pre-push` hook that runs **targeted quality checks**
(before each push) via `python -m agentic_devtools.cli.checks`. Agents do NOT need to manually run lint, format, type checking, or test
commands before pushing.

---

## What the Pre-Push Hook Runs

When you push (via `agdt-git-save-work` or `git push`), the hook runs `python -m agentic_devtools.cli.checks` targeted checks (depending on changed files), including:

1. **Test structure validation** — ensures 1:1:1 test structure
2. **ruff format** — auto-fixes formatting (Python files only; aborts push if files were reformatted)
3. **ruff check** — linting (Python files only)
4. **mypy** — type checking on changed Python files
5. **Per-file 100% branch coverage** — tests for changed `agentic_devtools/` source files

This takes up to **2 minutes**. Do NOT interrupt the terminal during this time.

---

## The Push-Fix-Push Loop

1. **Push** using `agdt-git-save-work` (stages, commits/amends, and pushes in one command)
2. **Wait** with `agdt-task-wait` — do NOT cancel the push (e.g., Ctrl+C) or close any terminal running `git push` while the hook runs
3. **If rejected**, read failure details from `.pre-push-output.log` first (it is always written by the hook). For non-format check failures, you may also see:
   - `check-output-condensed.txt` (condensed summary)
   - `check-output.txt` (full output)
4. **Fix** the reported issues
5. **Retry** with `agdt-git-save-work`, then `agdt-task-wait`
6. **Repeat** until the push succeeds

---

## Terminal Safety Rules

- To check progress: read `.pre-push-output.log` using a file-read tool or a **separate** terminal.
- After a failed push, read `check-output-condensed.txt` / `check-output.txt` for failure details.
- **Never poll the push terminal for status.**

---

## What NOT to Do

- ❌ Do NOT manually run `ruff format`, `ruff check`, or `mypy` before pushing
- ❌ Do NOT run `agdt-test` or `agdt-test-quick` as a pre-push validation step
- ❌ Do NOT use `--no-verify` to bypass the hook
- ❌ Do NOT run `agdt-git-force-push` after a normal `agdt-git-save-work` run (unless you intentionally used `--skip-push` and need a standalone force-push)

---

## `agdt-git-save-work` vs `agdt-git-force-push`

| Command | What it does | When to use |
|---------|--------------|-------------|
| `agdt-git-save-work` | Stages changes via `git add .` (run from the repo root; note: deletions require `git add -A` + `agdt-git-save-work --skip-stage`), commits/amends, and pushes (auto force-push when needed) | Default for almost all workflows; use for the standard push-fix-push loop |
| `agdt-git-force-push` | Force-pushes only (no staging, no committing) | **Only** when you need a standalone force-push after history rewriting without creating/amending a commit (e.g., squash-commits Phase 5 after Phase 3 used `git reset --soft` + `agdt-git-save-work --skip-push`) |

---

## Ensure Hooks Are Enabled

```bash
git config core.hooksPath .githooks
```

(If you’re not seeing the hook run, ensure `core.hooksPath` is set as above — Copilot environments configure this via `copilot-setup-steps.yml`, but local clones may not.)
