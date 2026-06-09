# Quickstart: Validate PR Template Body Resolution

1. Ensure the template exists (idempotent setup):

   ```bash
   agdt-init-pr-template
   agdt-set dry_run true
   agdt-set source_branch "feature/example-pr-body-template"
   agdt-set title "feat: validate PR body template rendering"
   ```

2. Verify state-first interpolation path:

   ```bash
   agdt-set git.last_commit_message "feat: example message"
   agdt-create-pull-request
   agdt-task-wait
   ```

3. Verify git-log fallback path:

   ```bash
   agdt-delete git.last_commit_message
   agdt-create-pull-request
   agdt-task-wait
   ```

4. Verify missing-template graceful degradation:

   ```bash
   python -c "from pathlib import Path; Path('.agdt/config/pull-request-template.md').unlink(missing_ok=True)"
   agdt-create-pull-request
   agdt-task-wait
   ```

Expected outcome:

- PR creation uses rendered template content when available.
- PR creation falls back to the resolved full commit message with warning output when the
  template is missing.
- PR creation falls back without warning when the template is empty.
