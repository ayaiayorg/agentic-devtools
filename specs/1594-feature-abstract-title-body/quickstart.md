# Quickstart: Validate Edit-Relevance Guard Behavior

1. Run targeted CI command tests:

   ```bash
   agdt-test-pattern tests/unit/cli/ci/commands -q
   ```

2. Run guard tests:

   ```bash
   agdt-test-pattern tests/unit/cli/ci/guards -q
   ```

3. Run provider parser tests:

   ```bash
   agdt-test-pattern tests/unit/cli/ci/github_provider -q
   agdt-test-pattern tests/unit/cli/ci/ado_provider -q
   ```

Expected outcome: edited body-only events are skipped; title/base edits continue.
