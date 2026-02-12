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

## Review Process

For the current file:

1. **Read the file prompt** to see the diff and any existing comment threads
2. **Analyze the changes** against the review criteria
3. **Submit your review** using one of the commands below

## Review Commands

Choose one action (all parameters inline, no agdt-set required):

### ✅ Approve (no issues found)

```bash
agdt-approve-file --file-path "{{current_file}}" --content "Looks good. Code follows conventions and no issues found."
```

### ⚠️ Request Changes (issues found)

```bash
agdt-request-changes --file-path "{{current_file}}" --line <LINE_NUMBER> --content "Issue description and required fix"
```

### 💡 Request Changes with Code Suggestion

```bash
agdt-request-changes-with-suggestion --file-path "{{current_file}}" --line <LINE_NUMBER> --content "\`\`\`suggestion
// Your suggested replacement code
\`\`\`"
```

## After Submitting

{% if pending_count <= 1 %}
Run `agdt-task-wait` to:

- Wait for the review to post
- Complete the file review workflow and proceed to summary

  {% else %}
  {% else %}
  **No wait required** - proceed directly to the next file after submitting.
  {% endif %}

---

**Workflow Status**: File review in progress
({{completed_count}}/{{total_count}} complete).
