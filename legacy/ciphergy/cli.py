"""
Ciphergy Pipeline - CLI Entry Point
Commands: init, status, check, sync, push, cascade, serve, dashboard, onboard, agents
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "cyan": "\033[96m",
    "dim": "\033[2m",
}


def c(text, color):
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"


def heading(text):
    print(f"\n{c(text, 'bold')}")
    print(c("-" * len(text), "dim"))


def ok(text):
    print(f"  {c('[OK]', 'green')} {text}")


def warn(text):
    print(f"  {c('[!!]', 'yellow')} {text}")


def err(text):
    print(f"  {c('[ERR]', 'red')} {text}")


def info(text):
    print(f"  {c('[--]', 'cyan')} {text}")


# ---------------------------------------------------------------------------
# Resolve base directory
# ---------------------------------------------------------------------------

def get_base() -> Path:
    return Path(os.environ.get("CIPHERGY_BASE", Path.cwd()))


def load_registry(base: Path) -> dict:
    reg_path = base / "registry.json"
    if reg_path.exists():
        return json.loads(reg_path.read_text())
    return {}


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_init(args):
    """Initialize a new Ciphergy project."""
    base = get_base()
    heading("Initializing Ciphergy Pipeline")

    # Create registry
    reg_path = base / "registry.json"
    if not reg_path.exists():
        reg = {
            "version": 1,
            "files": {},
            "monitored_files": [],
            "last_sync": None,
            "agents": {},
            "connectors": {},
            "audit_log": [{"action": "init", "ts": time.time()}],
        }
        reg_path.write_text(json.dumps(reg, indent=2))
        ok("Created registry.json")
    else:
        info("registry.json already exists")

    # Create config
    cfg_path = base / "config.json"
    if not cfg_path.exists():
        cfg = {
            "project_name": base.name,
            "priority_order": [
                "detect", "classify", "update_files",
                "re_score", "check_thresholds", "sync_check", "notify",
            ],
            "thresholds": {"min_score": 0.5, "max_stale_hours": 24},
            "notify": {"enabled": False},
        }
        cfg_path.write_text(json.dumps(cfg, indent=2))
        ok("Created config.json")
    else:
        info("config.json already exists")

    # Create versions dir
    versions_dir = base / "versions"
    versions_dir.mkdir(exist_ok=True)
    ok("Versions directory ready")

    # Create alerts
    alerts_path = base / "alerts.json"
    if not alerts_path.exists():
        alerts_path.write_text("[]")
        ok("Created alerts.json")

    ok(f"Ciphergy initialized at {base}")


def cmd_status(args):
    """Show current system status."""
    base = get_base()
    reg = load_registry(base)

    heading("Ciphergy Pipeline Status")

    if not reg:
        err("No registry found. Run 'ciphergy init' first.")
        return

    info(f"Registry version: {c('v' + str(reg.get('version', 0)), 'blue')}")
    info(f"Tracked files:    {c(str(len(reg.get('files', {}))), 'cyan')}")
    info(f"Monitored files:  {c(str(len(reg.get('monitored_files', []))), 'cyan')}")
    info(f"Active agents:    {c(str(len(reg.get('agents', {}))), 'cyan')}")
    info(f"Connectors:       {c(str(len(reg.get('connectors', {}))), 'cyan')}")

    last_sync = reg.get("last_sync")
    if last_sync:
        ago = time.time() - last_sync
        hours = ago / 3600
        color = "green" if hours < 24 else "yellow" if hours < 72 else "red"
        info(f"Last sync:        {c(f'{hours:.1f} hours ago', color)}")
    else:
        warn("Last sync:        Never")

    # Check for locked files
    locked = [n for n, i in reg.get("files", {}).items() if i.get("locked")]
    if locked:
        warn(f"Locked files:     {len(locked)}")
        for f in locked:
            print(f"    {c(f, 'red')}")

    # Alerts
    alerts_path = base / "alerts.json"
    if alerts_path.exists():
        alerts = json.loads(alerts_path.read_text())
        red = [a for a in alerts if isinstance(a, dict) and a.get("level") == "RED"]
        if red:
            err(f"RED alerts:       {len(red)}")
        else:
            ok("No RED alerts")


def cmd_check(args):
    """Check for stale files and bracket placeholders."""
    base = get_base()
    heading("Running Checks")

    from ciphergy.sync.manager import SyncManager
    from ciphergy.version_control.tracker import VersionTracker

    mgr = SyncManager(base_dir=base)
    tracker = VersionTracker(base_dir=base)

    stale = mgr.check_stale()
    if stale:
        warn(f"Stale files: {len(stale)}")
        for s in stale:
            delta = s.get("delta_seconds", 0)
            print(f"    {c(s['path'], 'yellow')} ({delta:.0f}s since sync)")
    else:
        ok("No stale files")

    brackets = tracker.get_brackets()
    if brackets:
        warn(f"Files with unfilled brackets: {len(brackets)}")
        for b in brackets:
            print(f"    {c(b['file'], 'yellow')}: {b['count']} brackets ({', '.join(b['brackets'][:5])})")
    else:
        ok("No unfilled brackets found")


def cmd_sync(args):
    """Show sync status."""
    base = get_base()
    heading("Sync Status")

    from ciphergy.sync.manager import SyncManager
    mgr = SyncManager(base_dir=base)

    manifest = mgr.get_manifest()
    info(f"Version:    {c('v' + str(manifest['version']), 'blue')}")
    info(f"Monitored:  {manifest['monitored_count']} files")
    info(f"Stale:      {c(str(manifest['stale_count']), 'yellow' if manifest['stale_count'] else 'green')}")

    if manifest["last_sync"]:
        ago = (time.time() - manifest["last_sync"]) / 3600
        info(f"Last sync:  {ago:.1f} hours ago")
    else:
        warn("Last sync:  Never")

    history = mgr.get_history()
    if history:
        info(f"Version history: {len(history)} snapshots")
        for h in history[-5:]:
            print(f"    {c(h['version'], 'cyan')}: {len(h['files'])} files")


def cmd_push(args):
    """Create a sync delta and push."""
    base = get_base()
    heading("Creating Sync Delta")

    from ciphergy.sync.manager import SyncManager
    mgr = SyncManager(base_dir=base)

    trigger = args.trigger if hasattr(args, "trigger") and args.trigger else "cli-push"
    path = mgr.create_delta(trigger=trigger)
    ok(f"Delta created at: {c(str(path), 'cyan')}")

    if not args.no_mark:
        mgr.mark_synced()
        ok("Marked as synced")


def cmd_cascade(args):
    """Trigger a cascade pipeline."""
    base = get_base()
    heading("Running Cascade")

    from ciphergy.version_control.cascade import CascadeEngine
    engine = CascadeEngine(base_dir=base)

    trigger = args.trigger if hasattr(args, "trigger") and args.trigger else "cli-cascade"
    result = asyncio.run(engine.execute(trigger=trigger))

    status_color = "green" if result["status"] == "complete" else "yellow"
    info(f"Status:   {c(result['status'], status_color)}")
    info(f"Duration: {result.get('duration_s', 0):.3f}s")
    info(f"Steps:")

    for step, detail in result.get("steps", {}).items():
        icon = c("[OK]", "green") if detail["status"] == "ok" else c("[!!]", "yellow")
        print(f"    {icon} {step}")


def cmd_serve(args):
    """Start the API server."""
    heading("Starting Ciphergy API Server")
    host = args.host if hasattr(args, "host") else "0.0.0.0"
    port = args.port if hasattr(args, "port") else 8000
    info(f"Listening on {host}:{port}")

    from ciphergy.api.server import serve
    serve(host=host, port=port)


def cmd_dashboard(args):
    """Start the dashboard."""
    heading("Starting Ciphergy Dashboard")
    host = args.host if hasattr(args, "host") else "0.0.0.0"
    port = args.port if hasattr(args, "port") else 5050
    info(f"Dashboard at http://{host}:{port}")

    from ciphergy.dashboard.app import serve
    serve(host=host, port=port, debug=args.debug if hasattr(args, "debug") else False)


def cmd_onboard(args):
    """Run onboarding for a project directory."""
    base = get_base()
    heading("Onboarding Project")

    project_path = args.path if hasattr(args, "path") and args.path else str(base)
    info(f"Scanning: {project_path}")

    from ciphergy.version_control.tracker import VersionTracker
    tracker = VersionTracker(base_dir=base)

    project = Path(project_path)
    count = 0
    for f in project.rglob("*"):
        if f.is_file() and not any(p in str(f) for p in [".git", "__pycache__", ".pyc", "node_modules", "versions/"]):
            rel = str(f.relative_to(base)) if str(f).startswith(str(base)) else str(f)
            tracker.register_file(rel, file_type=f.suffix.lstrip(".") or "unknown")
            count += 1

    ok(f"Registered {count} files")
    brackets = tracker.get_brackets()
    if brackets:
        warn(f"Found {len(brackets)} files with unfilled brackets")


def cmd_agents(args):
    """List or manage agents."""
    base = get_base()
    reg = load_registry(base)
    agents = reg.get("agents", {})

    heading("Active Agents")
    if not agents:
        info("No active agents")
        return

    for aid, agent in agents.items():
        status_color = "green" if agent.get("status") == "running" else "dim"
        print(f"  {c(aid, 'cyan')}  {agent.get('name', '?')}  "
              f"role={agent.get('role', '?')}  "
              f"status={c(agent.get('status', '?'), status_color)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="ciphergy",
        description="Ciphergy Pipeline - Multi-model AI debate consensus engine",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # init
    sub.add_parser("init", help="Initialize a new Ciphergy project")

    # status
    sub.add_parser("status", help="Show system status")

    # check
    sub.add_parser("check", help="Run stale/bracket checks")

    # sync
    sub.add_parser("sync", help="Show sync status")

    # push
    p_push = sub.add_parser("push", help="Create sync delta and push")
    p_push.add_argument("--trigger", default="cli-push", help="Trigger label")
    p_push.add_argument("--no-mark", action="store_true", help="Skip marking as synced")

    # cascade
    p_cascade = sub.add_parser("cascade", help="Trigger a cascade pipeline")
    p_cascade.add_argument("--trigger", default="cli-cascade", help="Trigger label")

    # serve
    p_serve = sub.add_parser("serve", help="Start the API server")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=8000)

    # dashboard
    p_dash = sub.add_parser("dashboard", help="Start the dashboard")
    p_dash.add_argument("--host", default="0.0.0.0")
    p_dash.add_argument("--port", type=int, default=5050)
    p_dash.add_argument("--debug", action="store_true")

    # onboard
    p_onboard = sub.add_parser("onboard", help="Onboard a project directory")
    p_onboard.add_argument("--path", help="Project directory to scan")

    # agents
    sub.add_parser("agents", help="List active agents")

    args = parser.parse_args()

    commands = {
        "init": cmd_init,
        "status": cmd_status,
        "check": cmd_check,
        "sync": cmd_sync,
        "push": cmd_push,
        "cascade": cmd_cascade,
        "serve": cmd_serve,
        "dashboard": cmd_dashboard,
        "onboard": cmd_onboard,
        "agents": cmd_agents,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
