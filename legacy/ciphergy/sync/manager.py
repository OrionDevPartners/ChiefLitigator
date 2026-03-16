"""
Ciphergy Pipeline - Sync Manager
Handles file synchronization, delta creation, and version manifests.
"""

import json
import os
import shutil
import time
from pathlib import Path
from typing import List, Optional


class SyncManager:
    """Manages file synchronization and delta versioning."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir or os.environ.get("CIPHERGY_BASE", Path.cwd()))
        self.registry_path = self.base_dir / "registry.json"
        self.versions_dir = self.base_dir / "versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)

    def _load_registry(self) -> dict:
        if self.registry_path.exists():
            return json.loads(self.registry_path.read_text())
        return {
            "version": 1,
            "files": {},
            "monitored_files": [],
            "last_sync": None,
            "agents": {},
            "connectors": {},
            "audit_log": [],
        }

    def _save_registry(self, reg: dict):
        self.registry_path.write_text(json.dumps(reg, indent=2, default=str))

    def check_stale(self) -> List[dict]:
        """Return list of stale monitored files (modified since last sync)."""
        reg = self._load_registry()
        last_sync = reg.get("last_sync") or 0
        monitored = reg.get("monitored_files", [])
        stale = []

        for entry in monitored:
            file_path = entry if isinstance(entry, str) else entry.get("path", "")
            full_path = self.base_dir / file_path
            if full_path.exists():
                mtime = full_path.stat().st_mtime
                if mtime > last_sync:
                    stale.append(
                        {
                            "path": file_path,
                            "mtime": mtime,
                            "last_sync": last_sync,
                            "delta_seconds": mtime - last_sync,
                        }
                    )

        return stale

    def create_delta(self, trigger: str = "manual") -> Path:
        """Create a versioned snapshot folder (v[N]/) with changed files."""
        reg = self._load_registry()
        current_version = reg.get("version", 0)
        new_version = current_version + 1
        version_dir = self.versions_dir / f"v{new_version}"
        version_dir.mkdir(parents=True, exist_ok=True)

        # Copy stale files into the version folder
        stale = self.check_stale()
        copied = []
        for item in stale:
            src = self.base_dir / item["path"]
            dst = version_dir / item["path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_file():
                shutil.copy2(str(src), str(dst))
                copied.append(item["path"])

        # Write delta manifest
        manifest = {
            "version": new_version,
            "trigger": trigger,
            "created_at": time.time(),
            "files_copied": copied,
            "stale_count": len(stale),
        }
        (version_dir / "delta_manifest.json").write_text(json.dumps(manifest, indent=2))

        # Update registry version
        reg["version"] = new_version
        reg.setdefault("audit_log", []).append(
            {
                "action": "create_delta",
                "version": new_version,
                "trigger": trigger,
                "ts": time.time(),
                "files": copied,
            }
        )
        self._save_registry(reg)

        return version_dir

    def mark_synced(self):
        """Update registry with current timestamp as last sync."""
        reg = self._load_registry()
        reg["last_sync"] = time.time()
        reg.setdefault("audit_log", []).append(
            {
                "action": "mark_synced",
                "ts": reg["last_sync"],
            }
        )
        self._save_registry(reg)

    def get_manifest(self) -> dict:
        """Return the current sync manifest."""
        reg = self._load_registry()
        stale = self.check_stale()
        return {
            "version": reg.get("version", 0),
            "last_sync": reg.get("last_sync"),
            "monitored_count": len(reg.get("monitored_files", [])),
            "stale_count": len(stale),
            "stale_files": [s["path"] for s in stale],
        }

    def get_history(self) -> List[dict]:
        """Return all version folders and their contents."""
        history = []
        if not self.versions_dir.exists():
            return history

        for vdir in sorted(self.versions_dir.iterdir()):
            if vdir.is_dir() and vdir.name.startswith("v"):
                manifest_path = vdir / "delta_manifest.json"
                manifest = {}
                if manifest_path.exists():
                    manifest = json.loads(manifest_path.read_text())
                files = [
                    str(f.relative_to(vdir)) for f in vdir.rglob("*") if f.is_file() and f.name != "delta_manifest.json"
                ]
                history.append(
                    {
                        "version": vdir.name,
                        "path": str(vdir),
                        "manifest": manifest,
                        "files": files,
                    }
                )

        return history
