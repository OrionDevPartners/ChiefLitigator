# Cyphergy Master Admin Panel -- V0 Prompts
# Owner: Bo Pennington | bo@symio.ai
# Created: 2026-03-15
# Usage: Paste each prompt into v0.dev individually. Each is self-contained.
#
# IMPORTANT: This admin panel is FULLY SEPARATE from the user-facing Cyphergy app.
# Separate deployment, separate auth (MFA required), separate build.
# No source code visible from browser inspect. No jailbreak path from user UI to admin.
#
# Stack: React + Tailwind CSS + shadcn/ui + recharts
# Theme: Dark mode default

---

## Prompt 1: Admin Dashboard (Main Landing)

```
Build a full-page admin dashboard for "Cyphergy Admin" -- a mission control panel for an AI legal co-counsel platform. This is a dark-mode-first internal admin dashboard (think Vercel dashboard or Linear admin -- data-dense but clean).

Layout:
- Fixed left sidebar (w-64) with dark background (bg-zinc-950). Sidebar items: Dashboard (active), Connectors, Agent Observatory, System Controls, Deployments. Each item has a Lucide icon. At the top of the sidebar, show the Cyphergy logo text in font-bold text-lg with a small shield icon. At the bottom of the sidebar, show the logged-in admin avatar, name, and a "Sign Out" link.
- Top bar with breadcrumb ("Admin / Dashboard"), a global search input (Command+K style), and a notification bell with a red badge showing "3".
- Main content area with bg-zinc-900 and p-6 spacing.

KPI Cards Row (top):
Use shadcn/ui Card components in a grid of 5 columns (grid-cols-5 on xl, responsive down to 2 cols). Each card has bg-zinc-800 border-zinc-700. Cards:
1. "Total Users" -- value "2,847" with a green +12.3% badge and a Users icon
2. "Active Cases" -- value "1,204" with a blue badge showing "38 this week" and a Briefcase icon
3. "Revenue MTD" -- value "$48,290" with a green +8.7% badge and a DollarSign icon
4. "API Cost MTD" -- value "$12,430" with a yellow -2.1% badge and a CreditCard icon
5. "WDC Pass Rate" -- value "94.2%" with a green checkmark badge and a ShieldCheck icon

Charts Section (2x2 grid below KPIs, grid-cols-2 on lg):
Use recharts for all charts. Each chart inside a Card with bg-zinc-800 border-zinc-700, with a CardHeader showing the title and a subtle CardDescription.
1. "User Growth" -- ResponsiveContainer with a LineChart showing 12 months of data. Line color #3b82f6 (blue-500). X-axis months, Y-axis user count. Include a Tooltip with bg-zinc-700 styling.
2. "Revenue vs Cost" -- AreaChart with two areas: revenue in #22c55e (green-500, fillOpacity 0.3) and cost in #f59e0b (amber-500, fillOpacity 0.2). Shared X-axis by month.
3. "Agent Usage Breakdown" -- BarChart with 5 bars for each agent: Lead Counsel (#3b82f6), Research (#8b5cf6), Drafting (#06b6d4), Red Team (#ef4444), Compliance (#f59e0b). Y-axis is "Tokens (M)". Show values like 4.2M, 3.1M, 1.8M, 2.5M, 0.9M.
4. "Citation Accuracy" -- A single large radial gauge (use a PieChart with innerRadius/outerRadius to create a gauge effect). Value 96.8% in the center in text-3xl font-bold. Green fill for the completed arc, zinc-700 for the remaining.

Bottom Section (2 columns):
Left column -- "Recent Activity" feed: A scrollable list (max-h-80 overflow-y-auto) of activity items. Each item has a colored dot (green for signups, blue for cases, amber for WDC reviews, red for alerts), timestamp in text-zinc-500 text-xs, and description text. Show 8 items like "New user: firm_admin@lawfirm.com", "Case created: Martinez v. State of CA", "WDC Review: 8.7/10 CERTIFIED", "Alert: CourtListener API latency > 2s".

Right column -- "System Health" panel: A Card with a list of services. Each row has a service name, a colored status dot (green/yellow/red), and uptime percentage. Services: API Gateway (green, 99.99%), LLM Provider (green, 99.95%), PostgreSQL (green, 99.99%), Redis Cache (green, 100%), CourtListener (yellow, 98.2%), Sentry (green, 99.9%), ECS Cluster (green, 99.97%). Use flex justify-between for each row.

All text uses text-zinc-100 for primary, text-zinc-400 for secondary. Use rounded-lg on all cards. Transitions on hover for interactive elements. No light mode toggle -- this is dark only.
```

---

## Prompt 2: Connector Management

```
Build a full-page "Connector Management" admin panel for "Cyphergy Admin" -- managing all external service integrations for an AI legal platform. Dark mode only.

Layout:
- Same sidebar as the dashboard (w-64, bg-zinc-950) with navigation items: Dashboard, Connectors (active, highlighted with bg-zinc-800 and a left border-2 border-blue-500), Agent Observatory, System Controls, Deployments. Cyphergy logo at top, admin avatar at bottom.
- Main content area: bg-zinc-900, p-6.

Page Header:
- Title "Connectors" in text-2xl font-bold text-zinc-100.
- Subtitle "Manage external service integrations and API connections" in text-zinc-400.
- Right-aligned "Add Connector" Button (shadcn/ui Button variant="default" with a Plus icon) that opens a dropdown (DropdownMenu) listing available integrations not yet connected.

Connector Grid:
Use a responsive grid (grid-cols-3 on xl, grid-cols-2 on lg, grid-cols-1 on sm). Each connector is a Card component with bg-zinc-800 border-zinc-700 hover:border-zinc-600 transition-colors cursor-pointer.

Each connector card contains:
- Top row: Service icon (use a colored circle with the first letter as fallback), service name in font-semibold text-zinc-100, and a status Badge -- "Connected" in green (bg-green-500/10 text-green-400 border-green-500/20) or "Disconnected" in red (bg-red-500/10 text-red-400 border-red-500/20).
- Stats row: "Last Sync: 2 min ago" and "Errors (24h): 0" in text-zinc-400 text-sm. If errors > 0, show in text-red-400.
- Bottom row: "Configure" link in text-blue-400 hover:text-blue-300.

Show these 11 connectors:
1. Anthropic -- Connected, last sync 2 min ago, 0 errors, env var: ANTHROPIC_API_KEY
2. AWS Bedrock -- Connected, last sync 5 min ago, 0 errors, env var: AWS_BEDROCK_ENDPOINT
3. Cloudflare -- Connected, last sync 1 min ago, 0 errors, env var: CLOUDFLARE_API_TOKEN
4. CourtListener -- Connected, last sync 8 min ago, 3 errors (show in red), env var: COURTLISTENER_API_KEY
5. Sentry -- Connected, last sync 1 min ago, 0 errors, env var: SENTRY_DSN
6. Linear -- Connected, last sync 15 min ago, 0 errors, env var: LINEAR_API_KEY
7. HuggingFace -- Disconnected, no sync, 0 errors, env var: HUGGINGFACE_TOKEN
8. Expo -- Connected, last sync 30 min ago, 0 errors, env var: EXPO_ACCESS_TOKEN
9. V0 -- Connected, last sync 1 hr ago, 0 errors, env var: V0_API_KEY
10. Devin -- Connected, last sync 3 min ago, 1 error, env var: DEVIN_TOKEN
11. GitHub -- Connected, last sync 1 min ago, 0 errors, env var: GITHUB_TOKEN

Configuration Modal (Dialog):
When "Configure" is clicked, show a shadcn/ui Dialog with:
- Service name as Dialog title
- Form fields:
  - "API Key" -- an Input with type="password" showing masked dots. A small eye icon (EyeOff/Eye toggle) to reveal/hide. Below the input, show the env var name in a code-styled span (bg-zinc-700 rounded px-2 py-0.5 text-xs font-mono text-zinc-400) like "ANTHROPIC_API_KEY".
  - "Endpoint URL" -- an Input with the current endpoint value, editable.
  - "Test Connection" Button (variant="outline") that shows a loading spinner, then a green checkmark or red X result.
  - "Save" Button (variant="default") and "Cancel" Button (variant="ghost").
- A note at the bottom in text-zinc-500 text-xs: "Values are stored as environment variables. Changes require service restart."
- The dialog should mention "CPAA Compliant" with a small shield icon in the corner.

All cards use rounded-lg. Text hierarchy: text-zinc-100 primary, text-zinc-400 secondary, text-zinc-500 tertiary. No light mode.
```

---

## Prompt 3: Agent Observatory

```
Build a full-page "Agent Observatory" admin panel for "Cyphergy Admin" -- a live monitoring view for 5 AI agents in a legal co-counsel system. Dark mode only.

Layout:
- Same sidebar (w-64, bg-zinc-950) with Connectors, Agent Observatory (active), System Controls, Deployments. Cyphergy logo, admin avatar.
- Main content: bg-zinc-900, p-6.

Page Header:
- "Agent Observatory" in text-2xl font-bold, subtitle "Real-time monitoring of all Cyphergy agents" in text-zinc-400.
- Right side: a live indicator -- a pulsing green dot (animate-pulse) with "All Agents Online" text.

Agent Cards Section:
5 Cards in a single row on xl (grid-cols-5), wrapping to 3+2 on lg and stacking on mobile. Each card is bg-zinc-800 border-zinc-700 with a colored top border (border-t-2) unique to each agent.

Agent cards:
1. "Lead Counsel" -- border-t-blue-500. Icon: Scale. Weight badge: "30%". Status: "Reviewing motion draft". Tokens today: "1.24M". Cost today: "$18.60". Avg WDC: "8.9". Last active: "12s ago".
2. "Research" -- border-t-purple-500. Icon: Search. Weight: "25%". Status: "Querying CourtListener". Tokens: "890K". Cost: "$13.35". Avg WDC: "8.7". Last active: "3s ago".
3. "Drafting" -- border-t-cyan-500. Icon: FileText. Weight: "15%". Status: "Idle". Tokens: "420K". Cost: "$6.30". Avg WDC: "8.4". Last active: "5 min ago".
4. "Red Team" -- border-t-red-500. Icon: ShieldAlert. Weight: "20%". Status: "Running adversarial check". Tokens: "680K". Cost: "$10.20". Avg WDC: "9.1". Last active: "45s ago".
5. "Compliance" -- border-t-amber-500. Icon: CheckCircle. Weight: "10% + VETO". Status: "Monitoring". Tokens: "210K". Cost: "$3.15". Avg WDC: "8.6". Last active: "2 min ago".

Each card layout:
- Agent name in font-semibold with the icon, weight badge in a small rounded pill (bg-zinc-700 text-xs).
- "Current Task" label in text-zinc-500 text-xs uppercase tracking-wide, then task text in text-zinc-300.
- Stats grid (2x2): Tokens, Cost, Avg WDC, Last Active. Each stat has a label in text-zinc-500 text-xs and value in text-zinc-200 font-mono.

WDC Debate Viewer Section (below agent cards):
A collapsible Card (use shadcn/ui Collapsible or Accordion) titled "Last WDC Debate Transcript". When expanded, show:
- Case header: "Martinez v. State of CA -- Motion to Dismiss" in font-semibold.
- A vertical timeline of debate entries. Each entry has the agent name (colored to match the agent), the score they gave (e.g., "8.7"), and a quote of their assessment in text-zinc-400 italic. Show all 5 agents in order.
- Final composite score in a large Badge: "Composite: 8.74 / 10 -- CERTIFIED" in green if >= 8.5, yellow if 7.0-8.4, red if < 7.0.
- A "View Full Transcript" link in text-blue-400.

Model Configuration Section (below debate viewer):
A Card titled "Model Configuration" with a table (shadcn/ui Table):
- Columns: Agent, Model, Temperature, Max Tokens, Actions.
- 5 rows for each agent. Model column shows a Select dropdown with options: "claude-opus-4-6 (1M)", "claude-sonnet-4-5", "claude-haiku-4-5". All currently set to opus. Temperature shows an Input (type number, step 0.1, min 0, max 1) currently 0.3 for all. Max Tokens shows an Input (type number) -- values like 8192, 16384. Actions column has a "Save" button (variant="outline" size="sm").
- A warning banner at the top in bg-amber-500/10 border-amber-500/20: "Legal agents require Opus 4.6 for citation accuracy. Downgrading models is not recommended for production."

Agent Weight Sliders Section:
A Card titled "WDC Agent Weights" with 5 horizontal sliders (shadcn/ui Slider). Each shows the agent name, a colored slider track matching the agent color, and the current weight value. Values: Lead 0.30, Research 0.25, Drafting 0.15, Red Team 0.20, Compliance 0.10. Below the sliders, show "Total: 1.00" in font-mono. If total != 1.00, show in text-red-400 with a warning. A "Save Weights" button.

Compliance Veto Log (bottom):
A Card titled "Compliance Veto Log" with a scrollable table (max-h-64 overflow-y-auto). Columns: Timestamp, Reason, Blocked Output (truncated to 80 chars with ellipsis), Case ID. Show 5 sample entries with timestamps, reasons like "HIPAA violation detected in output", "Unverified citation in conclusion", "PII found in draft section 3". Each row has a red left border (border-l-2 border-red-500). An "Export Log" button in the card header.

All text: text-zinc-100 primary, text-zinc-400 secondary. Rounded-lg on all cards. No light mode.
```

---

## Prompt 4: System Override Controls

```
Build a full-page "System Controls" admin panel for "Cyphergy Admin" -- override controls and feature flags for an AI legal platform. Dark mode only. This page contains potentially destructive operations, so use clear visual hierarchy to separate safe actions from dangerous ones.

Layout:
- Same sidebar (w-64, bg-zinc-950). System Controls is active (highlighted). Cyphergy logo, admin avatar.
- Main content: bg-zinc-900, p-6.

Page Header:
- "System Controls" in text-2xl font-bold, subtitle "Feature flags, model routing, and system overrides" in text-zinc-400.
- A yellow banner (bg-amber-500/10 border border-amber-500/20 rounded-lg p-3) at the top: "Changes on this page affect the live platform. Proceed with caution." with an AlertTriangle icon.

Section 1: Feature Flags
A Card (bg-zinc-800 border-zinc-700) titled "Feature Flags" with a list of toggles. Each row is a flex container with: flag name (font-medium text-zinc-100), description (text-zinc-400 text-sm), and a Switch (shadcn/ui Switch component) on the right.

Flags:
1. "WDC Multi-Agent Consensus" -- "Enable 5-agent weighted debate for output validation" -- ON (checked)
2. "Batch Document Intake" -- "Allow bulk upload of case documents for parallel processing" -- OFF
3. "Offline Courtroom Mode" -- "Enable local-first operation with sync-when-connected" -- OFF
4. "Citation Verification Chain" -- "External retrieval hard constraint for all citations" -- ON (this one has a lock icon and text "Cannot be disabled" in text-red-400 text-xs -- the switch is disabled)
5. "Real-Time Collaboration" -- "Multi-user simultaneous editing on case documents" -- OFF
6. "Advanced Analytics" -- "Detailed per-case cost and accuracy metrics" -- ON
7. "Compliance Auto-Veto" -- "Automatic blocking of non-compliant outputs" -- ON (also has a lock icon and "Cannot be disabled")

Section 2: Model Routing
A Card titled "Model Routing" with a note "Route specific agent types to different models. Legal agents are locked to Opus 4.6."
A table with columns: Agent Role, Current Model, Override Model, Status.
Rows:
1. Lead Counsel -- claude-opus-4-6 -- Select (disabled, locked) -- Badge "Locked" in zinc
2. Research -- claude-opus-4-6 -- Select (disabled, locked) -- Badge "Locked"
3. Drafting -- claude-opus-4-6 -- Select (disabled, locked) -- Badge "Locked"
4. Red Team -- claude-opus-4-6 -- Select (disabled, locked) -- Badge "Locked"
5. Compliance -- claude-opus-4-6 -- Select (disabled, locked) -- Badge "Locked"
6. Onboarding Assistant -- claude-sonnet-4-5 -- Select dropdown (claude-opus-4-6, claude-sonnet-4-5, claude-haiku-4-5) -- Badge "Active" green
7. Document Summary -- claude-haiku-4-5 -- Select dropdown (same options) -- Badge "Active" green
A footer note: "Legal pack models (Lead, Research, Drafting, Red Team, Compliance) cannot be changed from Opus 4.6. This is a safety constraint."

Section 3: Rate Limit Overrides
A Card titled "Rate Limit Overrides" with a table. Columns: Tenant, Current Limit, Override, Expires, Actions.
Show 4 rows with sample tenant names (law firm names), current limits like "100 req/min", override inputs (number Input), expiration date pickers, and "Apply" / "Remove" buttons. An "Add Override" button at the top of the card.

Section 4: Circuit Breakers
A Card titled "Circuit Breaker Status" with a grid of circuit breaker indicators (grid-cols-3 on lg).
Each breaker is a mini-card with:
- Service name
- Status: "Closed" (green, normal) or "Open" (red, tripped)
- Trip count and last trip time
- A "Reset" button (variant="outline" size="sm", only enabled when Open)

Breakers: CourtListener API (Closed), Anthropic API (Closed), PostgreSQL (Closed), Redis (Closed), Sentry Webhook (Open -- show in red with border-red-500, trip count: 3, last trip: "2 min ago"), ECS Health Check (Closed).

Section 5: Maintenance Mode
A Card with a prominent Switch labeled "Maintenance Mode". When toggled, it shows a Textarea for a custom maintenance message (placeholder: "Cyphergy is currently undergoing scheduled maintenance...") and a "Read-Only Mode" checkbox. A "Save" button. The entire card has a subtle yellow tint (bg-amber-500/5) to indicate caution.

Section 6: Danger Zone
A Card with a red border (border-red-500/50) and bg-red-500/5 tint. Title "Danger Zone" in text-red-400 with a Skull icon.
Destructive operations, each in its own row with a description and a red-outlined button:
1. "Clear All Caches" -- "Purge Redis cache and CDN cache. Users may experience slower responses." -- Button "Clear Cache" (variant="outline" with red text and border)
2. "Reset Rate Limits" -- "Remove all rate limit overrides and return to defaults." -- Button "Reset Limits"
3. "Force Deploy" -- "Trigger immediate deployment bypassing WDC validation. Emergency use only." -- Button "Force Deploy"
4. "Purge Citation Cache" -- "Delete all cached court opinions. Will trigger re-fetch on next request." -- Button "Purge Citations"

Each danger button should have an AlertDialog confirmation that requires typing the action name to confirm (similar to GitHub repo deletion). For example, "Type 'clear-cache' to confirm".

All text: text-zinc-100 primary, text-zinc-400 secondary. Rounded-lg on all cards. No light mode.
```

---

## Prompt 5: Deployment & Git Panel

```
Build a full-page "Deployments" admin panel for "Cyphergy Admin" -- deployment management and git integration for an AI legal platform running on AWS ECS. Dark mode only.

Layout:
- Same sidebar (w-64, bg-zinc-950). Deployments is active. Cyphergy logo, admin avatar.
- Main content: bg-zinc-900, p-6.

Page Header:
- "Deployments" in text-2xl font-bold, subtitle "Deployment pipeline, git integration, and release management" in text-zinc-400.

Section 1: Current Deployment
A prominent Card (bg-zinc-800 border-zinc-700) showing the live deployment status. Layout:
- Left side: Large green status dot (w-3 h-3 rounded-full bg-green-500 animate-pulse) with "Production" label in text-green-400 font-semibold text-lg.
- Info grid (grid-cols-4):
  - "Commit" -- show a truncated hash "a3f7c21" in font-mono text-blue-400 (clickable link style)
  - "Branch" -- "main" in a Badge with bg-zinc-700
  - "Deployed" -- "2 hours ago" with full timestamp on hover (use Tooltip)
  - "Status" -- Badge "Healthy" in green (bg-green-500/10 text-green-400)
- A second row showing: "ECS Service: cyphergy-prod", "Task Definition: cyphergy:47", "Running Tasks: 3/3", "CPU: 42%", "Memory: 68%"

Section 2: Deployment Actions
A row of 3 action Cards side by side (grid-cols-3):

Card 1: "Deploy to Staging"
- Icon: Rocket in blue
- Description: "Deploy the latest dev branch to the staging environment for testing."
- A Select dropdown for branch selection showing: dev (default), feature/remaining-agents, fix/courtlistener-retry
- "Deploy to Staging" Button (variant="default", blue). When clicked, show a loading state with progress dots.
- Last staging deploy: "45 min ago -- a1b2c3d (dev)"

Card 2: "Promote to Production"
- Icon: ArrowUpCircle in green
- Description: "Promote current staging build to production. Requires WDC validation pass."
- WDC Status: Show a green checkmark with "WDC Score: 8.74 -- PASS" or a red X with "WDC Score: 6.2 -- FAIL (blocked)"
- "Promote to Production" Button (variant="default", green). Disabled if WDC fails.
- A checkbox: "I confirm this has been tested in staging" (must be checked to enable button)

Card 3: "Rollback"
- Icon: RotateCcw in amber
- Description: "Revert production to the previous ECS task definition."
- Previous version: "cyphergy:46 -- deployed 3 days ago -- b4e5f6a"
- "Rollback to v46" Button (variant="outline" with amber text). Has an AlertDialog confirmation.
- Rollback history: "Last rollback: 12 days ago (v44 -> v43)"

Section 3: Git Integration
A Card titled "Recent Commits" with a scrollable list (max-h-72 overflow-y-auto). Each commit row:
- Commit hash (font-mono text-blue-400 text-sm, first 7 chars)
- Commit message (text-zinc-200, truncated to one line with ellipsis)
- Author name (text-zinc-400 text-sm)
- Relative timestamp (text-zinc-500 text-sm)
- Branch badge (bg-zinc-700 rounded text-xs px-2)

Show 10 commits. Mix of branches (main, dev, feature/remaining-agents). Messages like:
- "fix: deadline calculation for NY SOL edge case"
- "feat: add compliance veto logging to WDC engine"
- "chore: update ECS task definition memory limits"
- "fix: CourtListener retry logic for 429 responses"
- "feat: citation verification chain step 3 external retrieval"

Below the commits, a Card titled "Open Pull Requests" with a table:
- Columns: PR, Title, Author, WDC Score, Status, Actions
- Show 3 PRs:
  1. #3 -- "Infrastructure updates and CI hardening" -- Bo -- 8.6 (green badge) -- "Ready to merge" (green) -- "Merge" button
  2. #2 -- "Add remaining 4 agents" -- Devin -- 7.8 (yellow badge) -- "Review required" (yellow) -- "Review" button
  3. #4 -- "V0 frontend components" -- Bo -- "Pending" (gray badge) -- "Draft" (gray) -- "View" button

Section 4: Build Logs
A Card titled "Build Logs" with a terminal-style output area. Use bg-zinc-950 rounded-lg p-4 font-mono text-sm. The log area should be max-h-96 overflow-y-auto with a scrollbar.

Show simulated build output with colored text:
- Timestamps in text-zinc-600
- Info messages in text-zinc-400
- Success messages in text-green-400
- Warning messages in text-amber-400
- Step headers in text-blue-400 font-bold

Example log lines:
```
[14:32:01] Starting deployment pipeline...
[14:32:01] Branch: dev | Commit: a3f7c21
[14:32:02] Step 1/6: Running tests...
[14:32:15] ✓ 62 tests passed, 0 failed
[14:32:16] Step 2/6: Security scan (pip-audit)...
[14:32:22] ✓ No vulnerabilities found
[14:32:23] Step 3/6: Building Docker image...
[14:33:01] ✓ Image built: 892MB
[14:33:02] Step 4/6: Pushing to ECR...
[14:33:18] ✓ Pushed to 123456789.dkr.ecr.us-east-1.amazonaws.com/cyphergy:latest
[14:33:19] Step 5/6: Updating ECS task definition...
[14:33:21] ✓ Task definition cyphergy:47 registered
[14:33:22] Step 6/6: Deploying to ECS...
[14:33:45] ✓ Service stable. 3/3 tasks running.
[14:33:45] Deployment complete.
```

A "Clear Logs" button (variant="ghost" size="sm") and "Download Logs" button (variant="outline" size="sm") in the card header.

Section 5: Devin Session Monitor
A Card titled "Devin Sessions" with a table. Columns: Session ID, Task, Status, Started, Duration, Actions.
Show 3 rows:
1. "4a1924d" -- "Build master admin panel" -- Badge "Active" (green pulse) -- "2 hours ago" -- "2h 14m" -- "View" link (text-blue-400)
2. "b7e3f91" -- "Add remaining 4 agents" -- Badge "Completed" (green solid) -- "Yesterday" -- "4h 32m" -- "View" link
3. "c9d2a44" -- "Fix CourtListener integration" -- Badge "Failed" (red) -- "2 days ago" -- "1h 07m" -- "View" / "Retry" links

Below the table, a "New Devin Session" Button (variant="outline") that opens a Dialog with a Textarea for the task prompt and a "Launch Session" button.

All text: text-zinc-100 primary, text-zinc-400 secondary. Font-mono for hashes, logs, and technical values. Rounded-lg on all cards. No light mode.
```

---

## Usage Notes

1. Paste each prompt individually into v0.dev
2. After generation, download the React components
3. Each component will need real data hooks wired up (replace hardcoded values with API calls)
4. The sidebar is repeated in each prompt for standalone generation -- extract it into a shared layout component after all 5 are generated
5. Auth (MFA) and route protection are NOT included in V0 prompts -- those are backend concerns handled by Devin
6. All environment variable references are display-only (show the var name, never the value)
