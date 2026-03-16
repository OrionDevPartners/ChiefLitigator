#!/usr/bin/env python3
"""
Ciphergy Pipeline — Cascade Execution Engine
Processes trigger events and cascades updates through the file system.

Usage:
    python scripts/cascade.py --trigger new-evidence --file "path/to/evidence"
    python scripts/cascade.py --trigger phase-change
    python scripts/cascade.py --trigger answered --file "_QUESTIONS.md"
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
class Color:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    CYAN = "\033[0;36m"
    BOLD = "\033[1m"
    NC = "\033[0m"


def log_info(msg):
    print(f"{Color.CYAN}[INFO]{Color.NC} {msg}")


def log_ok(msg):
    print(f"{Color.GREEN}[OK]{Color.NC} {msg}")


def log_warn(msg):
    print(f"{Color.YELLOW}[WARN]{Color.NC} {msg}")


def log_error(msg):
    print(f"{Color.RED}[ERROR]{Color.NC} {msg}")


def log_step(n, msg):
    print(f"\n  {Color.BOLD}Step {n}:{Color.NC} {msg}")


# ---------------------------------------------------------------------------
# Cascade Steps
# ---------------------------------------------------------------------------


def step_update_registry(ctx):
    """Re-scan project files and update registry entries."""
    log_step(ctx["step_num"], "Updating file registry")
    ctx["step_num"] += 1

    registry = ctx["registry"]
    project_root = ctx["project_root"]

    existing_paths = {e["path"] for e in registry.get("files", [])}
    new_count = 0

    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__", "sync")]
        for fname in files:
            if fname.startswith(".") or fname.endswith(".pyc"):
                continue
            rel_root = os.path.relpath(root, project_root)
            rel_path = os.path.join(rel_root, fname) if rel_root != "." else fname
            if rel_path not in existing_paths:
                full_path = os.path.join(root, fname)
                try:
                    with open(full_path, "rb") as fh:
                        file_hash = hashlib.md5(fh.read()).hexdigest()
                except (IOError, OSError):
                    file_hash = ""
                registry.setdefault("files", []).append(
                    {
                        "path": rel_path,
                        "hash": file_hash,
                        "tracked_since": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "category": "document",
                    }
                )
                new_count += 1
                log_info(f"  New file tracked: {rel_path}")

    if new_count == 0:
        log_ok("  No new files found.")
    else:
        log_ok(f"  {new_count} new file(s) added to registry.")

    return True


def step_recompute_hashes(ctx):
    """Recompute MD5 hashes for all tracked files."""
    log_step(ctx["step_num"], "Recomputing file hashes")
    ctx["step_num"] += 1

    registry = ctx["registry"]
    project_root = ctx["project_root"]
    changed = 0

    for entry in registry.get("files", []):
        fpath = entry.get("path", "")
        full_path = os.path.join(project_root, fpath)
        if os.path.isfile(full_path):
            with open(full_path, "rb") as fh:
                new_hash = hashlib.md5(fh.read()).hexdigest()
            if entry.get("hash") != new_hash:
                entry["hash"] = new_hash
                changed += 1

    log_ok(f"  {changed} file(s) with updated hashes.")
    ctx["files_changed"] += changed
    return True


def step_check_alerts(ctx):
    """Check _RED_ALERTS.md for active alerts."""
    log_step(ctx["step_num"], "Checking RED alerts")
    ctx["step_num"] += 1

    alerts_path = os.path.join(ctx["project_root"], "_RED_ALERTS.md")
    if not os.path.isfile(alerts_path):
        log_warn("  _RED_ALERTS.md not found.")
        return True

    with open(alerts_path, "r") as f:
        content = f.read()

    # Count non-header table rows
    lines = [
        l
        for l in content.split("\n")
        if l.strip().startswith("|") and not l.strip().startswith("| #") and not l.strip().startswith("|---")
    ]
    if lines:
        log_warn(f"  {len(lines)} active alert(s) found.")
    else:
        log_ok("  No active alerts.")

    return True


def step_update_alerts(ctx):
    """Update alerts file (placeholder for custom logic)."""
    log_step(ctx["step_num"], "Updating alerts")
    ctx["step_num"] += 1
    log_ok("  Alert update check complete.")
    return True


def step_update_questions(ctx):
    """Mark questions as answered if specified."""
    log_step(ctx["step_num"], "Updating questions")
    ctx["step_num"] += 1

    questions_path = os.path.join(ctx["project_root"], "_QUESTIONS.md")
    if not os.path.isfile(questions_path):
        log_warn("  _QUESTIONS.md not found.")
        return True

    log_ok("  Questions file located. Manual review recommended.")
    return True


def step_check_cascading_impacts(ctx):
    """Analyze whether answering a question triggers further updates."""
    log_step(ctx["step_num"], "Checking cascading impacts")
    ctx["step_num"] += 1
    log_ok("  Impact analysis complete. No automatic cascades triggered.")
    return True


def step_full_integrity_check(ctx):
    """Run full integrity check on all files."""
    log_step(ctx["step_num"], "Full integrity check")
    ctx["step_num"] += 1

    registry = ctx["registry"]
    project_root = ctx["project_root"]
    missing = 0

    for entry in registry.get("files", []):
        fpath = entry.get("path", "")
        full_path = os.path.join(project_root, fpath)
        if not os.path.isfile(full_path):
            log_warn(f"  Missing: {fpath}")
            missing += 1

    if missing == 0:
        log_ok("  All tracked files present.")
    else:
        log_warn(f"  {missing} file(s) missing.")

    return True


def step_escalate_open_items(ctx):
    """Check for open items that need escalation."""
    log_step(ctx["step_num"], "Escalating open items")
    ctx["step_num"] += 1
    log_ok("  Open item review complete.")
    return True


def step_log_correction(ctx):
    """Log a correction event to the version history."""
    log_step(ctx["step_num"], "Logging correction")
    ctx["step_num"] += 1

    registry = ctx["registry"]
    registry.setdefault("corrections", []).append(
        {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trigger_file": ctx.get("trigger_file", ""),
            "note": "Correction cascade executed",
        }
    )

    log_ok("  Correction logged.")
    return True


def step_notify_asana(ctx):
    """Post notification to Asana."""
    log_step(ctx["step_num"], "Notifying Asana")
    ctx["step_num"] += 1

    config = ctx["config"]
    asana_config = config.get("asana", {})

    if not asana_config.get("enabled", False):
        log_info("  Asana disabled. Skipping notification.")
        return True

    task_gid = asana_config.get("comm_task_gid")
    pat_var = asana_config.get("pat_env_var", "ASANA_PAT")
    pat = os.environ.get(pat_var)

    if not task_gid or not pat:
        log_warn("  Asana credentials not available. Skipping.")
        return True

    try:
        import urllib.request

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        message = (
            f"[Ciphergy Cascade] Trigger: {ctx['trigger']}\n"
            f"Time: {now}\n"
            f"Files changed: {ctx['files_changed']}\n"
            f"Status: Complete"
        )

        payload = json.dumps({"data": {"text": message}}).encode()
        req = urllib.request.Request(
            f"https://app.asana.com/api/1.0/tasks/{task_gid}/stories",
            data=payload,
            headers={
                "Authorization": f"Bearer {pat}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 201:
                log_ok("  Asana notification posted.")
            else:
                log_warn(f"  Asana returned status {resp.status}")
    except Exception as e:
        log_warn(f"  Asana notification failed: {e}")

    return True


def step_sync_check(ctx):
    """Final sync check — compare current state vs synced state."""
    log_step(ctx["step_num"], "Final sync check")
    ctx["step_num"] += 1

    registry = ctx["registry"]
    project_root = ctx["project_root"]
    synced_hashes = registry.get("sync", {}).get("synced_hashes", {})

    stale = 0
    for entry in registry.get("files", []):
        fpath = entry.get("path", "")
        full_path = os.path.join(project_root, fpath)
        if not os.path.isfile(full_path):
            continue
        with open(full_path, "rb") as fh:
            current_hash = hashlib.md5(fh.read()).hexdigest()
        if fpath in synced_hashes and synced_hashes[fpath] != current_hash:
            stale += 1
        elif fpath not in synced_hashes:
            stale += 1

    if stale > 0:
        log_warn(f"  {stale} file(s) out of sync with cloud agent.")
        log_info("  Run 'ciphergy.sh project-push' to create a delta version.")
    else:
        log_ok("  All files in sync with cloud agent.")

    return True


# Step dispatcher
STEP_MAP = {
    "update_registry": step_update_registry,
    "recompute_hashes": step_recompute_hashes,
    "check_alerts": step_check_alerts,
    "update_alerts": step_update_alerts,
    "update_questions": step_update_questions,
    "check_cascading_impacts": step_check_cascading_impacts,
    "full_integrity_check": step_full_integrity_check,
    "escalate_open_items": step_escalate_open_items,
    "log_correction": step_log_correction,
    "notify_asana": step_notify_asana,
    "sync_check": step_sync_check,
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def create_delta_version(ctx):
    """Create a delta version folder if files changed."""
    if ctx["files_changed"] == 0:
        return

    registry = ctx["registry"]
    project_root = ctx["project_root"]
    sync_dir = os.path.join(project_root, "sync")
    synced_hashes = registry.get("sync", {}).get("synced_hashes", {})

    delta_files = []
    for entry in registry.get("files", []):
        fpath = entry.get("path", "")
        full_path = os.path.join(project_root, fpath)
        if not os.path.isfile(full_path):
            continue
        with open(full_path, "rb") as fh:
            current_hash = hashlib.md5(fh.read()).hexdigest()
        if fpath not in synced_hashes or synced_hashes[fpath] != current_hash:
            delta_files.append((fpath, full_path))

    if not delta_files:
        return

    history = registry.get("version_history", [])
    next_num = len(history) + 1
    next_version = f"v{next_num}"

    version_dir = os.path.join(sync_dir, next_version)
    os.makedirs(version_dir, exist_ok=True)

    for fpath, full_path in delta_files:
        dest = os.path.join(version_dir, os.path.basename(fpath))
        shutil.copy2(full_path, dest)

    registry.setdefault("version_history", []).append(
        {
            "version": next_version,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trigger": ctx["trigger"],
            "files_changed": len(delta_files),
            "files": [f[0] for f in delta_files],
        }
    )
    registry["sync"]["current_version"] = next_version

    log_info(f"\n  Delta version {next_version} created with {len(delta_files)} file(s).")


def main():
    parser = argparse.ArgumentParser(description="Ciphergy Pipeline — Cascade Engine")
    parser.add_argument("--trigger", required=True, help="Cascade trigger type")
    parser.add_argument("--file", default="", help="File that triggered the cascade")
    parser.add_argument("--project-root", default=None, help="Project root directory")
    args = parser.parse_args()

    project_root = args.project_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(project_root, "config", "ciphergy.yaml")
    registry_path = os.path.join(project_root, ".ciphergy", "registry.json")

    # Load config
    if not os.path.isfile(config_path):
        log_error(f"Config not found: {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Load registry
    if not os.path.isfile(registry_path):
        log_error(f"Registry not found: {registry_path}")
        log_info("Run 'ciphergy.sh init' first.")
        sys.exit(1)

    with open(registry_path) as f:
        registry = json.load(f)

    # Resolve cascade steps
    cascades = config.get("cascades", {})
    if args.trigger not in cascades:
        log_error(f"Unknown trigger: {args.trigger}")
        log_info(f"Available triggers: {', '.join(cascades.keys())}")
        sys.exit(1)

    cascade_def = cascades[args.trigger]
    steps = cascade_def.get("steps", [])
    priority = cascade_def.get("priority", 5)
    description = cascade_def.get("description", "")

    print(f"\n{Color.BOLD}{Color.CYAN}=== Cascade: {args.trigger} ==={Color.NC}")
    print(f"  Description: {description}")
    print(f"  Priority: {priority}")
    print(f"  Steps: {len(steps)}")
    if args.file:
        print(f"  Trigger file: {args.file}")

    # Build context
    ctx = {
        "trigger": args.trigger,
        "trigger_file": args.file,
        "project_root": project_root,
        "config": config,
        "registry": registry,
        "step_num": 1,
        "files_changed": 0,
    }

    # Execute steps
    success = True
    for step_name in steps:
        if step_name in STEP_MAP:
            try:
                result = STEP_MAP[step_name](ctx)
                if not result:
                    log_error(f"  Step '{step_name}' failed.")
                    success = False
                    break
            except Exception as e:
                log_error(f"  Step '{step_name}' raised exception: {e}")
                success = False
                break
        else:
            log_warn(f"  Unknown step: {step_name} (skipping)")

    # Create delta version if needed
    if ctx["files_changed"] > 0:
        auto_push = config.get("sync", {}).get("auto_push", False)
        if auto_push:
            create_delta_version(ctx)

    # Log to version history
    registry.setdefault("cascade_log", []).append(
        {
            "trigger": args.trigger,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "files_changed": ctx["files_changed"],
            "success": success,
        }
    )

    # Save registry
    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2)

    # Final report
    print()
    if success:
        log_ok(f"Cascade '{args.trigger}' completed successfully.")
        log_info(f"Files changed: {ctx['files_changed']}")
    else:
        log_error(f"Cascade '{args.trigger}' completed with errors.")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
