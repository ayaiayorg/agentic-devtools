# ADR-006: Mermaid for All Diagrams

**Status**: Accepted

**Context**: Need diagrams in documentation; must be maintainable and renderable in GitHub

**Decision**: Use Mermaid for all architecture diagrams

**Rationale**:

- Native GitHub rendering
- VS Code extension support
- Text-based (diffable, versionable)
- Simple syntax
- No external tools required

**Consequences**:

- ✅ GitHub native rendering
- ✅ Version control friendly
- ✅ Easy to update
- ⚠️ Limited layout control
- ⚠️ Learning curve for complex diagrams

**Alternatives Considered**:

| Alternative | Rejected Because |
|-------------|------------------|
| PlantUML | Requires external rendering |
| Graphviz | Complex syntax |
| Draw.io | Binary format, not diffable |
| Lucidchart | Commercial, not embeddable |
