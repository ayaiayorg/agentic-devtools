# Quick Start — Issue #1518: Thread Title Formatting for Subsequent Review Comments

## Reproduce the Current Bug

Start a PR review that causes a thread to be demoted (i.e., a new summary is posted to
replace the existing top-level summary):

```bash
# After a re-scaffolding event, inspect the demoted reply in Azure DevOps:
# The demoted reply should show a compact ### Commit: <hash> heading.
# Before this fix it incorrectly shows ## File Review Summary: <fileName>.
```

## Verify After Implementation

```bash
# Run targeted tests for the render helpers
agdt-test-pattern tests/unit/cli/azure_devops/review_templates/ -v

# Run the full test suite to catch regressions
agdt-test
agdt-task-wait
```

## Key Files

| File | Role |
|------|------|
| `agentic_devtools/cli/azure_devops/review_templates.py` | Add `is_subsequent` parameter + `rewrite_header_for_subsequent()` |
| `agentic_devtools/cli/azure_devops/review_scaffold.py` | Update `_demote_main_comment()` to use the rewrite utility |
| `agentic_devtools/cli/azure_devops/finalization/convergence.py` | Extend classification to include demoted-summary replies |
| `tests/unit/cli/azure_devops/review_templates/` | New and extended unit tests |
