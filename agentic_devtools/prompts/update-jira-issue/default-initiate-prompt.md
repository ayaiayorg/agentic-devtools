# Update Jira Issue Workflow

You are updating Jira issue **{{jira_issue_key}}**.

{% if jira_user_request %}

## User Request

{{jira_user_request}}
{% endif %}

## Workflow Steps

### Step 1: Document Current State (Pre-Update Snapshot)

First, retrieve and review the current issue state:

```bash
dfly-get-jira-issue
```

After retrieving, add a comment documenting the current state before making changes:

```bash
dfly-add-jira-comment --jira-comment "h4. Pre-Update Snapshot

*Current Summary:* <current summary>

*Current Description:*
<brief summary of current description>

*Reason for Update:*
<what the user requested to change>"
```

### Step 2: Make the Requested Updates

Based on the user request, set the fields that need to be updated, then call the update command once:

```bash
dfly-set jira.summary "<new summary>"
dfly-set jira.description "<new description>"
dfly-update-jira-issue
```

Only set the fields you need to change. The `dfly-update-jira-issue` command:

- Reads all set fields from state
- Updates them in a single API call
- Automatically retrieves and displays the updated issue details

### Step 3: Verify the Updates

Review the output from `dfly-update-jira-issue` and verify:

- [ ] Summary reflects the requested changes
- [ ] Description is complete and properly formatted
- [ ] Acceptance criteria are clear (if applicable)
- [ ] No information was accidentally removed

## Jira Formatting Reference

When writing descriptions or comments, use Jira wiki markup:

- _Headings:_ `h3. +Section Title+` (h3 for main), `h4. *Subsection*` (h4 for sub)
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
- Do NOT implement code changes - this workflow is for updating Jira issue metadata only
