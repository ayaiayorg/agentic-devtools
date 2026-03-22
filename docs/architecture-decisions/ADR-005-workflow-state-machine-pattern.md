# ADR-005: Workflow State Machine Pattern

**Status**: Accepted

**Context**: Complex multi-step workflows (11+ steps) are hard to manage and resume

**Decision**: Explicit workflow state with step transitions and auto-advancement

**Rationale**:

- Clear workflow progress tracking
- Resumable after failures
- Event-driven transitions
- Prompt generation based on current step

**Consequences**:

- ✅ Resumable workflows
- ✅ Clear progress tracking
- ✅ Step-specific prompts
- ⚠️ State machine complexity
- ⚠️ Event coordination required

**State Structure**:

```json
{
  "workflow": {
    "active": "work-on-jira-issue",
    "status": "in-progress",
    "step": "implementation",
    "context": {
      "issue_key": "PROJECT-1234",
      "pull_request_id": 123,
      "checklist": [...]
    }
  }
}
```
