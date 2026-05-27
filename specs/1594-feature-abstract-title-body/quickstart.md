# Quickstart: Validate Edit-Relevance Guard Behavior

1. Run targeted CI command tests:

   ```bash
   pytest tests/unit/cli/ci/commands -q
   ```

2. Run guard tests:

   ```bash
   pytest tests/unit/cli/ci/guards -q
   ```

3. Run provider parser tests:

   ```bash
   pytest tests/unit/cli/ci/github_provider -q
   pytest tests/unit/cli/ci/ado_provider -q
   ```

Expected outcome: edited body-only events are skipped; title/base edits continue.
