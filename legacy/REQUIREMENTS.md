# REQUIREMENTS.md — Ciphergy Pipeline Deployment Requirements

## System Requirements

### Runtime Environment

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | macOS 13+ / Ubuntu 22.04+ / Windows 11 (WSL2) | macOS 14+ (native shell) |
| Python | 3.10+ | 3.12+ |
| Node.js | 18+ | 20+ LTS |
| Bash | 4.0+ | 5.0+ (zsh compatible) |
| Disk | 500MB per project | 2GB+ for large document repos |
| RAM | 4GB | 8GB+ (for parallel agent spawning) |

### AI Environments

| Environment | Provider | Tier | Context Window |
|-------------|----------|------|---------------|
| **Agent Local** | Anthropic Claude Code CLI | Opus 4.6 (1M) or Sonnet 4.6 | 1M tokens (Opus) / 200K (Sonnet) |
| **Agent Cloud** | Claude.ai Desktop (claude.ai) | Pro plan (required for projects) | 200K tokens |

### External Services

| Service | Purpose | Tier | Required? |
|---------|---------|------|-----------|
| **Asana** | Message bus between agents | Free tier sufficient | YES |
| **Asana API** | Programmatic access | Personal Access Token | YES |
| **Anthropic API** | Claude Code CLI | API key + billing | YES |
| **Claude.ai** | Agent Cloud | Pro subscription | YES |

---

## Python Dependencies

```txt
# requirements.txt
pyyaml>=6.0              # YAML config parsing
requests>=2.31           # Asana API HTTP calls
python-dateutil>=2.8     # Timestamp handling
watchdog>=3.0            # File system monitoring (optional — for daemon mode)
rich>=13.0               # Terminal UI formatting (optional — for dashboard)
flask>=3.0               # Web dashboard (optional)
fpdf2>=2.7               # PDF generation (optional)
markdown>=3.5            # Markdown processing (optional)
```

### Install

```bash
pip install -r requirements.txt
```

---

## Node.js Dependencies

```json
// package.json
{
  "name": "ciphergy-pipeline",
  "version": "1.0.0",
  "description": "Dual-Environment AI Orchestration Platform",
  "dependencies": {
    "@anthropic/asana-mcp-server": "^1.0.0"
  },
  "devDependencies": {}
}
```

### Install

```bash
npm install
# OR for global MCP server
npm install -g @anthropic/asana-mcp-server
```

---

## CLI Tools (System-Level)

| Tool | Purpose | Install |
|------|---------|---------|
| `pandoc` | Markdown → DOCX/PDF conversion | `brew install pandoc` / `apt install pandoc` |
| `jq` | JSON processing in shell | `brew install jq` / `apt install jq` |
| `md5sum` / `md5` | File hash verification | Built-in (macOS: `md5`, Linux: `md5sum`) |
| `curl` | Asana API calls | Built-in |

---

## Asana Configuration

### Setup Steps

1. **Create Asana Account** — free tier at asana.com
2. **Create Project** — name it anything (e.g., "Ciphergy Workspace")
3. **Create Section** — name: "AGENTS COMM"
4. **Create Task 1** — name: "AGENT LOCAL" (this is the local agent's outbox)
5. **Create Task 2** — name: "AGENT CLOUD" (this is the cloud agent's outbox)
6. **Generate PAT** — My Settings → Apps → Developer Apps → Personal Access Tokens → Create New Token
7. **Record GIDs** — hover over each task URL to find the GID, or use the API:

```bash
# Get project GID
curl -H "Authorization: Bearer YOUR_PAT" \
  "https://app.asana.com/api/1.0/projects?workspace=YOUR_WORKSPACE_GID"

# Get task GIDs
curl -H "Authorization: Bearer YOUR_PAT" \
  "https://app.asana.com/api/1.0/projects/PROJECT_GID/tasks"
```

### Configuration File

```yaml
# config/ciphergy.yaml
asana:
  pat: "YOUR_ASANA_PAT"
  project_gid: "YOUR_PROJECT_GID"
  section_gid: "YOUR_SECTION_GID"
  agent_local_task_gid: "YOUR_LOCAL_TASK_GID"
  agent_cloud_task_gid: "YOUR_CLOUD_TASK_GID"
```

---

## Claude Code MCP Configuration

To enable native Asana tool calls in Claude Code (instead of curl):

```json
// ~/.claude/mcp-servers.json
{
  "asana": {
    "command": "npx",
    "args": ["-y", "@anthropic/asana-mcp-server"],
    "env": {
      "ASANA_ACCESS_TOKEN": "YOUR_PAT"
    }
  }
}
```

After adding, restart Claude Code. Asana tools will appear in the tool list.

---

## Deployment Architecture (SaaS/Commercial)

### Single-Tenant (Current)

```
User's Machine
├── Claude Code CLI (local agent)
├── Ciphergy Pipeline repo (this repo)
├── Asana (free tier, user's account)
└── Claude.ai Desktop (cloud agent, user's account)
```

### Multi-Tenant (Future SaaS)

```
Ciphergy Cloud Platform
├── API Gateway (FastAPI / Express)
├── Tenant Manager
│   ├── Tenant A config (Asana GIDs, monitored files)
│   ├── Tenant B config
│   └── ...
├── Version Control Service
│   ├── Registry per tenant
│   ├── Cascade engine
│   └── Sync manager
├── Asana Integration Service
│   ├── Message posting
│   ├── Message polling
│   └── Webhook receiver
├── Dashboard Service
│   ├── React/Next.js frontend
│   ├── WebSocket for real-time updates
│   └── REST API for status queries
├── Storage
│   ├── S3 / GCS for project files
│   ├── PostgreSQL for registry + audit trail
│   └── Redis for sync state cache
└── Auth
    ├── OAuth2 (Asana, Anthropic)
    ├── API key management
    └── Tenant isolation
```

### Required Cloud Services (Multi-Tenant)

| Service | Purpose | Provider Options |
|---------|---------|-----------------|
| Compute | API Gateway + services | AWS ECS / GCP Cloud Run / Fly.io |
| Database | Registry, audit trail | PostgreSQL (RDS / Cloud SQL / Supabase) |
| Cache | Sync state | Redis (ElastiCache / Upstash) |
| Storage | Project files | S3 / GCS / R2 |
| Auth | OAuth2 + API keys | Auth0 / Clerk / Supabase Auth |
| CDN | Dashboard frontend | Cloudflare / Vercel |
| Webhooks | Asana event triggers | AWS Lambda / Cloudflare Workers |

---

## Environment Variables

```bash
# Required
export ASANA_PAT="your_asana_personal_access_token"
export CIPHERGY_PROJECT_ROOT="/path/to/your/project"

# Optional
export CIPHERGY_CONFIG="config/ciphergy.yaml"    # Custom config path
export CIPHERGY_LOG_LEVEL="INFO"               # DEBUG, INFO, WARN, ERROR
export ANTHROPIC_API_KEY="your_api_key"      # For Claude Code CLI
```

---

## Security Considerations

| Concern | Mitigation |
|---------|-----------|
| Asana PAT exposure | Store in environment variable, never commit to git. Use `.env` file with `.gitignore`. |
| Sensitive documents in sync folder | The sync folder contains copies of monitored files. Treat it with same sensitivity as the main repo. |
| API key rotation | Asana PATs can be revoked and regenerated. Update `ciphergy.yaml` after rotation. |
| Multi-tenant isolation | Each tenant gets a separate Asana project + separate registry. No shared state. |
| Audit trail integrity | VERSION_REGISTRY.json is append-only for version_history. Hash verification detects tampering. |

---

## Supported Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| macOS (Apple Silicon) | Full Support | Primary development platform |
| macOS (Intel) | Full Support | |
| Ubuntu 22.04+ | Full Support | |
| Windows 11 (WSL2) | Supported | Requires WSL2 with Ubuntu |
| Windows (native) | Not Supported | bash scripts require Unix shell |
| Docker | Planned | Containerized deployment for SaaS |

---

*Ciphergy Pipeline — Deployment Requirements v1.0*
*Copyright 2026 Analog AGI*
