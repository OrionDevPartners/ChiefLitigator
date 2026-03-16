#!/usr/bin/env python3
"""Tests for sanitize_sync.py — Verifies zero case data leaks."""

import subprocess
import sys
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Case-specific terms that must NEVER appear in CIPHERGY
FORBIDDEN_TERMS = [
    "Pennington", "Campenni", "Palmisano", "Rapprich", "Collado", "Erickson",
    "Yupon", "Southard", "Flagler", "New Smyrna", "Volusia",
    "penningtonbros", "cpmproperties", "cfllawyer", "colladorealestate",
    "fortified-title", "touchstoneclosing",
    "504-343-3620", "603-234-0535", "386-451-5564",
    "1213575903318304", "1213575903318306", "1212370427563682",
    "bo@penningtonbros", "jim@cpmproperties", "bo@symio",
    "OrionDevPartners",
]

# Directories to scan (exclude legacy, node_modules, etc.)
SCAN_DIRS = ["agents", "config", "core", "docs", "scripts", "templates", ".claude"]
SCAN_EXTENSIONS = {".md", ".py", ".sh", ".yaml", ".yml", ".json", ".txt"}

def scan_file(filepath):
    """Scan a single file for forbidden terms. Returns list of (term, line_num, line)."""
    hits = []
    try:
        with open(filepath, "r") as f:
            for i, line in enumerate(f, 1):
                for term in FORBIDDEN_TERMS:
                    if term.lower() in line.lower():
                        hits.append((term, i, line.strip()[:80]))
    except (UnicodeDecodeError, PermissionError):
        pass
    return hits

def test_no_case_data_in_ciphergy():
    """Full scan of CIPHERGY for forbidden case-specific terms."""
    all_hits = []

    for scan_dir in SCAN_DIRS:
        dir_path = os.path.join(BASE, scan_dir)
        if not os.path.exists(dir_path):
            continue
        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') or d == '.claude']
            for fname in files:
                ext = os.path.splitext(fname)[1]
                if ext not in SCAN_EXTENSIONS:
                    continue
                fpath = os.path.join(root, fname)
                hits = scan_file(fpath)
                if hits:
                    all_hits.extend([(fpath, *h) for h in hits])

    if all_hits:
        print(f"  FAIL: {len(all_hits)} case data leak(s) found:")
        for fpath, term, line_num, line in all_hits[:10]:
            rel = os.path.relpath(fpath, BASE)
            print(f"    {rel}:{line_num} — '{term}' in: {line}")
        if len(all_hits) > 10:
            print(f"    ... and {len(all_hits) - 10} more")
        return False

    print(f"  PASS: Zero case data in {len(SCAN_DIRS)} directories")
    return True

def test_no_legacy_brand_references():
    """Verify old DuelAI branding is fully removed."""
    # NOTE: We search for the OLD brand name. "Ciphergy" is the CURRENT brand — it SHOULD be there.
    old_brand_terms = ["DuelAI", "duelai", "DUELAI", "duel_ai", "Duelai"]
    legacy_hits = []
    for scan_dir in SCAN_DIRS + ["."]:
        dir_path = os.path.join(BASE, scan_dir) if scan_dir != "." else BASE
        files_to_check = []
        if scan_dir == ".":
            files_to_check = [os.path.join(BASE, f) for f in os.listdir(BASE)
                             if os.path.isfile(os.path.join(BASE, f))
                             and os.path.splitext(f)[1] in SCAN_EXTENSIONS]
        else:
            if not os.path.exists(dir_path):
                continue
            for root, dirs, files in os.walk(dir_path):
                dirs[:] = [d for d in dirs if not d.startswith('.') or d == '.claude']
                for fname in files:
                    if os.path.splitext(fname)[1] in SCAN_EXTENSIONS:
                        files_to_check.append(os.path.join(root, fname))

        for fpath in files_to_check:
            try:
                with open(fpath) as f:
                    content = f.read()
                for term in old_brand_terms:
                    if term in content:
                        legacy_hits.append((fpath, term))
                        break
            except (UnicodeDecodeError, PermissionError):
                pass

    if legacy_hits:
        print(f"  FAIL: Legacy brand references found in {len(legacy_hits)} file(s):")
        for f, term in legacy_hits[:5]:
            print(f"    {os.path.relpath(f, BASE)} — '{term}'")
        return False

    print(f"  PASS: Zero legacy brand references")
    return True

def test_sanitizer_runs():
    """sanitize_sync.py audit should run without errors."""
    result = subprocess.run(
        [sys.executable, os.path.join(BASE, "scripts", "sanitize_sync.py"), "audit", BASE],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"Audit failed: {result.stderr}"
    print(f"  PASS: sanitize_sync.py audit runs clean")
    return True

if __name__ == "__main__":
    print("\nCIPHERGY — SANITIZATION TESTS")
    print("=" * 50)

    results = []
    for test in [test_no_case_data_in_ciphergy, test_no_legacy_brand_references, test_sanitizer_runs]:
        try:
            results.append(test())
        except Exception as e:
            print(f"  ERROR: {test.__name__}: {e}")
            results.append(False)

    passed = sum(1 for r in results if r)
    failed = len(results) - passed
    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed")
    sys.exit(1 if failed > 0 else 0)
