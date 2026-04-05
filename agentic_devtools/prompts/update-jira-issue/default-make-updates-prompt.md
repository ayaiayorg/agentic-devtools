# Update Jira Issue - Make Updates

You are updating Jira issue **{{jira_issue_key}}**.

{% if jira_user_request %}

## User Request

{{jira_user_request}}
{% endif %}

## Current Issue State

| Field | Value |
|-------|-------|
| **Summary** | {{jira_issue_summary}} |
| **Type** | {{jira_issue_type}} |
| **Labels** | {{jira_issue_labels}} |

### Description

{{jira_issue_description}}

### Recent Comments

{{jira_issue_comments}}

## Workflow Steps

### Step 1: Document Pre-Update Snapshot

The current issue state is shown above. Add a comment documenting it before
making changes:

```bash
agdt-add-jira-comment --jira-comment "h4. Pre-Update Snapshot

*Current Summary:* <copy from Current Issue State above>

*Current Description:*
<brief summary of current description>

*Reason for Update:*
<what the user requested to change>"
```

### Step 2: Make the Requested Updates

Based on the user request, set the fields that need to be updated, then call the
update command once:

```bash
agdt-set jira.summary "<new summary>"
agdt-set jira.description "<new description>"
agdt-update-jira-issue
```

Only set the fields you need to change. The `agdt-update-jira-issue` command:

- Reads all set fields from state
- Updates them in a single API call
- Automatically retrieves and displays the updated issue details

### Step 3: Verify the Updates

Review the output from `agdt-update-jira-issue` and verify:

- [ ] Summary reflects the requested changes
- [ ] Description is complete and properly formatted
- [ ] Acceptance criteria are clear (if applicable)
- [ ] No information was accidentally removed

## Jira Formatting Reference

When writing descriptions or comments, use Jira wiki markup:

- _Headings:_ `h3. +Section Title+` (h3 for main), `h4. *Subsection*` (h4 for
  sub)
- _Bold:_ `*text*`
- _Monospace:_ double curly braces around text
- _Code blocks:_ `{code:language}...{code}` (use `none` for plain text)
- _Bullets:_ `*` (single level), `**` (nested)
- _Links:_ `[text|url]`
- _Tables:_ `||Header||` for header row, `|Cell|` for data rows

## Important Notes

- Always document the current state BEFORE making changes
- Retrieve the issue AFTER updates to verify success
- If the user request is unclear, ask for clarification before proceeding
- Do NOT implement code changes - this workflow is for updating Jira issue
  metadata only
