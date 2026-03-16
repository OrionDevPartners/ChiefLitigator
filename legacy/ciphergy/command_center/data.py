"""Data layer for the Ciphergy Command Center.

Reads case repo files and provides structured data to Flask templates.
All data comes from the case repo at runtime -- no case-specific data
is hard-coded in this module.
"""

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Union

from file_watcher import FileWatcher
from parsers import (
    extract_percentage,
    parse_action_items,
    parse_alert_blocks,
    parse_all_md_tables,
    parse_diff_entries,
    parse_md_sections,
    parse_md_table,
    parse_questions,
    strip_md_formatting,
)


class CaseData:
    """Reads case repo files and provides structured data.

    Parameters
    ----------
    case_dir : str or Path
        Root directory of the case repo.
    """

    def __init__(self, case_dir: Union[str, Path]) -> None:
        self.case_dir = Path(case_dir)
        self._watcher = FileWatcher()
        self._cache: dict[str, object] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read(self, rel_path: str) -> Optional[str]:
        """Read a file relative to case_dir. Returns None on any error."""
        p = self.case_dir / rel_path
        try:
            return p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    def _read_json(self, rel_path: str) -> Optional[dict]:
        """Read and parse a JSON file. Returns None on error."""
        text = self._read(rel_path)
        if text is None:
            return None
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None

    def _cached(self, key: str, rel_path: str, loader: callable) -> object:
        """Return cached data, refreshing if the source file changed."""
        full_path = self.case_dir / rel_path
        if self._watcher.has_changed(full_path) or key not in self._cache:
            self._cache[key] = loader()
            self._watcher.mark_read(full_path)
        return self._cache[key]

    # ------------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------------

    def _load_manifest(self) -> dict:
        data = self._read_json("CASE_MANIFEST.json")
        return data if data else {}

    def _manifest(self) -> dict:
        return self._cached("manifest", "CASE_MANIFEST.json", self._load_manifest)

    # ------------------------------------------------------------------
    # Deadlines
    # ------------------------------------------------------------------

    def get_deadlines(self) -> list[dict]:
        """Parse CASE_MANIFEST.json deadlines with days_remaining calculated.

        Returns list of dicts:
            {id, date, date_obj, description, matter, status,
             action_required, alert_days_before, dependencies,
             days_remaining, is_overdue, is_urgent}
        """
        manifest = self._manifest()
        raw_deadlines = manifest.get("deadlines", [])
        today = date.today()
        results: list[dict] = []

        for d in raw_deadlines:
            deadline = dict(d)  # shallow copy
            # Parse date
            date_str = deadline.get("date", "")
            try:
                deadline_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                deadline_date = None

            deadline["date_obj"] = deadline_date

            if deadline_date:
                delta = (deadline_date - today).days
                deadline["days_remaining"] = delta
                deadline["is_overdue"] = delta < 0
                alert_days = deadline.get("alert_days_before", 7)
                deadline["is_urgent"] = 0 <= delta <= alert_days
            else:
                deadline["days_remaining"] = None
                deadline["is_overdue"] = False
                deadline["is_urgent"] = False

            results.append(deadline)

        # Sort: urgent first, then by days_remaining ascending
        def sort_key(d: dict) -> tuple:
            dr = d["days_remaining"]
            if dr is None:
                return (2, 9999)
            if d["is_urgent"]:
                return (0, dr)
            return (1, dr)

        results.sort(key=sort_key)
        return results

    # ------------------------------------------------------------------
    # Matters
    # ------------------------------------------------------------------

    def get_matters(self) -> list[dict]:
        """Parse CASE_MANIFEST.json matters.

        Returns list of dicts:
            {id, name, status, phase, case_number}
        """
        manifest = self._manifest()
        raw_matters = manifest.get("matters", {})
        results: list[dict] = []
        for matter_id, info in raw_matters.items():
            matter = dict(info)
            matter["id"] = matter_id
            results.append(matter)
        return results

    # ------------------------------------------------------------------
    # Entities (Person Analysis Reports)
    # ------------------------------------------------------------------

    def get_entities(self) -> list[dict]:
        """Scan 07_STRATEGY/PERSON_ANALYSIS_REPORT_*.md for entity cards.

        Returns list of dicts:
            {name, score, matter, claims: [{name, score}], file_path, file_name}
        """
        strategy_dir = self.case_dir / "07_STRATEGY"
        if not strategy_dir.is_dir():
            return []

        entities: list[dict] = []
        pattern = "PERSON_ANALYSIS_REPORT_*.md"

        for pa_file in sorted(strategy_dir.glob(pattern)):
            # Skip the template
            if "TEMPLATE" in pa_file.name:
                continue

            entity = self._parse_entity_card(pa_file)
            if entity:
                entities.append(entity)

        # Sort by score descending
        entities.sort(key=lambda e: e.get("score", 0), reverse=True)
        return entities

    def _parse_entity_card(self, pa_file: Path) -> Optional[dict]:
        """Extract summary card data from a Person Analysis Report file."""
        try:
            text = pa_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        # Extract name from filename: PERSON_ANALYSIS_REPORT_First_Last_vN.md
        name_match = re.search(r"PERSON_ANALYSIS_REPORT_(.+?)_v\d+\.md$", pa_file.name)
        if name_match:
            name = name_match.group(1).replace("_", " ")
        else:
            # Fallback: try from the title line
            title_match = re.search(r"#\s+PERSON ANALYSIS REPORT:\s*(.+)", text)
            name = title_match.group(1).strip() if title_match else pa_file.stem

        # Entity score — handles formats like:
        #   > **Entity Score:** 10.00 — MAXIMUM
        #   | **Entity Score** | **10.00 — MAXIMUM** |
        score_match = re.search(r"Entity\s+Score[:\s|]*\*{0,2}\s*([\d.]+)", text)
        score = float(score_match.group(1)) if score_match else 0.0

        # Determine matter from content
        matter = self._detect_matter(text)

        # Extract claim scores from the confidence summary table
        claims = self._extract_claim_scores(text)

        # Generate a stable ID from filename
        entity_id = pa_file.stem  # e.g. PERSON_ANALYSIS_REPORT_Anthony_Campenni_v1

        return {
            "id": entity_id,
            "name": name,
            "score": score,
            "matter": matter,
            "claims": claims,
            "file_path": str(pa_file),
            "file_name": pa_file.name,
        }

    def _detect_matter(self, text: str) -> str:
        """Detect which matter a PA report relates to, based on content."""
        text_lower = text.lower()
        if "palmisano" in text_lower and "campenni" not in text_lower[:500]:
            return "palmisano"
        if "campenni" in text_lower[:500]:
            return "campenni"
        # Check for key identifiers
        if "1413 southard" in text_lower:
            return "campenni"
        if "606 yupon" in text_lower:
            return "palmisano"
        return "unknown"

    def _extract_claim_scores(self, text: str) -> list[dict]:
        """Extract claim names and scores from a PA report.

        Looks for the revised confidence summary table or individual count headings.
        """
        claims: list[dict] = []

        # Pattern 1: summary table like "| I | Defamation Per Se | **85%** | FILED |"
        table_re = re.compile(
            r"\|\s*([IVX]+|\w+)\s*\|"  # count number
            r"\s*\*{0,2}([^|]+?)\*{0,2}\s*\|"  # claim name
            r"\s*\*{0,2}(\d{1,3})%\*{0,2}\s*\|"  # score
        )
        for m in table_re.finditer(text):
            claim_name = m.group(2).strip()
            score = int(m.group(3))
            claims.append({"name": claim_name, "score": score})

        if claims:
            return claims

        # Pattern 2: section headings like "### Count I — Defamation Per Se"
        # followed by "**Strength: 85%**"
        count_re = re.compile(
            r"###\s+Count\s+([IVX]+)\s*[—\-:]\s*(.+?)$"
            r".*?"
            r"Strength[:\s]*\*{0,2}(\d{1,3})%\*{0,2}",
            re.MULTILINE | re.DOTALL,
        )
        for m in count_re.finditer(text):
            claim_name = m.group(2).strip()
            score = int(m.group(3))
            claims.append({"name": claim_name, "score": score})

        return claims

    def get_entity_detail(self, entity_id: str) -> Optional[dict]:
        """Parse a single Person Analysis Report into full structured data.

        Parameters
        ----------
        entity_id : str
            The file stem, e.g. "PERSON_ANALYSIS_REPORT_Anthony_Campenni_v1"

        Returns dict with all 15 sections as structured data, or None if not found.
        """
        strategy_dir = self.case_dir / "07_STRATEGY"
        pa_file = strategy_dir / f"{entity_id}.md"

        if not pa_file.is_file():
            return None

        try:
            text = pa_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        # Start with the card data
        card = self._parse_entity_card(pa_file)
        if card is None:
            card = {}

        # Parse full sections
        sections = parse_md_sections(text, max_level=3)

        detail = dict(card)
        detail["sections"] = {}

        # Map known section titles to keys
        section_map = {
            "timeline": "SECTION 0",
            "entity": "SECTION 1",
            "claims": "SECTION 2",
            "evidence_in_hand": "SECTION 3",
            "stress_test": "SECTION 4",
            "contradictions": "SECTION 4A",
            "credibility_matrix": "SECTION 4B",
            "statutes": "SECTION 5",
            "evidence_cross_ref": "SECTION 6",
            "damages": "SECTION 7",
            "criminal_exposure": "SECTION 8",
            "final_summary": "SECTION 9",
            "actions": "SECTION 10",
            "deposition_questions": "SECTION 10A",
            "response_strategy": "SECTION 11",
            "additional_intel": "SECTION 12",
        }

        for key, section_marker in section_map.items():
            section_data = self._find_section(sections, section_marker)
            if section_data:
                detail["sections"][key] = section_data

        # Parse specific structured data from raw text sections
        # Timeline
        timeline_section = self._extract_section_text(text, "SECTION 0")
        if timeline_section:
            detail["timeline"] = parse_md_table(timeline_section)

        # Contradictions
        contradictions_section = self._extract_section_text(text, "SECTION 4A")
        if contradictions_section:
            detail["contradictions"] = parse_md_table(contradictions_section)

        # Credibility matrix
        cred_section = self._extract_section_text(text, "SECTION 4B")
        if cred_section:
            detail["credibility_matrix"] = parse_md_table(cred_section)

        # Evidence in hand
        evidence_section = self._extract_section_text(text, "SECTION 3")
        if evidence_section:
            detail["evidence_in_hand"] = parse_md_table(evidence_section)

        # Criminal exposure
        criminal_section = self._extract_section_text(text, "SECTION 8")
        if criminal_section:
            detail["criminal_exposure"] = parse_md_table(criminal_section)

        # Damages
        damages_section = self._extract_section_text(text, "SECTION 7")
        if damages_section:
            tables = parse_all_md_tables(damages_section)
            detail["damages_tables"] = tables

        # Actions
        actions_section = self._extract_section_text(text, "SECTION 10")
        if actions_section:
            tables = parse_all_md_tables(actions_section)
            detail["action_tables"] = tables

        # Deposition questions (numbered list)
        depo_section = self._extract_section_text(text, "SECTION 10A")
        if depo_section:
            detail["deposition_questions"] = self._parse_numbered_list(depo_section)

        # Witness reliability
        witness_section = self._extract_section_text(text, "12G")
        if witness_section:
            detail["witnesses"] = parse_md_table(witness_section)

        # Connections map (code block)
        connections_re = re.compile(r"```\s*\n((?:.*?\n)*?.*?)```", re.DOTALL)
        for block_match in connections_re.finditer(text):
            block = block_match.group(1)
            if "Orchestrator" in block or "├──" in block or "└──" in block:
                detail["connections_map"] = block.strip()
                break

        return detail

    def _find_section(self, sections: dict, marker: str) -> Optional[dict]:
        """Find a section whose title contains the marker string."""
        for key, val in sections.items():
            if key.startswith("_"):
                continue
            if marker.upper() in key.upper():
                return val
            if isinstance(val, dict):
                found = self._find_section(val, marker)
                if found:
                    return found
        return None

    def _extract_section_text(self, full_text: str, section_marker: str) -> Optional[str]:
        """Extract raw text for a section identified by marker in heading."""
        # Find heading containing the marker
        heading_re = re.compile(
            r"^(#{1,4})\s+.*?" + re.escape(section_marker) + r".*$",
            re.MULTILINE | re.IGNORECASE,
        )
        m = heading_re.search(full_text)
        if not m:
            return None

        level = len(m.group(1))
        start = m.end()

        # Find the next heading at same or higher level
        next_heading_re = re.compile(
            r"^#{1," + str(level) + r"}\s+",
            re.MULTILINE,
        )
        nm = next_heading_re.search(full_text, start)
        end = nm.start() if nm else len(full_text)

        return full_text[start:end].strip()

    def _parse_numbered_list(self, text: str) -> list[str]:
        """Parse a numbered list from text, returning the items."""
        items: list[str] = []
        num_re = re.compile(r"^\d+\.\s+(.+)$", re.MULTILINE)
        for m in num_re.finditer(text):
            items.append(m.group(1).strip().strip('"'))
        return items

    # ------------------------------------------------------------------
    # Evidence scores
    # ------------------------------------------------------------------

    def get_evidence_scores(self) -> dict:
        """Parse EVIDENCE_CONFIDENCE_MONITOR.md into structured scores.

        Returns dict:
            {
                "overall": {"score": 87, "rating": "VERY STRONG"},
                "locked_claims": [
                    {"count": "I", "name": "Defamation Per Se",
                     "score": 85, "rating": "VERY STRONG", "trend": "...",
                     "weakest_element": "..."}
                ],
                "building_claims": [
                    {"name": "Civil Conspiracy", "score": 55,
                     "threshold": 75, "gap": 20, "trigger": "..."}
                ],
                "evidence_in_hand": [...],
                "obtainable": [...],
                "discovery_dependent": [...],
                "witness_dependent": [...],
                "threshold_rules": [...]
            }
        """
        rel = "EVIDENCE_CONFIDENCE_MONITOR.md"

        def loader() -> dict:
            return self._parse_evidence_monitor()

        return self._cached("evidence_scores", rel, loader)

    def _parse_evidence_monitor(self) -> dict:
        text = self._read("EVIDENCE_CONFIDENCE_MONITOR.md")
        if not text:
            return {}

        result: dict = {
            "overall": {},
            "locked_claims": [],
            "building_claims": [],
            "evidence_in_hand": [],
            "obtainable": [],
            "discovery_dependent": [],
            "witness_dependent": [],
            "threshold_rules": [],
        }

        sections = parse_md_sections(text, max_level=3)

        # Overall posture from Section 5
        posture_text = self._extract_section_text(text, "SECTION 5")
        if posture_text:
            posture_table = parse_md_table(posture_text)
            result["locked_claims"] = []
            for row in posture_table:
                claim: dict = {}
                # Extract count identifier
                count_str = row.get("count", "")
                claim["count"] = strip_md_formatting(count_str).strip()
                claim["name"] = strip_md_formatting(row.get("claim", row.get("col", ""))).strip(" —-")
                pct = extract_percentage(row.get("confidence", row.get("score", "")))
                claim["score"] = pct if pct is not None else 0
                claim["rating"] = strip_md_formatting(row.get("rating", "")).strip()
                claim["trend"] = strip_md_formatting(row.get("trend", "")).strip()
                result["locked_claims"].append(claim)

            # Overall score from the **OVERALL CASE** row or explicit text
            overall_match = re.search(r"OVERALL CASE.*?(\d{1,3})%", posture_text)
            if overall_match:
                result["overall"]["score"] = int(overall_match.group(1))
            overall_rating = re.search(
                r"OVERALL CASE.*?\d+%.*?\*{0,2}([\w ]+)\*{0,2}\s*\|",
                posture_text,
            )
            if overall_rating:
                rating_text = overall_rating.group(1).strip()
                if rating_text:
                    result["overall"]["rating"] = rating_text
            # Fallback: look for explicit rating after the percentage
            if not result["overall"].get("rating"):
                rating_match2 = re.search(
                    r"OVERALL.*?(\d+)%.*?\*{2}([\w ]+)\*{2}",
                    posture_text,
                )
                if rating_match2:
                    result["overall"]["rating"] = rating_match2.group(2).strip()

        # Building claims from threshold monitor
        threshold_text = self._extract_section_text(text, "BUILDING CLAIM THRESHOLD MONITOR")
        if threshold_text:
            building_table = parse_md_table(threshold_text)
            for row in building_table:
                bc: dict = {}
                bc["name"] = strip_md_formatting(row.get("claim", "")).strip()
                bc["score"] = extract_percentage(row.get("current", row.get("current_%", ""))) or 0
                bc["threshold"] = extract_percentage(row.get("threshold", "")) or 75
                bc["gap"] = extract_percentage(row.get("gap", "")) or 0
                bc["trigger"] = strip_md_formatting(row.get("projected_trigger", "")).strip()
                result["building_claims"].append(bc)

        # Evidence collection sections
        sections_map = {
            "evidence_in_hand": "IN HAND",
            "obtainable": "OBTAINABLE",
            "discovery_dependent": "DISCOVERY DEPENDENT",
            "witness_dependent": "WITNESS DEPENDENT",
        }
        for result_key, section_marker in sections_map.items():
            section_text = self._extract_section_text(text, section_marker)
            if section_text:
                result[result_key] = parse_md_table(section_text)

        # Threshold rules
        rules_text = self._extract_section_text(text, "THRESHOLD RULES")
        if rules_text:
            result["threshold_rules"] = parse_md_table(rules_text)

        return result

    # ------------------------------------------------------------------
    # Cascade log (DIFF/ files)
    # ------------------------------------------------------------------

    def get_cascade_log(self, limit: int = 20) -> list[dict]:
        """Read DIFF/ files and return recent change entries.

        Returns list of dicts (newest first):
            {file, action, what_changed, reason, effect, session_date}
        """
        diff_dir = self.case_dir / "DIFF"
        if not diff_dir.is_dir():
            return []

        # Get diff files sorted by name descending (newest date first)
        diff_files = sorted(diff_dir.glob("*.md"), reverse=True)

        entries: list[dict] = []
        for diff_file in diff_files:
            if len(entries) >= limit:
                break

            try:
                text = diff_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Extract session date from filename: YYYY-MM-DD_session_diffs.md
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", diff_file.name)
            session_date = date_match.group(1) if date_match else ""

            file_entries = parse_diff_entries(text)
            for entry in file_entries:
                entry["session_date"] = session_date
                entries.append(entry)
                if len(entries) >= limit:
                    break

        return entries[:limit]

    # ------------------------------------------------------------------
    # Filings
    # ------------------------------------------------------------------

    def get_filings(self) -> list[dict]:
        """Scan 01_ACTIVE_FILINGS/ for filing packages with versions.

        Returns list of dicts:
            {phase, phase_dir, files: [{name, path, ext, size_kb}]}
        """
        filings_dir = self.case_dir / "01_ACTIVE_FILINGS"
        if not filings_dir.is_dir():
            return []

        phases: list[dict] = []
        for phase_dir in sorted(filings_dir.iterdir()):
            if not phase_dir.is_dir():
                continue

            phase: dict = {
                "phase": phase_dir.name,
                "phase_dir": str(phase_dir),
                "files": [],
            }

            for f in sorted(phase_dir.iterdir()):
                if f.is_file() and not f.name.startswith("."):
                    try:
                        size_kb = round(f.stat().st_size / 1024, 1)
                    except OSError:
                        size_kb = 0
                    phase["files"].append(
                        {
                            "name": f.stem,
                            "path": str(f),
                            "ext": f.suffix.lstrip("."),
                            "size_kb": size_kb,
                        }
                    )

            phases.append(phase)

        return phases

    # ------------------------------------------------------------------
    # Law library
    # ------------------------------------------------------------------

    def get_law_library(self) -> dict:
        """Scan THE_LAW/ for organized statutes, case law, bar rules, etc.

        Returns dict:
            {
                "statutes": [{name, path, statute_number}],
                "case_law": [{name, path, case_name}],
                "bar_rules": [{name, path, rule_number}],
                "claims": {
                    "matter_name": [{name, path}]
                },
                "procedures": [{name, path}]
            }
        """
        law_dir = self.case_dir / "THE_LAW"
        if not law_dir.is_dir():
            return {}

        result: dict = {
            "statutes": [],
            "case_law": [],
            "bar_rules": [],
            "claims": {},
            "procedures": [],
        }

        # Statutes
        stat_dir = law_dir / "STATUTES"
        if stat_dir.is_dir():
            for f in sorted(stat_dir.glob("*.md")):
                # Extract statute number from filename: FL_415.1111.md
                num_match = re.search(r"FL_(.+)\.md$", f.name)
                result["statutes"].append(
                    {
                        "name": f.stem.replace("_", " "),
                        "path": str(f),
                        "statute_number": num_match.group(1) if num_match else "",
                    }
                )

        # Case law
        case_dir = law_dir / "CASE_LAW"
        if case_dir.is_dir():
            for f in sorted(case_dir.glob("*.md")):
                result["case_law"].append(
                    {
                        "name": f.stem.replace("_", " "),
                        "path": str(f),
                        "case_name": f.stem.replace("_", " "),
                    }
                )

        # Bar rules
        bar_dir = law_dir / "BAR_RULES"
        if bar_dir.is_dir():
            for f in sorted(bar_dir.glob("*.md")):
                num_match = re.search(r"Rule_(.+)\.md$", f.name)
                result["bar_rules"].append(
                    {
                        "name": f.stem.replace("_", " "),
                        "path": str(f),
                        "rule_number": num_match.group(1).replace("_", "-") if num_match else "",
                    }
                )

        # Claims (per-matter)
        claims_dir = law_dir / "CLAIMS"
        if claims_dir.is_dir():
            for matter_dir in sorted(claims_dir.iterdir()):
                if matter_dir.is_dir():
                    matter_files: list[dict] = []
                    for f in sorted(matter_dir.glob("*.md")):
                        matter_files.append(
                            {
                                "name": f.stem.replace("_", " "),
                                "path": str(f),
                            }
                        )
                    if matter_files:
                        result["claims"][matter_dir.name] = matter_files

        # Procedures
        proc_dir = law_dir / "PROCEDURES"
        if proc_dir.is_dir():
            for f in sorted(proc_dir.glob("*.md")):
                result["procedures"].append(
                    {
                        "name": f.stem.replace("_", " "),
                        "path": str(f),
                    }
                )

        return result

    # ------------------------------------------------------------------
    # Action items (from dashboard)
    # ------------------------------------------------------------------

    def get_action_items(self) -> list[dict]:
        """Parse CASE_POSTURE_DASHBOARD.md for top action items.

        Returns list of dicts:
            {number, action, matter, deadline, status}
        """
        rel = "CASE_POSTURE_DASHBOARD.md"

        def loader() -> list[dict]:
            text = self._read(rel)
            if not text:
                return []

            # Find the "NEXT 5 CRITICAL ACTIONS" section
            section_text = self._extract_section_text(text, "CRITICAL ACTIONS")
            if not section_text:
                # Fallback: try parsing all action-like tables
                return parse_action_items(text)

            table = parse_md_table(section_text)
            items: list[dict] = []
            for row in table:
                items.append(
                    {
                        "number": strip_md_formatting(row.get("#", row.get("col", ""))).strip(),
                        "action": strip_md_formatting(row.get("action", "")).strip(),
                        "matter": strip_md_formatting(row.get("matter", "")).strip(),
                        "deadline": strip_md_formatting(row.get("deadline", "")).strip(),
                        "status": strip_md_formatting(row.get("status", "")).strip(),
                    }
                )
            return items

        return self._cached("action_items", rel, loader)

    # ------------------------------------------------------------------
    # Open questions
    # ------------------------------------------------------------------

    def get_open_questions(self) -> list[dict]:
        """Parse _QUESTIONS_FOR_BO.md for open questions.

        Returns list of dicts:
            {number, question, context, deadline, status, priority}
        """
        rel = "_QUESTIONS_FOR_BO.md"

        def loader() -> list[dict]:
            text = self._read(rel)
            if not text:
                return []

            questions = parse_questions(text)
            results: list[dict] = []
            for q in questions:
                # Detect priority from the section heading context
                priority = "MEDIUM"
                q_text = q.get("question", "")
                if "CRITICAL" in text[: text.find(q_text) if q_text in text else 0].split("##")[-1] if q_text else "":
                    priority = "CRITICAL"

                results.append(
                    {
                        "number": strip_md_formatting(q.get("#", q.get("col", ""))).strip(),
                        "question": strip_md_formatting(q.get("question", "")).strip(),
                        "context": strip_md_formatting(q.get("context", "")).strip(),
                        "deadline": strip_md_formatting(q.get("deadline", "")).strip(),
                        "status": strip_md_formatting(q.get("status", "")).strip(),
                        "priority": priority,
                    }
                )
            return results

        return self._cached("open_questions", rel, loader)

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def get_signals(self) -> list[dict]:
        """Read CIPHERGY_SIGNALS.md for signal log entries.

        Returns list of dicts (newest first):
            {timestamp, type, message, source}

        If the file does not exist, returns empty list.
        """
        rel = "CIPHERGY_SIGNALS.md"

        def loader() -> list[dict]:
            text = self._read(rel)
            if not text:
                return []

            signals: list[dict] = []

            # Try table format first
            tables = parse_all_md_tables(text)
            for table in tables:
                for row in table:
                    signals.append(
                        {
                            "timestamp": row.get("timestamp", row.get("date", "")),
                            "type": row.get("type", row.get("signal", "")),
                            "message": row.get("message", row.get("description", row.get("detail", ""))),
                            "source": row.get("source", ""),
                        }
                    )

            if signals:
                return signals

            # Try line-based format: [SIGNAL] TYPE | key: value
            signal_re = re.compile(r"\[SIGNAL\]\s*(\w+)\s*\|\s*(.+)", re.MULTILINE)
            for m in signal_re.finditer(text):
                sig_type = m.group(1)
                payload = m.group(2)
                signals.append(
                    {
                        "timestamp": "",
                        "type": sig_type,
                        "message": payload.strip(),
                        "source": "signal_log",
                    }
                )

            return signals

        return self._cached("signals", rel, loader)

    # ------------------------------------------------------------------
    # Red alerts
    # ------------------------------------------------------------------

    def get_red_alerts(self) -> list[dict]:
        """Parse _RED_ALERTS.md for alert items.

        Returns list of dicts:
            {claim, confidence, confidence_pct, status, threshold,
             recommended_action, date, alert_status}
        """
        rel = "_RED_ALERTS.md"

        def loader() -> list[dict]:
            text = self._read(rel)
            if not text:
                return []

            alerts = parse_alert_blocks(text)

            # Also parse the below-threshold tracking table
            below_text = self._extract_section_text(text, "BELOW-THRESHOLD")
            if below_text:
                below_table = parse_md_table(below_text)
                for row in below_table:
                    alerts.append(
                        {
                            "claim": strip_md_formatting(row.get("claim", "")).strip(),
                            "confidence_pct": extract_percentage(row.get("current", row.get("current_%", ""))) or 0,
                            "threshold": row.get("threshold", "75%"),
                            "status": "BELOW THRESHOLD",
                            "alert_status": "monitoring",
                            "watch_for": strip_md_formatting(row.get("watch_for", "")).strip(),
                        }
                    )

            return alerts

        return self._cached("red_alerts", rel, loader)

    # ------------------------------------------------------------------
    # Dashboard data (combined)
    # ------------------------------------------------------------------

    def get_dashboard_data(self) -> dict:
        """Get all data needed for the main dashboard view.

        Combines matters, deadlines, action items, claim scores,
        alerts, and opposing moves into a single dict.
        """
        text = self._read("CASE_POSTURE_DASHBOARD.md") or ""

        # Opposing side moves
        opposing_text = self._extract_section_text(text, "OPPOSING SIDE")
        opposing_moves: list[dict] = []
        if opposing_text:
            opposing_moves = parse_md_table(opposing_text)

        # Evidence gaps
        gaps_text = self._extract_section_text(text, "EVIDENCE GAPS")
        evidence_gaps: list[dict] = []
        if gaps_text:
            evidence_gaps = parse_md_table(gaps_text)

        # Claim strength from dashboard (quick view)
        claim_tables = []
        for marker in ("Campenni", "Palmisano"):
            section_text = self._extract_section_text(text, marker)
            if section_text:
                table = parse_md_table(section_text)
                if table:
                    claim_tables.append({"matter": marker.lower(), "claims": table})

        return {
            "matters": self.get_matters(),
            "deadlines": self.get_deadlines(),
            "action_items": self.get_action_items(),
            "red_alerts": self.get_red_alerts(),
            "opposing_moves": opposing_moves,
            "evidence_gaps": evidence_gaps,
            "claim_scores": claim_tables,
            "last_updated": self._extract_last_updated(text),
        }

    def _extract_last_updated(self, text: str) -> str:
        """Extract 'Last Updated' date from markdown text."""
        m = re.search(r"Last Updated[:\s]*(\d{4}-\d{2}-\d{2})", text)
        return m.group(1) if m else ""

    # ------------------------------------------------------------------
    # Utility: invalidate all caches
    # ------------------------------------------------------------------

    def clear_cache(self) -> None:
        """Force all data to be re-read on next access."""
        self._cache.clear()
        self._watcher.clear()
