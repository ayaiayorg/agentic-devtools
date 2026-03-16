# Optimize Issue for AI Agent Workflow

You are optimizing Jira issue **{{jira_issue_key}}** so that it is clear and
well-structured for an AI agent to work on.

{% if jira_user_request %}

## User Request

{{jira_user_request}}
{% endif %}

## Workflow Steps

### Step 1: Retrieve the Issue

Fetch the current issue details so you can assess its structure and clarity:

```bash
agdt-get-jira-issue
```

Review the retrieved issue carefully, paying attention to:

- Summary: Is it concise and action-oriented?
- Description: Is it clear, well-structured, and complete?
- Acceptance criteria: Are they specific and measurable?
- Labels and issue type: Are they accurate?

### Step 2: Analyze the Issue for AI-Agent Clarity

Evaluate the issue against these criteria:

- [ ] **Summary** clearly describes the work in one line (verb + object + context)
- [ ] **Description** explains the _what_, _why_, and _how_ (background, goal, approach)
- [ ] **Acceptance criteria** are explicit, testable, and listed individually
- [ ] **Scope** is clearly bounded — "in scope" and "out of scope" are stated
- [ ] **Dependencies** on other issues or systems are identified
- [ ] **Technical context** (relevant files, patterns, APIs) is provided where helpful
- [ ] No ambiguous pronouns or vague terms like "improve", "fix", "update" without specifics

### Step 3: Rewrite for Clarity

Prepare the updated content. Use Jira wiki markup for formatting:

- Document the improved summary and description
- Ensure acceptance criteria are bulleted and testable
- Add scope boundaries and dependency notes if missing
- Preserve all existing intent — do not change what is being asked, only how it is expressed

### Step 4: Update the Issue

Apply the improvements using the update command:

```bash
agdt-set jira.summary "<optimized summary>"
agdt-set jira.description "<optimized description>"
agdt-update-jira-issue
```

### Step 5: Add a Comment Documenting the Changes

Leave a comment explaining what was changed and why:

```bash
agdt-add-jira-comment --jira-comment "h4. Issue Optimized for AI Agent

The issue description has been rewritten for clarity and completeness:

*Changes made:*
* <list the specific improvements>

*Goal:* Ensure an AI coding agent can work on this issue without requiring
clarification."
```

## Jira Formatting Reference

When writing descriptions or comments, use Jira wiki markup:

- _Headings:_ `h3. Section Title` (h3 for main), `h4. Subsection` (h4 for sub)
- _Bold:_ `*text*`
- _Monospace:_ double curly braces around text
- _Code blocks:_ `{code:language}...{code}` (use `none` for plain text)
- _Bullets:_ `*` (single level), `**` (nested)
- _Links:_ `[text|url]`
- _Tables:_ `||Header||` for header row, `|Cell|` for data rows

## Important Notes

- Do NOT change the intent of the issue — only improve clarity and completeness
- Do NOT implement code changes — this workflow is for optimizing issue metadata only
- Retrieve the issue AFTER updates to verify the changes were applied correctly
- If the user request conflicts with the existing issue scope, ask for clarification
