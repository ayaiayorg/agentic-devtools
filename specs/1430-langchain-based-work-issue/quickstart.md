# Quickstart: Test LangChain Work-on-Issue Path

## 1) Start a LangChain Workflow

```bash
agdt-initiate-work-on-jira-issue-workflow --issue-key PROJECT-1234 --engine langchain
```

## 2) Resume After Planning-Gate Interrupt

```bash
agdt-initiate-work-on-jira-issue-workflow --issue-key PROJECT-1234 --engine langchain --resume
```

The backward-compatible alias is accepted for the same resume path:

```bash
agdt-initiate-work-on-jira-issue-workflow --issue-key PROJECT-1234 --use-langchain --resume
```

## 3) Resume After Implementation-Gate Interrupt

```bash
agdt-initiate-work-on-jira-issue-workflow --issue-key PROJECT-1234 --use-langchain --resume \
  --resume-data '{"completed": true, "summary": "Implementation finished and ready for review"}'
```

## 4) Start with the Backward-Compatible Alias

```bash
agdt-initiate-work-on-jira-issue-workflow --issue-key PROJECT-1234 --use-langchain
```

## 5) Expected Behaviors

- Without `--engine langchain` (or alias), existing workflow-manager behavior is unchanged.
- `--resume` requires LangChain engine selection via `--engine langchain` or `--use-langchain`.
- `--resume-data` is only required when resuming from the implementation gate.
- `--resume-data` schema for implementation-gate resume:
  - required `completed: true`
  - required non-empty `summary: string`
  - optional `affected_paths: string[]` (repo-relative paths)
- Invalid JSON, non-object payloads, or schema violations fail before graph invocation and do not advance checkpoints.
- Missing LangGraph dependencies surface the FR-009 install guidance message.
