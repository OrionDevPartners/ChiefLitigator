"""
Ciphergy Pipeline - Flask Dashboard
Production dashboard with WebSocket real-time updates.
"""

import json
import os
import time
from pathlib import Path

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(os.environ.get("CIPHERGY_BASE", Path.cwd()))
REGISTRY_PATH = BASE_DIR / "registry.json"
CONFIG_PATH = BASE_DIR / "config.json"
ALERTS_PATH = BASE_DIR / "alerts.json"

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)
app.config["SECRET_KEY"] = os.environ.get("CIPHERGY_SECRET", "ciphergy-dashboard-secret")

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path, default=None):
    if default is None:
        default = {}
    if path.exists():
        return json.loads(path.read_text())
    return default


def _load_registry():
    return _load_json(REGISTRY_PATH, {
        "version": 1,
        "files": {},
        "monitored_files": [],
        "last_sync": None,
        "agents": {},
        "connectors": {},
        "audit_log": [],
    })


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    reg = _load_registry()
    return jsonify({
        "registry_version": reg.get("version", 0),
        "file_count": len(reg.get("files", {})),
        "agent_count": len(reg.get("agents", {})),
        "connector_count": len(reg.get("connectors", {})),
        "last_sync": reg.get("last_sync"),
        "monitored_count": len(reg.get("monitored_files", [])),
        "ts": time.time(),
    })


@app.route("/api/files")
def api_files():
    reg = _load_registry()
    return jsonify({"files": reg.get("files", {})})


@app.route("/api/agents")
def api_agents():
    reg = _load_registry()
    return jsonify({"agents": reg.get("agents", {})})


@app.route("/api/alerts")
def api_alerts():
    alerts = _load_json(ALERTS_PATH, [])
    red = [a for a in alerts if a.get("level") == "RED"] if isinstance(alerts, list) else []
    return jsonify({"alerts": red, "count": len(red)})


@app.route("/api/connectors")
def api_connectors():
    reg = _load_registry()
    return jsonify({"connectors": reg.get("connectors", {})})


@app.route("/api/audit")
def api_audit():
    reg = _load_registry()
    return jsonify({"audit_log": reg.get("audit_log", [])[-50:]})


@app.route("/api/sync")
def api_sync():
    reg = _load_registry()
    return jsonify({
        "last_sync": reg.get("last_sync"),
        "monitored_files": reg.get("monitored_files", []),
        "version": reg.get("version", 0),
    })


# ---------------------------------------------------------------------------
# WebSocket events
# ---------------------------------------------------------------------------


@socketio.on("connect")
def handle_connect():
    reg = _load_registry()
    socketio.emit("status_update", {
        "registry_version": reg.get("version", 0),
        "file_count": len(reg.get("files", {})),
        "agent_count": len(reg.get("agents", {})),
        "ts": time.time(),
    })


@socketio.on("request_update")
def handle_request_update():
    reg = _load_registry()
    socketio.emit("status_update", {
        "registry_version": reg.get("version", 0),
        "file_count": len(reg.get("files", {})),
        "agent_count": len(reg.get("agents", {})),
        "ts": time.time(),
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def serve(host: str = "0.0.0.0", port: int = 5050, debug: bool = False):
    """Start the dashboard server."""
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    serve(debug=True)
