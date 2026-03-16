#!/usr/bin/env python3
"""
CIPHERGY NERVE CENTER — Domain-Agnostic Cascade Engine
Reads domain config from config/ciphergy.yaml and domain profile.

Usage:
    python3 scripts/nerve_center.py startup       — Session startup checks
    python3 scripts/nerve_center.py deadlines      — Check all milestones
    python3 scripts/nerve_center.py dashboard       — Render situation dashboard
    python3 scripts/nerve_center.py intake          — Check intake folder for new data
    python3 scripts/nerve_center.py diff "msg"      — Log a diff entry
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# ================================================================
# CONFIG — Loaded from ciphergy.yaml at runtime
# ================================================================

BASE = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE / "config" / "ciphergy.yaml"

TODAY = datetime.now().strftime("%Y-%m-%d")
TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def load_config():
    """Load ciphergy.yaml config. Falls back to defaults if yaml not available."""
    try:
        import yaml

        with open(CONFIG_FILE) as f:
            return yaml.safe_load(f)
    except ImportError:
        # No PyYAML — use defaults
        return {
            "project": {"name": "Ciphergy"},
            "domain": "default",
            "cascade": {
                "auto_update_dashboard": True,
                "auto_log_diffs": True,
                "auto_check_deadlines": True,
                "auto_read_comms": True,
            },
        }
    except FileNotFoundError:
        return {"project": {"name": "Ciphergy"}, "domain": "default"}


def load_domain_vocab(config):
    """Load domain vocabulary from the active domain profile."""
    domain = config.get("domain", "default")
    profile_path = BASE / "config" / "domain_profiles" / f"{domain}.yaml"
    try:
        import yaml

        with open(profile_path) as f:
            profile = yaml.safe_load(f)
            return profile.get("vocabulary", {})
    except (ImportError, FileNotFoundError):
        return {
            "entity": "Entity",
            "hypothesis": "Hypothesis",
            "evidence": "Evidence",
            "milestone": "Milestone",
            "confidence_monitor": "Confidence Monitor",
        }


def load_milestones():
    """Load milestones from manifest if it exists."""
    manifest_path = BASE / "project_manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            data = json.load(f)
            return data.get("milestones", [])
    return []


def days_until(date_str):
    """Calculate days from today to a date string."""
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return (target - today).days
    except ValueError:
        return 999


def log_diff(message):
    """Append a diff entry to today's diff log."""
    diff_dir = BASE / "DIFF"
    diff_dir.mkdir(exist_ok=True)
    diff_file = diff_dir / f"{TODAY}_auto_diffs.md"

    mode = "a" if diff_file.exists() else "w"
    header = f"# DIFF LOG — {TODAY}\n\n" if mode == "w" else ""

    with open(diff_file, mode) as f:
        f.write(f"{header}- `{TIMESTAMP}` | {message}\n")

    print(f"{GREEN}[DIFF]{RESET} Logged: {message}")


# ================================================================
# COMMANDS
# ================================================================


def cmd_startup():
    """Full session startup."""
    config = load_config()
    vocab = load_domain_vocab(config)
    project_name = config.get("project", {}).get("name", "Ciphergy")

    print(f"\n{BOLD}{CYAN}{'=' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {project_name} — NERVE CENTER STARTUP{RESET}")
    print(f"{BOLD}{CYAN}  Domain: {config.get('domain', 'default')} | {TIMESTAMP}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 60}{RESET}\n")

    # 1. Check milestones
    cmd_deadlines()

    # 2. Check intake folder
    cmd_intake()

    # 3. Dashboard summary
    cmd_dashboard()

    print(f"\n{GREEN}[STARTUP COMPLETE]{RESET}\n")


def cmd_deadlines():
    """Check all milestones."""
    vocab = load_domain_vocab(load_config())
    milestone_word = vocab.get("milestone", "Milestone")
    milestones = load_milestones()

    print(f"\n{BOLD}{milestone_word.upper()} CHECK{RESET}")
    print(f"{'─' * 60}")

    if not milestones:
        print(f"  {YELLOW}No {milestone_word.lower()}s configured.{RESET}")
        print(f"  Run onboarding to set up your {milestone_word.lower()} tracker.")
        return []

    alerts = []
    for m in milestones:
        days = days_until(m.get("date", "2099-01-01"))
        desc = m.get("description", "Unnamed")
        status = m.get("status", "PENDING")

        if "COMPLETE" in status or "EXPIRED" in status:
            print(f"  {GREEN}✓{RESET} {desc} — {status}")
        elif days < 0:
            print(f"  {RED}⚠ OVERDUE{RESET} {desc} — {abs(days)} days ago")
            alerts.append(("OVERDUE", m))
        elif days <= 3:
            print(f"  {RED}🔴 {days}d{RESET} {desc}")
            alerts.append(("CRITICAL", m))
        elif days <= 7:
            print(f"  {YELLOW}🟡 {days}d{RESET} {desc}")
            alerts.append(("WARNING", m))
        else:
            print(f"  {GREEN}🟢 {days}d{RESET} {desc}")

    if alerts:
        print(f"\n  {RED}{BOLD}⚠ {len(alerts)} {milestone_word.lower()}(s) need attention{RESET}")

    return alerts


def cmd_intake():
    """Check intake folder for new data."""
    config = load_config()
    vocab = load_domain_vocab(config)
    intake_name = vocab.get("intake_folder", "New-Data")
    intake_dir = BASE / intake_name

    print(f"\n{BOLD}INTAKE CHECK ({intake_name}/){RESET}")
    print(f"{'─' * 60}")

    if not intake_dir.exists():
        print(f"  {DIM}Intake folder not found. Creating {intake_name}/{RESET}")
        intake_dir.mkdir(exist_ok=True)
        return

    processed_file = intake_dir / ".processed"
    processed_list = set()
    if processed_file.exists():
        with open(processed_file) as f:
            for line in f:
                if "→" in line or "->" in line:
                    processed_list.add(line.split("→")[0].split("->")[0].strip())

    all_files = [f.name for f in intake_dir.iterdir() if f.is_file() and not f.name.startswith(".")]

    unprocessed = [f for f in all_files if f not in processed_list]

    if unprocessed:
        print(f"  {YELLOW}⚠ {len(unprocessed)} unprocessed file(s):{RESET}")
        for f in unprocessed:
            print(f"    → {f}")
    else:
        print(f"  {GREEN}✓{RESET} All files processed")


def cmd_dashboard():
    """Quick dashboard summary."""
    config = load_config()
    project_name = config.get("project", {}).get("name", "Ciphergy")

    print(f"\n{BOLD}SITUATION DASHBOARD{RESET}")
    print(f"{'─' * 60}")
    print(f"  Project: {project_name}")
    print(f"  Domain: {config.get('domain', 'default')}")

    manifest_path = BASE / "project_manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        matters = manifest.get("matters", {})
        for key, matter in matters.items():
            print(f"  {CYAN}{matter.get('name', key)}{RESET}")
            print(f"    Status: {matter.get('status', 'unknown')} | Phase: {matter.get('phase', 'unknown')}")
    else:
        print(f"  {YELLOW}No project manifest found. Run onboarding.{RESET}")


# ================================================================
# MAIN
# ================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "startup":
        cmd_startup()
    elif cmd == "deadlines":
        cmd_deadlines()
    elif cmd == "dashboard":
        cmd_dashboard()
    elif cmd == "intake":
        cmd_intake()
    elif cmd == "diff" and len(sys.argv) > 2:
        log_diff(" ".join(sys.argv[2:]))
    else:
        print(f"Unknown: {cmd}")
        print(__doc__)
