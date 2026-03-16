# CIPHERGY — QUICKSTART (5 Minutes)

## Prerequisites

- Python 3.10+
- Claude Code CLI (Anthropic)
- Claude.ai Pro account
- Asana account (free tier OK)
- `jq` installed (`brew install jq`)

## Setup

```bash
# 1. Clone / navigate to your Ciphergy project
cd /path/to/your/project

# 2. Install Python dependencies
pip install pyyaml

# 3. Configure your domain
# Edit config/ciphergy.yaml:
#   domain: "legal"  (or medical, investigation, engineering, default)
#   Set your Asana task GIDs and PAT source

# 4. Create your intake folder
mkdir New-Data

# 5. Test the nerve center
python3 scripts/nerve_center.py startup

# 6. Test agent communication (if Asana configured)
python3 scripts/agent_comm.py status

# 7. Start a Claude Code session in this directory
# The SessionStart hook fires automatically:
#   → Checks milestones
#   → Checks intake folder
#   → Reads agent comms
#   → Renders dashboard
```

## First Use

1. Drop a document into `New-Data/`
2. Start a Claude Code session
3. The Onboarding Agent guides you through setup
4. The Evidence Coach scores your first data
5. You're operational

## Daily Workflow

1. Session starts → hooks fire → dashboard renders → comms read
2. Drop new data → Evidence Coach scores → cascades update
3. Draft a communication → Draft Guardian filters → 7 gates
4. Face a decision → Strategy Advisor → Three Moves Ahead
5. Milestone approaching → Deadline Sentinel → alerts
