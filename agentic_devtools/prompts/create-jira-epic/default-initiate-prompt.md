# Create Jira Epic Workflow

You are creating a new epic in project **{{jira_project_key}}**.

## Understanding Epics

Epics are large bodies of work that can be broken down into smaller stories or tasks. They typically:

- Span multiple sprints
- Represent a significant feature or initiative
- Group related user stories together

## Gathering Information

Before creating the epic, prepare:

1. **Epic Name**: Short, memorable name for the epic
2. **Summary**: Brief description of the epic's goal
3. **User Story**: Role, desired outcome, and benefit

## Creating the Epic

1. Set the required state:

   ```bash
   dfly-set jira.project_key {{jira_project_key}}
   dfly-set jira.summary "<epic summary>"
   dfly-set jira.epic_name "<short epic name>"
   dfly-set jira.role "<user role>"
   dfly-set jira.desired_outcome "<what the user wants>"
   dfly-set jira.benefit "<why they want it>"
   ```

2. Create the epic:

   ```bash
   dfly-create-epic
   ```

## Epic Description Format

The created epic will use this structure:

```none
As a <role>,
I want <desired outcome>,
So that <benefit>.

h3. +Scope+
* Define what's included
* Define what's excluded

h3. +Success Criteria+
* Measurable outcomes
```

## After Creation

Once the epic is created:

1. Create child stories/tasks using `dfly-create-issue` with the epic link
2. Set up the epic's roadmap in Jira
3. Prioritize child issues within the epic
