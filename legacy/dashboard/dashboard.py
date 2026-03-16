#!/usr/bin/env python3
"""
Ciphergy Pipeline — Web Dashboard
Simple Flask application for monitoring project status, file versions,
sync state, and alerts.

Usage:
    python dashboard/dashboard.py
    Opens at http://localhost:5050
"""

import json
import os
import sys
import hashlib
from datetime import datetime, timezone

try:
    from flask import Flask, render_template, jsonify, send_from_directory
except ImportError:
    print("[ERROR] Flask is required. Install with: pip install flask")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "ciphergy.yaml")
REGISTRY_PATH = os.path.join(PROJECT_ROOT, ".ciphergy", "registry.json")
ALERTS_PATH = os.path.join(PROJECT_ROOT, "_RED_ALERTS.md")

app = Flask(__name__, template_folder=SCRIPT_DIR, static_folder=SCRIPT_DIR)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config():
    """Load the YAML config."""
    if not os.path.isfile(CONFIG_PATH):
        return {"project": {"name": "Unconfigured", "domain": "unknown"}}
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f) or {}


def load_registry():
    """Load the JSON registry."""
    if not os.path.isfile(REGISTRY_PATH):
        return {"files": [], "agents": {}, "sync": {}, "version_history": []}
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def load_alerts():
    """Load RED ALERTS markdown."""
    if not os.path.isfile(ALERTS_PATH):
        return "No alerts file found."
    with open(ALERTS_PATH) as f:
        return f.read()


def compute_sync_state(registry):
    """Compute per-file sync state."""
    synced_hashes = registry.get("sync", {}).get("synced_hashes", {})
    states = []

    for entry in registry.get("files", []):
        fpath = entry.get("path", "")
        full_path = os.path.join(PROJECT_ROOT, fpath)
        current_hash = ""
        exists = os.path.isfile(full_path)

        if exists:
            try:
                with open(full_path, "rb") as fh:
                    current_hash = hashlib.md5(fh.read()).hexdigest()
            except (IOError, OSError):
                pass

        if not exists:
            state = "missing"
        elif fpath in synced_hashes and synced_hashes[fpath] == current_hash:
            state = "synced"
        elif fpath in synced_hashes:
            state = "stale"
        else:
            state = "new"

        states.append({
            "path": fpath,
            "state": state,
            "hash": current_hash[:12] if current_hash else "---",
            "category": entry.get("category", "other"),
        })

    return states


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the main dashboard page."""
    return send_from_directory(SCRIPT_DIR, "index.html")


@app.route("/api/status")
def api_status():
    """Return full project status as JSON."""
    config = load_config()
    registry = load_registry()
    alerts_content = load_alerts()
    sync_states = compute_sync_state(registry)

    # Count sync states
    state_counts = {"synced": 0, "stale": 0, "new": 0, "missing": 0}
    for s in sync_states:
        state_counts[s["state"]] = state_counts.get(s["state"], 0) + 1

    return jsonify({
        "project": config.get("project", {}),
        "agents": registry.get("agents", {}),
        "files": sync_states,
        "file_count": len(registry.get("files", [])),
        "sync": {
            "current_version": registry.get("sync", {}).get("current_version", "v0"),
            "last_synced": registry.get("sync", {}).get("last_synced", "never"),
            "counts": state_counts,
        },
        "version_history": registry.get("version_history", [])[-10:],
        "cascade_log": registry.get("cascade_log", [])[-10:],
        "alerts": alerts_content,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    config = load_config()
    port = config.get("dashboard", {}).get("port", 5050)

    print(f"\n  Ciphergy Dashboard")
    print(f"  Project: {config.get('project', {}).get('name', 'Unknown')}")
    print(f"  URL: http://localhost:{port}")
    print(f"  Press Ctrl+C to stop.\n")

    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
