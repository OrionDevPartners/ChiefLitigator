#!/usr/bin/env bash
###############################################################################
# Ciphergy Pipeline CLI
# Domain-agnostic dual-environment AI orchestration tool
# Usage: ciphergy.sh <command> [options]
###############################################################################

set -euo pipefail

# --- Colors ----------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# --- Globals ---------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="$PROJECT_ROOT/config/ciphergy.yaml"
REGISTRY_FILE="$PROJECT_ROOT/.ciphergy/registry.json"
SYNC_DIR="$PROJECT_ROOT/sync"

# --- Helpers ---------------------------------------------------------------
log_info()    { echo -e "${CYAN}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*"; }
log_header()  { echo -e "\n${BOLD}${CYAN}=== $* ===${NC}\n"; }

require_config() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Config not found: $CONFIG_FILE"
        log_warn "Run 'ciphergy.sh init' to create a new project, or copy config/ciphergy.yaml.example"
        exit 1
    fi
}

require_registry() {
    if [[ ! -f "$REGISTRY_FILE" ]]; then
        log_error "Registry not found: $REGISTRY_FILE"
        log_warn "Run 'ciphergy.sh init' to initialize the project registry."
        exit 1
    fi
}

# Read a YAML value using python3 + pyyaml
yaml_get() {
    local key="$1"
    python3 -c "
import yaml, sys
try:
    with open('$CONFIG_FILE') as f:
        cfg = yaml.safe_load(f)
    keys = '$key'.split('.')
    val = cfg
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            val = None
            break
    if val is not None:
        print(val)
    else:
        sys.exit(1)
except Exception as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)
" 2>/dev/null
}

# Read registry value using python3
registry_get() {
    local key="$1"
    python3 -c "
import json, sys
try:
    with open('$REGISTRY_FILE') as f:
        reg = json.load(f)
    keys = '$key'.split('.')
    val = reg
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        elif isinstance(val, list):
            val = val[int(k)] if k.isdigit() and int(k) < len(val) else None
        else:
            val = None
            break
    if val is not None:
        if isinstance(val, (dict, list)):
            print(json.dumps(val, indent=2))
        else:
            print(val)
    else:
        sys.exit(1)
except Exception as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)
" 2>/dev/null
}

# Get list of monitored files from registry
get_monitored_files() {
    python3 -c "
import json
with open('$REGISTRY_FILE') as f:
    reg = json.load(f)
for entry in reg.get('files', []):
    print(entry.get('path', ''))
" 2>/dev/null
}

# --- Commands ---------------------------------------------------------------

cmd_status() {
    require_config
    require_registry

    local project_name
    project_name=$(yaml_get "project.name" || echo "Unknown")
    local domain
    domain=$(yaml_get "project.domain" || echo "Unknown")

    log_header "Ciphergy Pipeline Status"
    echo -e "  ${BOLD}Project:${NC}  $project_name"
    echo -e "  ${BOLD}Domain:${NC}   $domain"
    echo -e "  ${BOLD}Root:${NC}     $PROJECT_ROOT"
    echo ""

    # File counts
    local total_files=0
    local missing_files=0
    local stale_files=0
    while IFS= read -r fpath; do
        [[ -z "$fpath" ]] && continue
        total_files=$((total_files + 1))
        local full_path="$PROJECT_ROOT/$fpath"
        if [[ ! -f "$full_path" ]]; then
            missing_files=$((missing_files + 1))
        fi
    done < <(get_monitored_files)

    echo -e "  ${BOLD}Tracked files:${NC}  $total_files"
    if [[ $missing_files -gt 0 ]]; then
        echo -e "  ${RED}Missing files:${NC}  $missing_files"
    else
        echo -e "  ${GREEN}Missing files:${NC}  0"
    fi

    # Sync state
    local current_version
    current_version=$(registry_get "sync.current_version" || echo "unknown")
    local last_sync
    last_sync=$(registry_get "sync.last_synced" || echo "never")

    echo ""
    echo -e "  ${BOLD}Sync version:${NC}   $current_version"
    echo -e "  ${BOLD}Last synced:${NC}    $last_sync"

    # Agent status
    echo ""
    echo -e "  ${BOLD}Agent Status:${NC}"
    local agent_count
    agent_count=$(python3 -c "
import json
with open('$REGISTRY_FILE') as f:
    reg = json.load(f)
agents = reg.get('agents', {})
for name, info in agents.items():
    status = info.get('status', 'unknown')
    color = '\\033[0;32m' if status == 'active' else '\\033[1;33m' if status == 'idle' else '\\033[0;31m'
    print(f'    {color}{name}: {status}\\033[0m')
" 2>/dev/null || echo "    No agents configured")
    echo -e "$agent_count"

    echo ""
    log_success "Status check complete."
}

cmd_check() {
    require_config
    require_registry

    log_header "Integrity Check"

    local errors=0

    # Check all monitored files exist
    while IFS= read -r fpath; do
        [[ -z "$fpath" ]] && continue
        local full_path="$PROJECT_ROOT/$fpath"
        if [[ -f "$full_path" ]]; then
            echo -e "  ${GREEN}[FOUND]${NC} $fpath"
        else
            echo -e "  ${RED}[MISS]${NC}  $fpath"
            errors=$((errors + 1))
        fi
    done < <(get_monitored_files)

    # Check config integrity
    echo ""
    if python3 -c "import yaml; yaml.safe_load(open('$CONFIG_FILE'))" 2>/dev/null; then
        echo -e "  ${GREEN}[OK]${NC} Config YAML is valid"
    else
        echo -e "  ${RED}[FAIL]${NC} Config YAML is invalid"
        errors=$((errors + 1))
    fi

    # Check registry integrity
    if python3 -c "import json; json.load(open('$REGISTRY_FILE'))" 2>/dev/null; then
        echo -e "  ${GREEN}[OK]${NC} Registry JSON is valid"
    else
        echo -e "  ${RED}[FAIL]${NC} Registry JSON is invalid"
        errors=$((errors + 1))
    fi

    # Check hash consistency
    echo ""
    log_info "Verifying file hashes..."
    local hash_mismatches=0
    python3 -c "
import json, hashlib, os

with open('$REGISTRY_FILE') as f:
    reg = json.load(f)

for entry in reg.get('files', []):
    fpath = entry.get('path', '')
    stored_hash = entry.get('hash', '')
    full_path = os.path.join('$PROJECT_ROOT', fpath)
    if not os.path.isfile(full_path):
        continue
    with open(full_path, 'rb') as fh:
        current_hash = hashlib.md5(fh.read()).hexdigest()
    if stored_hash and stored_hash != current_hash:
        print(f'  \033[1;33m[STALE]\033[0m {fpath} (hash changed)')
    elif stored_hash:
        print(f'  \033[0;32m[MATCH]\033[0m {fpath}')
    else:
        print(f'  \033[0;36m[NEW]\033[0m   {fpath} (no stored hash)')
" 2>/dev/null

    echo ""
    if [[ $errors -eq 0 ]]; then
        log_success "Integrity check passed. No critical issues."
    else
        log_error "Integrity check found $errors issue(s)."
        exit 1
    fi
}

cmd_hash() {
    require_config
    require_registry

    log_header "Computing File Hashes"

    python3 -c "
import json, hashlib, os

with open('$REGISTRY_FILE') as f:
    reg = json.load(f)

updated = 0
for entry in reg.get('files', []):
    fpath = entry.get('path', '')
    full_path = os.path.join('$PROJECT_ROOT', fpath)
    if os.path.isfile(full_path):
        with open(full_path, 'rb') as fh:
            new_hash = hashlib.md5(fh.read()).hexdigest()
        old_hash = entry.get('hash', '')
        entry['hash'] = new_hash
        status = 'updated' if old_hash and old_hash != new_hash else 'computed' if not old_hash else 'unchanged'
        color = '\033[1;33m' if status == 'updated' else '\033[0;36m' if status == 'computed' else '\033[0;32m'
        print(f'  {color}[{status.upper():>9}]\033[0m {fpath}: {new_hash}')
        if status != 'unchanged':
            updated += 1
    else:
        print(f'  \033[0;31m[MISSING]\033[0m   {fpath}')

with open('$REGISTRY_FILE', 'w') as f:
    json.dump(reg, f, indent=2)

print(f'\n  Hashes updated: {updated}')
" 2>/dev/null

    log_success "Hash computation complete. Registry updated."
}

cmd_sync_check() {
    require_config
    require_registry

    log_header "Sync Check: Repo vs Cloud Agent Knowledge"

    python3 -c "
import json, hashlib, os

with open('$REGISTRY_FILE') as f:
    reg = json.load(f)

sync_info = reg.get('sync', {})
synced_version = sync_info.get('current_version', 'v0')
synced_hashes = sync_info.get('synced_hashes', {})

stale = []
new_files = []
in_sync = []

for entry in reg.get('files', []):
    fpath = entry.get('path', '')
    full_path = os.path.join('$PROJECT_ROOT', fpath)
    if not os.path.isfile(full_path):
        continue
    with open(full_path, 'rb') as fh:
        current_hash = hashlib.md5(fh.read()).hexdigest()
    if fpath in synced_hashes:
        if synced_hashes[fpath] == current_hash:
            in_sync.append(fpath)
        else:
            stale.append(fpath)
    else:
        new_files.append(fpath)

for f in in_sync:
    print(f'  \033[0;32m[SYNCED]\033[0m  {f}')
for f in stale:
    print(f'  \033[1;33m[STALE]\033[0m   {f}')
for f in new_files:
    print(f'  \033[0;36m[NEW]\033[0m     {f}')

print(f'\n  In sync: {len(in_sync)} | Stale: {len(stale)} | New: {len(new_files)}')

if stale or new_files:
    print(f'\n  \033[1;33mAction required:\033[0m Run \"ciphergy.sh project-push\" to create a delta version.')
else:
    print(f'\n  \033[0;32mAll files in sync with cloud agent.\033[0m')
" 2>/dev/null
}

cmd_mark_synced() {
    require_config
    require_registry

    log_header "Marking Current State as Synced"

    python3 -c "
import json, hashlib, os
from datetime import datetime

with open('$REGISTRY_FILE') as f:
    reg = json.load(f)

synced_hashes = {}
for entry in reg.get('files', []):
    fpath = entry.get('path', '')
    full_path = os.path.join('$PROJECT_ROOT', fpath)
    if os.path.isfile(full_path):
        with open(full_path, 'rb') as fh:
            synced_hashes[fpath] = hashlib.md5(fh.read()).hexdigest()

reg.setdefault('sync', {})
reg['sync']['synced_hashes'] = synced_hashes
reg['sync']['last_synced'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

with open('$REGISTRY_FILE', 'w') as f:
    json.dump(reg, f, indent=2)

print(f'  Marked {len(synced_hashes)} files as synced.')
print(f'  Timestamp: {reg[\"sync\"][\"last_synced\"]}')
" 2>/dev/null

    log_success "Sync state recorded. Cloud agent is now considered up to date."
}

cmd_project_status() {
    require_config
    require_registry

    log_header "Project Sync Status"

    # Show sync folder contents
    if [[ -d "$SYNC_DIR" ]]; then
        echo -e "  ${BOLD}Sync folder:${NC} $SYNC_DIR"
        echo ""
        local versions
        versions=$(ls -d "$SYNC_DIR"/v*/ 2>/dev/null | sort -V || true)
        if [[ -n "$versions" ]]; then
            for vdir in $versions; do
                local vname
                vname=$(basename "$vdir")
                local fcount
                fcount=$(find "$vdir" -type f 2>/dev/null | wc -l | tr -d ' ')
                echo -e "    ${CYAN}$vname${NC} — $fcount file(s)"
            done
        else
            echo -e "    ${YELLOW}No version folders found.${NC}"
        fi
    else
        echo -e "  ${RED}Sync folder not found.${NC}"
    fi

    # Show version history from registry
    echo ""
    echo -e "  ${BOLD}Version History:${NC}"
    python3 -c "
import json

with open('$REGISTRY_FILE') as f:
    reg = json.load(f)

history = reg.get('version_history', [])
if not history:
    print('    No version history recorded.')
else:
    for entry in history[-10:]:
        v = entry.get('version', '?')
        date = entry.get('date', '?')
        trigger = entry.get('trigger', '?')
        files_changed = entry.get('files_changed', 0)
        print(f'    {v} | {date} | {trigger} | {files_changed} file(s)')
" 2>/dev/null

    echo ""
    log_success "Project status displayed."
}

cmd_project_push() {
    require_config
    require_registry

    log_header "Creating Delta Version"

    python3 -c "
import json, hashlib, os, shutil
from datetime import datetime

with open('$REGISTRY_FILE') as f:
    reg = json.load(f)

sync_info = reg.get('sync', {})
synced_hashes = sync_info.get('synced_hashes', {})

# Find stale and new files
delta_files = []
for entry in reg.get('files', []):
    fpath = entry.get('path', '')
    full_path = os.path.join('$PROJECT_ROOT', fpath)
    if not os.path.isfile(full_path):
        continue
    with open(full_path, 'rb') as fh:
        current_hash = hashlib.md5(fh.read()).hexdigest()
    if fpath not in synced_hashes or synced_hashes[fpath] != current_hash:
        delta_files.append((fpath, full_path))

if not delta_files:
    print('  \033[0;32mNo changes detected. Nothing to push.\033[0m')
    exit(0)

# Determine next version
history = reg.get('version_history', [])
next_num = len(history) + 1
next_version = f'v{next_num}'

# Create version folder
version_dir = os.path.join('$SYNC_DIR', next_version)
os.makedirs(version_dir, exist_ok=True)

for fpath, full_path in delta_files:
    dest = os.path.join(version_dir, os.path.basename(fpath))
    shutil.copy2(full_path, dest)
    print(f'  \033[0;36m[COPIED]\033[0m {fpath} -> {next_version}/')

# Update registry
reg.setdefault('version_history', [])
reg['version_history'].append({
    'version': next_version,
    'date': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    'trigger': 'manual-push',
    'files_changed': len(delta_files),
    'files': [f[0] for f in delta_files]
})
reg['sync']['current_version'] = next_version

with open('$REGISTRY_FILE', 'w') as f:
    json.dump(reg, f, indent=2)

print(f'\n  Created {next_version} with {len(delta_files)} file(s).')
print(f'  Upload \"{version_dir}\" to your cloud agent project.')
" 2>/dev/null

    log_success "Delta version created. Upload the folder to your cloud agent."
}

cmd_cascade() {
    local trigger="${1:-}"
    if [[ -z "$trigger" ]]; then
        log_error "Usage: ciphergy.sh cascade <trigger>"
        log_info "Triggers: new-evidence, answered, phase-change, deadline, correction, escalation"
        exit 1
    fi

    require_config
    require_registry

    log_header "Cascade: $trigger"

    # Delegate to cascade.py
    if [[ -f "$SCRIPT_DIR/cascade.py" ]]; then
        python3 "$SCRIPT_DIR/cascade.py" --trigger "$trigger" --project-root "$PROJECT_ROOT"
    else
        log_error "cascade.py not found at $SCRIPT_DIR/cascade.py"
        exit 1
    fi
}

cmd_init() {
    log_header "Ciphergy Project Initialization"

    local name=""
    local domain="custom"

    # Parse arguments
    shift || true
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --name) name="$2"; shift 2 ;;
            --domain) domain="$2"; shift 2 ;;
            *) shift ;;
        esac
    done

    if [[ -z "$name" ]]; then
        echo -n "  Project name: "
        read -r name
    fi

    if [[ -z "$name" ]]; then
        log_error "Project name is required."
        exit 1
    fi

    # Delegate to ciphergy_init.py
    if [[ -f "$SCRIPT_DIR/ciphergy_init.py" ]]; then
        python3 "$SCRIPT_DIR/ciphergy_init.py" --name "$name" --domain "$domain" --project-root "$PROJECT_ROOT"
    else
        log_error "ciphergy_init.py not found at $SCRIPT_DIR/ciphergy_init.py"
        exit 1
    fi
}

cmd_help() {
    echo -e "${BOLD}${CYAN}"
    echo "  ____             _    _    ___   ____  _            _ _            "
    echo " |  _ \\ _   _  ___| |  / \\  |_ _| |  _ \\(_)_ __   ___| (_)_ __   ___ "
    echo " | | | | | | |/ _ \\ | / _ \\  | |  | |_) | | '_ \\ / _ \\ | | '_ \\ / _ \\"
    echo " | |_| | |_| |  __/ |/ ___ \\ | |  |  __/| | |_) |  __/ | | | | |  __/"
    echo " |____/ \\__,_|\\___|_/_/   \\_\\___| |_|   |_| .__/ \\___|_|_|_| |_|\\___|"
    echo "                                           |_|"
    echo -e "${NC}"
    echo -e "${BOLD}Usage:${NC} ciphergy.sh <command> [options]"
    echo ""
    echo -e "${BOLD}Commands:${NC}"
    echo -e "  ${CYAN}status${NC}          Show project state (agents, files, sync)"
    echo -e "  ${CYAN}check${NC}           Verify integrity (files present, hashes, refs)"
    echo -e "  ${CYAN}hash${NC}            Compute MD5 hashes for all tracked files"
    echo -e "  ${CYAN}sync-check${NC}      Compare repo state vs cloud agent knowledge"
    echo -e "  ${CYAN}mark-synced${NC}     Record that human uploaded to cloud"
    echo -e "  ${CYAN}project-status${NC}  Show sync folder state + version history"
    echo -e "  ${CYAN}project-push${NC}    Create delta version folder with stale files"
    echo -e "  ${CYAN}cascade${NC} <trigger>  Run a cascade (new-evidence, answered, etc.)"
    echo -e "  ${CYAN}init${NC}            Initialize a new project"
    echo -e "  ${CYAN}help${NC}            Show this help message"
    echo ""
    echo -e "${BOLD}Cascade Triggers:${NC}"
    echo -e "  new-evidence    New data or documents added"
    echo -e "  answered        A question has been answered"
    echo -e "  phase-change    Project phase transition"
    echo -e "  deadline        Deadline approaching or reached"
    echo -e "  correction      Error correction in existing data"
    echo -e "  escalation      Priority escalation"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  ciphergy.sh init --name \"My Project\" --domain legal"
    echo "  ciphergy.sh status"
    echo "  ciphergy.sh cascade new-evidence"
    echo "  ciphergy.sh project-push"
    echo ""
}

# --- Main -------------------------------------------------------------------

COMMAND="${1:-help}"

case "$COMMAND" in
    status)         cmd_status ;;
    check)          cmd_check ;;
    hash)           cmd_hash ;;
    sync-check)     cmd_sync_check ;;
    mark-synced)    cmd_mark_synced ;;
    project-status) cmd_project_status ;;
    project-push)   cmd_project_push ;;
    cascade)        shift; cmd_cascade "$@" ;;
    init)           cmd_init "$@" ;;
    help|--help|-h) cmd_help ;;
    *)
        log_error "Unknown command: $COMMAND"
        echo ""
        cmd_help
        exit 1
        ;;
esac
