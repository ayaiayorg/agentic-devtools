# ADR-012: Cross-Platform File Locking

**Status**: Accepted

**Context**: State file needs concurrent access protection on Windows, macOS, Linux

**Decision**: Use platform-specific file locking (`msvcrt` on Windows, `fcntl` on Unix)

**Rationale**:

- Native OS support
- No external dependencies
- Reliable locking
- Standard practice

**Consequences**:

- ✅ Cross-platform compatible
- ✅ Reliable concurrency control
- ✅ No dependencies
- ⚠️ Platform-specific code
- ⚠️ Lock timeouts possible

**Implementation**:

```python
import sys

if sys.platform == 'win32':
    import msvcrt
    # Use msvcrt.locking()
else:
    import fcntl
    # Use fcntl.flock()
```
