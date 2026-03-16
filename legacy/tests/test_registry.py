"""Tests for registry operations via VersionTracker and SyncManager."""

import json
import time

import pytest
from ciphergy.sync.manager import SyncManager
from ciphergy.version_control.tracker import VersionTracker


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory with registry."""
    reg = {
        "version": 1,
        "files": {},
        "monitored_files": [],
        "last_sync": None,
        "agents": {},
        "connectors": {},
        "audit_log": [],
    }
    (tmp_path / "registry.json").write_text(json.dumps(reg))
    (tmp_path / "versions").mkdir()
    return tmp_path


class TestVersionTracker:
    def test_register_file(self, tmp_project):
        tracker = VersionTracker(base_dir=tmp_project)
        info = tracker.register_file("test.txt", file_type="text")
        assert info["version"] == 1
        assert info["locked"] is False
        assert info["type"] == "text"

    def test_increment_version(self, tmp_project):
        tracker = VersionTracker(base_dir=tmp_project)
        tracker.register_file("doc.md")
        v = tracker.increment_version("doc.md")
        assert v == 2
        v = tracker.increment_version("doc.md")
        assert v == 3

    def test_increment_version_new_file(self, tmp_project):
        tracker = VersionTracker(base_dir=tmp_project)
        v = tracker.increment_version("new_file.txt")
        assert v == 1

    def test_lock_unlock(self, tmp_project):
        tracker = VersionTracker(base_dir=tmp_project)
        tracker.register_file("locked.txt")
        newly_locked = tracker.lock("locked.txt")
        assert newly_locked is True
        # Lock again should return False (already locked)
        already = tracker.lock("locked.txt")
        assert already is False
        # Get locked files
        locked = tracker.get_locked_files()
        assert "locked.txt" in locked
        # Unlock
        was_locked = tracker.unlock("locked.txt")
        assert was_locked is True

    def test_create_new_version(self, tmp_project):
        tracker = VersionTracker(base_dir=tmp_project)
        # Create a real file
        (tmp_project / "versioned.txt").write_text("content v1")
        tracker.register_file("versioned.txt")
        dst = tracker.create_new_version("versioned.txt")
        assert dst is not None
        assert dst.exists()
        assert dst.read_text() == "content v1"

    def test_create_new_version_locked(self, tmp_project):
        tracker = VersionTracker(base_dir=tmp_project)
        tracker.register_file("locked.txt")
        tracker.lock("locked.txt")
        dst = tracker.create_new_version("locked.txt")
        assert dst is None

    def test_get_brackets(self, tmp_project):
        tracker = VersionTracker(base_dir=tmp_project)
        (tmp_project / "bracket.txt").write_text("Hello [NAME], your case [CASE NUMBER] is pending.")
        tracker.register_file("bracket.txt")
        brackets = tracker.get_brackets()
        assert len(brackets) == 1
        assert "NAME" in brackets[0]["brackets"]
        assert "CASE NUMBER" in brackets[0]["brackets"]

    def test_get_file_info(self, tmp_project):
        tracker = VersionTracker(base_dir=tmp_project)
        tracker.register_file("info.txt", file_type="document")
        info = tracker.get_file_info("info.txt")
        assert info is not None
        assert info["type"] == "document"
        assert tracker.get_file_info("nonexistent.txt") is None


class TestSyncManager:
    def test_check_stale_empty(self, tmp_project):
        mgr = SyncManager(base_dir=tmp_project)
        stale = mgr.check_stale()
        assert stale == []

    def test_check_stale_with_monitored(self, tmp_project):
        # Add monitored file
        (tmp_project / "watched.txt").write_text("content")
        reg = json.loads((tmp_project / "registry.json").read_text())
        reg["monitored_files"] = ["watched.txt"]
        reg["last_sync"] = time.time() - 3600  # 1 hour ago
        (tmp_project / "registry.json").write_text(json.dumps(reg))

        mgr = SyncManager(base_dir=tmp_project)
        stale = mgr.check_stale()
        assert len(stale) == 1
        assert stale[0]["path"] == "watched.txt"

    def test_create_delta(self, tmp_project):
        (tmp_project / "file.txt").write_text("delta content")
        reg = json.loads((tmp_project / "registry.json").read_text())
        reg["monitored_files"] = ["file.txt"]
        reg["last_sync"] = 0
        (tmp_project / "registry.json").write_text(json.dumps(reg))

        mgr = SyncManager(base_dir=tmp_project)
        path = mgr.create_delta(trigger="test")
        assert path.exists()
        assert (path / "delta_manifest.json").exists()
        manifest = json.loads((path / "delta_manifest.json").read_text())
        assert manifest["trigger"] == "test"
        assert "file.txt" in manifest["files_copied"]

    def test_mark_synced(self, tmp_project):
        mgr = SyncManager(base_dir=tmp_project)
        mgr.mark_synced()
        reg = json.loads((tmp_project / "registry.json").read_text())
        assert reg["last_sync"] is not None
        assert reg["last_sync"] > 0

    def test_get_manifest(self, tmp_project):
        mgr = SyncManager(base_dir=tmp_project)
        manifest = mgr.get_manifest()
        assert "version" in manifest
        assert "stale_count" in manifest
        assert "monitored_count" in manifest

    def test_get_history(self, tmp_project):
        mgr = SyncManager(base_dir=tmp_project)
        # Initially empty
        history = mgr.get_history()
        assert history == []
        # Create a delta
        (tmp_project / "h.txt").write_text("history")
        reg = json.loads((tmp_project / "registry.json").read_text())
        reg["monitored_files"] = ["h.txt"]
        reg["last_sync"] = 0
        (tmp_project / "registry.json").write_text(json.dumps(reg))
        mgr.create_delta("history-test")
        history = mgr.get_history()
        assert len(history) == 1
        assert history[0]["version"] == "v2"
