"""Tests for ReviewState dataclass."""

from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewState,
)


def _make_review_state(**kwargs) -> ReviewState:
    defaults = {
        "prId": 25365,
        "repoId": "repo-guid",
        "repoName": "dfly-platform-management",
        "project": "DragonflyMgmt",
        "organization": "https://dev.azure.com/swica",
        "latestIterationId": 5,
        "scaffoldedUtc": "2026-02-25T10:00:00Z",
        "overallSummary": OverallSummary(threadId=161000, commentId=1771800000),
    }
    defaults.update(kwargs)
    return ReviewState(**defaults)


class TestReviewState:
    """Tests for ReviewState dataclass."""

    def test_creation_with_defaults(self):
        """Test creation with minimal required fields and defaults."""
        state = _make_review_state()
        assert state.prId == 25365
        assert state.repoId == "repo-guid"
        assert state.repoName == "dfly-platform-management"
        assert state.project == "DragonflyMgmt"
        assert state.organization == "https://dev.azure.com/swica"
        assert state.latestIterationId == 5
        assert state.scaffoldedUtc == "2026-02-25T10:00:00Z"
        assert state.folders == {}
        assert state.files == {}

    def test_to_dict(self):
        """Test serialization to dictionary."""
        state = _make_review_state()
        d = state.to_dict()
        assert d["prId"] == 25365
        assert d["repoId"] == "repo-guid"
        assert d["latestIterationId"] == 5
        assert "overallSummary" in d
        assert d["folders"] == {}
        assert d["files"] == {}

    def test_to_dict_with_folders_and_files(self):
        """Test serialization with folders and files."""
        folder = FolderGroup(files=["/src/app.py"])
        file_entry = FileEntry(threadId=3, commentId=4, folder="src", fileName="app.py")
        state = _make_review_state(
            folders={"src": folder},
            files={"/src/app.py": file_entry},
        )
        d = state.to_dict()
        assert "src" in d["folders"]
        assert "/src/app.py" in d["files"]

    def test_from_dict(self):
        """Test deserialization from a dictionary."""
        data = {
            "prId": 25365,
            "repoId": "repo-guid",
            "repoName": "dfly-platform-management",
            "project": "DragonflyMgmt",
            "organization": "https://dev.azure.com/swica",
            "latestIterationId": 5,
            "scaffoldedUtc": "2026-02-25T10:00:00Z",
            "overallSummary": {"threadId": 161000, "commentId": 1771800000, "status": "unreviewed"},
            "folders": {},
            "files": {},
        }
        state = ReviewState.from_dict(data)
        assert state.prId == 25365
        assert state.repoName == "dfly-platform-management"
        assert state.overallSummary.threadId == 161000
        assert state.folders == {}
        assert state.files == {}

    def test_from_dict_with_folders_and_files(self):
        """Test deserialization with nested folders and files."""
        data = {
            "prId": 25365,
            "repoId": "repo-guid",
            "repoName": "dfly-platform-management",
            "project": "DragonflyMgmt",
            "organization": "https://dev.azure.com/swica",
            "latestIterationId": 5,
            "scaffoldedUtc": "2026-02-25T10:00:00Z",
            "overallSummary": {"threadId": 161000, "commentId": 1771800000, "status": "unreviewed"},
            "folders": {
                "mgmt-backend": {
                    "files": ["/mgmt-backend/SomeFile.cs"],
                }
            },
            "files": {
                "/mgmt-backend/SomeFile.cs": {
                    "threadId": 161048,
                    "commentId": 1771800050,
                    "folder": "mgmt-backend",
                    "fileName": "SomeFile.cs",
                    "status": "unreviewed",
                    "summary": None,
                    "changeTrackingId": 42,
                    "suggestions": [],
                }
            },
        }
        state = ReviewState.from_dict(data)
        assert "mgmt-backend" in state.folders
        assert state.folders["mgmt-backend"].files == ["/mgmt-backend/SomeFile.cs"]
        assert "/mgmt-backend/SomeFile.cs" in state.files
        assert state.files["/mgmt-backend/SomeFile.cs"].fileName == "SomeFile.cs"

    def test_roundtrip(self):
        """Test to_dict/from_dict round-trips correctly."""
        folder = FolderGroup(files=["/src/app.py"])
        file_entry = FileEntry(threadId=3, commentId=4, folder="src", fileName="app.py", status="approved")
        original = _make_review_state(
            folders={"src": folder},
            files={"/src/app.py": file_entry},
        )
        restored = ReviewState.from_dict(original.to_dict())
        assert restored.prId == 25365
        assert restored.folders["src"].files == ["/src/app.py"]
        assert restored.files["/src/app.py"].fileName == "app.py"

    def test_folders_default_is_independent(self):
        """Test that default folders dicts are independent per instance."""
        s1 = _make_review_state()
        s2 = _make_review_state()
        s1.folders["test"] = FolderGroup()
        assert "test" not in s2.folders

    def test_files_default_is_independent(self):
        """Test that default files dicts are independent per instance."""
        s1 = _make_review_state()
        s2 = _make_review_state()
        s1.files["/test.py"] = FileEntry(threadId=1, commentId=2, folder="x", fileName="test.py")
        assert "/test.py" not in s2.files

    def test_from_dict_normalizes_file_keys(self):
        """Test that from_dict normalizes file dict keys with leading slash."""
        data = {
            "prId": 25365,
            "repoId": "repo-guid",
            "repoName": "dfly-platform-management",
            "project": "DragonflyMgmt",
            "organization": "https://dev.azure.com/swica",
            "latestIterationId": 5,
            "scaffoldedUtc": "2026-02-25T10:00:00Z",
            "overallSummary": {"threadId": 161000, "commentId": 1771800000, "status": "unreviewed"},
            "folders": {},
            "files": {
                "src/app.py": {
                    "threadId": 1,
                    "commentId": 2,
                    "folder": "src",
                    "fileName": "app.py",
                    "status": "unreviewed",
                    "suggestions": [],
                }
            },
        }
        state = ReviewState.from_dict(data)
        assert "/src/app.py" in state.files
        assert "src/app.py" not in state.files

    def test_new_fields_defaults(self):
        """Test that new fields have correct default values."""
        state = _make_review_state()
        assert state.commitHash is None
        assert state.modelId is None
        assert state.activityLogThreadId == 0
        assert state.sessions == []

    def test_to_dict_includes_new_fields(self):
        """Test that to_dict includes all new fields."""
        state = _make_review_state(
            commitHash="abc123",
            modelId="claude-4",
            activityLogThreadId=999,
        )
        d = state.to_dict()
        assert d["commitHash"] == "abc123"
        assert d["modelId"] == "claude-4"
        assert d["activityLogThreadId"] == 999
        assert d["sessions"] == []

    def test_from_dict_reads_new_fields(self):
        """Test that from_dict deserializes all new fields."""
        from agentic_devtools.cli.azure_devops.review_state import ReviewSession

        data = {
            "prId": 25365,
            "repoId": "repo-guid",
            "repoName": "dfly-platform-management",
            "project": "DragonflyMgmt",
            "organization": "https://dev.azure.com/swica",
            "latestIterationId": 5,
            "scaffoldedUtc": "2026-02-25T10:00:00Z",
            "overallSummary": {"threadId": 161000, "commentId": 1771800000, "status": "unreviewed"},
            "folders": {},
            "files": {},
            "commitHash": "deadbeef",
            "modelId": "gpt-5",
            "activityLogThreadId": 42,
            "sessions": [
                {
                    "sessionId": "sess-1",
                    "modelId": "gpt-5",
                    "startedUtc": "2026-03-01T10:00:00Z",
                    "status": "completed",
                }
            ],
        }
        state = ReviewState.from_dict(data)
        assert state.commitHash == "deadbeef"
        assert state.modelId == "gpt-5"
        assert state.activityLogThreadId == 42
        assert len(state.sessions) == 1
        assert isinstance(state.sessions[0], ReviewSession)
        assert state.sessions[0].sessionId == "sess-1"

    def test_from_dict_defaults_for_missing_new_fields(self):
        """Test that from_dict defaults new fields when missing."""
        data = {
            "prId": 25365,
            "repoId": "repo-guid",
            "repoName": "dfly-platform-management",
            "project": "DragonflyMgmt",
            "organization": "https://dev.azure.com/swica",
            "latestIterationId": 5,
            "scaffoldedUtc": "2026-02-25T10:00:00Z",
            "overallSummary": {"threadId": 161000, "commentId": 1771800000, "status": "unreviewed"},
            "folders": {},
            "files": {},
        }
        state = ReviewState.from_dict(data)
        assert state.commitHash is None
        assert state.modelId is None
        assert state.activityLogThreadId == 0
        assert state.sessions == []

    def test_roundtrip_with_new_fields(self):
        """Test to_dict/from_dict round-trips new fields correctly."""
        from agentic_devtools.cli.azure_devops.review_state import ReviewSession

        session = ReviewSession(
            sessionId="sess-1",
            modelId="claude-4",
            startedUtc="2026-03-01T10:00:00Z",
            completedUtc="2026-03-01T10:30:00Z",
            status="completed",
        )
        original = _make_review_state(
            commitHash="abc123",
            modelId="claude-4",
            activityLogThreadId=999,
            sessions=[session],
        )
        restored = ReviewState.from_dict(original.to_dict())
        assert restored.commitHash == "abc123"
        assert restored.modelId == "claude-4"
        assert restored.activityLogThreadId == 999
        assert len(restored.sessions) == 1
        assert restored.sessions[0].sessionId == "sess-1"

    def test_sessions_default_is_independent(self):
        """Test that default sessions lists are independent per instance."""
        from agentic_devtools.cli.azure_devops.review_state import ReviewSession

        s1 = _make_review_state()
        s2 = _make_review_state()
        s1.sessions.append(ReviewSession(sessionId="x", modelId="m", startedUtc="t"))
        assert s2.sessions == []
