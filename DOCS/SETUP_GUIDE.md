# Ciphergy Pipeline Setup Guide

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python 3 | 3.8+ | Scripts, cascade engine, dashboard |
| Bash | 4.0+ | CLI tool |
| pip | Latest | Python package management |

### Optional Software

| Software | Version | Purpose |
|----------|---------|---------|
| Node.js | 16+ | Future extension support |
| Git | 2.30+ | Version control |

### Python Packages

The following Python packages are required:

- `pyyaml` -- YAML configuration parsing
- `flask` -- Web dashboard

Install all dependencies:

```bash
pip install -r requirements.txt
```

## Installation

### Step 1: Clone or Download

Place the `CIPHERGY_PIPELINE` folder in your desired location:

```bash
cd /path/to/your/projects
# If cloning from git:
git clone <repository-url> CIPHERGY_PIPELINE
# Or if copying:
cp -r /source/CIPHERGY_PIPELINE ./CIPHERGY_PIPELINE
```

### Step 2: Install Dependencies

```bash
cd CIPHERGY_PIPELINE
pip install -r requirements.txt
```

### Step 3: Make CLI Executable

```bash
chmod +x scripts/ciphergy.sh
```

### Step 4: Create Shell Alias (Recommended)

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
alias ciphergy='/path/to/CIPHERGY_PIPELINE/scripts/ciphergy.sh'
```

Reload your shell:

```bash
source ~/.zshrc  # or ~/.bashrc
```

## Asana Configuration

### Step 1: Generate a Personal Access Token

1. Go to [Asana Developer Console](https://app.asana.com/0/developer-console)
2. Click "Create new token"
3. Name it "Ciphergy Pipeline"
4. Copy the token

### Step 2: Set Environment Variable

```bash
export ASANA_PAT="your_token_here"
```

For persistence, add to your shell profile:

```bash
echo 'export ASANA_PAT="your_token_here"' >> ~/.zshrc
```

### Step 3: Find Your Asana GIDs

You need three GIDs:

1. **Workspace GID**: Found in the URL when viewing your workspace
2. **Project GID**: Found in the URL when viewing the project
3. **Communication Task GID**: Create a task for Ciphergy messages, get its GID from the URL

### Step 4: Update Config

After initialization, edit `config/ciphergy.yaml`:

```yaml
asana:
  enabled: true
  pat_env_var: ASANA_PAT
  workspace_gid: "1234567890"
  project_gid: "1234567890"
  comm_task_gid: "1234567890"
```

## First Project Initialization

### Step 1: Initialize

```bash
ciphergy init --name "My Project" --domain custom
```

Available domains:
- `custom` -- Generic project
- `legal` -- Legal case management
- `startup` -- Startup / product development
- `medical` -- Medical case / research

### Step 2: Review Generated Files

After initialization, check:

```bash
ciphergy status
```

You should see:
- Project name and domain
- Tracked file count
- Agent statuses
- Sync version v1

### Step 3: Review Config

Open `config/ciphergy.yaml` and customize:
- Project name and domain
- Agent definitions
- Cascade rules and steps
- Asana settings (if using)
- Dashboard port

### Step 4: Upload to Cloud Agent

1. Upload all files from `sync/v1/` to your cloud agent project
2. Mark as synced:

```bash
ciphergy mark-synced
```

## Verification

Run these commands to verify everything works:

```bash
# Check project status
ciphergy status

# Verify file integrity
ciphergy check

# Compute hashes
ciphergy hash

# Check sync state
ciphergy sync-check

# Launch dashboard
python dashboard/dashboard.py
# Then open http://localhost:5050
```

## Troubleshooting

### "Config not found" Error

**Cause:** `config/ciphergy.yaml` does not exist.
**Fix:** Run `ciphergy init` to create it, or copy from a template.

### "Registry not found" Error

**Cause:** `.ciphergy/registry.json` does not exist.
**Fix:** Run `ciphergy init` to create it.

### "PyYAML not installed" Error

**Cause:** Python pyyaml package is missing.
**Fix:** `pip install pyyaml`

### "Flask not installed" Error

**Cause:** Flask is not installed (only needed for dashboard).
**Fix:** `pip install flask`

### Asana Connection Fails

**Cause:** Invalid PAT or network issue.
**Fix:**
1. Verify PAT: `echo $ASANA_PAT`
2. Test manually: `curl -H "Authorization: Bearer $ASANA_PAT" https://app.asana.com/api/1.0/users/me`
3. Check if PAT has expired and regenerate if needed

### Dashboard Won't Start

**Cause:** Port 5050 already in use.
**Fix:** Change port in `config/ciphergy.yaml` under `dashboard.port`, or kill the process using the port:
```bash
lsof -i :5050
kill -9 <PID>
```

### Hash Mismatches After Edit

**Cause:** Files were edited but hashes not recomputed.
**Fix:** Run `ciphergy hash` to update all hashes in the registry.

### Sync Shows All Files as "New"

**Cause:** `mark-synced` was never run after upload.
**Fix:** After uploading to cloud agent, run `ciphergy mark-synced`.

---
*Ciphergy Pipeline --- Setup Guide*
