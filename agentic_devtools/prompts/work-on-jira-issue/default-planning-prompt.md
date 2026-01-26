# Work on Jira Issue - Planning Step

You are planning work for Jira issue **{{issue_key}}**: {{issue_summary}}

## Your Task

Analyze the issue details and create a plan. Your plan should:

1. **Break down the work** into specific, actionable tasks
2. **Identify affected components** - which files/services need changes
3. **Note any dependencies** - what must be done first
4. **Estimate complexity** - simple, moderate, or complex
5. **Identify risks** - potential blockers or challenges

## Plan Format

Structure your plan comment like this:

```none
h4. Plan Outline

*Scope:*
* <high-level goal>

*Key Tasks:*
* 1) <first task>
* 2) <second task>
* 3) <third task>

*Affected Components:*
* <file or service 1>
* <file or service 2>

*Risks / Dependencies:*
* <known dependency or risk>
```

## Next Action

Post your plan to Jira:

```bash
{{add_jira_comment_usage}}
```

**Parameter**: {{add_jira_comment_hint}}

---

**Workflow Status**: Planning in progress. After posting your plan comment, the workflow will advance to the implementation step.
