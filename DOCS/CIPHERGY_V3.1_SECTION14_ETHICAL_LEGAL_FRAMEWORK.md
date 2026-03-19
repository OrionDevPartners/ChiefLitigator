# CIPHERGY V3.1 — SECTION 14: ETHICAL & LEGAL FRAMEWORK

## Addition to Product Spec V3
## March 15, 2026

---

## DESIGN PHILOSOPHY

Ciphergy is a **tool founded in law**. Every user who finds this platform is already in — or approaching — litigation. They know the stakes. They don't need to be frightened; they need to be informed.

The framework follows three principles:
1. **Protect the platform** — legally airtight service agreement with verified acknowledgment
2. **Respect the user** — professional, clear language that informs without condescending
3. **Stay out of the way** — once acknowledged, disclaimers live in the footer and confidence flags, not in the user's face

---

## 14.1 ONBOARDING AUTHENTICATION & AGREEMENT

### A. Signup Identity Verification

Every account creation records:

```
SIGNUP RECORD
─────────────────────────────────────
user_id:          uuid
email:            verified (confirmation link required)
ip_address:       recorded at signup
geo_location:     derived from IP (country, state, city)
device_fingerprint: browser/device hash
signup_timestamp:  UTC with timezone offset
agreement_version: "SA-2026-03-v1"
scroll_completed:  true (required)
checkbox_checked:  true (required)
signature_hash:    SHA-256 of (user_id + agreement_version + timestamp)
```

**Authentication requirements:**
- Email verification (confirmation link before account activates)
- IP address logged on every signup AND every login
- Geo-tag (IP-derived location) stored — relevant for jurisdictional disclaimers
- Device fingerprint for fraud prevention
- All records immutable in the `user_agreements` table

### B. Service Agreement Flow (Forced Scroll + Acknowledge)

The onboarding agreement is a **single scrollable document** — not a popup, not a checkbox-at-the-bottom trick. The user must scroll to the end before the acknowledgment checkbox activates.

**UX Implementation:**

```
┌──────────────────────────────────────────────────────┐
│  CIPHERGY — SERVICE AGREEMENT                        │
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │                                              │    │
│  │  [Agreement text — scrollable area]          │    │
│  │                                              │    │
│  │  The user must scroll through the entire     │    │
│  │  document. A scroll progress indicator       │    │
│  │  shows position. The checkbox below          │    │
│  │  remains DISABLED (grayed out) until         │    │
│  │  the user has scrolled to the bottom.        │    │
│  │                                              │    │
│  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░ 68%          │    │
│  │                                              │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
│  ░ [DISABLED] I have read and acknowledge the        │
│    Ciphergy Service Agreement, including the         │
│    litigation tool disclaimers in Section 4.         │
│                                                      │
│  ░ [DISABLED] Create My Account                      │
│                                                      │
└──────────────────────────────────────────────────────┘

After scrolling to 100%:

│  ☑ [ENABLED] I have read and acknowledge the         │
│    Ciphergy Service Agreement, including the          │
│    litigation tool disclaimers in Section 4.          │
│                                                       │
│  [ Create My Account ]  ← now active                  │
```

**Technical enforcement:**
- `scroll_position` tracked via `IntersectionObserver` on a sentinel element at the document bottom
- Checkbox `disabled` attribute removed only when sentinel is observed
- Scroll-to-bottom timestamp recorded (prevents automated fast-scrolling detection: if scroll time < 30 seconds for a document of this length, prompt "Please take a moment to review the agreement")
- No "Accept All" shortcut — the user scrolls and checks

### C. Agreement Re-Acknowledgment

- **On major agreement updates:** User prompted to review and re-acknowledge before continuing to use the platform. Same scroll requirement applies.
- **On jurisdiction change:** If user adds a matter in a new state/jurisdiction, a brief jurisdictional supplement appears (not full re-scroll — just the new jurisdiction's specific notes).

---

## 14.2 SERVICE AGREEMENT CONTENT

The agreement is written in **plain English** — no legalese walls. Organized in numbered sections for quick reference. Tone: professional, direct, respectful.

### Section 1: What Ciphergy Is

> Ciphergy is an AI-powered litigation support tool. It uses artificial intelligence to help you research legal issues, draft documents, manage deadlines, and develop case strategy.
>
> Ciphergy is a tool — like a word processor, a legal research database, or a case management system. It is a powerful tool, but it is still a tool. It does not replace a licensed attorney. It does not create an attorney-client relationship between you and Ciphergy, its creators, or any AI system.

### Section 2: What Ciphergy Does

> Ciphergy can:
> - Research statutes, case law, and court rules
> - Draft motions, pleadings, briefs, demand letters, and other legal documents
> - Track deadlines and compute filing dates
> - Analyze claims, defenses, and case strategy
> - Organize evidence and manage case files
> - Simulate opposing counsel arguments to stress-test your position
>
> Every output is generated by AI and reviewed through a multi-agent debate process designed to catch errors. But no AI system is perfect, and no automated review replaces human judgment.

### Section 3: What Ciphergy Does NOT Do

> Ciphergy does not:
> - Practice law or provide legal advice within the meaning of any state's unauthorized practice of law statutes
> - Create an attorney-client relationship
> - Guarantee the accuracy of any legal citation, deadline, or analysis
> - Appear in court or file documents on your behalf
> - Protect your communications under attorney-client privilege — communications with AI systems are generally not privileged
> - Replace the judgment of a licensed attorney for complex or high-stakes matters
>
> You are responsible for every document you file, every deadline you track, and every decision you make in your case.

### Section 4: Litigation Tool Disclaimers

> **4.1 — AI-Generated Content**
> All legal research, document drafts, and strategic analysis produced by Ciphergy are generated by artificial intelligence. While the system uses multiple AI agents to review and verify output, AI can produce errors including incorrect citations, outdated legal authority, miscalculated deadlines, and flawed analysis. You should independently verify all output before relying on it.
>
> **4.2 — Citation Verification**
> Ciphergy attempts to verify every legal citation through public databases. Citations that cannot be verified are flagged. However, full citation verification (KeyCite, Shepard's) requires access to premium legal databases (Westlaw, LexisNexis) that are not included in the standard subscription. You should verify critical citations through these services, through Google Scholar, or through your local law library before citing them in court filings.
>
> **4.3 — Deadline Accuracy**
> Ciphergy computes deadlines using published rules of civil procedure, local rules, and court calendars. However, courts change rules, modify holiday schedules, and issue orders that alter standard deadlines. You should independently verify all deadlines against the applicable rules and any court orders in your case.
>
> **4.4 — Jurisdictional Limitations**
> Laws vary significantly between jurisdictions. Ciphergy covers federal law and an expanding set of state jurisdictions. Coverage for your specific jurisdiction may be limited. Always confirm that the legal authority cited applies in your jurisdiction.
>
> **4.5 — Litigation Risk**
> Litigation inherently involves risk, including the risk of unfavorable outcomes, sanctions, adverse judgments, and cost. Ciphergy helps you make informed decisions, but no tool can eliminate the inherent uncertainty of legal proceedings.
>
> **4.6 — Privilege Warning**
> Communications with AI systems — including Ciphergy — are generally not protected by attorney-client privilege. Exercise appropriate judgment about the information you share. If privilege protection is critical, consult a licensed attorney.

### Section 5: Your Responsibilities

> By using Ciphergy, you acknowledge that:
>
> 1. You are responsible for reviewing all output before filing it with any court or sending it to any party
> 2. You will independently verify legal citations, deadlines, and jurisdictional requirements
> 3. You understand that AI-generated content may contain errors
> 4. You will not hold Ciphergy liable for outcomes in your legal proceedings
> 5. You will comply with all applicable court rules and ethical obligations
> 6. You will seek licensed legal counsel when the complexity or stakes of your matter warrant it

### Section 6: Data & Privacy (Summary)

> Your case data is yours. Ciphergy processes your data to provide the service. Your data is encrypted in transit and at rest. Your data is not used to train AI models. You can export all your data at any time. You can delete your account and all associated data at any time. Full privacy details are in the Privacy Policy [link].

### Section 7: Limitation of Liability

> Ciphergy is provided "as is." To the maximum extent permitted by law, Ciphergy's total liability for any claim arising from your use of the platform shall not exceed the amount you paid for the service in the 12 months preceding the claim. Ciphergy is not liable for any outcome in your legal proceedings, including but not limited to adverse judgments, sanctions, missed deadlines, or incorrect legal analysis.

### Section 8: Dispute Resolution

> Any dispute arising from your use of Ciphergy shall be resolved through binding arbitration under the rules of [AAA/JAMS] in [jurisdiction], except that either party may seek injunctive relief in any court of competent jurisdiction. Class action waiver: you agree to resolve disputes individually, not as part of a class or representative action.
>
> *(Note: the irony of an arbitration clause in a litigation tool is acknowledged. This is standard SaaS practice and protects the platform from class actions.)*

### Section 9: Changes to Agreement

> Ciphergy may update this agreement. Material changes require re-acknowledgment (scroll + checkbox). Non-material changes take effect upon posting. You will be notified of all changes via email and in-app notification.

---

## 14.3 PERSISTENT FOOTER DISCLAIMER

After onboarding, the agreement lives in the background. A persistent footer disclaimer appears on every page:

```
┌──────────────────────────────────────────────────────────────────┐
│  [Main application content]                                      │
│                                                                  │
│                                                                  │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  Ciphergy is an AI litigation support tool, not a law firm.      │
│  Verify all citations and deadlines independently.               │
│  Service Agreement · Privacy Policy · Support                    │
└──────────────────────────────────────────────────────────────────┘
```

**Design specifications:**
- Single line of text — doesn't eat screen real estate
- Muted color (gray text on slightly darker background) — visible but not distracting
- Links to full Service Agreement and Privacy Policy
- Always present, never dismissible
- On mobile: collapses to icon that expands on tap

**Per-output confidence flags** (inline, not footer):
- Appear directly on AI-generated content where relevant
- High confidence: no flag (clean output)
- Moderate confidence: small amber indicator — "[Verify in your jurisdiction]"
- Low confidence / unverified citation: red indicator — "[UNVERIFIED — confirm before relying]"
- These are contextual, not generic — they flag specific assertions, not entire documents

---

## 14.4 REGULATORY COMPLIANCE MATRIX

### Current Regulatory Landscape

| Regulation | Applicability | Ciphergy Compliance Mechanism |
|------------|--------------|------------------------------|
| **State UPL statutes** | Every US state | Service Agreement §1, §3: explicitly disclaims legal practice; tool, not lawyer |
| **EU AI Act (Article 14)** | If serving EU users | HITL gates (WDC approval + user review before filing); audit trail; transparency |
| **EU AI Act — High Risk** | Legal AI classified as high-risk | Risk assessment documentation; human oversight; data quality (anti-hallucination loop) |
| **GDPR** | EU users | Data minimization, right to erasure, DPA with processors, privacy by design |
| **CCPA/CPRA** | California users | Right to know, right to delete, opt-out of sale (N/A — we don't sell data) |
| **State data breach notification** | All US states | Incident response plan; notification within state-specific timeframes |
| **ABA Model Rule 1.1** | Attorney users | Documentation of how system works; transparent methodology |
| **State bar AI guidelines** | Varies by state (growing) | Track and comply as states issue guidance; configurable per jurisdiction |
| **FTC Act §5** | Consumer protection | No deceptive claims about AI capabilities; clear disclaimers |

### State Bar AI Guidelines Tracker

Several states have issued or are developing AI-in-legal-practice guidelines. Ciphergy tracks these and adapts:

| State | Status | Key Requirements | Ciphergy Compliance |
|-------|--------|-----------------|-------------------|
| California | Proposed rules (2025) | Disclosure of AI use in filings | Template includes AI disclosure language |
| Florida | Standing order (varies by judge) | AI-generated content must be verified | Anti-hallucination loop + user verification requirement |
| Texas | Guidelines issued (2025) | Attorney responsible for AI output | Service Agreement §5 — user responsibility |
| New York | Rules proposed (2025) | Certification that AI citations verified | Citation verification pipeline + user certification prompt |
| Federal (various) | Standing orders per judge | Varies — some require disclosure, some ban AI | Configurable per-court compliance; judge profile includes AI stance |

**Implementation:** When a user identifies their jurisdiction and court, Compliance Counsel checks the Judge Profile Database for AI-specific standing orders and alerts the user if disclosure or certification is required.

---

## 14.5 DATABASE SCHEMA FOR AGREEMENTS

```sql
-- User agreements tracking
CREATE TABLE user_agreements (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    agreement_version VARCHAR(20) NOT NULL,  -- e.g., "SA-2026-03-v1"

    -- Authentication data
    ip_address      INET NOT NULL,
    geo_country     VARCHAR(2),              -- ISO 3166-1 alpha-2
    geo_region      VARCHAR(100),            -- state/province
    geo_city        VARCHAR(100),
    device_fingerprint VARCHAR(64),          -- SHA-256 hash
    user_agent      TEXT,

    -- Scroll verification
    scroll_started_at   TIMESTAMPTZ NOT NULL,
    scroll_completed_at TIMESTAMPTZ NOT NULL,
    scroll_duration_seconds INTEGER NOT NULL,

    -- Acknowledgment
    checkbox_checked_at TIMESTAMPTZ NOT NULL,
    signature_hash      VARCHAR(64) NOT NULL, -- SHA-256(user_id + version + timestamp)

    -- Metadata
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT min_scroll_duration CHECK (scroll_duration_seconds >= 30)
);

-- Index for quick lookup
CREATE INDEX idx_user_agreements_user ON user_agreements(user_id);
CREATE INDEX idx_user_agreements_version ON user_agreements(agreement_version);

-- Login audit trail
CREATE TABLE login_audit (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    ip_address      INET NOT NULL,
    geo_country     VARCHAR(2),
    geo_region      VARCHAR(100),
    geo_city        VARCHAR(100),
    device_fingerprint VARCHAR(64),
    login_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    success         BOOLEAN NOT NULL
);

CREATE INDEX idx_login_audit_user ON login_audit(user_id);
```

---

## 14.6 CONFIDENCE FLAG SYSTEM (IN-APP)

Confidence flags are the primary ongoing disclosure mechanism — they appear on specific assertions, not as generic banners.

### Flag Taxonomy

| Flag | Visual | When Applied | User Action |
|------|--------|-------------|-------------|
| **Verified** | Green check (subtle) | Citation passed 5-step verification; statute confirmed current | None needed |
| **Verify** | Amber dot | Based on training data; may be jurisdiction-dependent; recently amended area of law | User should confirm in their jurisdiction |
| **Unverified** | Red dot | Citation could not be verified; source unavailable; confidence below threshold | User MUST independently verify before relying |
| **Computed** | Blue clock | Deadline computed from rules; holidays accounted for | User should verify against court calendar |
| **AI Analysis** | Gray brain icon | Strategic recommendation; case assessment; viability scoring | User should apply their own judgment |

### Display Rules

1. **Flags are inline** — they appear next to the specific assertion, citation, or deadline. Not in a separate panel.
2. **Flags don't interrupt** — they're visible but don't block the user from reading or working.
3. **Flags are interactive** — clicking/tapping a flag shows the verification details (what was checked, what the source was, when it was verified).
4. **High confidence = clean** — when everything checks out, the output is clean. No unnecessary flags. The system is confident and shows it.
5. **Only flag what needs flagging** — the goal is signal, not noise. A document that's 95% verified should highlight the 5% that needs attention, not plaster every line with green checks.

### Example: Motion to Compel Draft

```
MOTION TO COMPEL PRODUCTION OF DOCUMENTS

Defendant ABC Corporation has failed to produce documents
responsive to Plaintiff's First Request for Production,
served on January 15, 2026, in violation of FRCP Rule 34(b)(2)(A) ✓
which requires a response within 30 days of service. ⏱ Computed: Feb 14, 2026

Despite Plaintiff's good faith meet-and-confer efforts on
February 20, 2026 (Exhibit A), Defendant has provided no
substantive response.

Courts routinely grant motions to compel where the responding
party fails to timely respond. See Johnson v. Williams,
847 F.3d 1142 (9th Cir. 2024) ✓ (verified — CourtListener)
("A complete failure to respond to discovery requests
constitutes a waiver of all objections.")

Under FRCP Rule 37(a)(5)(A), the Court shall award reasonable
expenses including attorney's fees incurred in making this
motion, unless the opposing party's nondisclosure was
substantially justified. ✓

Plaintiff respectfully requests sanctions in the amount of
$1,200, representing 8 hours of preparation at $150/hour. 🧠
[AI Analysis: Sanctions amount is reasonable for this motion
 type; courts in the 9th Circuit typically award $800-2,500
 for routine motions to compel]
```

The user sees: verified citations (green), computed deadlines (blue), and one AI analysis flag (gray) on the sanctions amount. Clean, professional, trustworthy.

---

## 14.7 JURISDICTIONAL DISCLOSURE AUTOMATION

When Compliance Counsel detects that the user's court or judge has an AI-disclosure requirement:

```
┌──────────────────────────────────────────────────────────┐
│  ⚖️  JUDICIAL AI DISCLOSURE NOTICE                       │
│                                                          │
│  Judge Mitchell (E.D. Louisiana) has a standing order    │
│  requiring parties to disclose the use of AI tools in    │
│  preparing court filings. (Standing Order 2025-14)       │
│                                                          │
│  Ciphergy has prepared the required disclosure language   │
│  for inclusion in your filing:                           │
│                                                          │
│  "Portions of this filing were prepared with the         │
│  assistance of an AI litigation support tool. All        │
│  legal citations have been independently verified        │
│  by the undersigned through [Westlaw/Google Scholar/     │
│  CourtListener]. The undersigned accepts full            │
│  responsibility for the content of this filing."         │
│                                                          │
│  [ Include in Filing ]    [ Review Standing Order ]      │
└──────────────────────────────────────────────────────────┘
```

This is proactive and helpful — not scary. It says "your judge requires this, here's the language, we've drafted it for you."

---

## 14.8 FRAMEWORK SUMMARY

| Layer | What It Does | When User Sees It |
|-------|-------------|-------------------|
| **Service Agreement** | Full legal protection; forced-scroll + acknowledge | Once at signup; again on material updates |
| **Signup Authentication** | IP, geo, device, timestamp, signature hash | Once at signup (invisible to user — backend) |
| **Footer Disclaimer** | Persistent one-line reminder | Every page, always |
| **Confidence Flags** | Inline verification status on specific assertions | During work, on AI output |
| **Jurisdictional Alerts** | Court/judge-specific AI disclosure requirements | When filing in courts with AI standing orders |
| **Re-acknowledgment** | Material agreement changes | Only when agreement changes materially |

**The user experience:**
1. Sign up → scroll the agreement → understand what the tool is and isn't → acknowledge → done
2. Use the platform → see clean output with occasional flags on items that need verification
3. Footer is always there as a quiet reminder
4. If their judge has AI rules, the system handles it for them

**No fear. Full protection. Professional trust.**

---

*This framework protects the platform legally while respecting the user's intelligence. They came here because they're in litigation — they already know the stakes. We inform them clearly, once, with the service agreement. Then we get out of their way and help them win.*
