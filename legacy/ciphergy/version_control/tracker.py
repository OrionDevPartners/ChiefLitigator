"""
Ciphergy Pipeline - Version Tracker
Wraps registry operations for version control of tracked files.
"""

import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import List, Optional


class VersionTracker:
    """Version control operations on registry-tracked files."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir or os.environ.get("CIPHERGY_BASE", Path.cwd()))
        self.registry_path = self.base_dir / "registry.json"
        self.versions_dir = self.base_dir / "versions"

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

    def increment_version(self, file_name: str) -> int:
        """Bump the version number of a tracked file. Returns new version."""
        reg = self._load_registry()
        files = reg.setdefault("files", {})
        if file_name not in files:
            files[file_name] = {"version": 0, "locked": False, "created_at": time.time()}
        files[file_name]["version"] = files[file_name].get("version", 0) + 1
        files[file_name]["updated_at"] = time.time()
        new_ver = files[file_name]["version"]

        reg.setdefault("audit_log", []).append(
            {
                "action": "increment_version",
                "file": file_name,
                "new_version": new_ver,
                "ts": time.time(),
            }
        )
        self._save_registry(reg)
        return new_ver

    def lock(self, file_name: str) -> bool:
        """Lock a file to prevent modification. Returns True if newly locked."""
        reg = self._load_registry()
        files = reg.setdefault("files", {})
        if file_name not in files:
            files[file_name] = {"version": 1, "locked": False, "created_at": time.time()}

        was_locked = files[file_name].get("locked", False)
        files[file_name]["locked"] = True
        files[file_name]["locked_at"] = time.time()

        reg.setdefault("audit_log", []).append(
            {
                "action": "lock",
                "file": file_name,
                "ts": time.time(),
            }
        )
        self._save_registry(reg)
        return not was_locked

    def unlock(self, file_name: str) -> bool:
        """Unlock a file. Returns True if it was locked."""
        reg = self._load_registry()
        files = reg.get("files", {})
        if file_name not in files:
            return False
        was_locked = files[file_name].get("locked", False)
        files[file_name]["locked"] = False
        files[file_name].pop("locked_at", None)
        self._save_registry(reg)
        return was_locked

    def create_new_version(self, file_name: str) -> Optional[Path]:
        """Copy the file to a new versioned folder v[N+1]. Returns path or None."""
        reg = self._load_registry()
        files = reg.setdefault("files", {})
        if file_name not in files:
            files[file_name] = {"version": 0, "locked": False, "created_at": time.time()}

        if files[file_name].get("locked", False):
            return None  # Cannot version a locked file

        new_ver = files[file_name].get("version", 0) + 1
        files[file_name]["version"] = new_ver
        files[file_name]["updated_at"] = time.time()

        # Copy file to version directory
        src = self.base_dir / file_name
        version_dir = self.versions_dir / f"v{new_ver}"
        version_dir.mkdir(parents=True, exist_ok=True)
        dst = version_dir / file_name

        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))

        reg.setdefault("audit_log", []).append(
            {
                "action": "create_new_version",
                "file": file_name,
                "version": new_ver,
                "ts": time.time(),
            }
        )
        self._save_registry(reg)
        return dst

    def get_locked_files(self) -> List[str]:
        """Return list of locked file names."""
        reg = self._load_registry()
        return [name for name, info in reg.get("files", {}).items() if info.get("locked", False)]

    def get_brackets(self) -> List[dict]:
        """Scan tracked files for unfilled [BRACKET] placeholders."""
        reg = self._load_registry()
        bracket_re = re.compile(r"\[([A-Z][A-Z0-9_ ]+)\]")
        results = []

        for file_name in reg.get("files", {}):
            full_path = self.base_dir / file_name
            if not full_path.exists() or not full_path.is_file():
                continue
            try:
                content = full_path.read_text(errors="ignore")
            except Exception:
                continue

            matches = bracket_re.findall(content)
            if matches:
                results.append(
                    {
                        "file": file_name,
                        "brackets": list(set(matches)),
                        "count": len(matches),
                    }
                )

        return results

    def get_file_info(self, file_name: str) -> Optional[dict]:
        """Get version info for a specific file."""
        reg = self._load_registry()
        return reg.get("files", {}).get(file_name)

    def register_file(self, file_name: str, file_type: str = "document", monitor: bool = True) -> dict:
        """Register a new file in the registry."""
        reg = self._load_registry()
        files = reg.setdefault("files", {})
        files[file_name] = {
            "version": 1,
            "type": file_type,
            "locked": False,
            "created_at": time.time(),
            "score": 1.0,
        }
        if monitor:
            monitored = reg.setdefault("monitored_files", [])
            if file_name not in monitored:
                monitored.append(file_name)
        self._save_registry(reg)
        return files[file_name]
