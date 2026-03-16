#!/usr/bin/env python3
"""
CIPHERGY AGENT COMMUNICATION — Inter-Agent Bus
Agent Local ↔ Agent Cloud via Asana

Usage:
    python3 scripts/agent_comm.py read             — Read from Agent Cloud (auto-decrypts)
    python3 scripts/agent_comm.py write "msg"       — Write to Agent Local's task (auto-encrypts if key exists)
    python3 scripts/agent_comm.py write --plain "m" — Write plaintext (skip encryption)
    python3 scripts/agent_comm.py status            — Show channel status
"""

import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Encryption support
def _get_vault():
    """Load CiphergyVault if key exists. Returns None if no key."""
    try:
        from crypto import CiphergyVault
        vault = CiphergyVault()
        _ = vault.key  # Test that key loads
        return vault
    except (ImportError, FileNotFoundError):
        return None

# Colors
RED = "\033[91m"
GREEN = "\033[92m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

def load_bus_config():
    """Load agent and bus config from ciphergy.yaml."""
    try:
        import yaml
        with open(BASE / "config" / "ciphergy.yaml") as f:
            config = yaml.safe_load(f)
        agents = config.get("agents", {})
        bus = config.get("bus", {})
        return {
            "local_task": agents.get("local", {}).get("asana_task_gid"),
            "cloud_task": agents.get("cloud", {}).get("asana_task_gid"),
            "pat_env_var": bus.get("pat_env_var", "ASANA_PAT"),
            "pat_source": bus.get("pat_source"),
            "local_name": agents.get("local", {}).get("name", "Agent Local"),
            "cloud_name": agents.get("cloud", {}).get("name", "Agent Cloud"),
        }
    except (ImportError, FileNotFoundError):
        return None

def get_pat(config):
    """Get Asana PAT from environment or source file."""
    pat = os.environ.get(config["pat_env_var"], "")
    if not pat and config.get("pat_source"):
        source_file = Path(config["pat_source"])
        if source_file.exists():
            with open(source_file) as f:
                for line in f:
                    if line.startswith(f"export {config['pat_env_var']}="):
                        pat = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    return pat

def curl_get(url, pat):
    """GET from Asana API."""
    result = subprocess.run(
        ["curl", "-s", "-H", f"Authorization: Bearer {pat}", url],
        capture_output=True, text=True
    )
    return json.loads(result.stdout) if result.stdout else {}

def curl_post(url, data, pat):
    """POST to Asana API."""
    result = subprocess.run(
        ["curl", "-s", "-X", "POST",
         "-H", f"Authorization: Bearer {pat}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(data), url],
        capture_output=True, text=True
    )
    return json.loads(result.stdout) if result.stdout else {}

def cmd_read():
    """Read latest messages from Agent Cloud's task."""
    config = load_bus_config()
    if not config or not config["cloud_task"]:
        print(f"{RED}[ERROR]{RESET} Agent Cloud task not configured. Run onboarding.")
        return

    pat = get_pat(config)
    if not pat:
        print(f"{RED}[ERROR]{RESET} No Asana PAT found.")
        return

    url = f"https://app.asana.com/api/1.0/tasks/{config['cloud_task']}/stories?opt_fields=text,created_at,type"
    data = curl_get(url, pat)
    comments = [s for s in data.get("data", []) if s.get("type") == "comment"]

    vault = _get_vault()

    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {config['cloud_name']} — Latest Messages{RESET}")
    if vault:
        print(f"{BOLD}{CYAN}  🔐 AES-256-GCM decryption active{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}\n")

    for c in comments[-3:]:
        text = c.get("text", "(empty)")
        # Auto-decrypt if encrypted and we have a key
        if vault and vault.is_encrypted(text):
            try:
                text = vault.decrypt(text)
                print(f"{DIM}--- {c.get('created_at', 'unknown')} [🔐 DECRYPTED] ---{RESET}")
            except ValueError:
                print(f"{DIM}--- {c.get('created_at', 'unknown')} [🔐 DECRYPT FAILED — wrong key?] ---{RESET}")
        else:
            print(f"{DIM}--- {c.get('created_at', 'unknown')} ---{RESET}")
        print(text)
        print()

def cmd_write(message, plaintext=False):
    """Post message to Agent Local's task. Auto-encrypts if key exists."""
    config = load_bus_config()
    if not config or not config["local_task"]:
        print(f"{RED}[ERROR]{RESET} Agent Local task not configured.")
        return

    pat = get_pat(config)
    if not pat:
        print(f"{RED}[ERROR]{RESET} No Asana PAT found.")
        return

    # Auto-encrypt if key exists and --plain not specified
    vault = _get_vault()
    if vault and not plaintext:
        message = vault.encrypt(message)
        print(f"{CYAN}[🔐]{RESET} Message encrypted with AES-256-GCM")

    url = f"https://app.asana.com/api/1.0/tasks/{config['local_task']}/stories"
    result = curl_post(url, {"data": {"text": message}}, pat)
    created = result.get("data", {}).get("created_at", "ERROR")
    print(f"{GREEN}[{config['local_name']}]{RESET} Posted at {created}")

def cmd_status():
    """Show comm channel status."""
    config = load_bus_config()
    if not config:
        print(f"{RED}[ERROR]{RESET} Bus not configured.")
        return

    pat = get_pat(config)
    if not pat:
        print(f"{RED}[ERROR]{RESET} No Asana PAT.")
        return

    print(f"\n{BOLD}COMM STATUS{RESET}")
    print(f"{'─'*60}")

    for role, task_key, label in [
        ("cloud", "cloud_task", "reads from"),
        ("local", "local_task", "writes to")
    ]:
        task_gid = config.get(task_key)
        name = config.get(f"{role}_name", role)
        if task_gid:
            url = f"https://app.asana.com/api/1.0/tasks/{task_gid}/stories?opt_fields=text,created_at,type"
            data = curl_get(url, pat)
            comments = [s for s in data.get("data", []) if s.get("type") == "comment"]
            if comments:
                latest = comments[-1]
                print(f"  {CYAN}{name} ({label}){RESET}: Last msg {latest.get('created_at', '?')}")
            else:
                print(f"  {CYAN}{name} ({label}){RESET}: No messages")
        else:
            print(f"  {CYAN}{name}{RESET}: Not configured")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "read":
        cmd_read()
    elif cmd == "write":
        plaintext = "--plain" in sys.argv
        args = [a for a in sys.argv[2:] if a != "--plain"]
        if args:
            cmd_write(" ".join(args), plaintext=plaintext)
        else:
            print("Usage: agent_comm.py write [--plain] 'message'")
    elif cmd == "status":
        cmd_status()
    else:
        print(__doc__)
