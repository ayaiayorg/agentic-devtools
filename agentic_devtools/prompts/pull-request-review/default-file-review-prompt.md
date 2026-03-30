# Pull Request Review - File Review Step

You are reviewing files in Pull Request **#{{pull_request_id}}**.

## Queue Progress

- **Completed**: {{completed_count}} file(s)
- **Remaining**: {{pending_count}} file(s)

{% if current_file %}

## Current File

**Path**: `{{current_file}}`

Read the file prompt for detailed diff and existing threads:

```none
{{prompt_file_path}}
```

{% endif %}

## Submission Strategies

Choose a strategy based on your review context:

- **Strategy A (One-at-a-time)**: Review and submit each file individually. Best when files require detailed per-file analysis with unique findings.
- **Strategy B (Batch)**: Submit multiple files at once with shared outcomes.
  Best when remaining files share the same outcome (e.g., mechanical refactor).
  Consider this when 3+ files have similar outcomes.

{% if current_file %}

## Review Process

For the current file:

1. **Read the file prompt** to see the diff and any existing comment threads
2. **Analyze the changes** against the review criteria
3. **Submit your review** using one of the strategies below

## Strategy A: One-at-a-Time Commands

Choose one action per file (all parameters inline, no agdt-set required):

### ✅ Approve (no issues found)

```bash
agdt-approve-file --file-path "{{current_file}}" --summary "Looks good. Code follows conventions and no issues found."
```

### ⚠️ Request Changes (issues found)

```bash
agdt-request-changes --file-path "{{current_file}}" --summary "Overall assessment of issues found." --suggestions '[{"line": <LINE_NUMBER>, "severity": "high", "content": "Issue description and required fix"}]'
```

### 💡 Request Changes with Code Suggestion

```bash
agdt-request-changes-with-suggestion --file-path "{{current_file}}" --summary "Overall assessment of issues found." --suggestions '[{"line": <LINE_NUMBER>, "severity": "high", "content": "Issue description", "replacement_code": "// Your suggested replacement code"}]'
```

{% endif %}

## Strategy B: Batch Commands

Use batch commands to submit multiple file reviews at once.

### Approve Multiple Files

Use `agdt-approve-files` when all remaining files can be approved with a shared summary:

```bash
agdt-approve-files --summary "Mechanical refactor only. LGTM." --file-paths '["/src/a.ts","/src/b.ts"]'
```

### Mixed Outcomes with Defaults

Use `agdt-submit-reviews` for mixed outcomes with a defaults schema:

```bash
agdt-submit-reviews --reviews '{"default_outcome": "approve", "default_summary": "Mechanical refactor. LGTM.", "items": [{"file_path": "/src/a.ts"}, {"file_path": "/src/b.ts"}, {"file_path": "/src/c.ts", "outcome": "request-changes", "summary": "Missing null check.", "suggestions": [{"line": 42, "severity": "high", "content": "Add null guard"}]}]}'
```

### Batch Request Changes

Use `agdt-request-changes-batch` when multiple files need changes requested:

```bash
agdt-request-changes-batch --reviews '{"default_summary": "Missing error handling.", "items": [{"file_path": "/src/a.ts", "suggestions": [{"line": 10, "severity": "high", "content": "Add try/catch"}]}, {"file_path": "/src/b.ts", "suggestions": [{"line": 20, "severity": "medium", "content": "Add error boundary"}]}]}'
```

## After Submitting

Submissions are processed asynchronously — no wait is required.

- **Strategy A**: Proceed immediately to the next file.
- **Strategy B**: If all files have been submitted, proceed to the decision step.

---

**Workflow Status**: File review in progress
({{completed_count}}/{{total_count}} complete).
