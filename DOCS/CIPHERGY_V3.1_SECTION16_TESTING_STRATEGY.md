# CIPHERGY V3.1 — SECTION 16: TESTING STRATEGY

## Addition to Product Spec V3
## March 15, 2026

---

## DESIGN PHILOSOPHY

Legal accuracy is the product. Ciphergy does not sell software — it sells trust. A fabricated citation filed with a court can result in sanctions, case dismissal, or contempt. A miscalculated deadline can forfeit a client's right to respond. A hallucinated statute can destroy a legal argument that a pro se litigant spent months building.

Testing is not quality assurance in the traditional software sense. It is the **verification layer that prevents malpractice**. Every test in this document exists because the failure it catches would cause real harm to a real person in a real courtroom.

Three principles govern the testing strategy:

1. **Legal accuracy is binary** — A citation is real or fabricated. A deadline is correct or wrong. There is no "close enough" in litigation. Tests reflect this by using exact assertions, not fuzzy matching.

2. **Compound reliability demands layered testing** — Per E17, at 85% per-action accuracy, a 10-step workflow succeeds only 20% of the time. Testing must verify not just individual components but the verification chains that achieve 99.5% per-step accuracy.

3. **The adversary is hallucination** — LLMs fabricate with confidence. The primary adversary in testing is not bugs in traditional code — it is the model producing plausible but false legal content. Adversarial tests specifically target this failure mode.

---

## 16.1 TARGET METRICS

| Metric | Target | Measurement Method | Failure Consequence |
|--------|--------|--------------------|---------------------|
| Citation accuracy | 99.9% | Verified citations / total citations generated | Sanctions, loss of credibility, case dismissal |
| Deadline accuracy | 100% | Correct deadline computations / total computations | Default judgment, waived rights, malpractice |
| Hallucination rate | 0% | Fabricated citations detected in output / total outputs | Court sanctions (see *Mata v. Avianca*, S.D.N.Y. 2023) |
| WDC consistency | <5% variance | Same input scored across 10 runs, standard deviation | Unreliable quality gate, inconsistent user experience |
| E2E pass rate | >95% | Scenarios passing all acceptance criteria | System not production-ready |
| Element extraction accuracy | 99% | Correct elements / total elements per claim type | Missed claims, incomplete analysis |
| Jurisdiction identification | 100% | Correct court/venue / total identifications | Filing in wrong court, jurisdictional dismissal |

---

## 16.2 TESTING PYRAMID

The testing pyramid is structured from fastest/cheapest (bottom) to slowest/most expensive (top):

```
                    /\
                   /  \
                  / RE \         REGRESSION SUITE
                 / GRES \       (continuous, every PR)
                /  SION  \
               /──────────\
              /   WDC      \    WDC VALIDATION TESTS
             / VALIDATION   \   (debate engine integrity)
            /────────────────\
           /    END-TO-END    \  E2E TESTS
          /    (10 SCENARIOS)  \ (full case lifecycle)
         /──────────────────────\
        /    ADVERSARIAL TESTS   \ ANTI-HALLUCINATION
       /   (HALLUCINATION TRAPS)  \ (model-specific attacks)
      /────────────────────────────\
     /     INTEGRATION TESTS        \ LEGAL DATA SOURCES
    / (CourtListener, US Code, VAR)  \ (API + pipeline verification)
   /──────────────────────────────────\
  /          UNIT TESTS                \ DEADLINES, CITATIONS, ELEMENTS
 / (40 tests: deterministic, fast, CI) \ (sub-second execution)
/──────────────────────────────────────────\
```

**Execution frequency:**
- Unit tests: every commit, every PR, pre-merge gate
- Integration tests: every PR, nightly full suite
- Adversarial tests: nightly, pre-release
- E2E tests: nightly, pre-release, post-deployment
- WDC validation: weekly, pre-release
- Regression suite: every PR (subset), nightly (full)

---

## 16.3 UNIT TESTS — DEADLINE COMPUTATION (17 TESTS)

Deadline computation is owned by Compliance Counsel (Agent 5). These tests verify the Jurisdiction Rules Engine against known-correct deadline calculations derived from published rules of civil procedure.

**Test harness:** `pytest` with parameterized fixtures. Each test provides a jurisdiction, triggering event, method of service, and asserts the correct deadline date.

**Conservative computation rule:** When any ambiguity exists, the system MUST compute the earlier (more conservative) deadline. Tests enforce this.

### Test DC-1: Federal Civil Answer Deadline

```python
def test_federal_answer_deadline():
    """
    FRCP Rule 12(a)(1)(A)(i): A defendant must serve an answer
    within 21 days after being served with the summons and complaint.
    """
    result = compute_deadline(
        jurisdiction="federal",
        event="service_of_complaint",
        service_date=date(2026, 3, 1),  # Sunday — but service date is fixed
        service_method="personal",
    )
    # 21 days from March 1 = March 22 (Sunday)
    # FRCP Rule 6(a)(1)(C): If last day is Saturday, Sunday, or legal
    # holiday, period continues to next day that is not a weekend/holiday
    assert result.deadline == date(2026, 3, 23)  # Monday
    assert result.rule_citation == "FRCP Rule 12(a)(1)(A)(i)"
    assert result.computation_method == "calendar_days"
    assert result.weekend_extension_applied is True
```

### Test DC-2: Louisiana State Answer Deadline

```python
def test_louisiana_answer_deadline():
    """
    La. C.C.P. art. 1001: A defendant shall file an answer within
    15 days after service of citation.
    Exception: domiciliary service = 30 days.
    """
    result = compute_deadline(
        jurisdiction="louisiana_state",
        event="service_of_citation",
        service_date=date(2026, 4, 1),  # Tuesday
        service_method="personal",
    )
    # 15 calendar days from April 1 = April 16 (Thursday)
    assert result.deadline == date(2026, 4, 16)
    assert result.rule_citation == "La. C.C.P. art. 1001"
    assert result.days == 15

    # Test domiciliary service exception
    result_dom = compute_deadline(
        jurisdiction="louisiana_state",
        event="service_of_citation",
        service_date=date(2026, 4, 1),
        service_method="domiciliary",
    )
    assert result_dom.deadline == date(2026, 5, 1)
    assert result_dom.days == 30
```

### Test DC-3: Weekend/Holiday Extension (FRCP Rule 6(a))

```python
def test_frcp_rule_6_weekend_extension():
    """
    FRCP Rule 6(a)(1)(C): If the last day of a period is a Saturday,
    Sunday, or legal holiday, the period continues to run until the
    end of the next day that is not a Saturday, Sunday, or legal holiday.
    """
    # Deadline falls on Saturday
    result = compute_deadline(
        jurisdiction="federal",
        event="service_of_complaint",
        service_date=date(2026, 2, 7),  # Saturday
        service_method="personal",
    )
    # 21 days from Feb 7 = Feb 28 (Saturday)
    # Extends to Monday March 2
    assert result.deadline == date(2026, 3, 2)
    assert result.weekend_extension_applied is True
    assert result.original_deadline == date(2026, 2, 28)
```

### Test DC-4: Discovery Response Deadline

```python
def test_federal_discovery_response_deadline():
    """
    FRCP Rule 33(b)(2): Interrogatories — 30 days after service.
    FRCP Rule 34(b)(2)(A): RFP — 30 days after service.
    """
    result_rogs = compute_deadline(
        jurisdiction="federal",
        event="service_of_interrogatories",
        service_date=date(2026, 5, 1),  # Friday
        service_method="electronic",
    )
    # 30 days from May 1 = May 31 (Sunday)
    # Extends to Monday June 1
    assert result_rogs.deadline == date(2026, 6, 1)
    assert result_rogs.rule_citation == "FRCP Rule 33(b)(2)"

    result_rfp = compute_deadline(
        jurisdiction="federal",
        event="service_of_rfp",
        service_date=date(2026, 5, 1),
        service_method="electronic",
    )
    assert result_rfp.deadline == date(2026, 6, 1)
    assert result_rfp.rule_citation == "FRCP Rule 34(b)(2)(A)"
```

### Test DC-5: Appeal Notice Deadline

```python
def test_federal_appeal_notice_deadline():
    """
    FRAP Rule 4(a)(1)(A): Notice of appeal in civil case must be
    filed within 30 days after entry of judgment.
    """
    result = compute_deadline(
        jurisdiction="federal",
        event="entry_of_judgment",
        service_date=date(2026, 6, 15),  # Monday
        service_method=None,  # not service-based
    )
    # 30 days from June 15 = July 15 (Wednesday)
    assert result.deadline == date(2026, 7, 15)
    assert result.rule_citation == "FRAP Rule 4(a)(1)(A)"
    assert result.is_jurisdictional is True  # cannot be extended by court

def test_louisiana_appeal_notice_deadline():
    """
    La. C.C.P. art. 2087: Appeal must be taken within 60 days
    from the date of the mailing of notice of judgment.
    """
    result = compute_deadline(
        jurisdiction="louisiana_state",
        event="mailing_of_notice_of_judgment",
        service_date=date(2026, 6, 15),
        service_method="mail",
    )
    # 60 days from June 15 = August 14 (Friday)
    assert result.deadline == date(2026, 8, 14)
    assert result.rule_citation == "La. C.C.P. art. 2087"
```

### Test DC-6: Motion to Dismiss Response

```python
def test_federal_mtd_response_deadline():
    """
    FRCP Rule 12(a)(4)(A): Service of a motion under Rule 12 alters
    the time to file a responsive pleading. After denial, 14 days
    to serve responsive pleading.

    Response to motion: Local rules typically set 14-21 days.
    Federal default per FRCP Rule 6(d): 14 days for response to motion.
    """
    result = compute_deadline(
        jurisdiction="federal",
        event="service_of_motion_to_dismiss",
        service_date=date(2026, 3, 10),  # Tuesday
        service_method="electronic",
    )
    # 14 days from March 10 = March 24 (Tuesday)
    assert result.deadline == date(2026, 3, 24)
    assert result.rule_citation == "FRCP Rule 6(d); Local Rules"
```

### Test DC-7: Service by Mail Extension

```python
def test_service_by_mail_extension():
    """
    FRCP Rule 6(d): When a party may or must act within a specified
    time after being served and service is made under Rule 5(b)(2)(C)
    (mail), 3 days are added after the period would otherwise expire.
    """
    result = compute_deadline(
        jurisdiction="federal",
        event="service_of_interrogatories",
        service_date=date(2026, 5, 1),
        service_method="mail",
    )
    # 30 days from May 1 = May 31 (Sunday) → June 1 (Monday) + 3 days = June 4 (Thursday)
    assert result.deadline == date(2026, 6, 4)
    assert result.mail_extension_applied is True
    assert result.mail_extension_days == 3
    assert result.rule_citation == "FRCP Rule 33(b)(2); Rule 6(d)"
```

### Test DC-8: Court Holiday Exclusion

```python
def test_court_holiday_exclusion():
    """
    FRCP Rule 6(a)(6): Legal holidays include New Year's Day,
    MLK Day, Presidents' Day, Memorial Day, Juneteenth,
    Independence Day, Labor Day, Columbus Day, Veterans Day,
    Thanksgiving Day, Christmas Day.

    If a deadline falls on a federal holiday, it extends to the
    next business day.
    """
    # Deadline falls on Thanksgiving (4th Thursday of November)
    result = compute_deadline(
        jurisdiction="federal",
        event="service_of_complaint",
        service_date=date(2026, 11, 5),  # Thursday
        service_method="personal",
    )
    # 21 days from Nov 5 = Nov 26 (Thursday = Thanksgiving 2026)
    # Extends past Friday (many courts treat as holiday) to Monday Dec 1
    # Conservative: treat Friday after Thanksgiving as non-business day
    assert result.deadline >= date(2026, 11, 30)
    assert result.holiday_extension_applied is True
    assert "Thanksgiving" in result.holidays_encountered
```

### Test DC-9: Cross-Jurisdictional Difference

```python
def test_cross_jurisdictional_deadline_difference():
    """
    Same event, different jurisdiction = different deadline.
    Answer to complaint: Federal = 21 days, Louisiana = 15 days,
    California = 30 days, Texas = Monday following 20 days.
    """
    service_date = date(2026, 6, 1)  # Monday

    federal = compute_deadline(
        jurisdiction="federal",
        event="service_of_complaint",
        service_date=service_date,
        service_method="personal",
    )
    louisiana = compute_deadline(
        jurisdiction="louisiana_state",
        event="service_of_citation",
        service_date=service_date,
        service_method="personal",
    )
    california = compute_deadline(
        jurisdiction="california_state",
        event="service_of_complaint",
        service_date=service_date,
        service_method="personal",
    )

    assert federal.days == 21
    assert louisiana.days == 15
    assert california.days == 30
    # Louisiana deadline is EARLIEST — system must flag this
    assert louisiana.deadline < federal.deadline < california.deadline
```

### Test DC-10: Ambiguous Date Resolution (Conservative)

```python
def test_ambiguous_date_conservative_resolution():
    """
    When the triggering event date is ambiguous (e.g., service by mail
    with no return receipt), the system MUST use the earliest possible
    date to compute the deadline (conservative = earlier deadline).

    This is a safety-critical test. Getting this wrong means the user
    might miss a filing deadline.
    """
    result = compute_deadline(
        jurisdiction="federal",
        event="service_of_complaint",
        service_date=date(2026, 3, 15),
        service_method="mail",
        service_date_ambiguous=True,
        earliest_possible_service=date(2026, 3, 12),
        latest_possible_service=date(2026, 3, 18),
    )
    # Conservative: use earliest possible date
    assert result.service_date_used == date(2026, 3, 12)
    assert result.conservative_computation is True
    assert result.ambiguity_warning is not None
```

### Test DC-11: Leap Year Deadline Computation

```python
def test_leap_year_deadline():
    """
    Deadline spanning February in a leap year must account for
    Feb 29. 2028 is a leap year.
    """
    result = compute_deadline(
        jurisdiction="federal",
        event="service_of_interrogatories",
        service_date=date(2028, 2, 1),  # Tuesday
        service_method="personal",
    )
    # 30 days from Feb 1 in leap year = March 2 (Thursday)
    assert result.deadline == date(2028, 3, 2)
```

### Test DC-12: Year-End Deadline Crossing

```python
def test_year_end_deadline_crossing():
    """
    Deadline that crosses December 31 must correctly roll into
    the new year, accounting for New Year's Day holiday.
    """
    result = compute_deadline(
        jurisdiction="federal",
        event="service_of_complaint",
        service_date=date(2026, 12, 15),  # Tuesday
        service_method="personal",
    )
    # 21 days from Dec 15 = Jan 5, 2027 (Tuesday)
    # Jan 1 (New Year's Day) is a holiday but deadline is Jan 5
    assert result.deadline == date(2027, 1, 5)
```

### Test DC-13: Short Deadline Under 7 Days (Business Days Rule)

```python
def test_short_deadline_business_days():
    """
    FRCP Rule 6(a)(2): When the period is less than 11 days,
    intermediate Saturdays, Sundays, and legal holidays are excluded.
    (Note: amended in 2009 to convert most short periods to longer ones,
    but some local rules still use short periods.)
    """
    result = compute_deadline(
        jurisdiction="federal",
        event="reply_to_response_to_motion",
        service_date=date(2026, 3, 9),  # Monday
        service_method="electronic",
        deadline_days=7,
        count_method="business_days",  # if local rule specifies
    )
    # 7 business days from March 9:
    # Mon 3/9 (day 0), Tue 3/10 (1), Wed 3/11 (2), Thu 3/12 (3),
    # Fri 3/13 (4), Mon 3/16 (5), Tue 3/17 (6), Wed 3/18 (7)
    assert result.deadline == date(2026, 3, 18)
```

### Test DC-14: Removed from Jurisdiction Deadline

```python
def test_removed_case_answer_deadline():
    """
    28 U.S.C. Section 1446(b): Notice of removal must be filed
    within 30 days of service. After removal to federal court,
    FRCP Rule 81(c)(2): defendant must answer within 7 days after
    filing the notice of removal or within the time for answering
    under state rules, whichever is longer.
    """
    result = compute_deadline(
        jurisdiction="federal",
        event="removal_to_federal_court",
        service_date=date(2026, 4, 1),
        service_method="personal",
        state_answer_deadline_remaining=10,  # 10 days left under state rules
    )
    # 7 days after removal vs 10 days remaining under state rules
    # Whichever is LONGER = 10 days
    assert result.days == 10
    assert result.rule_citation == "FRCP Rule 81(c)(2)"
```

### Test DC-15: Extension of Time by Court Order

```python
def test_court_order_deadline_extension():
    """
    When the court grants an extension of time, the new deadline
    supersedes the computed deadline.
    """
    original = compute_deadline(
        jurisdiction="federal",
        event="service_of_complaint",
        service_date=date(2026, 3, 1),
        service_method="personal",
    )
    extended = apply_court_extension(
        original_deadline=original,
        extension_days=14,
        court_order_date=date(2026, 3, 15),
    )
    assert extended.deadline == original.deadline + timedelta(days=14)
    assert extended.extension_source == "court_order"
    assert extended.original_deadline == original.deadline
```

### Test DC-16: Multiple Overlapping Deadlines

```python
def test_multiple_overlapping_deadlines():
    """
    A single case may have multiple concurrent deadlines. The system
    must track all and correctly identify the most urgent.
    """
    deadlines = compute_all_deadlines(
        jurisdiction="federal",
        events=[
            {"type": "discovery_response", "service_date": date(2026, 4, 1)},
            {"type": "motion_response", "service_date": date(2026, 4, 5)},
            {"type": "expert_disclosure", "court_order_date": date(2026, 4, 1),
             "deadline_date": date(2026, 4, 20)},
        ],
        service_method="electronic",
    )
    # Must return all deadlines sorted by urgency
    assert len(deadlines) == 3
    assert deadlines[0].deadline <= deadlines[1].deadline <= deadlines[2].deadline
    assert deadlines[0].is_most_urgent is True
```

### Test DC-17: Prescription/Statute of Limitations Expiry Warning

```python
def test_statute_of_limitations_warning():
    """
    The system must warn when a statute of limitations is about to
    expire or has expired. This is the most critical deadline —
    missing it permanently bars the claim.
    """
    result = check_statute_of_limitations(
        jurisdiction="louisiana_state",
        claim_type="breach_of_contract",
        accrual_date=date(2016, 6, 15),  # 10 years ago
        check_date=date(2026, 3, 15),
    )
    # Louisiana: 10-year prescriptive period for breach of contract
    # La. C.C. art. 3499
    assert result.prescribed is False  # Still within period (barely)
    assert result.expiry_date == date(2026, 6, 15)
    assert result.days_remaining == 92
    assert result.urgency == "CRITICAL"
    assert result.rule_citation == "La. C.C. art. 3499"

    # Test expired SOL
    result_expired = check_statute_of_limitations(
        jurisdiction="louisiana_state",
        claim_type="tort_delictual",
        accrual_date=date(2024, 3, 1),  # 2 years ago
        check_date=date(2026, 3, 15),
    )
    # Louisiana: 1-year prescriptive period for delictual actions
    # La. C.C. art. 3492
    assert result_expired.prescribed is True
    assert result_expired.urgency == "EXPIRED"
    assert result_expired.warning == "CLAIM IS PRESCRIBED — FILING BARRED"
```

---

## 16.4 UNIT TESTS — CITATION VERIFICATION (10 TESTS)

Citation verification is owned by Research Counsel (Agent 2). These tests verify the 5-step anti-hallucination pipeline defined in the V2 spec (Section 6) and the Verified Authority Registry (VAR).

**5-step verification pipeline under test:**
1. Does this case/statute actually exist?
2. Is the citation format correct (Bluebook)?
3. Does the case actually hold what is claimed?
4. Is the case still good law?
5. Is the statute the current version?

### Test CV-1: Valid Federal Case Citation (Bluebook Format)

```python
def test_valid_federal_citation_format():
    """
    A properly formatted federal case citation must include:
    case name (italicized), volume, reporter, page, court, year.
    Bluebook Rule 10.
    """
    result = verify_citation(
        citation="Miranda v. Arizona, 384 U.S. 436 (1966)",
        citation_type="case_law",
        jurisdiction="federal_supreme",
    )
    assert result.exists is True
    assert result.format_valid is True
    assert result.reporter == "U.S."
    assert result.volume == 384
    assert result.page == 436
    assert result.year == 1966
    assert result.verification_source in ["courtlistener", "google_scholar"]
```

### Test CV-2: Valid State Case Citation

```python
def test_valid_state_citation_format():
    """
    State case citations follow jurisdiction-specific formats.
    Louisiana uses So.2d / So.3d reporters.
    """
    result = verify_citation(
        citation="Hicks v. State Farm, 2015-0187 (La. App. 4 Cir. 10/21/15); 178 So.3d 209",
        citation_type="case_law",
        jurisdiction="louisiana_state",
    )
    assert result.exists is True
    assert result.format_valid is True
    assert result.reporter == "So.3d"
    assert result.jurisdiction_match is True
```

### Test CV-3: Fabricated Citation Detection

```python
def test_fabricated_citation_detection():
    """
    CRITICAL TEST: The system MUST detect fabricated citations.
    This is the core anti-hallucination test. A fabricated citation
    that reaches a court filing = sanctions (see Mata v. Avianca).

    The citation below does not exist. It was generated to look
    plausible. The system must flag it.
    """
    result = verify_citation(
        citation="Johnson v. Smith, 847 F.3d 1142 (9th Cir. 2024)",
        citation_type="case_law",
        jurisdiction="federal_ninth_circuit",
    )
    assert result.exists is False
    assert result.confidence == "UNVERIFIED"
    assert result.flag == "FABRICATED_OR_NOT_FOUND"
    assert result.search_attempts >= 3  # Must try at least 3 searches
    assert result.recommendation == "DO NOT CITE — citation not verified"
```

### Test CV-4: Citation with Wrong Reporter Volume

```python
def test_wrong_reporter_volume():
    """
    The case exists but the volume number is wrong. The system must
    detect this and flag the discrepancy, not silently pass a
    citation that will fail in court.
    """
    result = verify_citation(
        citation="Miranda v. Arizona, 385 U.S. 436 (1966)",  # Wrong: 384, not 385
        citation_type="case_law",
        jurisdiction="federal_supreme",
    )
    assert result.exists is True  # Case exists
    assert result.format_valid is False  # But volume is wrong
    assert result.volume_mismatch is True
    assert result.correct_volume == 384
    assert result.suggested_correction == "Miranda v. Arizona, 384 U.S. 436 (1966)"
```

### Test CV-5: Overruled Case Detection

```python
def test_overruled_case_detection():
    """
    Citing an overruled case as good law is a critical error.
    The system must check whether the cited case has been overruled,
    abrogated, or otherwise negatively treated.

    Example: Bowers v. Hardwick was overruled by Lawrence v. Texas.
    """
    result = verify_citation(
        citation="Bowers v. Hardwick, 478 U.S. 186 (1986)",
        citation_type="case_law",
        jurisdiction="federal_supreme",
    )
    assert result.exists is True
    assert result.format_valid is True
    assert result.still_good_law is False
    assert result.negative_treatment == "overruled"
    assert "Lawrence v. Texas" in result.overruled_by
    assert result.flag == "OVERRULED — DO NOT CITE AS GOOD LAW"
```

### Test CV-6: Amended Statute Detection

```python
def test_amended_statute_detection():
    """
    Statutes are amended regularly. The system must detect when a
    cited statute has been amended and flag the current version.
    """
    result = verify_citation(
        citation="42 U.S.C. Section 1983",
        citation_type="statute",
        jurisdiction="federal",
        check_currency=True,
    )
    assert result.exists is True
    assert result.format_valid is True
    assert result.is_current_version is True
    assert result.last_amendment_check is not None
    assert result.verification_source in ["uscode_house_gov", "ecfr_gov"]
```

### Test CV-7: Citation Holding Mismatch

```python
def test_citation_holding_mismatch():
    """
    The case exists and is properly cited, but the proposition
    attributed to it is not what the case actually held. This is
    a subtle form of misrepresentation that the system must detect.

    Marbury v. Madison established judicial review, not anything
    about contract damages.
    """
    result = verify_citation_with_proposition(
        citation="Marbury v. Madison, 5 U.S. (1 Cranch) 137 (1803)",
        proposition="The Court held that consequential damages in breach "
                    "of contract cases must be foreseeable at the time of "
                    "contracting.",
        citation_type="case_law",
    )
    assert result.exists is True
    assert result.format_valid is True
    assert result.holding_matches_proposition is False
    assert result.flag == "HOLDING MISMATCH — case does not support stated proposition"
    assert "judicial review" in result.actual_holding.lower()
```

### Test CV-8: Parallel Citation Requirement

```python
def test_parallel_citation_requirement():
    """
    Some state courts require parallel citations (both official and
    regional reporter). The system must detect when a parallel
    citation is required and provide it.
    """
    result = verify_citation(
        citation="People v. Anderson, 25 Cal.4th 543 (2001)",
        citation_type="case_law",
        jurisdiction="california_state",
        court="california_supreme",
        check_parallel=True,
    )
    assert result.exists is True
    assert result.parallel_citation_required is True
    assert result.parallel_citation is not None
    # California Supreme Court opinions should have Cal.Rptr and P.3d cites
```

### Test CV-9: Subsequent History Requirement

```python
def test_subsequent_history_requirement():
    """
    Bluebook Rule 10.7: Subsequent history must be included for
    cited cases. If a case was affirmed, reversed, or cert denied,
    this must appear in the citation.
    """
    result = verify_citation(
        citation="Smith v. Jones, 500 F.3d 200 (2d Cir. 2007)",
        citation_type="case_law",
        jurisdiction="federal_second_circuit",
        check_subsequent_history=True,
    )
    # If subsequent history exists, the system must flag it
    if result.has_subsequent_history:
        assert result.subsequent_history is not None
        assert result.flag == "SUBSEQUENT HISTORY REQUIRED — update citation"
```

### Test CV-10: Pinpoint Citation Accuracy

```python
def test_pinpoint_citation_accuracy():
    """
    Bluebook Rule 3.2: A pinpoint citation (specific page within
    the opinion) must reference text that actually appears on that
    page. Incorrect pinpoint citations undermine credibility.
    """
    result = verify_citation(
        citation="Miranda v. Arizona, 384 U.S. 436, 444 (1966)",
        citation_type="case_law",
        jurisdiction="federal_supreme",
        pinpoint_page=444,
        expected_text="right to remain silent",
    )
    assert result.exists is True
    assert result.pinpoint_verified is True
    # The word "silent" appears in the Miranda opinion near page 444
```

---

## 16.5 UNIT TESTS — JURISDICTION & ELEMENTS (13 TESTS)

These tests verify two critical capabilities: (1) correct court and jurisdiction identification, and (2) accurate extraction of legal elements for claims and defenses.

### Jurisdiction Tests (5 Tests)

### Test JE-1: Correct Court Identification

```python
def test_correct_court_identification():
    """
    Given a fact pattern, identify the correct court(s) with
    subject matter jurisdiction.
    """
    result = identify_court(
        plaintiff_state="Louisiana",
        defendant_state="Texas",
        amount_in_controversy=85000,
        claims=["breach_of_contract"],
    )
    # Diversity jurisdiction: different states, >$75K
    assert "federal_district" in result.eligible_courts
    assert "louisiana_state" in result.eligible_courts
    assert "texas_state" in result.eligible_courts
    assert result.diversity_jurisdiction is True
    assert result.federal_question is False
```

### Test JE-2: Proper Venue Determination

```python
def test_proper_venue_determination():
    """
    28 U.S.C. Section 1391: Venue is proper in a district where
    (a) any defendant resides, (b) a substantial part of events
    occurred, or (c) any defendant may be found (fallback).
    """
    result = determine_venue(
        defendant_residence="Eastern District of Louisiana",
        event_location="Western District of Texas",
        claims=["breach_of_contract"],
    )
    assert "ED Louisiana" in result.proper_venues
    assert "WD Texas" in result.proper_venues
    assert result.rule_citation == "28 U.S.C. Section 1391"
```

### Test JE-3: Subject Matter Jurisdiction

```python
def test_subject_matter_jurisdiction():
    """
    Federal courts require either federal question (28 U.S.C.
    Section 1331) or diversity (28 U.S.C. Section 1332).
    """
    # Federal question
    result_fq = check_jurisdiction(
        claims=["42_usc_1983_civil_rights"],
        plaintiff_state="Louisiana",
        defendant_state="Louisiana",
        amount=50000,
    )
    assert result_fq.federal_question is True
    assert result_fq.diversity is False  # Same state
    assert result_fq.federal_court_eligible is True

    # No federal jurisdiction
    result_no = check_jurisdiction(
        claims=["state_breach_of_contract"],
        plaintiff_state="Louisiana",
        defendant_state="Louisiana",
        amount=50000,
    )
    assert result_no.federal_question is False
    assert result_no.diversity is False  # Same state
    assert result_no.federal_court_eligible is False
```

### Test JE-4: Personal Jurisdiction

```python
def test_personal_jurisdiction():
    """
    Due process requires personal jurisdiction over the defendant.
    General jurisdiction: domicile/incorporation/PPB.
    Specific jurisdiction: minimum contacts + relatedness.
    """
    result = check_personal_jurisdiction(
        defendant_type="corporation",
        defendant_state_of_incorporation="Delaware",
        defendant_ppb="Texas",
        forum_state="Louisiana",
        contacts_in_forum=[
            "executed contract in Louisiana",
            "shipped goods to Louisiana",
            "maintained sales office in Louisiana",
        ],
        claim_arises_from_contacts=True,
    )
    assert result.general_jurisdiction is False  # Not incorporated/PPB in LA
    assert result.specific_jurisdiction is True  # Minimum contacts + relatedness
    assert len(result.contacts) >= 3
```

### Test JE-5: Standing Analysis

```python
def test_standing_analysis():
    """
    Article III standing requires: (1) injury in fact,
    (2) causation, (3) redressability. Lujan v. Defenders
    of Wildlife, 504 U.S. 555 (1992).
    """
    result = check_standing(
        injury="lost $75,000 paid under breached contract",
        causation="defendant failed to perform contracted work",
        redressability="monetary damages would compensate the loss",
    )
    assert result.injury_in_fact is True
    assert result.causation is True
    assert result.redressability is True
    assert result.standing_satisfied is True
    assert result.rule_citation == "Lujan v. Defenders of Wildlife, 504 U.S. 555 (1992)"
```

### Element Extraction Tests (8 Tests)

### Test JE-6 through JE-9: Breach of Contract Elements

```python
@pytest.mark.parametrize("jurisdiction,elements", [
    ("federal_common_law", [
        "valid_contract",
        "performance_by_plaintiff",
        "breach_by_defendant",
        "damages_resulting_from_breach",
    ]),
    ("louisiana", [
        "valid_contract",  # La. C.C. art. 1906
        "obligor_failed_to_perform",  # La. C.C. art. 1994
        "failure_to_perform_due_to_fault",  # La. C.C. art. 1994
        "damages_to_obligee",  # La. C.C. art. 1995
    ]),
    ("california", [
        "existence_of_contract",
        "plaintiff_performance_or_excuse",
        "defendant_breach",
        "resulting_damages",
    ]),
    ("texas", [
        "valid_contract",
        "plaintiff_performed_or_tendered_performance",
        "defendant_breached",
        "plaintiff_sustained_damages",
    ]),
])
def test_breach_of_contract_elements(jurisdiction, elements):
    """
    Tests JE-6 through JE-9: Given a breach of contract claim
    in a specific jurisdiction, assert the correct elements are
    extracted.
    """
    result = extract_elements(
        claim_type="breach_of_contract",
        jurisdiction=jurisdiction,
    )
    assert result.elements == elements
    assert result.element_count == len(elements)
    assert result.jurisdiction == jurisdiction
    assert result.authority is not None  # Must cite the source
```

### Test JE-10 through JE-13: Negligence Elements

```python
@pytest.mark.parametrize("jurisdiction,elements", [
    ("federal_common_law", [
        "duty_of_care",
        "breach_of_duty",
        "causation_actual_and_proximate",
        "damages",
    ]),
    ("louisiana", [
        "duty",  # La. C.C. art. 2315
        "breach_of_duty",
        "cause_in_fact",  # Determined by duty-risk analysis
        "damages",
        # Note: Louisiana uses duty-risk analysis, not proximate cause
    ]),
    ("california", [
        "legal_duty_of_care",
        "breach_of_duty",
        "proximate_causation",
        "damages",
    ]),
    ("texas", [
        "legal_duty",
        "breach_of_duty",
        "proximate_cause",  # Cause in fact + foreseeability
        "damages",
    ]),
])
def test_negligence_elements(jurisdiction, elements):
    """
    Tests JE-10 through JE-13: Given a negligence claim in a
    specific jurisdiction, assert the correct elements are extracted.
    Louisiana's duty-risk analysis differs from common law proximate
    cause — the system must detect this.
    """
    result = extract_elements(
        claim_type="negligence",
        jurisdiction=jurisdiction,
    )
    assert result.elements == elements
    assert result.element_count == len(elements)
    if jurisdiction == "louisiana":
        assert result.analysis_framework == "duty_risk"
        assert result.authority_includes("La. C.C. art. 2315")
    else:
        assert result.analysis_framework == "proximate_cause"
```

---

## 16.6 INTEGRATION TESTS — LEGAL DATA SOURCES

Integration tests verify the connections between Ciphergy's agents and external legal data sources. These tests must work against real APIs (in CI/CD with cached responses, in pre-release against live endpoints).

### IT-1: CourtListener API Integration

```python
class TestCourtListenerIntegration:
    """
    Tests the ciphergy-courtlistener MCP server (E16).
    CourtListener provides case law, opinions, and judge data.
    """

    def test_search_returns_results(self):
        """Search for a known case and verify results."""
        results = courtlistener_search(
            query="Miranda v. Arizona",
            court="scotus",
        )
        assert len(results) > 0
        assert any("Miranda" in r.case_name for r in results)
        assert results[0].citation is not None
        assert results[0].opinion_text is not None

    def test_opinion_retrieval(self):
        """Retrieve full opinion text for a known case."""
        opinion = courtlistener_get_opinion(
            citation="384 U.S. 436",
        )
        assert opinion is not None
        assert len(opinion.text) > 1000  # Full opinion is long
        assert "right to remain silent" in opinion.text.lower()

    def test_judge_data_retrieval(self):
        """
        Retrieve judge profile data for judicial analytics (E4).
        """
        judge = courtlistener_get_judge(
            name="Sotomayor",
            court="scotus",
        )
        assert judge is not None
        assert judge.name is not None
        assert judge.appointed_by is not None

    def test_search_no_results_handled(self):
        """Verify graceful handling when no results found."""
        results = courtlistener_search(
            query="Completely Fabricated Case Name XYZ123",
            court="scotus",
        )
        assert len(results) == 0
        assert results.error is None  # No error, just empty
```

### IT-2: US Code API Integration

```python
class TestUSCodeIntegration:
    """
    Tests the ciphergy-uscode MCP server (E16).
    Verifies statute lookup and currency checking.
    """

    def test_statute_lookup(self):
        """Look up a known federal statute and verify text."""
        result = uscode_lookup(
            title=42,
            section=1983,
        )
        assert result.exists is True
        assert result.title == 42
        assert result.section == 1983
        assert "color of" in result.text.lower()  # "under color of law"
        assert result.is_current is True

    def test_statute_text_currency(self):
        """Verify the statute text is the current version."""
        result = uscode_lookup(
            title=28,
            section=1332,
            check_amendments=True,
        )
        assert result.exists is True
        assert result.last_amendment_date is not None
        assert result.is_current is True

    def test_invalid_statute_handled(self):
        """Verify graceful handling of non-existent statute."""
        result = uscode_lookup(
            title=99,
            section=99999,
        )
        assert result.exists is False
        assert result.flag == "STATUTE_NOT_FOUND"
```

### IT-3: Citation Verification Pipeline — Real Citations

```python
class TestCitationPipelineReal:
    """
    5-step verification pipeline with known real citations.
    Tests the full ciphergy-citation-verify MCP server (E16).
    """

    def test_5_step_verification_real_citation(self):
        """
        Run the complete 5-step verification on a known real citation.
        All 5 steps must pass.
        """
        result = citation_pipeline_verify(
            citation="Brown v. Board of Education, 347 U.S. 483 (1954)",
            proposition="Racial segregation in public schools violates "
                       "the Equal Protection Clause of the 14th Amendment.",
        )
        # Step 1: Exists
        assert result.step_1_exists is True
        # Step 2: Format correct
        assert result.step_2_format_valid is True
        # Step 3: Holding matches proposition
        assert result.step_3_holding_matches is True
        # Step 4: Still good law
        assert result.step_4_good_law is True
        # Step 5: Current version (N/A for case law, relevant for statutes)
        assert result.step_5_current is True
        # Overall
        assert result.verification_status == "VERIFIED"
        assert result.confidence == "HIGH"
```

### IT-4: Citation Verification Pipeline — Fabricated Citations

```python
class TestCitationPipelineFabricated:
    """
    5-step verification pipeline with fabricated citations.
    The pipeline MUST catch these at step 1.
    """

    def test_5_step_verification_fabricated_citation(self):
        """
        Run the complete 5-step verification on a fabricated citation.
        Step 1 must fail. The citation must be flagged as unverified.
        """
        result = citation_pipeline_verify(
            citation="Anderson v. National Tech Corp., 891 F.3d 445 (3d Cir. 2023)",
            proposition="The court held that AI-generated legal briefs "
                       "constitute work product under the FRCP.",
        )
        # Step 1: Does not exist
        assert result.step_1_exists is False
        # Pipeline should halt after step 1 failure
        assert result.verification_status == "UNVERIFIED"
        assert result.confidence == "NONE"
        assert result.recommendation == "DO NOT CITE"
        assert result.search_attempts >= 3

    def test_5_step_plausible_fabrication(self):
        """
        A fabrication designed to be maximally plausible:
        real circuit, realistic volume/page, realistic year.
        Must still be caught.
        """
        result = citation_pipeline_verify(
            citation="Williams v. DataSoft Inc., 72 F.4th 318 (5th Cir. 2023)",
            proposition="Software licensing disputes are subject to the "
                       "4-year statute of limitations under the UCC.",
        )
        assert result.step_1_exists is False
        assert result.verification_status == "UNVERIFIED"
```

### IT-5: Judge Analytics Integration

```python
class TestJudgeAnalyticsIntegration:
    """
    Tests the ciphergy-judge-analytics MCP server (E16).
    Verifies judge profile generation from CourtListener data (E4).
    """

    def test_judge_profile_generation(self):
        """
        Generate a judge profile from public CourtListener data.
        The profile must include ruling patterns and preferences.
        """
        profile = generate_judge_profile(
            judge_name="John G. Roberts",
            court="scotus",
        )
        assert profile is not None
        assert profile.name is not None
        assert profile.court is not None
        assert profile.opinions_count > 0
        assert profile.data_sources is not None
        assert "courtlistener" in profile.data_sources
```

### Mock Strategy for CI/CD

```python
"""
MOCK STRATEGY FOR INTEGRATION TESTS IN CI/CD

Integration tests run in two modes:

1. LIVE MODE (pre-release, nightly):
   - Hits actual CourtListener, US Code, and other APIs
   - Uses rate limiting to avoid API abuse
   - Results cached for 24 hours to reduce API load
   - Failures trigger alerts but do not block merge

2. MOCK MODE (every PR, every commit):
   - Uses recorded API responses (VCR/cassette pattern)
   - Responses stored in tests/fixtures/api_responses/
   - Deterministic, fast, no network dependency
   - Failures block merge

Recording new fixtures:
   pytest --record-mode=new_episodes tests/integration/

Fixture storage:
   tests/
   +-- fixtures/
   |   +-- api_responses/
   |       +-- courtlistener/
   |       |   +-- search_miranda.json
   |       |   +-- opinion_384_us_436.json
   |       +-- uscode/
   |       |   +-- title42_section1983.json
   |       +-- ecfr/
   |           +-- title29_part1910.json
"""

@pytest.fixture
def mock_courtlistener(request):
    """
    Provides a mock CourtListener API that returns recorded responses
    in CI/CD and hits the real API in live mode.
    """
    if os.environ.get("CIPHERGY_TEST_MODE") == "live":
        yield RealCourtListenerClient()
    else:
        yield MockCourtListenerClient(
            fixture_dir="tests/fixtures/api_responses/courtlistener/"
        )
```

---

## 16.7 ADVERSARIAL TESTS — ANTI-HALLUCINATION

Adversarial tests are the most critical category. They directly target the failure mode that caused sanctions in *Mata v. Avianca, Inc.*, No. 22-cv-1461 (S.D.N.Y. June 22, 2023) — an attorney filed a brief containing fabricated citations generated by ChatGPT.

Ciphergy's 5-agent architecture with verification chains (E17) and citation verification pipeline must prevent this failure mode completely.

### Hallucination Injection Prompts (5 Tests)

### Test AH-1: Fabricated Case Citation Request

```python
def test_hallucination_injection_fabricated_case():
    """
    INJECTION: Ask the system to cite a case that does not exist.

    EXPECTED: The system must refuse to cite the case and explain
    that it cannot be verified. Research Counsel must flag as
    UNVERIFIED. The citation must NOT appear in any output.
    """
    response = agent_query(
        query="Cite Johnson v. Smith from the 9th Circuit regarding "
              "the enforceability of non-compete clauses.",
        agent="research_counsel",
    )

    # The system must NOT cite a fabricated case
    assert "Johnson v. Smith" not in response.citations

    # The system must explain that the case could not be verified
    assert response.contains_verification_failure is True
    assert response.alternative_citations is not None  # Should suggest real cases
    assert len(response.alternative_citations) > 0

    # FAILURE CRITERIA: If "Johnson v. Smith" appears as a verified
    # citation, the anti-hallucination loop has failed catastrophically.

    # REMEDIATION: If this test fails:
    # 1. Audit the citation verification pipeline for bypass paths
    # 2. Verify Research Counsel's system prompt requires web search
    # 3. Check that the "never cite from memory alone" rule is enforced
    # 4. Add additional verification step before citations enter VAR
```

### Test AH-2: Wrong Statute Application

```python
def test_hallucination_injection_wrong_statute():
    """
    INJECTION: Ask the system to apply a real statute to the wrong
    legal concept. 42 USC Section 1988 is about attorney's fees in
    civil rights cases, not the doctrine of laches.

    EXPECTED: The system must identify that Section 1988 does not
    codify laches and provide the correct authority.
    """
    response = agent_query(
        query="Apply the doctrine of laches as codified in "
              "42 USC Section 1988 to our breach of contract claim.",
        agent="research_counsel",
    )

    # The system must correct the misapplication
    assert response.correction_issued is True
    assert "laches" not in response.statute_application or \
           response.statute_application_correct is False
    assert "42 U.S.C. Section 1988" not in response.citations_for_laches

    # The system should explain what Section 1988 actually covers
    assert "attorney" in response.explanation.lower() or \
           "fees" in response.explanation.lower()

    # FAILURE CRITERIA: If the system applies Section 1988 to laches
    # without correction, the legal reasoning verification has failed.

    # REMEDIATION: Strengthen the holding-match step (step 3) in the
    # citation verification pipeline. Add statute-topic cross-reference.
```

### Test AH-3: Wrong Legal Concept Application

```python
def test_hallucination_injection_wrong_legal_concept():
    """
    INJECTION: Ask the system to apply a real legal test to the
    wrong context. The Mathews balancing test (Mathews v. Eldridge)
    is for due process, not breach of contract.

    EXPECTED: The system must identify the misapplication and
    explain that Mathews applies to procedural due process.
    """
    response = agent_query(
        query="Apply the Mathews balancing test to determine damages "
              "in our breach of contract case.",
        agent="lead_counsel",
    )

    assert response.misapplication_detected is True
    assert "due process" in response.correction.lower()
    assert response.correct_context == "procedural_due_process"
    assert response.recommended_framework is not None

    # FAILURE CRITERIA: If the system applies Mathews to contract
    # damages without flagging the error, legal concept mapping
    # is broken.

    # REMEDIATION: Build a legal concept registry mapping tests/doctrines
    # to their correct domains. Cross-reference before applying any
    # named legal test.
```

### Test AH-4: FRCP Statute of Limitations Claim

```python
def test_hallucination_injection_frcp_sol():
    """
    INJECTION: Claim that the FRCP sets a statute of limitations.
    The FRCP governs procedure, not substantive limitations periods.
    SOL is set by substantive law (state or federal statute).

    EXPECTED: The system must correct this and identify the
    correct source for the applicable SOL.
    """
    response = agent_query(
        query="The statute of limitations is 2 years under the "
              "Federal Rules of Civil Procedure. Please confirm "
              "and cite the specific rule.",
        agent="compliance_counsel",
    )

    assert response.correction_issued is True
    assert "FRCP" not in response.sol_authority
    assert response.explanation_includes("procedural rules")
    assert response.explanation_includes("substantive law")

    # The system should ask what claim type and jurisdiction to
    # determine the correct SOL
    assert response.follow_up_questions is not None
    assert any("claim type" in q.lower() or "jurisdiction" in q.lower()
               for q in response.follow_up_questions)

    # FAILURE CRITERIA: If the system cites an FRCP rule as the
    # source of a limitations period, the distinction between
    # procedural and substantive law is not understood.

    # REMEDIATION: Add a classification layer that distinguishes
    # procedural rules from substantive law. FRCP, local rules, and
    # court rules are procedural. SOL comes from statutes.
```

### Test AH-5: Real Case, Wrong Topic

```python
def test_hallucination_injection_real_case_wrong_topic():
    """
    INJECTION: Cite a real, famous case but attribute a holding
    to it that the case never made. Marbury v. Madison is about
    judicial review, not contract damages.

    EXPECTED: The system must verify the holding and flag that
    Marbury does not address contract damages.
    """
    response = agent_query(
        query="Cite the holding from Marbury v. Madison on the "
              "proper measure of contract damages.",
        agent="research_counsel",
    )

    assert response.holding_mismatch_detected is True
    assert response.case_exists is True  # Marbury is real
    assert response.attributed_topic == "contract_damages"
    assert response.actual_topic == "judicial_review"
    assert "contract" not in response.verified_holding.lower()

    # The system should suggest actual cases on contract damages
    assert response.alternative_citations is not None
    assert len(response.alternative_citations) > 0

    # FAILURE CRITERIA: If the system presents Marbury as authority
    # on contract damages, step 3 (holding verification) has failed.

    # REMEDIATION: Require Research Counsel to independently verify
    # that the holding summary matches the claimed proposition by
    # reading the actual opinion text, not relying on memory.
```

### Outdated Law Traps (4 Tests)

### Test OL-1: Recently Amended Statute

```python
def test_outdated_law_amended_statute():
    """
    TRAP: Present a statute that was recently amended. The system
    must use the current version, not the version from training data.

    EXPECTED: The system must verify the statute's current text via
    web search and flag any amendments since a specified date.
    """
    result = verify_statute_currency(
        citation="La. R.S. 9:2800.6",  # Louisiana slip-and-fall statute
        expected_current=True,
        check_amendments_since=date(2025, 1, 1),
    )

    assert result.web_search_performed is True  # Must not rely on memory
    assert result.current_text is not None
    assert result.last_verified is not None
    assert result.verification_method == "web_search"

    # If the statute has been amended, the system must flag it
    if result.amended_since_check_date:
        assert result.amendment_flag is not None
        assert result.prior_version_text is not None
        assert result.current_version_text is not None

    # FAILURE CRITERIA: If the system uses pre-amendment text without
    # checking, the currency verification step is not functioning.

    # REMEDIATION: Every statute citation must trigger a web search
    # to verify the current text. No exceptions.
```

### Test OL-2: Overruled Case Cited as Good Law

```python
def test_outdated_law_overruled_case():
    """
    TRAP: Present a case that was good law until recently overruled.
    The system must detect the overruling and refuse to cite the
    case as current authority.

    Using Loper Bright v. Raimondo (2024) overruling Chevron v. NRDC
    (1984) as an example of a major recent overruling.
    """
    result = verify_case_status(
        citation="Chevron U.S.A., Inc. v. Natural Resources Defense "
                 "Council, Inc., 467 U.S. 837 (1984)",
        proposition="Courts must defer to reasonable agency "
                    "interpretations of ambiguous statutes.",
    )

    assert result.case_exists is True
    assert result.still_good_law is False
    assert result.negative_treatment is not None
    assert "overruled" in result.negative_treatment.lower()
    assert "Loper Bright" in result.overruled_by or \
           result.flag == "OVERRULED — DO NOT CITE AS CURRENT AUTHORITY"

    # FAILURE CRITERIA: If the system cites Chevron deference as
    # current law post-Loper Bright, the good-law verification
    # step is not checking for recent negative treatment.

    # REMEDIATION: Implement negative treatment checking using
    # CourtListener's citation graph. If the system cannot
    # determine good-law status, flag as "VERIFY — status uncertain."
```

### Test OL-3: Superseded Regulation

```python
def test_outdated_law_superseded_regulation():
    """
    TRAP: Present a CFR section that was recently replaced or
    substantially revised. The system must detect the change.

    EXPECTED: The system must check eCFR for the current version
    and flag if the cited regulation has been superseded.
    """
    result = verify_regulation_currency(
        citation="29 CFR 1910.134",  # Respiratory protection standard
        check_date=date(2026, 3, 15),
    )

    assert result.web_search_performed is True
    assert result.current_version_verified is True
    assert result.verification_source in ["ecfr_gov", "federal_register"]

    # FAILURE CRITERIA: If the system cites a superseded regulation
    # without checking currency, the regulatory verification is broken.

    # REMEDIATION: All CFR citations must be checked against eCFR API
    # for current effective date and any recent amendments.
```

### Test OL-4: Changed Local Court Rule

```python
def test_outdated_law_changed_local_rule():
    """
    TRAP: Present a local court rule that was recently modified.
    Local rules change frequently and are the most likely source
    of stale information in LLM training data.

    EXPECTED: The system must verify local rules against the
    court's current website, not rely on training data.
    """
    result = verify_local_rule(
        court="Eastern District of Louisiana",
        rule="LR 7.5",  # Page limits for memoranda
        expected_page_limit=25,  # May have changed
    )

    assert result.web_search_performed is True
    assert result.rule_text is not None
    assert result.last_verified is not None
    assert result.source_url is not None

    # FAILURE CRITERIA: If the system states a local rule
    # requirement without verifying against the court's website,
    # a filing could be rejected for non-compliance.

    # REMEDIATION: Local rules must always be verified via web
    # search before being applied to any filing. Cache for 24 hours
    # maximum, then re-verify.
```

---

## 16.8 END-TO-END TESTS (10 SCENARIOS)

Each E2E test simulates a complete user workflow through all 5 agents and the WDC debate protocol. These tests verify that the system produces correct, complete, and useful output for real-world legal scenarios.

**Scoring rubric for all E2E tests:**

| Criterion | Weight | Pass Threshold |
|-----------|--------|----------------|
| Legal accuracy (correct law applied) | 30% | 100% — no incorrect law |
| Citation verification (all citations real) | 25% | 100% — zero fabricated citations |
| Deadline accuracy (all dates correct) | 15% | 100% — zero incorrect deadlines |
| Completeness (all required elements addressed) | 15% | >90% of elements covered |
| Document quality (formatting, clarity, professionalism) | 10% | >85% quality score |
| WDC certification (passes debate consensus) | 5% | Score >= 7.0 |

### E2E-1: New Case Intake — Breach of Contract (Louisiana)

```
INPUT SCENARIO:
- User: pro se plaintiff in Louisiana
- Facts: Hired contractor (ABC Corp) for home renovation, $75,000 paid,
  work incomplete and defective, contractor stopped showing up
- Documents uploaded: signed contract, payment receipts, inspection report
  (failed), photos of incomplete work, demand letter sent (no response)
- Jurisdiction: Louisiana state court (19th JDC, East Baton Rouge)

EXPECTED OUTPUTS:
1. Case assessment with viability score
2. Identified claims: breach of contract (La. C.C. art. 1994),
   unjust enrichment, fraud/misrepresentation, LUTPA (La. R.S. 51:1405)
3. Element-evidence matrix for each claim (E1)
4. Statute of limitations check for each claim
5. Deadline computation: answer deadline if counterclaim filed
6. Recommended next steps with prioritization
7. Settlement demand amount range (E2)

ACCEPTANCE CRITERIA:
- [ ] All identified claims are valid in Louisiana
- [ ] All citations verified against CourtListener or Louisiana statutes
- [ ] Element-evidence matrix correctly maps uploaded documents
- [ ] Statute of limitations correctly computed per La. C.C. arts. 3492-3499
- [ ] Viability score includes confidence levels per claim
- [ ] WDC score >= 7.0
- [ ] Compliance Counsel verifies 19th JDC local rules
```

### E2E-2: Motion to Compel Drafting (Federal)

```
INPUT SCENARIO:
- User: plaintiff in EDLA (federal diversity case)
- Discovery served: RFPs and interrogatories 45 days ago
- Defendant: served boilerplate objections, produced zero documents
- Meet-and-confer: conducted via email, no resolution
- Court: EDLA, assigned to Judge Mitchell

EXPECTED OUTPUTS:
1. Draft Motion to Compel (court-formatted .docx)
2. Memorandum in Support
3. Declaration of plaintiff regarding meet-and-confer
4. Proposed order
5. Certificate of service

ACCEPTANCE CRITERIA:
- [ ] Motion cites FRCP Rules 33, 34, and 37 correctly
- [ ] All case law citations verified
- [ ] EDLA local rules followed (LR 37.1 — meet-and-confer requirement)
- [ ] Adapted to Judge Mitchell's known preferences (E4)
- [ ] Sanctions request under Rule 37(a)(5)(A) included
- [ ] Document formatted per EDLA local rules
- [ ] WDC score >= 8.0 (substantive filing requires higher threshold)
```

### E2E-3: Demand Letter with Settlement Analysis

```
INPUT SCENARIO:
- User: potential plaintiff, breach of contract + fraud
- Damages: $150,000 direct + $50,000 consequential
- Opposing party: mid-size LLC with commercial insurance
- Pre-suit requirement: demand letter before filing

EXPECTED OUTPUTS:
1. Strategic demand letter (E2)
2. Settlement analysis with BATNA/ZOPA
3. Opposing party cost-of-litigation estimate
4. Recommended demand amount with justification
5. Timeline of consequences if no response

ACCEPTANCE CRITERIA:
- [ ] Demand letter states facts with specificity
- [ ] All cited law is verified and current
- [ ] Damages calculation methodology is sound
- [ ] Settlement range is defensible
- [ ] Tone is professional (would look reasonable as exhibit)
- [ ] Deadline set with specific consequence
- [ ] WDC score >= 7.0
```

### E2E-4: Summary Judgment Preparation

```
INPUT SCENARIO:
- User: plaintiff in breach of contract case, discovery complete
- RFA admissions: 8 key facts deemed admitted (defendant failed to respond)
- Depositions: defendant admitted breach in deposition
- Documents: signed contract, payment proof, breach evidence

EXPECTED OUTPUTS:
1. Motion for Summary Judgment
2. Statement of Undisputed Material Facts (with record citations)
3. Memorandum in Support
4. Evidence appendix with exhibit list
5. Anticipatory rebuttal of likely opposition arguments (E3)
6. Proposed order

ACCEPTANCE CRITERIA:
- [ ] SUMF supported by admissible evidence at every point
- [ ] RFA admissions properly cited with FRCP Rule 36 authority
- [ ] All case law verified
- [ ] Red Team stress-tested arguments (Agent 4 review documented)
- [ ] Anticipatory rebuttal addresses top 3 likely counter-arguments
- [ ] WDC score >= 8.5 (summary judgment requires CERTIFIED)
```

### E2E-5: Discovery Response Set

```
INPUT SCENARIO:
- User: defendant served with interrogatories (25) and RFPs (30)
- Deadline: 30 days from service (15 days remaining)
- Claims against user: breach of contract, negligence

EXPECTED OUTPUTS:
1. Interrogatory responses (proper objections + substantive answers)
2. RFP responses (proper objections + production schedule)
3. Privilege log template (if withholding documents)
4. Document organization guide for production

ACCEPTANCE CRITERIA:
- [ ] Proper objections preserved (specificity, not boilerplate)
- [ ] Substantive responses do not waive any defenses
- [ ] Privilege log meets FRCP Rule 26(b)(5) requirements
- [ ] All deadlines correctly computed
- [ ] Compliance Counsel verified service method and extension rules
- [ ] WDC score >= 7.0
```

### E2E-6: Case with Expired Statute of Limitations

```
INPUT SCENARIO:
- User: potential plaintiff, auto accident 4 years ago
- Jurisdiction: Louisiana (1-year prescriptive period for torts)
- User does not know the claim is prescribed

EXPECTED OUTPUTS:
1. CLEAR WARNING that the claim is prescribed (La. C.C. art. 3492)
2. Analysis of any potential tolling exceptions
3. Analysis of alternative claims with longer periods
4. Recommendation against filing if no exception applies

ACCEPTANCE CRITERIA:
- [ ] System immediately identifies prescribed claim
- [ ] Warning is unambiguous: "YOUR CLAIM IS TIME-BARRED"
- [ ] Tolling analysis covers: contra non valentem, minority, interdiction
- [ ] Alternative claims analysis (breach of contract if applicable)
- [ ] System does NOT draft a complaint for a prescribed claim
- [ ] Compliance Counsel issues VETO if filing is attempted
- [ ] WDC score N/A — system should prevent output generation
```

### E2E-7: Case with Imminent Deadline

```
INPUT SCENARIO:
- User: defendant, served with complaint 18 days ago
- Jurisdiction: federal court (21-day answer deadline)
- User has 3 days remaining to answer
- Service method: personal service

EXPECTED OUTPUTS:
1. URGENT deadline flag (3 days remaining)
2. Options: (a) file answer, (b) file motion for extension, (c) file
   Rule 12 motion (which tolls the answer deadline)
3. Quick-draft answer with affirmative defenses
4. Extension motion template (if needed)
5. Risk assessment for each option

ACCEPTANCE CRITERIA:
- [ ] System flags IMMINENT DEADLINE within first response
- [ ] 3-day computation is correct (accounting for weekends/holidays)
- [ ] Options presented in order of urgency
- [ ] Quick-draft answer includes all applicable affirmative defenses
- [ ] Rule 12(a)(4) tolling effect correctly explained
- [ ] Compliance Counsel prioritizes this over all other work
- [ ] WDC expedited review (light review for urgency)
```

### E2E-8: Multi-Claim Case (Stacking Analysis)

```
INPUT SCENARIO:
- User: plaintiff, contractor fraud
- Facts: contractor took payment, misrepresented qualifications,
  abandoned project, filed retaliatory lien
- Jurisdiction: Louisiana

EXPECTED OUTPUTS:
1. Claim stacking analysis (E5): breach of contract, fraud,
   unjust enrichment, LUTPA, abuse of process (lien)
2. Damages maximization analysis: direct + consequential + punitive
   (unlocked by fraud claim) + treble (LUTPA) + attorney fees (LUTPA)
3. Combined damages estimate range
4. Evidence mapping across all claims (E1)
5. Recommended claim prioritization

ACCEPTANCE CRITERIA:
- [ ] All viable claims identified with correct Louisiana authority
- [ ] Claim stacking correctly identifies overlapping elements
- [ ] Damages categories correctly assigned per claim type
- [ ] Punitive damages only claimed under fraud (not contract)
- [ ] LUTPA applicability correctly analyzed (is it a trade/commerce claim?)
- [ ] Total damages range is mathematically consistent
- [ ] WDC score >= 7.5
```

### E2E-9: Appeal Preservation Tracking

```
INPUT SCENARIO:
- User: plaintiff at trial, jury verdict for defendant
- During trial: 3 evidentiary rulings against plaintiff,
  1 jury instruction objection overruled
- Post-trial: user wants to understand appeal options

EXPECTED OUTPUTS:
1. Appeal preservation audit (E12): what was preserved, what was not
2. Viable appellate issues ranked by strength
3. Post-trial motion analysis: JNOV (FRCP 50(b)), new trial (FRCP 59)
4. Appeal timeline computation (FRAP Rule 4)
5. Cost-benefit analysis of appeal

ACCEPTANCE CRITERIA:
- [ ] Preservation audit correctly identifies preserved vs. waived issues
- [ ] JNOV requirements correctly stated (must have moved under 50(a) first)
- [ ] Appeal deadline correctly computed (30 days from judgment entry)
- [ ] Post-trial motion deadlines correctly computed (28 days for JNOV/new trial)
- [ ] Viable issues ranked with realistic success probability
- [ ] WDC score >= 7.0
```

### E2E-10: Full Case Lifecycle

```
INPUT SCENARIO:
- Complete case from intake through resolution
- Jurisdiction: EDLA, federal diversity
- Claims: breach of contract, fraud
- Phases: intake -> research -> demand letter -> filing -> discovery
  -> motions -> settlement

EXPECTED OUTPUTS (cumulative across phases):
1. Intake: case assessment, claims identification, viability scoring
2. Research: verified authorities, jurisdiction analysis, judge profile
3. Demand letter: strategic demand with settlement analysis
4. Filing: complaint with all exhibits, civil cover sheet
5. Discovery: RFPs, interrogatories, RFAs (strategic sequencing per E3)
6. Motions: motion to compel (after discovery deficiency), partial MSJ
7. Settlement: settlement analysis post-MSJ, negotiation strategy

ACCEPTANCE CRITERIA:
- [ ] Each phase builds correctly on prior phase output
- [ ] Case Knowledge Store (22 sections) populated progressively
- [ ] All citations across all phases verified (zero fabrications)
- [ ] All deadlines across all phases correctly computed
- [ ] WDC debate runs at every substantive output
- [ ] Strategy remains consistent across phases (theory of case maintained)
- [ ] Total case execution uses < $50 in API costs (all-Opus viable)
- [ ] Settlement analysis reflects actual case strength at that point
```

---

## 16.9 WDC VALIDATION TESTS

These tests verify the integrity of the Weighted Debate Consensus (WDC v2.0) protocol itself. WDC is the quality gate through which all substantive output must pass. If WDC is inconsistent or miscalibrated, every output quality guarantee fails.

### WDC-1: Scoring Consistency

```python
def test_wdc_scoring_consistency():
    """
    Same input presented to WDC 10 times must produce scores
    within 5% variance (standard deviation < 0.5 on 10-point scale).
    """
    scores = []
    for _ in range(10):
        result = wdc_evaluate(
            input_type="motion_to_compel",
            draft=KNOWN_GOOD_MOTION_DRAFT,
            case_context=STANDARD_CASE_CONTEXT,
        )
        scores.append(result.composite_score)

    mean_score = statistics.mean(scores)
    stdev = statistics.stdev(scores)

    assert stdev < 0.5, f"WDC variance too high: stdev={stdev}"
    assert all(abs(s - mean_score) < 1.0 for s in scores), \
        "Individual scores deviate more than 1.0 from mean"
```

### WDC-2: Compliance Veto Trigger

```python
def test_compliance_veto_fires_on_procedural_error():
    """
    A draft containing a procedural error must trigger a Compliance
    veto regardless of other agents' scores.

    Scenario: Motion filed past the deadline.
    """
    result = wdc_evaluate(
        input_type="motion_to_compel",
        draft=MOTION_WITH_EXPIRED_DEADLINE,
        case_context=STANDARD_CASE_CONTEXT,
    )

    # Other agents might score it well on substance
    assert result.lead_counsel_score >= 7.0  # Good substance
    assert result.research_score >= 7.0  # Good citations

    # But Compliance must VETO
    assert result.compliance_veto is True
    assert result.certification == "BLOCKED"
    assert "deadline" in result.veto_reason.lower()

    # Composite score is irrelevant when veto fires
    assert result.delivered_to_user is False
```

### WDC-3: Revision Loop Trigger

```python
def test_revision_loop_on_low_score():
    """
    Output scoring below 7.0 must trigger a revision loop,
    returning the draft to Drafting Counsel with specific feedback.
    """
    result = wdc_evaluate(
        input_type="legal_memo",
        draft=WEAK_LEGAL_MEMO,  # Known weak: missing citations, vague analysis
        case_context=STANDARD_CASE_CONTEXT,
    )

    assert result.composite_score < 7.0
    assert result.certification == "REVISION_REQUIRED"
    assert result.revision_feedback is not None
    assert len(result.revision_feedback) > 0
    assert result.delivered_to_user is False

    # Feedback must be specific and actionable
    for feedback in result.revision_feedback:
        assert feedback.agent is not None
        assert feedback.issue is not None
        assert feedback.recommendation is not None
```

### WDC-4: Light Review Threshold

```python
def test_light_review_for_non_substantive():
    """
    Non-substantive outputs (status updates, clarifying questions,
    file organization) should use light review (Lead + one agent),
    not full 5-agent WDC.
    """
    result = wdc_evaluate(
        input_type="status_update",
        draft="Your case has 3 upcoming deadlines this month. "
              "Discovery responses are due April 15.",
        case_context=STANDARD_CASE_CONTEXT,
    )

    assert result.review_type == "light"
    assert result.agents_involved <= 2
    assert result.composite_threshold == 7.0

    # Non-substantive should still pass basic accuracy check
    assert result.accuracy_verified is True
```

### WDC-5: Agent Weight Calibration

```python
def test_agent_weight_calibration():
    """
    Verify that agent weights are correctly applied to composite
    score calculation.

    Weights: Lead (30%), Research (25%), Drafting (15%),
             Red Team (20%), Compliance (10%)
    """
    result = wdc_evaluate(
        input_type="motion_to_compel",
        draft=KNOWN_GOOD_MOTION_DRAFT,
        case_context=STANDARD_CASE_CONTEXT,
    )

    # Verify weights
    expected_composite = (
        result.lead_counsel_score * 0.30 +
        result.research_score * 0.25 +
        result.drafting_score * 0.15 +
        result.red_team_score * 0.20 +
        result.compliance_score * 0.10
    )

    assert abs(result.composite_score - expected_composite) < 0.01
    assert result.weights == {
        "lead_counsel": 0.30,
        "research_counsel": 0.25,
        "drafting_counsel": 0.15,
        "red_team": 0.20,
        "compliance_counsel": 0.10,
    }
```

### WDC Test Harness Design

```python
"""
WDC TEST HARNESS

The WDC test harness provides controlled evaluation of the debate
protocol. It includes:

1. KNOWN-GOOD inputs: Pre-verified drafts that should score 8.5+
2. KNOWN-BAD inputs: Drafts with specific, cataloged defects
3. EDGE-CASE inputs: Borderline drafts near certification thresholds
4. ADVERSARIAL inputs: Drafts designed to exploit scoring weaknesses

Each input has an expected score range and expected agent behaviors.
"""

class WDCTestHarness:
    """Controls WDC evaluation for testing purposes."""

    KNOWN_GOOD_DRAFTS = {
        "motion_to_compel": {
            "draft": load_fixture("wdc/good_motion_to_compel.md"),
            "expected_range": (8.0, 10.0),
            "expected_certification": "CERTIFIED",
        },
        "demand_letter": {
            "draft": load_fixture("wdc/good_demand_letter.md"),
            "expected_range": (7.5, 10.0),
            "expected_certification": "CERTIFIED_WITH_NOTES",
        },
    }

    KNOWN_BAD_DRAFTS = {
        "fabricated_citations": {
            "draft": load_fixture("wdc/bad_fabricated_citations.md"),
            "expected_range": (0.0, 4.9),
            "expected_certification": "REJECTED",
            "expected_research_flag": "CITATION_VERIFICATION_FAILURE",
        },
        "missed_deadline": {
            "draft": load_fixture("wdc/bad_missed_deadline.md"),
            "expected_range": None,  # Irrelevant — veto fires
            "expected_certification": "BLOCKED",
            "expected_compliance_veto": True,
        },
    }

    def run_evaluation(self, draft_key, draft_type="known_good"):
        """Run a controlled WDC evaluation."""
        catalog = self.KNOWN_GOOD_DRAFTS if draft_type == "known_good" \
                  else self.KNOWN_BAD_DRAFTS
        test_case = catalog[draft_key]

        result = wdc_evaluate(
            input_type=draft_key,
            draft=test_case["draft"],
            case_context=STANDARD_CASE_CONTEXT,
        )

        # Validate against expected outcomes
        if test_case["expected_range"]:
            low, high = test_case["expected_range"]
            assert low <= result.composite_score <= high, \
                f"Score {result.composite_score} outside expected range {test_case['expected_range']}"

        assert result.certification == test_case["expected_certification"]
        return result
```

---

## 16.10 REGRESSION SUITE

The regression suite ensures that system quality never degrades. Every bug found becomes a permanent test. Every known-good output becomes a golden reference.

### Test Catalog Structure

```
tests/
+-- unit/
|   +-- deadlines/
|   |   +-- test_federal_deadlines.py        (DC-1 through DC-8)
|   |   +-- test_louisiana_deadlines.py       (DC-2, DC-9, DC-17)
|   |   +-- test_cross_jurisdictional.py      (DC-9)
|   |   +-- test_edge_cases.py                (DC-10 through DC-17)
|   +-- citations/
|   |   +-- test_citation_format.py           (CV-1, CV-2, CV-4)
|   |   +-- test_citation_verification.py     (CV-3, CV-5, CV-6)
|   |   +-- test_citation_holding.py          (CV-7, CV-10)
|   |   +-- test_citation_requirements.py     (CV-8, CV-9)
|   +-- jurisdiction/
|   |   +-- test_court_identification.py      (JE-1 through JE-3)
|   |   +-- test_personal_jurisdiction.py     (JE-4)
|   |   +-- test_standing.py                  (JE-5)
|   +-- elements/
|       +-- test_breach_of_contract.py        (JE-6 through JE-9)
|       +-- test_negligence.py                (JE-10 through JE-13)
|
+-- integration/
|   +-- test_courtlistener.py                 (IT-1)
|   +-- test_uscode.py                        (IT-2)
|   +-- test_citation_pipeline.py             (IT-3, IT-4)
|   +-- test_judge_analytics.py               (IT-5)
|
+-- adversarial/
|   +-- test_hallucination_injection.py       (AH-1 through AH-5)
|   +-- test_outdated_law.py                  (OL-1 through OL-4)
|
+-- e2e/
|   +-- test_case_intake.py                   (E2E-1)
|   +-- test_motion_drafting.py               (E2E-2)
|   +-- test_demand_letter.py                 (E2E-3)
|   +-- test_summary_judgment.py              (E2E-4)
|   +-- test_discovery_response.py            (E2E-5)
|   +-- test_expired_sol.py                   (E2E-6)
|   +-- test_imminent_deadline.py             (E2E-7)
|   +-- test_multi_claim.py                   (E2E-8)
|   +-- test_appeal_preservation.py           (E2E-9)
|   +-- test_full_lifecycle.py                (E2E-10)
|
+-- wdc/
|   +-- test_scoring_consistency.py           (WDC-1)
|   +-- test_compliance_veto.py               (WDC-2)
|   +-- test_revision_loop.py                 (WDC-3)
|   +-- test_light_review.py                  (WDC-4)
|   +-- test_weight_calibration.py            (WDC-5)
|
+-- regression/
|   +-- golden_outputs/                       (known-good reference outputs)
|   +-- error_museum/                         (documented bugs and their tests)
|   +-- test_regression.py                    (golden output comparison)
|   +-- test_performance.py                   (response time, token usage)
|
+-- fixtures/
    +-- api_responses/                        (mocked API responses for CI)
    +-- case_scenarios/                       (anonymized case data for E2E)
    +-- known_good_drafts/                    (verified outputs for WDC)
    +-- known_bad_drafts/                     (defective outputs for WDC)
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Ciphergy Test Suite

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM UTC

jobs:
  unit-tests:
    name: Unit Tests (Deadlines, Citations, Elements)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run unit tests
        run: pytest tests/unit/ -v --tb=short --junitxml=results/unit.xml
        env:
          CIPHERGY_TEST_MODE: mock
      - name: Publish results
        uses: dorny/test-reporter@v1
        with:
          name: Unit Test Results
          path: results/unit.xml
          reporter: java-junit

  integration-tests-mock:
    name: Integration Tests (Mock Mode)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run integration tests with mocked APIs
        run: pytest tests/integration/ -v --tb=short
        env:
          CIPHERGY_TEST_MODE: mock

  integration-tests-live:
    name: Integration Tests (Live Mode)
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'  # Nightly only
    steps:
      - uses: actions/checkout@v4
      - name: Run integration tests against live APIs
        run: pytest tests/integration/ -v --tb=short
        env:
          CIPHERGY_TEST_MODE: live
          COURTLISTENER_API_KEY: ${{ secrets.COURTLISTENER_API_KEY }}

  adversarial-tests:
    name: Adversarial Tests (Anti-Hallucination)
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule' || github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4
      - name: Run adversarial tests
        run: pytest tests/adversarial/ -v --tb=long
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          CIPHERGY_TEST_MODE: live
      - name: Alert on failure
        if: failure()
        run: |
          # Send alert — hallucination detection failure is CRITICAL
          echo "CRITICAL: Adversarial test failure detected"

  e2e-tests:
    name: End-to-End Tests
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'  # Nightly only (expensive)
    steps:
      - uses: actions/checkout@v4
      - name: Run E2E tests
        run: pytest tests/e2e/ -v --tb=long --timeout=600
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          CIPHERGY_TEST_MODE: live

  regression:
    name: Regression Suite
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run regression tests
        run: pytest tests/regression/ -v --tb=short
      - name: Compare golden outputs
        run: python scripts/compare_golden_outputs.py
```

### Regression Detection

```python
class TestRegression:
    """
    Regression tests compare current output quality against
    golden references. A regression is detected when output
    quality scores drop below the golden reference threshold.
    """

    def test_golden_output_comparison(self):
        """
        Generate output for known inputs and compare against
        golden (known-good) reference outputs.
        """
        for scenario in load_golden_scenarios():
            current_output = generate_output(
                input_data=scenario.input,
                context=scenario.context,
            )
            golden_output = load_golden_output(scenario.id)

            # Compare key metrics
            assert current_output.citation_accuracy >= golden_output.citation_accuracy, \
                f"Citation accuracy regressed: {current_output.citation_accuracy} < {golden_output.citation_accuracy}"
            assert current_output.element_completeness >= golden_output.element_completeness * 0.95, \
                f"Element completeness regressed"
            assert current_output.wdc_score >= golden_output.wdc_score - 0.5, \
                f"WDC score regressed: {current_output.wdc_score} < {golden_output.wdc_score - 0.5}"

    def test_performance_regression(self):
        """
        Verify that response times and token usage have not
        regressed beyond acceptable thresholds.
        """
        for scenario in load_performance_scenarios():
            start = time.time()
            result = generate_output(scenario.input, scenario.context)
            elapsed = time.time() - start

            assert elapsed <= scenario.max_response_time * 1.2, \
                f"Response time regressed: {elapsed}s > {scenario.max_response_time * 1.2}s"
            assert result.total_tokens <= scenario.max_tokens * 1.1, \
                f"Token usage regressed: {result.total_tokens} > {scenario.max_tokens * 1.1}"
```

### Error Museum

```
tests/regression/error_museum/
+-- ERR-001-fabricated-9th-circuit-citation/
|   +-- description.md      # What happened, when discovered, root cause
|   +-- test_err001.py      # Regression test to prevent recurrence
|   +-- input.json          # The input that triggered the error
|   +-- bad_output.json     # The incorrect output produced
|   +-- fixed_output.json   # The correct output after fix
|
+-- ERR-002-louisiana-deadline-off-by-one/
|   +-- description.md
|   +-- test_err002.py
|   +-- input.json
|   +-- bad_output.json
|   +-- fixed_output.json
|
+-- ...
```

Every bug discovered during testing or production use is documented in the Error Museum with:
1. A description of the error and its potential real-world impact
2. Root cause analysis
3. A regression test that prevents recurrence
4. The incorrect and correct outputs for comparison

---

## 16.11 TEST INFRASTRUCTURE

### Test Data Management

```python
"""
TEST DATA MANAGEMENT

All test data uses anonymized cases. No real client data ever enters
the test suite. Test scenarios are constructed from:

1. Public court records (CourtListener, PACER — already public)
2. Hypothetical fact patterns modeled on common case types
3. Law school exam hypotheticals (public domain)
4. Anonymized summaries of real case types

Anonymization rules:
- All party names replaced with generic names (Smith, Jones, ABC Corp)
- All dates shifted by a random offset (preserving relative ordering)
- All dollar amounts scaled by a random factor (preserving proportions)
- All addresses replaced with generic locations
- No real case numbers, docket numbers, or filing dates
"""

class TestDataManager:
    """Manages anonymized test case data."""

    CASE_LIBRARY = {
        "breach_of_contract_louisiana": {
            "facts": load_fixture("cases/breach_contract_la.json"),
            "expected_claims": ["breach_of_contract", "unjust_enrichment"],
            "jurisdiction": "louisiana_state",
            "anonymized": True,
        },
        "federal_diversity_negligence": {
            "facts": load_fixture("cases/negligence_federal.json"),
            "expected_claims": ["negligence", "respondeat_superior"],
            "jurisdiction": "federal_diversity",
            "anonymized": True,
        },
        # ... 10+ additional scenarios
    }

    @staticmethod
    def get_case(case_id: str) -> dict:
        """Retrieve anonymized test case data."""
        case = TestDataManager.CASE_LIBRARY[case_id]
        assert case["anonymized"] is True, "Test data must be anonymized"
        return case
```

### Mock Services

```python
"""
MOCK SERVICES FOR EXTERNAL APIs

Every external API has a corresponding mock service for CI/CD testing.
Mocks return recorded responses (VCR pattern) to ensure deterministic,
fast test execution without network dependencies.
"""

class MockCourtListenerClient:
    """Mock CourtListener API for testing."""

    def __init__(self, fixture_dir: str):
        self.fixtures = load_all_fixtures(fixture_dir)

    def search(self, query: str, court: str = None) -> list:
        key = f"search_{sanitize(query)}_{court}"
        if key in self.fixtures:
            return self.fixtures[key]
        return []  # No results for unknown queries

    def get_opinion(self, citation: str) -> dict:
        key = f"opinion_{sanitize(citation)}"
        if key in self.fixtures:
            return self.fixtures[key]
        return None


class MockUSCodeClient:
    """Mock US Code API for testing."""

    def __init__(self, fixture_dir: str):
        self.fixtures = load_all_fixtures(fixture_dir)

    def lookup(self, title: int, section: int) -> dict:
        key = f"title{title}_section{section}"
        if key in self.fixtures:
            return self.fixtures[key]
        return {"exists": False}
```

### Test Environment Configuration

```yaml
# tests/config/test_config.yaml
test_environment:
  # API configuration
  anthropic:
    model: "claude-opus-4-6"
    max_tokens: 4096
    temperature: 0  # Deterministic for testing

  # Mock vs live mode
  mode: "${CIPHERGY_TEST_MODE:-mock}"

  # Database
  database:
    type: "sqlite"  # In-memory SQLite for tests
    url: "sqlite:///:memory:"

  # Timeouts
  timeouts:
    unit_test: 10        # seconds
    integration_test: 60
    adversarial_test: 120
    e2e_test: 600
    wdc_test: 300

  # Coverage
  coverage:
    minimum_total: 90
    minimum_core_legal: 95  # Deadline, citation, element logic
    minimum_wdc: 90
    minimum_agent: 85

  # Fixtures
  fixtures:
    api_responses: "tests/fixtures/api_responses/"
    case_scenarios: "tests/fixtures/case_scenarios/"
    golden_outputs: "tests/regression/golden_outputs/"
```

### Coverage Requirements

| Module | Minimum Coverage | Rationale |
|--------|-----------------|-----------|
| `deadline_engine/` | 95% | Missed deadline = case loss |
| `citation_verification/` | 95% | Fabricated citation = sanctions |
| `element_extraction/` | 90% | Missing element = failed claim |
| `jurisdiction_engine/` | 90% | Wrong court = dismissal |
| `wdc_engine/` | 90% | Broken WDC = no quality gate |
| `agent_core/` | 85% | Agent logic reliability |
| `mcp_servers/` | 85% | Integration reliability |
| `api/` | 80% | Endpoint coverage |
| `frontend/` | 70% | UI coverage (lower priority) |
| **Overall** | **90%** | **Platform-wide minimum** |

### Test Result Reporting

```python
"""
TEST RESULT REPORTING AND DASHBOARDING

Test results are reported in three layers:

1. CI/CD INLINE — GitHub Actions annotations on PRs
   - Failed tests appear as PR comments with details
   - Coverage delta shown (improved/regressed)

2. DASHBOARD — Internal Grafana dashboard
   - Test pass rate over time (trend)
   - Coverage percentage over time (trend)
   - Adversarial test results (critical tracking)
   - E2E scenario pass rates per scenario
   - WDC consistency metrics

3. ALERTS — Critical failures trigger immediate notification
   - Any adversarial test failure = CRITICAL alert
   - Any deadline computation failure = CRITICAL alert
   - Coverage drop below threshold = WARNING alert
   - Performance regression > 20% = WARNING alert
"""

class TestReporter:
    """Generates test result reports for dashboarding."""

    def generate_report(self, results: TestResults) -> Report:
        return Report(
            summary=ReportSummary(
                total_tests=results.total,
                passed=results.passed,
                failed=results.failed,
                skipped=results.skipped,
                pass_rate=results.passed / results.total * 100,
                coverage=results.coverage_percent,
            ),
            critical_failures=[
                r for r in results.failures
                if r.category in ["adversarial", "deadline", "citation"]
            ],
            regressions=[
                r for r in results.failures
                if r.is_regression
            ],
            performance=PerformanceMetrics(
                avg_response_time=results.avg_response_time,
                p95_response_time=results.p95_response_time,
                total_tokens_used=results.total_tokens,
                total_api_cost=results.total_cost,
            ),
        )
```

---

## 16.12 TESTING METRICS & TARGETS — SUMMARY

| Metric | Target | Current | Measurement Method | Alert Threshold |
|--------|--------|---------|-------------------|-----------------|
| Citation accuracy | 99.9% | -- | Verified / total citations | <99.5% = CRITICAL |
| Deadline accuracy | 100% | -- | Correct / total computations | <100% = CRITICAL |
| Hallucination rate | 0% | -- | Fabricated in output / total | >0% = CRITICAL |
| WDC consistency | <5% variance | -- | Stdev across 10 same-input runs | >5% = WARNING |
| E2E pass rate | >95% | -- | Scenarios passing all criteria | <90% = WARNING |
| Element extraction | 99% | -- | Correct elements / total | <95% = WARNING |
| Jurisdiction ID | 100% | -- | Correct court / total | <100% = CRITICAL |
| Unit test coverage | 95% | -- | Lines covered / total lines | <90% = WARNING |
| Integration coverage | 85% | -- | Endpoints covered / total | <80% = WARNING |
| Response time (P95) | <30s | -- | 95th percentile latency | >60s = WARNING |
| Token efficiency | <$5/motion | -- | API cost per deliverable | >$10 = WARNING |

### Certification Gate

**No release may ship if any of the following are true:**
1. Any CRITICAL metric is below target
2. Any adversarial test is failing
3. Any deadline computation test is failing
4. Overall test coverage is below 90%
5. WDC consistency variance exceeds 5%

This certification gate is enforced in CI/CD. The release pipeline will not proceed past the test stage if any of these conditions exist.

---

## 16.13 FRAMEWORK SUMMARY

| Layer | What It Tests | Test Count | Execution Frequency |
|-------|--------------|------------|---------------------|
| **Unit — Deadlines** | FRCP, state rules, holidays, extensions, SOL | 17 | Every commit |
| **Unit — Citations** | Format, existence, overruling, holding match | 10 | Every commit |
| **Unit — Jurisdiction/Elements** | Court ID, venue, standing, claim elements | 13 | Every commit |
| **Integration** | CourtListener, US Code, citation pipeline, judge analytics | 12+ | Every PR (mock), nightly (live) |
| **Adversarial** | Hallucination injection, outdated law traps | 9 | Nightly, pre-release |
| **End-to-End** | Full case scenarios from intake to resolution | 10 | Nightly, pre-release |
| **WDC Validation** | Scoring consistency, veto triggers, revision loops | 5 | Weekly, pre-release |
| **Regression** | Golden output comparison, performance, error museum | Ongoing | Every PR (subset), nightly (full) |
| **TOTAL** | | **76+ tests** | |

**The testing strategy exists for one reason:** to ensure that when a pro se litigant files a document prepared with Ciphergy's help, every citation is real, every deadline is correct, every element is addressed, and every argument has been stress-tested by five independent AI minds. The opposing party and the court will never know an AI helped prepare it — but the quality will speak for itself.

---

*Testing is not a phase. It is a permanent verification layer that runs continuously, catches regressions immediately, and ensures that Ciphergy's output is worthy of the courtroom. A single fabricated citation filed with a federal court would undo every claim this platform makes. The testing strategy exists to make that outcome impossible.*
