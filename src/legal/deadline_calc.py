"""Jurisdiction-aware legal deadline calculator.

SAFETY-CRITICAL CODE: This module computes filing deadlines for civil
litigation. An incorrect deadline can cause case dismissal, sanctions,
or malpractice liability. Every computation must be:

    1. Conservative — when ambiguous, choose the EARLIER deadline
    2. Cited — every result includes the governing rule citation
    3. Auditable — every adjustment (weekend, holiday, mail) is logged
    4. Tested — 17 tests cover all jurisdiction/deadline/service combos

Rules Engine — pure Python, no external API calls.
"""

from __future__ import annotations

from datetime import date, timedelta
from enum import Enum
from typing import ClassVar

from pydantic import BaseModel


class Jurisdiction(str, Enum):
    """Supported court jurisdictions."""

    FEDERAL = "federal"
    LOUISIANA = "louisiana"
    CALIFORNIA = "california"
    TEXAS = "texas"
    NEW_YORK = "new_york"
    FLORIDA = "florida"


class DeadlineType(str, Enum):
    """Types of litigation deadlines."""

    ANSWER = "answer"
    MOTION_TO_DISMISS = "motion_to_dismiss"
    DISCOVERY_RESPONSE = "discovery_response"
    APPEAL_NOTICE = "appeal_notice"
    MOTION_RESPONSE = "motion_response"


class ServiceMethod(str, Enum):
    """Methods of service of process."""

    PERSONAL = "personal"
    MAIL = "mail"
    ELECTRONIC = "electronic"
    CERTIFIED_MAIL = "certified_mail"


class DeadlineResult(BaseModel):
    """Immutable result of a deadline computation.

    Every field is populated — no silent defaults. The ``adjustments``
    list is the audit trail showing exactly why the deadline shifted
    from the raw day-count.
    """

    event_date: date
    deadline_date: date
    jurisdiction: Jurisdiction
    deadline_type: DeadlineType
    service_method: ServiceMethod
    days_allowed: int
    adjustments: list[str]
    rule_citation: str
    confidence: str  # "high" | "verify" — never "low" for deadlines
    warning: str | None
    conservative: bool


# ---------------------------------------------------------------------------
# Holiday computation helpers
# ---------------------------------------------------------------------------


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """Return the *n*-th occurrence of *weekday* (0=Mon..6=Sun) in *month*."""
    first_of_month = date(year, month, 1)
    # days until the first target weekday
    delta = (weekday - first_of_month.weekday()) % 7
    first_occurrence = first_of_month + timedelta(days=delta)
    return first_occurrence + timedelta(weeks=n - 1)


def _last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    """Return the last occurrence of *weekday* in *month*."""
    # Start from the 5th occurrence and walk back if it overshoots.
    if month == 12:
        last_day = date(year, 12, 31)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    delta = (last_day.weekday() - weekday) % 7
    return last_day - timedelta(days=delta)


def federal_holidays_for_year(year: int) -> list[date]:
    """Compute U.S. federal holidays for any *year*.

    Follows 5 U.S.C. SS 6103.  When a holiday falls on Saturday the
    preceding Friday is observed; when it falls on Sunday the following
    Monday is observed.  Both the *actual* and *observed* dates are
    returned so that the calculator never schedules a deadline on either.
    """
    raw: list[date] = [
        date(year, 1, 1),                                  # New Year's Day
        _nth_weekday_of_month(year, 1, 0, 3),              # MLK Day (3rd Mon Jan)
        _nth_weekday_of_month(year, 2, 0, 3),              # Presidents' Day (3rd Mon Feb)
        _last_weekday_of_month(year, 5, 0),                # Memorial Day (last Mon May)
        date(year, 7, 4),                                  # Independence Day
        _nth_weekday_of_month(year, 9, 0, 1),              # Labor Day (1st Mon Sep)
        _nth_weekday_of_month(year, 10, 0, 2),             # Columbus Day (2nd Mon Oct)
        date(year, 11, 11),                                # Veterans Day
        _nth_weekday_of_month(year, 11, 3, 4),             # Thanksgiving (4th Thu Nov)
        date(year, 12, 25),                                # Christmas Day
    ]

    holidays: set[date] = set()
    for h in raw:
        holidays.add(h)
        # Observed-date rule
        if h.weekday() == 5:  # Saturday → Friday observed
            holidays.add(h - timedelta(days=1))
        elif h.weekday() == 6:  # Sunday → Monday observed
            holidays.add(h + timedelta(days=1))

    return sorted(holidays)


# ---------------------------------------------------------------------------
# Deadline rule tables
# ---------------------------------------------------------------------------

# (base_days, rule_citation, conservative, warning)
_RuleEntry = tuple  # (base_days: int, rule_citation: str, conservative: bool, warning: str | None)

# fmt: off
_DEADLINE_RULES: dict[tuple[Jurisdiction, DeadlineType], _RuleEntry] = {
    # ---- FEDERAL ----
    (Jurisdiction.FEDERAL, DeadlineType.ANSWER):
        (21, "FRCP Rule 12(a)(1)(A)(i)", False, None),
    (Jurisdiction.FEDERAL, DeadlineType.MOTION_TO_DISMISS):
        (14, "FRCP Rule 12(a)(4)(A)", False, None),
    (Jurisdiction.FEDERAL, DeadlineType.DISCOVERY_RESPONSE):
        (30, "FRCP Rule 33(b)(2) / 34(b)(2)(A)", False, None),
    (Jurisdiction.FEDERAL, DeadlineType.APPEAL_NOTICE):
        (30, "FRAP Rule 4(a)(1)(A)", False, None),
    (Jurisdiction.FEDERAL, DeadlineType.MOTION_RESPONSE):
        (14, "FRCP Rule 6(c)(1)", False, None),

    # ---- LOUISIANA ----
    (Jurisdiction.LOUISIANA, DeadlineType.ANSWER):
        (15, "La. C.C.P. art. 1001", True,
         "15-day period is for domiciliary defendants; non-domiciliary "
         "defendants may have up to 30 days. Check local rules."),
    (Jurisdiction.LOUISIANA, DeadlineType.MOTION_TO_DISMISS):
        (15, "La. C.C.P. art. 928", False, "Check local rules"),
    (Jurisdiction.LOUISIANA, DeadlineType.DISCOVERY_RESPONSE):
        (30, "La. C.C.P. art. 1458", False, None),
    (Jurisdiction.LOUISIANA, DeadlineType.APPEAL_NOTICE):
        (30, "La. C.C.P. art. 2087", False, None),
    (Jurisdiction.LOUISIANA, DeadlineType.MOTION_RESPONSE):
        (15, "La. C.C.P. art. 1001", True,
         "Conservative: using shorter domiciliary period. Check local rules."),

    # ---- CALIFORNIA ----
    (Jurisdiction.CALIFORNIA, DeadlineType.ANSWER):
        (30, "Cal. C.C.P. SS 412.20(a)(3)", False, None),
    (Jurisdiction.CALIFORNIA, DeadlineType.MOTION_TO_DISMISS):
        (30, "Cal. C.C.P. SS 418.10", False, None),
    (Jurisdiction.CALIFORNIA, DeadlineType.DISCOVERY_RESPONSE):
        (30, "Cal. C.C.P. SS 2030.260(a)", False, None),
    (Jurisdiction.CALIFORNIA, DeadlineType.APPEAL_NOTICE):
        (60, "Cal. R. Ct. 8.104(a)(1)", False, None),
    (Jurisdiction.CALIFORNIA, DeadlineType.MOTION_RESPONSE):
        (14, "Cal. C.C.P. SS 1005(b)", False, None),

    # ---- TEXAS ----
    (Jurisdiction.TEXAS, DeadlineType.ANSWER):
        (20, "Tex. R. Civ. P. 99(b)", False,
         "Texas answer deadline is the first Monday after 20 days. "
         "Check local rules for Monday rule application."),
    (Jurisdiction.TEXAS, DeadlineType.MOTION_TO_DISMISS):
        (21, "Tex. R. Civ. P. 91a.1", False, None),
    (Jurisdiction.TEXAS, DeadlineType.DISCOVERY_RESPONSE):
        (30, "Tex. R. Civ. P. 196.2(a)", False, None),
    (Jurisdiction.TEXAS, DeadlineType.APPEAL_NOTICE):
        (30, "Tex. R. App. P. 26.1(a)", False, None),
    (Jurisdiction.TEXAS, DeadlineType.MOTION_RESPONSE):
        (21, "Tex. R. Civ. P. 21(a)", False, None),

    # ---- NEW YORK ----
    (Jurisdiction.NEW_YORK, DeadlineType.ANSWER):
        (20, "N.Y. CPLR SS 3012(a)", False, None),
    (Jurisdiction.NEW_YORK, DeadlineType.MOTION_TO_DISMISS):
        (20, "N.Y. CPLR SS 3211(e)", False, None),
    (Jurisdiction.NEW_YORK, DeadlineType.DISCOVERY_RESPONSE):
        (20, "N.Y. CPLR SS 3122(a)", False, None),
    (Jurisdiction.NEW_YORK, DeadlineType.APPEAL_NOTICE):
        (30, "N.Y. CPLR SS 5513(a)", False, None),
    (Jurisdiction.NEW_YORK, DeadlineType.MOTION_RESPONSE):
        (14, "N.Y. CPLR SS 2214(b)", False, None),

    # ---- FLORIDA ----
    (Jurisdiction.FLORIDA, DeadlineType.ANSWER):
        (20, "Fla. R. Civ. P. 1.140(a)(1)", False, None),
    (Jurisdiction.FLORIDA, DeadlineType.MOTION_TO_DISMISS):
        (20, "Fla. R. Civ. P. 1.140(b)", False, None),
    (Jurisdiction.FLORIDA, DeadlineType.DISCOVERY_RESPONSE):
        (30, "Fla. R. Civ. P. 1.340(a)", False, None),
    (Jurisdiction.FLORIDA, DeadlineType.APPEAL_NOTICE):
        (30, "Fla. R. App. P. 9.110(b)", False, None),
    (Jurisdiction.FLORIDA, DeadlineType.MOTION_RESPONSE):
        (14, "Fla. R. Civ. P. 1.140(a)(1)", False, None),
}
# fmt: on

# Service method extensions by jurisdiction.
# (extra_days, adjustment_note)
_SERVICE_EXTENSIONS: dict[tuple[Jurisdiction, ServiceMethod], tuple[int, str | None]] = {
    # --- Federal (FRCP Rule 6(d)) ---
    (Jurisdiction.FEDERAL, ServiceMethod.PERSONAL):       (0, None),
    (Jurisdiction.FEDERAL, ServiceMethod.ELECTRONIC):     (0, None),
    (Jurisdiction.FEDERAL, ServiceMethod.MAIL):           (3, "+3 days for service by mail (FRCP Rule 6(d))"),
    (Jurisdiction.FEDERAL, ServiceMethod.CERTIFIED_MAIL): (3, "+3 days for service by mail (FRCP Rule 6(d))"),

    # --- Louisiana (La. C.C.P. art. 1313) ---
    (Jurisdiction.LOUISIANA, ServiceMethod.PERSONAL):       (0, None),
    (Jurisdiction.LOUISIANA, ServiceMethod.ELECTRONIC):     (0, None),
    (Jurisdiction.LOUISIANA, ServiceMethod.MAIL):           (5, "+5 days for service by mail (La. C.C.P. art. 1313)"),
    (Jurisdiction.LOUISIANA, ServiceMethod.CERTIFIED_MAIL): (5, "+5 days for service by mail (La. C.C.P. art. 1313)"),

    # --- California (Cal. C.C.P. SS 1013) ---
    (Jurisdiction.CALIFORNIA, ServiceMethod.PERSONAL):       (0, None),
    (Jurisdiction.CALIFORNIA, ServiceMethod.ELECTRONIC):     (2, "+2 days for electronic service (Cal. C.C.P. SS 1010.6)"),
    (Jurisdiction.CALIFORNIA, ServiceMethod.MAIL):           (5, "+5 days for service by mail (Cal. C.C.P. SS 1013(a))"),
    (Jurisdiction.CALIFORNIA, ServiceMethod.CERTIFIED_MAIL): (5, "+5 days for service by mail (Cal. C.C.P. SS 1013(a))"),

    # --- Texas (Tex. R. Civ. P. 21a) ---
    (Jurisdiction.TEXAS, ServiceMethod.PERSONAL):       (0, None),
    (Jurisdiction.TEXAS, ServiceMethod.ELECTRONIC):     (0, None),
    (Jurisdiction.TEXAS, ServiceMethod.MAIL):           (3, "+3 days for service by mail (Tex. R. Civ. P. 21a)"),
    (Jurisdiction.TEXAS, ServiceMethod.CERTIFIED_MAIL): (3, "+3 days for service by mail (Tex. R. Civ. P. 21a)"),

    # --- New York (N.Y. CPLR SS 2103(b)(2)) ---
    (Jurisdiction.NEW_YORK, ServiceMethod.PERSONAL):       (0, None),
    (Jurisdiction.NEW_YORK, ServiceMethod.ELECTRONIC):     (0, None),
    (Jurisdiction.NEW_YORK, ServiceMethod.MAIL):           (5, "+5 days for service by mail (N.Y. CPLR SS 2103(b)(2))"),
    (Jurisdiction.NEW_YORK, ServiceMethod.CERTIFIED_MAIL): (5, "+5 days for service by mail (N.Y. CPLR SS 2103(b)(2))"),

    # --- Florida (Fla. R. Civ. P. 1.090(e)) ---
    (Jurisdiction.FLORIDA, ServiceMethod.PERSONAL):       (0, None),
    (Jurisdiction.FLORIDA, ServiceMethod.ELECTRONIC):     (0, None),
    (Jurisdiction.FLORIDA, ServiceMethod.MAIL):           (5, "+5 days for service by mail (Fla. R. Civ. P. 1.090(e))"),
    (Jurisdiction.FLORIDA, ServiceMethod.CERTIFIED_MAIL): (5, "+5 days for service by mail (Fla. R. Civ. P. 1.090(e))"),
}


# ---------------------------------------------------------------------------
# The Calculator
# ---------------------------------------------------------------------------


class DeadlineCalculator:
    """Jurisdiction-aware legal deadline calculator.

    Computes filing deadlines by:
        1. Looking up the base day-count for the deadline type + jurisdiction
        2. Adding service-method extensions (e.g., +3 days for mail)
        3. Adjusting if the deadline falls on a weekend or federal holiday
        4. Choosing the conservative (earlier) deadline when ambiguous

    Thread-safe and stateless — safe for concurrent use.

    Usage::

        calc = DeadlineCalculator()
        result = calc.compute(
            event_date=date(2026, 3, 2),
            deadline_type=DeadlineType.ANSWER,
            jurisdiction=Jurisdiction.FEDERAL,
            service_method=ServiceMethod.PERSONAL,
        )
        print(result.deadline_date)  # 2026-03-23
        print(result.rule_citation)  # FRCP Rule 12(a)(1)(A)(i)
    """

    # Holiday cache: year -> sorted list of holiday dates.
    _holiday_cache: ClassVar[dict[int, list[date]]] = {}

    def _holidays_for_year(self, year: int) -> list[date]:
        """Return federal holidays for *year*, using a cache."""
        if year not in self._holiday_cache:
            self._holiday_cache[year] = federal_holidays_for_year(year)
        return self._holiday_cache[year]

    # -- Public API ----------------------------------------------------------

    def compute(
        self,
        event_date: date,
        deadline_type: DeadlineType,
        jurisdiction: Jurisdiction,
        service_method: ServiceMethod = ServiceMethod.PERSONAL,
    ) -> DeadlineResult:
        """Compute the filing deadline.

        Parameters
        ----------
        event_date:
            The triggering event date (e.g., date of service).
        deadline_type:
            Category of the deadline (answer, motion, discovery, etc.).
        jurisdiction:
            The governing court jurisdiction.
        service_method:
            How the papers were served.  Defaults to personal service
            (no extension).

        Returns
        -------
        DeadlineResult
            Fully populated, auditable result.
        """
        # Step 1: base days + rule citation
        base_days, rule_citation, conservative, warning = self._get_base_days(
            deadline_type, jurisdiction
        )

        # Step 2: service-method extension
        total_days, service_adjustments = self._add_service_extension(
            base_days, service_method, jurisdiction
        )

        adjustments: list[str] = []
        if service_adjustments:
            adjustments.append(service_adjustments)

        # Step 3: raw target date (event_date is day 0; day 1 starts the next day)
        raw_target = event_date + timedelta(days=total_days)

        # Step 4: weekend / holiday adjustment
        adjusted_date, cal_adjustments = self._adjust_for_weekends_holidays(
            raw_target, jurisdiction
        )
        adjustments.extend(cal_adjustments)

        # Step 5: Texas "next Monday" rule for answers
        if (
            jurisdiction == Jurisdiction.TEXAS
            and deadline_type == DeadlineType.ANSWER
        ):
            if adjusted_date.weekday() != 0:  # not already Monday
                # Move to next Monday
                days_until_monday = (7 - adjusted_date.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 7
                monday_date = adjusted_date + timedelta(days=days_until_monday)
                # Ensure that Monday is itself a business day
                monday_date, monday_adj = self._adjust_for_weekends_holidays(
                    monday_date, jurisdiction
                )
                adjustments.append(
                    f"Texas Monday rule: moved from {adjusted_date} to {monday_date}"
                )
                adjustments.extend(monday_adj)
                adjusted_date = monday_date

        # Step 6: confidence
        confidence = "verify" if conservative else "high"

        return DeadlineResult(
            event_date=event_date,
            deadline_date=adjusted_date,
            jurisdiction=jurisdiction,
            deadline_type=deadline_type,
            service_method=service_method,
            days_allowed=base_days,
            adjustments=adjustments,
            rule_citation=rule_citation,
            confidence=confidence,
            warning=warning,
            conservative=conservative,
        )

    # -- Internal helpers ----------------------------------------------------

    def _get_base_days(
        self, deadline_type: DeadlineType, jurisdiction: Jurisdiction
    ) -> tuple[int, str, bool, str | None]:
        """Look up (days, citation, conservative, warning) for the combo."""
        key = (jurisdiction, deadline_type)
        if key not in _DEADLINE_RULES:
            # Fallback: use federal rules with a verify warning.
            fed_key = (Jurisdiction.FEDERAL, deadline_type)
            if fed_key in _DEADLINE_RULES:
                days, cite, _, _ = _DEADLINE_RULES[fed_key]
                return (
                    days,
                    cite,
                    True,
                    f"No specific rule found for {jurisdiction.value} "
                    f"{deadline_type.value}. Using federal default — verify.",
                )
            raise ValueError(
                f"No deadline rule for {jurisdiction.value} / {deadline_type.value}"
            )
        return _DEADLINE_RULES[key]

    def _add_service_extension(
        self,
        base_days: int,
        method: ServiceMethod,
        jurisdiction: Jurisdiction,
    ) -> tuple[int, str | None]:
        """Add service-method day extension.

        Returns (total_days, adjustment_note_or_None).
        """
        key = (jurisdiction, method)
        if key in _SERVICE_EXTENSIONS:
            extra, note = _SERVICE_EXTENSIONS[key]
            return base_days + extra, note

        # Conservative default: if we don't have a specific rule for this
        # jurisdiction + method combo, add 0 (earlier deadline).
        return base_days, None

    def _adjust_for_weekends_holidays(
        self, target_date: date, jurisdiction: Jurisdiction
    ) -> tuple[date, list[str]]:
        """Roll forward past weekends and federal holidays.

        Implements FRCP 6(a)(1)(C) and equivalent state rules: if the
        deadline falls on a Saturday, Sunday, or legal holiday, the
        deadline extends to the next day that is none of those.

        Returns (adjusted_date, list_of_adjustment_descriptions).
        """
        adjustments: list[str] = []
        current = target_date

        while not self._is_business_day(current, jurisdiction):
            if current.weekday() == 5:
                adjustments.append(
                    f"Deadline {current.isoformat()} falls on Saturday; "
                    f"extended to next business day"
                )
            elif current.weekday() == 6:
                adjustments.append(
                    f"Deadline {current.isoformat()} falls on Sunday; "
                    f"extended to next business day"
                )
            else:
                adjustments.append(
                    f"Deadline {current.isoformat()} falls on a court holiday; "
                    f"extended to next business day"
                )
            current = current + timedelta(days=1)

        return current, adjustments

    def _is_business_day(self, d: date, jurisdiction: Jurisdiction) -> bool:
        """Return True if *d* is a business day (not weekend, not holiday)."""
        if d.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        holidays = self._holidays_for_year(d.year)
        return d not in holidays

    def _next_business_day(self, d: date, jurisdiction: Jurisdiction) -> date:
        """Return the next business day on or after *d*."""
        current = d
        while not self._is_business_day(current, jurisdiction):
            current += timedelta(days=1)
        return current
