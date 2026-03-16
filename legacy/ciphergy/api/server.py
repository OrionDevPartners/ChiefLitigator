"""
Ciphergy Pipeline - FastAPI Server
Main API server for the Ciphergy multi-model debate consensus engine.
"""

import json
import os
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Security, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(os.environ.get("CIPHERGY_BASE", Path.cwd()))
REGISTRY_PATH = BASE_DIR / "registry.json"
CONFIG_PATH = BASE_DIR / "config.json"
ALERTS_PATH = BASE_DIR / "alerts.json"
API_KEY = os.environ.get("CIPHERGY_API_KEY", "")

app = FastAPI(
    title="Ciphergy Pipeline API",
    version="1.0.0",
    description="Multi-model AI debate consensus engine API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(key: Optional[str] = Security(api_key_header)):
    """Verify the API key if one is configured."""
    if API_KEY and key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return key


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path, default=None):
    if default is None:
        default = {}
    if path.exists():
        return json.loads(path.read_text())
    return default


def _save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))


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


def _save_registry(reg):
    _save_json(REGISTRY_PATH, reg)


# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------

_agents: dict = {}
_onboard_jobs: dict = {}

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class SpawnRequest(BaseModel):
    name: str
    role: str = "general"
    config: dict = {}


class CascadeRequest(BaseModel):
    trigger: str
    context: dict = {}


class SyncMarkRequest(BaseModel):
    note: str = ""


class OnboardRequest(BaseModel):
    project_path: str
    options: dict = {}


class ConnectorConnectRequest(BaseModel):
    config: dict = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "ts": time.time(), "version": "1.0.0"}


@app.get("/status", dependencies=[Depends(verify_api_key)])
async def status():
    reg = _load_registry()
    return {
        "registry_version": reg.get("version", 0),
        "file_count": len(reg.get("files", {})),
        "agent_count": len(_agents),
        "sync_state": {
            "last_sync": reg.get("last_sync"),
            "monitored": len(reg.get("monitored_files", [])),
        },
        "ts": time.time(),
    }


# -- Agents -----------------------------------------------------------------

@app.get("/agents", dependencies=[Depends(verify_api_key)])
async def list_agents():
    return {"agents": list(_agents.values()), "count": len(_agents)}


@app.post("/agents/spawn", dependencies=[Depends(verify_api_key)])
async def spawn_agent(req: SpawnRequest):
    agent_id = str(uuid.uuid4())[:8]
    agent = {
        "id": agent_id,
        "name": req.name,
        "role": req.role,
        "config": req.config,
        "status": "running",
        "spawned_at": time.time(),
    }
    _agents[agent_id] = agent
    reg = _load_registry()
    reg.setdefault("agents", {})[agent_id] = agent
    _save_registry(reg)
    return {"agent": agent}


@app.get("/agents/{agent_id}", dependencies=[Depends(verify_api_key)])
async def get_agent(agent_id: str):
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent": _agents[agent_id]}


@app.delete("/agents/{agent_id}", dependencies=[Depends(verify_api_key)])
async def kill_agent(agent_id: str):
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = _agents.pop(agent_id)
    agent["status"] = "killed"
    agent["killed_at"] = time.time()
    reg = _load_registry()
    reg.get("agents", {}).pop(agent_id, None)
    _save_registry(reg)
    return {"agent": agent}


# -- Registry ---------------------------------------------------------------

@app.get("/registry", dependencies=[Depends(verify_api_key)])
async def get_registry():
    return _load_registry()


@app.get("/registry/{file_name}", dependencies=[Depends(verify_api_key)])
async def get_registry_file(file_name: str):
    reg = _load_registry()
    files = reg.get("files", {})
    if file_name not in files:
        raise HTTPException(status_code=404, detail="File not in registry")
    return {"file": file_name, "info": files[file_name]}


# -- Cascade ----------------------------------------------------------------

@app.post("/cascade", dependencies=[Depends(verify_api_key)])
async def trigger_cascade(req: CascadeRequest):
    from ciphergy.version_control.cascade import CascadeEngine
    engine = CascadeEngine(base_dir=BASE_DIR)
    result = await engine.execute(trigger=req.trigger, context=req.context)
    return {"cascade": result}


# -- Sync -------------------------------------------------------------------

@app.get("/sync", dependencies=[Depends(verify_api_key)])
async def sync_status():
    from ciphergy.sync.manager import SyncManager
    mgr = SyncManager(base_dir=BASE_DIR)
    stale = mgr.check_stale()
    manifest = mgr.get_manifest()
    return {
        "stale_files": stale,
        "manifest": manifest,
        "last_sync": _load_registry().get("last_sync"),
    }


@app.post("/sync/push", dependencies=[Depends(verify_api_key)])
async def sync_push():
    from ciphergy.sync.manager import SyncManager
    mgr = SyncManager(base_dir=BASE_DIR)
    path = mgr.create_delta(trigger="api-push")
    return {"delta_path": str(path)}


@app.post("/sync/mark", dependencies=[Depends(verify_api_key)])
async def sync_mark(req: SyncMarkRequest):
    from ciphergy.sync.manager import SyncManager
    mgr = SyncManager(base_dir=BASE_DIR)
    mgr.mark_synced()
    return {"synced": True, "ts": time.time(), "note": req.note}


# -- Alerts -----------------------------------------------------------------

@app.get("/alerts", dependencies=[Depends(verify_api_key)])
async def get_alerts():
    alerts = _load_json(ALERTS_PATH, [])
    red = [a for a in alerts if a.get("level") == "RED"] if isinstance(alerts, list) else []
    return {"alerts": red, "count": len(red)}


# -- Connectors -------------------------------------------------------------

@app.get("/connectors", dependencies=[Depends(verify_api_key)])
async def list_connectors():
    reg = _load_registry()
    return {"connectors": reg.get("connectors", {})}


@app.post("/connectors/{name}/connect", dependencies=[Depends(verify_api_key)])
async def connect_connector(name: str, req: ConnectorConnectRequest):
    reg = _load_registry()
    connectors = reg.setdefault("connectors", {})
    connectors[name] = {
        "name": name,
        "status": "connected",
        "config": req.config,
        "connected_at": time.time(),
    }
    _save_registry(reg)
    return {"connector": connectors[name]}


# -- Onboarding -------------------------------------------------------------

@app.post("/onboard", dependencies=[Depends(verify_api_key)])
async def start_onboard(req: OnboardRequest):
    job_id = str(uuid.uuid4())[:12]
    _onboard_jobs[job_id] = {
        "job_id": job_id,
        "project_path": req.project_path,
        "options": req.options,
        "status": "running",
        "started_at": time.time(),
        "steps_completed": [],
    }
    # Simulate async onboarding steps
    steps = ["scan_files", "build_registry", "detect_brackets", "score_files", "generate_config"]
    for step in steps:
        _onboard_jobs[job_id]["steps_completed"].append(step)
    _onboard_jobs[job_id]["status"] = "complete"
    _onboard_jobs[job_id]["completed_at"] = time.time()
    return {"job_id": job_id, "status": "running"}


@app.get("/onboard/{job_id}", dependencies=[Depends(verify_api_key)])
async def onboard_status(job_id: str):
    if job_id not in _onboard_jobs:
        raise HTTPException(status_code=404, detail="Onboarding job not found")
    return _onboard_jobs[job_id]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def serve(host: str = "0.0.0.0", port: int = 8000):
    """Start the API server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    serve()
