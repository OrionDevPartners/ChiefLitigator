"""
Ciphergy Pipeline - Cascade Engine
Executes full cascade: detect -> classify -> update -> re-score -> threshold -> sync -> notify.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional


class CascadeEngine:
    """Runs a full cascade pipeline with audit logging."""

    STEPS = [
        "detect",
        "classify",
        "update_files",
        "re_score",
        "check_thresholds",
        "sync_check",
        "notify",
    ]

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir or os.environ.get("CIPHERGY_BASE", Path.cwd()))
        self.registry_path = self.base_dir / "registry.json"
        self.config_path = self.base_dir / "config.json"

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

    def _load_config(self) -> dict:
        if self.config_path.exists():
            return json.loads(self.config_path.read_text())
        return {
            "priority_order": self.STEPS,
            "thresholds": {"min_score": 0.5, "max_stale_hours": 24},
            "notify": {"enabled": False},
        }

    async def execute(self, trigger: str, context: dict = None) -> dict:
        """Run the full cascade pipeline."""
        context = context or {}
        config = self._load_config()
        reg = self._load_registry()

        steps_order = config.get("priority_order", self.STEPS)
        result = {
            "trigger": trigger,
            "started_at": time.time(),
            "steps": {},
            "status": "running",
        }

        for step_name in steps_order:
            handler = getattr(self, f"_step_{step_name}", None)
            if handler is None:
                result["steps"][step_name] = {"status": "skipped", "reason": "no handler"}
                continue

            try:
                step_result = handler(reg, config, context)
                result["steps"][step_name] = {"status": "ok", "result": step_result}
            except Exception as exc:
                result["steps"][step_name] = {"status": "error", "error": str(exc)}
                result["status"] = "partial"
                break

        if result["status"] == "running":
            result["status"] = "complete"

        result["completed_at"] = time.time()
        result["duration_s"] = round(result["completed_at"] - result["started_at"], 3)

        # Audit log
        reg.setdefault("audit_log", []).append(
            {
                "action": "cascade",
                "trigger": trigger,
                "status": result["status"],
                "ts": result["completed_at"],
                "duration_s": result["duration_s"],
                "steps_run": len(result["steps"]),
            }
        )
        self._save_registry(reg)

        return result

    # -- Pipeline steps -----------------------------------------------------

    def _step_detect(self, reg: dict, config: dict, context: dict) -> dict:
        """Detect changes in monitored files."""
        monitored = reg.get("monitored_files", [])
        last_sync = reg.get("last_sync") or 0
        changed = []
        for entry in monitored:
            fpath = entry if isinstance(entry, str) else entry.get("path", "")
            full = self.base_dir / fpath
            if full.exists() and full.stat().st_mtime > last_sync:
                changed.append(fpath)
        return {"changed_files": changed, "count": len(changed)}

    def _step_classify(self, reg: dict, config: dict, context: dict) -> dict:
        """Classify detected changes by type."""
        files = reg.get("files", {})
        classified = {}
        for name, info in files.items():
            ftype = info.get("type", "unknown")
            classified.setdefault(ftype, []).append(name)
        return {"classifications": classified}

    def _step_update_files(self, reg: dict, config: dict, context: dict) -> dict:
        """Update file metadata in registry."""
        updated = []
        for name, info in reg.get("files", {}).items():
            full = self.base_dir / name
            if full.exists():
                info["last_checked"] = time.time()
                info["size"] = full.stat().st_size
                updated.append(name)
        return {"updated": updated, "count": len(updated)}

    def _step_re_score(self, reg: dict, config: dict, context: dict) -> dict:
        """Re-score files based on current state."""
        scores = {}
        for name, info in reg.get("files", {}).items():
            version = info.get("version", 1)
            locked = info.get("locked", False)
            # Simple scoring: higher version + not locked = higher score
            score = round(min(1.0, version * 0.1 + (0.2 if not locked else 0.0)), 2)
            info["score"] = score
            scores[name] = score
        return {"scores": scores}

    def _step_check_thresholds(self, reg: dict, config: dict, context: dict) -> dict:
        """Check if any files fall below configured thresholds."""
        thresholds = config.get("thresholds", {})
        min_score = thresholds.get("min_score", 0.5)
        violations = []
        for name, info in reg.get("files", {}).items():
            if info.get("score", 1.0) < min_score:
                violations.append({"file": name, "score": info["score"], "threshold": min_score})
        return {"violations": violations, "count": len(violations)}

    def _step_sync_check(self, reg: dict, config: dict, context: dict) -> dict:
        """Check sync status of monitored files."""
        last_sync = reg.get("last_sync") or 0
        max_stale = config.get("thresholds", {}).get("max_stale_hours", 24) * 3600
        now = time.time()
        needs_sync = now - last_sync > max_stale if last_sync else True
        return {"needs_sync": needs_sync, "hours_since_sync": round((now - last_sync) / 3600, 1) if last_sync else None}

    def _step_notify(self, reg: dict, config: dict, context: dict) -> dict:
        """Send notifications if configured."""
        notify_config = config.get("notify", {})
        if not notify_config.get("enabled", False):
            return {"sent": False, "reason": "notifications disabled"}
        return {"sent": True, "channel": notify_config.get("channel", "log")}
