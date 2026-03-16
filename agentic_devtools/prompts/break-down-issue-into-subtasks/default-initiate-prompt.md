# Break Down Issue into Subtasks Workflow

You are breaking down Jira issue **{{jira_issue_key}}** into smaller, actionable
subtasks that can be worked on independently.

{% if jira_user_request %}

## User Request

{{jira_user_request}}
{% endif %}

## Workflow Steps

### Step 1: Retrieve the Issue

Fetch the current issue details so you can understand its scope and content:

```bash
agdt-get-jira-issue
```

Review the retrieved issue carefully, paying attention to:

- The overall goal and acceptance criteria
- The scope boundaries (in scope / out of scope)
- Technical context and dependencies
- Estimated complexity

### Step 2: Analyze the Scope and Identify Subtasks

Break down the issue into subtasks following these guidelines:

- Each subtask should be completable in a single focused session
- Subtasks should have clear, unambiguous acceptance criteria
- Order subtasks by dependency (foundational work first)
- Aim for 3–8 subtasks; if more are needed, consider whether the parent issue
  should itself be split

For each subtask, identify:

- [ ] A concise, action-oriented summary (verb + object + context)
- [ ] A brief description explaining what needs to be done
- [ ] Any dependencies on other subtasks in this set

### Step 3: Create Each Subtask

For each identified subtask, use the subtask workflow:

```bash
agdt-initiate-create-jira-subtask-workflow --parent-key {{jira_issue_key}}
```

Follow the prompts to create each subtask with:

- A clear summary
- A description explaining the work
- References to acceptance criteria from the parent issue (where applicable)

### Step 4: Add a Comment to the Parent Issue

After all subtasks are created, add a comment to the parent issue summarizing
the breakdown:

```bash
agdt-add-jira-comment --jira-comment "h4. Issue Broken Down into Subtasks

The following subtasks have been created:

* [DFLY-XXXX] <subtask 1 summary>
* [DFLY-XXXX] <subtask 2 summary>
* [DFLY-XXXX] <subtask 3 summary>

*Approach:* <brief explanation of the breakdown strategy>"
```

## Subtask Quality Checklist

Before finalizing the breakdown, verify each subtask:

- [ ] Summary is clear and action-oriented
- [ ] Description explains the _what_ and _why_
- [ ] Acceptance criteria are explicit and testable
- [ ] Dependencies on sibling subtasks are documented
- [ ] Subtask is completable independently (after its dependencies are done)

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

- Focus on breaking the issue into _actionable_ subtasks, not just re-listing
  bullet points from the description
- Do NOT implement code changes — this workflow is for issue decomposition only
- If the parent issue is too vague to break down meaningfully, run the
  `optimize-issue-for-ai-agent` workflow first
- Retrieve the parent issue AFTER subtask creation to verify links are correct
