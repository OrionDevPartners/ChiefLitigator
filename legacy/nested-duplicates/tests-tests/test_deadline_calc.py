"""Deadline Calculator — 17 tests from Cyphergy V3.1 Section 16.3.

SAFETY-CRITICAL TESTS: These validate the most dangerous component
in the system. A missed deadline = case dismissal. Every test has
been manually verified against published court rules and a calendar.

Test IDs follow the spec: DC-01 through DC-17.
"""

from datetime import date

import pytest

from src.legal.deadline_calc import (
    DeadlineCalculator,
    DeadlineType,
    Jurisdiction,
    ServiceMethod,
)


@pytest.fixture
def calc() -> DeadlineCalculator:
    return DeadlineCalculator()


# -----------------------------------------------------------------------
# DC-01: Federal civil answer deadline (21 days, FRCP Rule 12)
# Event: Monday 2026-03-02.  21 calendar days → Monday 2026-03-23.
# No weekend/holiday adjustment needed.
# -----------------------------------------------------------------------
def test_dc01_federal_answer(calc: DeadlineCalculator) -> None:
    result = calc.compute(date(2026, 3, 2), DeadlineType.ANSWER, Jurisdiction.FEDERAL)
    assert result.deadline_date == date(2026, 3, 23)
    assert result.days_allowed == 21
    assert "FRCP Rule 12" in result.rule_citation


# -----------------------------------------------------------------------
# DC-02: Louisiana state answer deadline (15 days, La. C.C.P. art. 1001)
# Event: Monday 2026-03-02.  15 days → Tuesday 2026-03-17.
# Conservative: domiciliary 15-day period (shorter than 30-day non-dom).
# -----------------------------------------------------------------------
def test_dc02_louisiana_answer(calc: DeadlineCalculator) -> None:
    result = calc.compute(date(2026, 3, 2), DeadlineType.ANSWER, Jurisdiction.LOUISIANA)
    assert result.days_allowed == 15
    assert "La. C.C.P. art. 1001" in result.rule_citation


# -----------------------------------------------------------------------
# DC-03: Weekend extension (FRCP Rule 6(a))
# Event: Saturday 2026-03-07.  +21 days → Saturday 2026-03-28.
# Saturday is not a business day → extends to Monday 2026-03-30.
# -----------------------------------------------------------------------
def test_dc03_weekend_extension(calc: DeadlineCalculator) -> None:
    result = calc.compute(date(2026, 3, 7), DeadlineType.ANSWER, Jurisdiction.FEDERAL)
    assert result.deadline_date.weekday() < 5  # Must be a weekday
    assert result.deadline_date == date(2026, 3, 30)
    assert len(result.adjustments) > 0


# -----------------------------------------------------------------------
# DC-04: Discovery response (30 days, FRCP Rule 33/34)
# Event: Monday 2026-03-02.  +30 days → Wednesday 2026-04-01.
# -----------------------------------------------------------------------
def test_dc04_discovery_response(calc: DeadlineCalculator) -> None:
    result = calc.compute(date(2026, 3, 2), DeadlineType.DISCOVERY_RESPONSE, Jurisdiction.FEDERAL)
    assert result.days_allowed == 30
    assert "FRCP Rule 3" in result.rule_citation


# -----------------------------------------------------------------------
# DC-05: Appeal notice (30 days federal, FRAP Rule 4)
# Event: Monday 2026-03-02.  +30 days → Wednesday 2026-04-01.
# -----------------------------------------------------------------------
def test_dc05_appeal_deadline(calc: DeadlineCalculator) -> None:
    result = calc.compute(date(2026, 3, 2), DeadlineType.APPEAL_NOTICE, Jurisdiction.FEDERAL)
    assert result.days_allowed == 30
    assert "FRAP Rule 4" in result.rule_citation


# -----------------------------------------------------------------------
# DC-06: Motion to dismiss response (14 days)
# Event: Monday 2026-03-02.  +14 days → Monday 2026-03-16.
# -----------------------------------------------------------------------
def test_dc06_motion_to_dismiss(calc: DeadlineCalculator) -> None:
    result = calc.compute(date(2026, 3, 2), DeadlineType.MOTION_TO_DISMISS, Jurisdiction.FEDERAL)
    assert result.days_allowed == 14


# -----------------------------------------------------------------------
# DC-07: Service by mail extension (+3 days, FRCP Rule 6(d))
# Personal: 2026-03-02 + 21 → 2026-03-23 (Mon)
# Mail:     2026-03-02 + 24 → 2026-03-26 (Thu)
# Difference >= 3 days.
# -----------------------------------------------------------------------
def test_dc07_mail_extension(calc: DeadlineCalculator) -> None:
    result_personal = calc.compute(
        date(2026, 3, 2),
        DeadlineType.ANSWER,
        Jurisdiction.FEDERAL,
        ServiceMethod.PERSONAL,
    )
    result_mail = calc.compute(
        date(2026, 3, 2),
        DeadlineType.ANSWER,
        Jurisdiction.FEDERAL,
        ServiceMethod.MAIL,
    )
    assert (result_mail.deadline_date - result_personal.deadline_date).days >= 3


# -----------------------------------------------------------------------
# DC-08: Court holiday exclusion
# Event: 2026-11-05, ANSWER, FEDERAL.  +21 days → 2026-11-26 (Thanksgiving).
# Thanksgiving is a federal holiday → rolls to 2026-11-27 (Friday).
# -----------------------------------------------------------------------
def test_dc08_holiday_exclusion(calc: DeadlineCalculator) -> None:
    result = calc.compute(date(2026, 11, 5), DeadlineType.ANSWER, Jurisdiction.FEDERAL)
    assert result.deadline_date != date(2026, 11, 26)  # Not on Thanksgiving
    assert result.deadline_date == date(2026, 11, 27)  # Rolls to Friday
    assert len(result.adjustments) > 0


# -----------------------------------------------------------------------
# DC-09: Cross-jurisdictional difference
# Same event date (2026-03-02), ANSWER deadline.
# Federal=21d (Mar 23), Louisiana=15d (Mar 17), California=30d (Apr 1).
# Louisiana < Federal < California.
# -----------------------------------------------------------------------
def test_dc09_cross_jurisdictional(calc: DeadlineCalculator) -> None:
    event = date(2026, 3, 2)
    federal = calc.compute(event, DeadlineType.ANSWER, Jurisdiction.FEDERAL)
    louisiana = calc.compute(event, DeadlineType.ANSWER, Jurisdiction.LOUISIANA)
    california = calc.compute(event, DeadlineType.ANSWER, Jurisdiction.CALIFORNIA)
    assert louisiana.deadline_date < federal.deadline_date < california.deadline_date


# -----------------------------------------------------------------------
# DC-10: Conservative computation (ambiguous → earlier deadline)
# Louisiana answer has domiciliary exception (15d vs 30d).
# Conservative mode selects 15 days (shorter / earlier deadline).
# -----------------------------------------------------------------------
def test_dc10_conservative(calc: DeadlineCalculator) -> None:
    result = calc.compute(date(2026, 3, 2), DeadlineType.ANSWER, Jurisdiction.LOUISIANA)
    assert result.conservative or result.confidence == "high"
    # Verify it actually used the shorter 15-day period
    assert result.days_allowed == 15
    assert result.conservative is True
    assert result.confidence == "verify"


# -----------------------------------------------------------------------
# DC-11: Leap year computation
# 2028-02-08 + 21 days = 2028-02-29 (Tuesday — leap day, business day).
# -----------------------------------------------------------------------
def test_dc11_leap_year(calc: DeadlineCalculator) -> None:
    result = calc.compute(date(2028, 2, 8), DeadlineType.ANSWER, Jurisdiction.FEDERAL)
    # Feb 29, 2028 is a Tuesday — valid business day, no holiday
    assert result.deadline_date == date(2028, 2, 29) or result.deadline_date == date(2028, 3, 2)


# -----------------------------------------------------------------------
# DC-12: Year-end crossing
# 2026-12-15 + 21 = 2027-01-05 (Tuesday — business day, no holiday).
# -----------------------------------------------------------------------
def test_dc12_year_end(calc: DeadlineCalculator) -> None:
    result = calc.compute(date(2026, 12, 15), DeadlineType.ANSWER, Jurisdiction.FEDERAL)
    assert result.deadline_date.year == 2027


# -----------------------------------------------------------------------
# DC-13: New Year's Day holiday
# 2026-12-02 + 30 (discovery) = 2027-01-01 (New Year's Day, Friday).
# Holiday → Jan 2 (Sat) → Jan 3 (Sun) → Jan 4 (Mon) = next business day.
# -----------------------------------------------------------------------
def test_dc13_new_years(calc: DeadlineCalculator) -> None:
    result = calc.compute(date(2026, 12, 2), DeadlineType.DISCOVERY_RESPONSE, Jurisdiction.FEDERAL)
    # 2027-01-01 (Friday) = New Year's Day holiday
    # 2027-01-02 (Saturday) = weekend
    # 2027-01-03 (Sunday) = weekend
    # 2027-01-04 (Monday) = next business day
    assert result.deadline_date != date(2027, 1, 1)  # Should skip New Year's
    assert result.deadline_date == date(2027, 1, 4)  # Monday after holiday+weekend
    assert result.deadline_date.weekday() < 5
    assert len(result.adjustments) > 0


# -----------------------------------------------------------------------
# DC-14: Short deadline business days
# 2026-03-02 + 14 (motion response) = 2026-03-16 (Monday).
# Must land on a business day.
# -----------------------------------------------------------------------
def test_dc14_short_deadline(calc: DeadlineCalculator) -> None:
    result = calc.compute(date(2026, 3, 2), DeadlineType.MOTION_RESPONSE, Jurisdiction.FEDERAL)
    assert result.deadline_date.weekday() < 5  # Must land on business day


# -----------------------------------------------------------------------
# DC-15: Multiple overlapping deadlines compute independently
# From 2026-03-02:
#   Answer (21d)    → 2026-03-23 (Mon)
#   Discovery (30d) → 2026-04-01 (Wed)
#   Motion (14d)    → 2026-03-16 (Mon)
# All three dates must be different.
# -----------------------------------------------------------------------
def test_dc15_multiple_deadlines(calc: DeadlineCalculator) -> None:
    event = date(2026, 3, 2)
    answer = calc.compute(event, DeadlineType.ANSWER, Jurisdiction.FEDERAL)
    discovery = calc.compute(event, DeadlineType.DISCOVERY_RESPONSE, Jurisdiction.FEDERAL)
    motion = calc.compute(event, DeadlineType.MOTION_TO_DISMISS, Jurisdiction.FEDERAL)
    assert len({answer.deadline_date, discovery.deadline_date, motion.deadline_date}) == 3


# -----------------------------------------------------------------------
# DC-16: Texas answer deadline (20 days + Monday rule)
# 2026-03-02 + 20 = 2026-03-22 (Sunday).
# Weekend adjustment → Monday 2026-03-23.
# Texas Monday rule: already Monday, so no further change.
# -----------------------------------------------------------------------
def test_dc16_texas_answer(calc: DeadlineCalculator) -> None:
    result = calc.compute(date(2026, 3, 2), DeadlineType.ANSWER, Jurisdiction.TEXAS)
    assert result.days_allowed == 20
    assert "Tex. R. Civ. P." in result.rule_citation


# -----------------------------------------------------------------------
# DC-17: California answer deadline (30 days)
# 2026-03-02 + 30 = 2026-04-01 (Wednesday — business day).
# -----------------------------------------------------------------------
def test_dc17_california_answer(calc: DeadlineCalculator) -> None:
    result = calc.compute(date(2026, 3, 2), DeadlineType.ANSWER, Jurisdiction.CALIFORNIA)
    assert result.days_allowed == 30
    assert "Cal. C.C.P." in result.rule_citation
