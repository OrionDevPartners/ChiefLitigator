#!/usr/bin/env python3
"""Tests for nerve_center.py — Smoke tests + domain-agnostic verification."""

import subprocess
import sys
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(BASE, "scripts")

def run_cmd(args):
    """Run a command and return (exit_code, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable] + args,
        capture_output=True, text=True, cwd=BASE
    )
    return result.returncode, result.stdout, result.stderr

def test_startup_runs_clean():
    """nerve_center.py startup should run without errors."""
    code, out, err = run_cmd([os.path.join(SCRIPTS, "nerve_center.py"), "startup"])
    assert code == 0, f"startup failed with exit code {code}: {err}"
    assert "STARTUP COMPLETE" in out, f"Missing STARTUP COMPLETE in output"
    print("  PASS: startup runs clean")

def test_deadlines_runs_clean():
    """nerve_center.py deadlines should run without errors."""
    code, out, err = run_cmd([os.path.join(SCRIPTS, "nerve_center.py"), "deadlines"])
    assert code == 0, f"deadlines failed: {err}"
    print("  PASS: deadlines runs clean")

def test_dashboard_runs_clean():
    """nerve_center.py dashboard should run without errors."""
    code, out, err = run_cmd([os.path.join(SCRIPTS, "nerve_center.py"), "dashboard"])
    assert code == 0, f"dashboard failed: {err}"
    print("  PASS: dashboard runs clean")

def test_no_case_data_in_output():
    """Startup output must contain zero case-specific data."""
    code, out, err = run_cmd([os.path.join(SCRIPTS, "nerve_center.py"), "startup"])
    leaked = []
    for term in ["Pennington", "Campenni", "Palmisano", "Rapprich", "Yupon",
                 "Southard", "Volusia", "504-343", "603-234", "bo@symio",
                 "penningtonbros", "cfllawyer", "colladorealestate"]:
        if term.lower() in out.lower():
            leaked.append(term)
    assert len(leaked) == 0, f"Case data leaked in output: {leaked}"
    print("  PASS: zero case data in output")

def test_domain_shows_in_startup():
    """Startup should display the configured domain."""
    code, out, err = run_cmd([os.path.join(SCRIPTS, "nerve_center.py"), "startup"])
    assert "Domain:" in out, "Domain not displayed in startup"
    print("  PASS: domain displayed in startup")

if __name__ == "__main__":
    print("\nCIPHERGY — NERVE CENTER TESTS")
    print("=" * 50)
    tests = [
        test_startup_runs_clean,
        test_deadlines_runs_clean,
        test_dashboard_runs_clean,
        test_no_case_data_in_output,
        test_domain_shows_in_startup,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {test.__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed")
    sys.exit(1 if failed > 0 else 0)
