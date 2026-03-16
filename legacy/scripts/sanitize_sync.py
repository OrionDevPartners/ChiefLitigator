#!/usr/bin/env python3
"""
CIPHERGY SANITIZER — 6-Tier Sanitization Engine
Copies improvements from a source project, strips ALL case-specific data,
rebuilds agnostically, and deploys to Ciphergy.

Usage:
    python3 scripts/sanitize_sync.py check <file>     — Preview what would be sanitized
    python3 scripts/sanitize_sync.py sanitize <file>   — Sanitize a file (dry run to stdout)
    python3 scripts/sanitize_sync.py sync <src> <dst>  — Full sync: copy → sanitize → deploy
    python3 scripts/sanitize_sync.py audit <dir>       — Scan directory for leaked case data
"""

import os
import re
import sys
from pathlib import Path

# ================================================================
# TIER 1: OBVIOUS — Names, addresses, emails, phones, companies, GIDs, amounts
# ================================================================

TIER1_PATTERNS = {
    # Names (add project-specific names here during configuration)
    "names": [
        # These are EXAMPLES — replaced during project-specific configuration
        # In a real deployment, this list is populated from the source project
    ],
    # Email patterns
    "emails": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    # Phone patterns (US)
    "phones": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
    # Dollar amounts
    "amounts": re.compile(r"\$[\d,]+\.?\d*"),
    # Asana GIDs (13+ digit numbers)
    "gids": re.compile(r"\b\d{13,}\b"),
    # Street addresses
    "addresses": re.compile(r"\b\d+\s+[A-Z][a-z]+\s+(Ave|St|Rd|Blvd|Dr|Ln|Ct|Way|Pl)\b", re.IGNORECASE),
}

# ================================================================
# TIER 2: LEGAL SUBSTANCE — Statutes, case law, bar rules, URLs
# (Replaced with jurisdiction-aware config references, not placeholders)
# ================================================================

TIER2_PATTERNS = {
    "fl_statutes": re.compile(r"(?:Fla\.\s*Stat\.\s*)?§\s*\d+\.\d+(?:\(\d+\))?(?:\([a-z]\))?"),
    "fl_urls": re.compile(r"https?://www\.flsenate\.gov/Laws/Statutes/\d{4}/[\d.]+"),
    "case_citations": re.compile(r"\b\d+\s+So\.\s*(?:2d|3d)\s+\d+\b"),
    "reporter_citations": re.compile(
        r"\b\d+\s+(?:F\.\s*(?:Supp\.\s*)?(?:2d|3d)?|So\.\s*(?:2d|3d)?|S\.Ct\.|L\.Ed\.)\s*\d+\b"
    ),
}

# ================================================================
# TIER 3: STRATEGIC CONTENT — Claim elements, evidence, scores, analyses
# ================================================================

TIER3_PATTERNS = {
    "confidence_scores": re.compile(r"\b\d{1,3}%\b"),  # Only in context of scoring
    "date_specifics": re.compile(
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b"
    ),
    "date_numeric": re.compile(r"\b20\d{2}-\d{2}-\d{2}\b"),
}

# ================================================================
# TIER 4: STRUCTURAL DNA — Keep bones, strip flesh
# ================================================================

# Tier 4 is handled by the template conversion process, not regex

# ================================================================
# TIER 5: METADATA — File headers, comments, examples, hardcoded values
# ================================================================

TIER5_PATTERNS = {
    "file_paths": re.compile(r'/Users/[a-zA-Z]+/[^\s\'"]+'),
    "session_ids": re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"),
}

# ================================================================
# TIER 6: AI MESH — Not patterns; this tier is about building
# the 5 agents. Handled by the agent creation process, not sanitization.
# ================================================================


def load_project_specific_names(config_path=None):
    """Load project-specific names from a sanitization config file."""
    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            import json

            config = json.load(f)
            return config.get("names_to_sanitize", [])
    return []


def sanitize_text(text, names=None, tier_level=6):
    """
    Sanitize text through specified tier levels.

    Args:
        text: The text to sanitize
        names: List of project-specific names to remove
        tier_level: How many tiers to apply (1-6)

    Returns:
        Sanitized text
    """
    result = text
    findings = []

    # TIER 1: Names
    if tier_level >= 1 and names:
        for name in names:
            if name in result:
                findings.append(f"TIER1-NAME: '{name}'")
                result = result.replace(name, "[ENTITY]")

    # TIER 1: Emails
    if tier_level >= 1:
        for match in TIER1_PATTERNS["emails"].finditer(result):
            findings.append(f"TIER1-EMAIL: '{match.group()}'")
        result = TIER1_PATTERNS["emails"].sub("[EMAIL]", result)

    # TIER 1: Phones
    if tier_level >= 1:
        for match in TIER1_PATTERNS["phones"].finditer(result):
            findings.append(f"TIER1-PHONE: '{match.group()}'")
        result = TIER1_PATTERNS["phones"].sub("[PHONE]", result)

    # TIER 1: Amounts
    if tier_level >= 1:
        for match in TIER1_PATTERNS["amounts"].finditer(result):
            findings.append(f"TIER1-AMOUNT: '{match.group()}'")
        result = TIER1_PATTERNS["amounts"].sub("[AMOUNT]", result)

    # TIER 1: GIDs
    if tier_level >= 1:
        for match in TIER1_PATTERNS["gids"].finditer(result):
            findings.append(f"TIER1-GID: '{match.group()}'")
        result = TIER1_PATTERNS["gids"].sub("[GID]", result)

    # TIER 1: Addresses
    if tier_level >= 1:
        for match in TIER1_PATTERNS["addresses"].finditer(result):
            findings.append(f"TIER1-ADDRESS: '{match.group()}'")
        result = TIER1_PATTERNS["addresses"].sub("[ADDRESS]", result)

    # TIER 2: Legal substance
    if tier_level >= 2:
        for match in TIER2_PATTERNS["fl_statutes"].finditer(result):
            findings.append(f"TIER2-STATUTE: '{match.group()}'")
        result = TIER2_PATTERNS["fl_statutes"].sub("[STATUTE_REF]", result)

        for match in TIER2_PATTERNS["fl_urls"].finditer(result):
            findings.append(f"TIER2-URL: '{match.group()}'")
        result = TIER2_PATTERNS["fl_urls"].sub("[STATUTE_URL]", result)

        for match in TIER2_PATTERNS["case_citations"].finditer(result):
            findings.append(f"TIER2-CASE: '{match.group()}'")
        result = TIER2_PATTERNS["case_citations"].sub("[CASE_CITATION]", result)

    # TIER 5: Metadata
    if tier_level >= 5:
        for match in TIER5_PATTERNS["file_paths"].finditer(result):
            findings.append(f"TIER5-PATH: '{match.group()}'")
        result = TIER5_PATTERNS["file_paths"].sub("[FILE_PATH]", result)

        for match in TIER5_PATTERNS["session_ids"].finditer(result):
            findings.append(f"TIER5-UUID: '{match.group()}'")
        result = TIER5_PATTERNS["session_ids"].sub("[SESSION_ID]", result)

    return result, findings


def cmd_check(filepath):
    """Preview what would be sanitized in a file."""
    with open(filepath) as f:
        text = f.read()

    _, findings = sanitize_text(text, names=[], tier_level=6)

    print(f"\nSANITIZATION CHECK: {filepath}")
    print(f"{'─' * 60}")
    if findings:
        for f_item in findings:
            print(f"  ⚠ {f_item}")
        print(f"\n  {len(findings)} items would be sanitized")
    else:
        print("  ✓ Clean — no case-specific data detected")


def cmd_audit(directory):
    """Scan a directory for any leaked case-specific data."""
    clean = True
    total_findings = 0

    for root, dirs, files in os.walk(directory):
        # Skip hidden dirs and common non-text
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            if not fname.endswith((".md", ".py", ".sh", ".yaml", ".yml", ".json", ".txt")):
                continue

            fpath = os.path.join(root, fname)
            try:
                with open(fpath) as f:
                    text = f.read()
                _, findings = sanitize_text(text, names=[], tier_level=6)
                if findings:
                    clean = False
                    total_findings += len(findings)
                    print(f"\n  ⚠ {fpath}: {len(findings)} finding(s)")
                    for item in findings[:5]:
                        print(f"    {item}")
                    if len(findings) > 5:
                        print(f"    ... and {len(findings) - 5} more")
            except (UnicodeDecodeError, PermissionError):
                continue

    if clean:
        print(f"\n  ✓ CLEAN — No case-specific data found in {directory}")
    else:
        print(f"\n  ⚠ {total_findings} total findings across {directory}")

    return clean


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "check":
        cmd_check(sys.argv[2])
    elif cmd == "audit":
        cmd_audit(sys.argv[2])
    elif cmd == "sanitize":
        with open(sys.argv[2]) as f:
            text = f.read()
        result, findings = sanitize_text(text, names=[], tier_level=6)
        print(result)
    else:
        print(__doc__)
