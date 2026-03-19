# CIPHERGY V0 PROMPTS
# Paste each prompt directly into v0.dev to generate components
# Owner: Bo Pennington | bo@symio.ai
# Date: 2026-03-15

---

## PROMPT 1: Main Chat Interface

```
Build a full-page legal AI chat interface for "Cyphergy" — a conversational legal co-counsel app. React + Tailwind CSS + shadcn/ui. Dark mode default with a toggle.

LAYOUT:
- Collapsible left sidebar (240px desktop, full-screen overlay on mobile, hidden by default on mobile). Sidebar contains: Cyphergy logo at top (simple wordmark, no icon), a "New Chat" button (primary, full-width), then a scrollable list of past conversations grouped by date ("Today", "Yesterday", "Previous 7 Days"). Each conversation item shows a truncated title and a case badge (small colored pill: blue for active, gray for closed). At the bottom of the sidebar: dark/light mode toggle (sun/moon icons) and a user avatar + name row that opens a dropdown menu (Settings, Billing, Sign Out).
- Main content area: vertically centered when empty, scrollable message history when active.

EMPTY STATE (no messages yet):
- Centered vertically and horizontally. Large heading: "What can I help with?" in text-2xl font-medium text-foreground. Below it, a full-width input bar (max-w-2xl, rounded-2xl, bg-muted border border-border) with placeholder text "Ask about your case, draft a motion, check a deadline..." and a send button (ArrowUp icon, rounded-full, bg-primary). Below the input bar, 4 suggestion chips in a 2x2 grid on mobile, single row on desktop: "Analyze my complaint", "Check filing deadlines", "Draft a motion to dismiss", "Review opposing counsel's brief". Chips are rounded-xl bg-muted hover:bg-muted/80 px-4 py-3 text-sm.

MESSAGE HISTORY (active conversation):
- Messages scroll top-to-bottom. User messages: right-aligned, bg-primary text-primary-foreground rounded-2xl rounded-br-sm px-4 py-3 max-w-[80%]. AI messages: left-aligned, bg-muted rounded-2xl rounded-bl-sm px-4 py-3 max-w-[85%].
- Each AI message has an inline confidence indicator at the bottom-right: a small badge — green (Shield icon + "Verified") for citations verified via CourtListener, amber (AlertTriangle icon + "Verify") for citations that need user verification, red (XCircle icon + "Unverified") for unverified claims. Badge is text-xs with appropriate text/bg color classes.
- Below each AI message: a row of subtle action icons (text-muted-foreground hover:text-foreground): Copy, ThumbsUp, ThumbsDown, Share.
- When the AI is responding, show a typing indicator: three animated dots in bg-muted rounded-2xl.

INPUT BAR (pinned to bottom):
- Sticky at the bottom of the main content area. Same style as empty state input. Left side has a Paperclip icon button for file upload. Right side has the send button. Above the input, a thin banner shows the active case context: "Smith v. Jones | 3rd Cir. | Active" as a dismissable chip.
- Below the input bar in text-xs text-muted-foreground: "Cyphergy is an AI assistant, not a lawyer. Always verify legal advice with a licensed attorney."

COLORS: Use shadcn/ui CSS variables. Dark mode: zinc-950 background, zinc-900 sidebar, zinc-800 muted. Light mode: white background, zinc-50 sidebar, zinc-100 muted. Primary: blue-600.

Make it fully responsive. No marketing content, no upsell banners, no clutter. Clean like ChatGPT or Claude. Mobile-first.
```

---

## PROMPT 2: Case Dashboard

```
Build a case dashboard page for "Cyphergy", a legal AI platform. React + Tailwind CSS + shadcn/ui. Supports dark/light mode via CSS variables.

PAGE STRUCTURE:
- Top bar: breadcrumb ("Cases > Smith v. Jones") on the left, case status badge on the right (green "Active", amber "Pending", red "Urgent"). Below that, a row of tabs: Overview, Claims, Deadlines, Documents, Activity. Default to Overview tab.

OVERVIEW TAB — 3-column grid on desktop (lg:grid-cols-3), single column on mobile:

COLUMN 1 — Case Summary Card:
- Card (rounded-xl border bg-card shadow-sm) with heading "Case Summary".
- Key-value pairs stacked vertically: Case Name, Court, Jurisdiction, Case Number, Filed Date, Judge, Opposing Counsel. Each row: label in text-xs text-muted-foreground uppercase tracking-wide, value in text-sm font-medium.
- Below the pairs: an "Overall Confidence" circular progress ring (SVG, 120px diameter). Green fill if >= 75%, amber if >= 50%, red if < 50%. Center shows the percentage in text-2xl font-bold.

COLUMN 2 — Deadlines Card:
- Card heading "Upcoming Deadlines" with a "View All" link.
- List of the next 5 deadlines. Each item is a row with: a colored left-border (4px) — red-500 if <= 3 days, amber-500 if <= 7 days, blue-500 if <= 14 days, green-500 if > 14 days. Content: deadline title in font-medium, rule citation below in text-xs text-muted-foreground (e.g., "FRCP 12(b)(6)"), and days remaining as a badge on the right side ("2 days" in red, "6 days" in amber, etc.).
- Below the list: a mini calendar heatmap showing the next 30 days as a 5x7 grid of small squares (w-3 h-3 rounded-sm). Squares are colored by deadline density: bg-muted (none), bg-blue-500/30 (1), bg-blue-500/60 (2), bg-blue-500 (3+).

COLUMN 3 — Stacked Cards:

Card A — "Claims Matrix" (compact):
- Table with columns: Claim, Elements Met, Evidence Strength, Status.
- Evidence Strength shown as a horizontal bar (h-2 rounded-full bg-muted with colored fill). 3-4 rows of sample data.

Card B — "Agent Activity":
- Scrollable feed (max-h-64 overflow-y-auto). Each item: agent avatar (colored circle with initials: LC=blue, RA=purple, DA=green, RT=red, CC=amber), agent name, current action in text-sm, and relative timestamp in text-xs text-muted-foreground. Sample entries: "Lead Counsel — Analyzing opposition brief — 2m ago", "Red Team — Stress-testing damages calculation — 5m ago", "Compliance — Verifying filing deadline — 12m ago".

Card C — "Cost Tracker":
- Horizontal bar chart showing: "This Month" usage vs budget. Usage bar in bg-primary, budget cap as a dashed vertical line. Below: "Tokens Used: 1.2M / 5M" and "Est. Cost: $4.20 / $15.00 budget" in text-sm.

Footer row spanning full width:
- "Last updated 30 seconds ago" in text-xs text-muted-foreground with a refresh icon button.

Make it fully responsive — cards stack on mobile. No marketing. Clean data-dense design like Linear or Notion.
```

---

## PROMPT 3: Citation Viewer

```
Build a citation verification viewer component for "Cyphergy", a legal AI platform. React + Tailwind CSS + shadcn/ui. Dark/light mode support.

This component shows a single legal citation with its verification status and expandable details. It should work as a standalone card that can be embedded in chat messages or case dashboards.

COLLAPSED STATE (default):
- A card (rounded-xl border bg-card p-4) displaying one citation.
- Top row: verification badge on the left, citation text on the right.
- Verification badges are three variants:
  1. VERIFIED: bg-green-500/10 text-green-500 border-green-500/20 — ShieldCheck icon + "Verified" + "CourtListener" in text-xs.
  2. VERIFY: bg-amber-500/10 text-amber-500 border-amber-500/20 — AlertTriangle icon + "Needs Verification".
  3. UNVERIFIED: bg-red-500/10 text-red-500 border-red-500/20 — XCircle icon + "Unverified".
- Citation text in font-serif italic text-sm: e.g., "Ashcroft v. Iqbal, 556 U.S. 662, 678 (2009)".
- Right side: a ChevronDown button to expand, and a Copy button (clipboard icon) that copies Bluebook-formatted citation to clipboard with a brief "Copied!" toast.

EXPANDED STATE (on click):
- Smoothly expands below the collapsed content with a Collapsible from shadcn/ui.
- Section 1 — "Case Details": key-value grid (2 columns on desktop, 1 on mobile). Fields: Full Name, Citation, Court, Date Decided, Docket Number, Source (with link to CourtListener URL), Good Law Status (badge: green "Good Law", amber "Questioned", red "Overruled/Reversed").
- Section 2 — "Holding Summary": a paragraph in text-sm bg-muted rounded-lg p-3 with a quotation-mark icon. The AI-generated summary of the case holding.
- Section 3 — "Citing Opinions" (if verified): a compact list of 3-5 cases that cite this opinion. Each item: case name as a link, year, and treatment badge (green "Followed", amber "Distinguished", red "Overruled"). "View all on CourtListener" link at bottom.
- Section 4 — "Verification Chain": a vertical stepper showing the 4-step verification process. Each step: numbered circle (1-4), step name, status icon (green check or gray clock). Steps: 1. "Citation Parsed" 2. "External Lookup (CourtListener)" 3. "Opinion Text Retrieved" (with note: "Source: external retrieval, NOT model memory") 4. "Cross-Reference Validated". Show timestamp for each completed step.
- Action row at bottom: "Verify Again" button (outline variant, RefreshCw icon — triggers re-verification), "Copy Bluebook" button (primary variant), "Open in CourtListener" button (ghost variant, ExternalLink icon).

LOADING STATE:
- When verification is running, show a Skeleton loader for the badge area and a subtle pulsing border animation on the card (animate-pulse on the border).

Make it compact but information-rich. Typography: serif for case names and citations, sans-serif for everything else. Responsive — full width on mobile, max-w-2xl on desktop.
```

---

## PROMPT 4: Deadline Manager

```
Build a deadline management page for "Cyphergy", a legal AI platform. React + Tailwind CSS + shadcn/ui. Dark/light mode support.

PAGE LAYOUT:
- Header row: "Deadlines" heading on left, view toggle on right (Calendar view / Timeline view / List view — using shadcn ToggleGroup with CalendarDays, GanttChart, List icons). A primary "Add Deadline" button with Plus icon. A filter dropdown: "All Cases" / specific case names.

TIMELINE VIEW (default):
- A horizontal scrollable timeline (overflow-x-auto) showing the next 90 days.
- Month headers ("March 2026", "April 2026") as sticky labels at the top.
- Day columns marked with vertical gridlines. Today is highlighted with a blue-500 vertical line and "Today" label.
- Deadlines appear as horizontal bars positioned on their due date. Each bar: rounded-lg h-10, color-coded by urgency: bg-red-500 if <= 3 days remaining, bg-amber-500 if <= 7 days, bg-blue-500 if <= 14 days, bg-green-500 if > 14 days. Bar content: deadline title (truncated) in text-xs font-medium text-white. Hover shows a tooltip with full details.
- Left column (sticky, w-48): case name labels for each row.

LIST VIEW:
- A table (shadcn Table component) with columns: Status (color dot), Deadline, Case, Type, Rule/Statute, Jurisdiction, Days Remaining, Confidence.
- Status column: a filled circle (w-3 h-3 rounded-full) — red/amber/blue/green by urgency.
- Days Remaining: bold text with same color coding. Overdue deadlines show in red with "OVERDUE" badge.
- Confidence column: a small badge — green "High", amber "Medium", red "Low" indicating computation confidence.
- Sortable columns (click header to sort). Default sort: days remaining ascending.
- Rows are hoverable with hover:bg-muted/50.

CALENDAR VIEW:
- Monthly calendar grid. Each day cell shows deadline dots (colored by urgency). Click a day to see a popover listing all deadlines for that date. Navigation arrows for month switching. Today highlighted with ring-2 ring-primary.

ADD DEADLINE DIALOG (shadcn Dialog):
- Title: "Add Deadline". Form fields in a clean vertical stack:
  1. Case (Select dropdown of user's cases)
  2. Deadline Type (Select: "Motion Due", "Response Due", "Discovery Cutoff", "Trial Date", "Hearing", "Filing", "Service", "Appeal", "Custom")
  3. Jurisdiction (Select: federal circuits, state courts)
  4. Triggering Event Date (DatePicker — "When did the event that started this deadline occur?")
  5. Service Method (Select: "Electronic", "Personal", "Mail (+3 days)", "Mail out-of-state (+6 days)")
  6. Rule/Statute Citation (Input — e.g., "FRCP 12(b)(6)")
  7. Notes (Textarea)
- Below the form: a computed result card (bg-muted rounded-lg p-4): "Calculated Due Date: April 15, 2026" with the calculation breakdown shown step by step (base days + service days + holiday adjustments = total). Confidence badge for the computation.
- Action buttons: "Cancel" (ghost) and "Add Deadline" (primary).

ALERTS SECTION (top of page, collapsible):
- Alert banners stacked vertically:
  - Red alert (destructive variant): "OVERDUE: Answer to Complaint — Smith v. Jones — was due 2 days ago"
  - Amber alert (warning): "DUE TODAY: Motion to Compel — Doe v. Corp"
  - Blue alert (info): "UPCOMING: Discovery responses due in 5 days"
- Each alert has a "Dismiss" X button and a "Go to deadline" arrow link.

Bottom action bar:
- "Export to Google Calendar" button (outline, CalendarPlus icon), "Export CSV" button (outline, Download icon).

Responsive: timeline scrolls horizontally on mobile, list view becomes card-based on small screens. No marketing. Data-dense, professional.
```

---

## PROMPT 5: Onboarding Flow

```
Build a 5-step onboarding flow for "Cyphergy", a legal AI platform for people representing themselves in legal matters. React + Tailwind CSS + shadcn/ui. Dark mode default with toggle. Mobile-first design.

SHELL:
- Clean full-screen layout, no sidebar. Cyphergy wordmark centered at the very top (text-lg font-semibold tracking-tight). Below it, a progress bar (h-1 rounded-full bg-muted with bg-primary fill) showing current step out of 5, with subtle step labels underneath ("Sign Up", "Your Situation", "Details", "Your Case", "First Result"). Content area is max-w-lg mx-auto px-4, vertically centered on larger screens.

STEP 1 — SIGN UP:
- Heading: "Get started in 60 seconds" in text-2xl font-semibold. Subtext: "No credit card required." in text-muted-foreground.
- "Continue with Google" button (outline variant, full-width, with Google icon SVG). A horizontal divider with "or" text.
- Email input (Input component, placeholder "you@example.com") and Password input (type password, show/hide toggle). Minimal password hint: "8+ characters" in text-xs text-muted-foreground.
- "Create Account" primary button, full-width.
- Below: "Already have an account? Sign in" link in text-sm text-primary.
- Legal footer: "By continuing you agree to the Terms of Service and Privacy Policy" in text-xs text-muted-foreground with underlined links.

STEP 2 — YOUR SITUATION:
- Heading: "What do you need help with?" in text-2xl font-semibold. Subtext: "This helps us set up the right tools for you." in text-sm text-muted-foreground.
- 4 large selection cards in a 2x2 grid (gap-3). Each card: rounded-xl border-2 p-6 cursor-pointer, hover:border-primary transition. Selected state: border-primary bg-primary/5. Each card has:
  1. Icon (ShieldAlert) + "I received a lawsuit" + "Someone filed against you" in text-xs text-muted-foreground.
  2. Icon (Scale) + "I need to file a lawsuit" + "You want to take legal action".
  3. Icon (FileText) + "I need document help" + "Contracts, letters, or filings".
  4. Icon (Briefcase) + "I have an ongoing case" + "Import an existing matter".
- "Continue" primary button at bottom, disabled until selection made.

STEP 3 — TELL US MORE:
- Heading: "Tell us about your situation" in text-2xl font-semibold. Subtext: "The more detail you give, the better we can help. Everything is confidential." in text-sm text-muted-foreground.
- A conversational interview UI: a mini chat interface inside the step. AI asks guided questions one at a time ("What type of case is this?", "Which state are you in?", "When did the incident happen?", "What's your desired outcome?"). User types answers in a small input bar at the bottom of this mini-chat. Each Q&A pair stacks upward.
- Below the mini-chat: a drag-and-drop file upload zone (dashed border-2 border-dashed border-muted-foreground/30 rounded-xl p-8 text-center). Icon: Upload cloud. Text: "Drag documents here or click to upload". Subtext: "Complaints, contracts, correspondence, evidence — any format". Shows uploaded file chips (FileName.pdf X) below the zone.
- "Continue" button.

STEP 4 — YOUR CASE:
- Heading: "Here's what we found" in text-2xl font-semibold with a subtle green check animation.
- An auto-generated case summary card (bg-card rounded-xl border p-6):
  - Case type badge (e.g., "Breach of Contract")
  - Jurisdiction (detected from interview)
  - Key parties listed
  - Preliminary claims identified (bulleted list with confidence dots: green/amber/red)
  - Initial deadline alert if applicable: "Response deadline: ~20 days from service" in a yellow-tinted banner.
- Below: "Edit Case Details" ghost button and "Looks Right" primary button.

STEP 5 — FIRST RESULT:
- Heading: "Your first analysis is ready" in text-2xl font-semibold.
- Based on Step 2 selection, show ONE of these deliverables in a card:
  - If "received lawsuit": a defense analysis summary — claims against you, initial assessment, key deadlines, recommended next steps. Truncated with "View Full Analysis" link.
  - If "file lawsuit": claim viability assessment — strength rating (circular progress), elements checklist, statute of limitations status.
  - If "document help": smart template recommendation with preview.
  - If "ongoing case": imported case dashboard summary.
- Below the card: "Go to Dashboard" primary button (full-width) and "Ask a follow-up question" ghost button that navigates to the chat interface.
- Confetti or subtle checkmark animation to celebrate completion (optional, tasteful).

TRANSITIONS: Each step slides left-to-right with a smooth 200ms ease-out transition. "Back" button (ghost, ArrowLeft) appears on steps 2-5. Mobile: everything is full-width stacked, touch-friendly hit targets (min h-12 for buttons). No marketing on any step.
```

---

## PROMPT 6: Mobile App Shell (Expo React Native)

```
Build a mobile app shell for "Cyphergy", a legal AI co-counsel app. Use React Native conventions with Expo styling patterns. Use a tab-based navigation layout with 5 bottom tabs. Design for both iOS and Android. Dark mode default.

BOTTOM TAB BAR:
- 5 tabs with icons and labels: Cases (Briefcase icon), Chat (MessageSquare icon), Deadlines (Clock icon), Documents (FileText icon), Settings (Settings icon).
- Tab bar: bg-zinc-900 border-t border-zinc-800, h-20 (accounting for safe area on iPhone). Active tab: text-blue-500 icon color, inactive: text-zinc-500. Active tab has a subtle dot indicator below the icon (w-1 h-1 rounded-full bg-blue-500).

CASES TAB (home):
- Top bar: "Cyphergy" wordmark on left (text-lg font-semibold text-white tracking-tight), notification bell icon on right with red badge count.
- Search bar below header: rounded-full bg-zinc-800 px-4 h-10 with Search icon and placeholder "Search cases..."
- Section heading: "Active Cases" with count badge.
- Scrollable list of case cards. Each card: rounded-xl bg-zinc-900 border border-zinc-800 p-4 mb-3. Content: Case title in font-semibold text-white, court name in text-xs text-zinc-400, a status badge (rounded-full px-2 py-0.5 text-xs — green bg-green-500/20 text-green-400 "Active", amber bg-amber-500/20 text-amber-400 "Pending", red bg-red-500/20 text-red-400 "Urgent"). Below: a row of 3 mini stats — "3 deadlines" with clock icon, "12 citations" with book icon, "85% confidence" with shield icon, all in text-xs text-zinc-500.
- Pull-to-refresh indicator (spinner at top when pulling down).
- Empty state: illustration placeholder area + "No cases yet" heading + "Start by telling us about your situation" + primary "Get Started" button.

CHAT TAB:
- Same conversational interface as the web version but adapted for mobile.
- Messages take full width minus 16px padding. User bubbles: bg-blue-600 rounded-2xl rounded-br-sm. AI bubbles: bg-zinc-800 rounded-2xl rounded-bl-sm.
- Confidence badges inline at bottom of AI messages (same green/amber/red system).
- Input bar fixed at bottom with safe area padding. TextInput rounded-2xl bg-zinc-800, send button on right (bg-blue-600 rounded-full), attachment button on left.
- Keyboard-aware: input bar pushes up when keyboard appears using KeyboardAvoidingView behavior.

DEADLINES TAB:
- Header: "Deadlines" title + filter toggle (Upcoming / Overdue / All).
- Alert banner at top if any overdue: bg-red-500/10 border border-red-500/20 rounded-xl p-3 with text "2 overdue deadlines" and ChevronRight.
- List of deadline items grouped by time period ("This Week", "Next Week", "This Month"). Each item: left color bar (4px wide, red/amber/blue/green), deadline title, case name in text-xs text-zinc-400, days remaining badge, and rule citation in text-xs.
- Tapping a deadline expands it inline to show: full calculation breakdown, confidence score, "Add to Calendar" button, and "View in Case" link.

DOCUMENTS TAB:
- Grid view (2 columns) of document thumbnails. Each: rounded-xl bg-zinc-900 border border-zinc-800, document type icon (PDF, DOC, image), file name truncated, upload date in text-xs. Long press for context menu: Share, Download, Delete.
- Floating action button (bottom-right, rounded-full bg-blue-600 w-14 h-14 shadow-lg): Plus icon for uploading new documents. Opens a bottom sheet with options: "Take Photo", "Choose from Library", "Upload File".

SETTINGS TAB:
- Grouped list sections with section headers in text-xs text-zinc-500 uppercase tracking-wider.
- Section "Account": Profile, Email, Password, Subscription.
- Section "Preferences": Dark Mode toggle (Switch component, default on), Notifications toggle, Default Jurisdiction (Select).
- Section "Legal": Terms of Service, Privacy Policy, Disclaimer.
- Section "Support": Help Center, Contact Us, Version (text-xs text-zinc-600 "v1.0.0").
- Sign Out button at bottom: text-red-400, separated by a spacer.

OFFLINE INDICATOR:
- When no connectivity, a persistent banner slides down from the top: bg-amber-500 text-black text-xs font-medium py-1 text-center "You're offline — some features unavailable". Dismisses automatically when connection restores.

No marketing anywhere in the app. Clean, fast, native feel. All touch targets minimum 44x44 points. Smooth 60fps transitions.
```

---

## USAGE NOTES

1. Paste each prompt into v0.dev one at a time
2. After generation, export the React components
3. Place web components in `src/frontend/components/`
4. Place mobile components in `mobile/components/`
5. All components use shadcn/ui primitives — install with `npx shadcn-ui@latest init`
6. Prompts reference Cyphergy's real architecture: 5 agents (Lead Counsel, Research, Drafting, Red Team, Compliance), CourtListener verification chain, conservative deadline computation, WDC confidence scoring
7. No prompt contains marketing — marketing lives only on /pricing and /about pages, built separately
