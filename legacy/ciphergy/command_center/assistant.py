"""
AI Assistant module for the Ciphergy Command Center.

Manages template selection, execution preparation, and the DraftGuardian
7-gate quality filter for outbound communications.

This module does NOT call Claude directly. It prepares prompts that can be
pasted into Claude Code sessions for execution.
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default emotional / discipline words (overridable via config)
# ---------------------------------------------------------------------------

_DEFAULT_EMOTIONAL_WORDS = [
    "outrageous",
    "unbelievable",
    "disgusting",
    "shocking",
    "furious",
    "angry",
    "frustrated",
    "upset",
    "terrible",
    "ridiculous",
    "absurd",
    "insane",
    "crazy",
    "stupid",
    "liar",
    "cheat",
    "thief",
    "criminal",
    "corrupt",
    "demand",
    "insist",
    "threaten",
    "warn",
    "promise",
    "always",
    "never",
    "everyone",
    "nobody",
    "obviously",
    "clearly",
    "certainly",
    "definitely",
]

# Phrases that suggest fabricated or placeholder content
_PLACEHOLDER_PATTERNS = [
    r"\[INSERT\b",
    r"\[TODO\b",
    r"\[FILL\b",
    r"\[PLACEHOLDER\b",
    r"\bTBD\b",
    r"\bXXX\b",
    r"\bLorem ipsum\b",
    r"\[YOUR NAME\b",
    r"\[DATE\b",
    r"\[CASE NUMBER\b",
]

# Threshold / trigger keywords that require extra review
_DEFAULT_TRIGGER_KEYWORDS = [
    "emergency",
    "ex parte",
    "TRO",
    "restraining order",
    "immediate",
    "irreparable harm",
    "contempt",
    "sanctions",
    "default judgment",
    "summary judgment",
]


# ---------------------------------------------------------------------------
# TemplateRunner
# ---------------------------------------------------------------------------


class TemplateRunner:
    """Manages template selection and execution preparation.

    Templates are Markdown files stored in a templates directory, with YAML
    front-matter containing metadata (name, description, trigger phrases,
    required fields).

    Template file naming convention: ``<slug>.template.md``
    """

    def __init__(self, templates_dir: Union[str, Path], case_dir: Union[str, Path]) -> None:
        self.templates_dir = Path(templates_dir)
        self.case_dir = Path(case_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_templates(self) -> list[dict]:
        """List all available templates with name, description, and trigger phrases.

        Scans ``templates_dir`` for ``*.template.md`` files and parses their
        front-matter.

        Returns a list of dicts::

            [
                {
                    "name": "opposition_brief",
                    "file": "opposition_brief.template.md",
                    "description": "Draft an opposition brief ...",
                    "trigger_phrases": ["oppose", "opposition", "respond to motion"],
                },
                ...
            ]
        """
        templates: list[dict] = []
        if not self.templates_dir.is_dir():
            logger.warning("Templates directory does not exist: %s", self.templates_dir)
            return templates

        for path in sorted(self.templates_dir.glob("*.template.md")):
            meta = self._parse_front_matter(path)
            templates.append(
                {
                    "name": meta.get("name", path.stem.replace(".template", "")),
                    "file": path.name,
                    "description": meta.get("description", ""),
                    "trigger_phrases": meta.get("trigger_phrases", []),
                }
            )

        return templates

    def get_template(self, name: str) -> dict:
        """Load a template with its full content and field definitions.

        Parameters
        ----------
        name : str
            The template slug (without ``.template.md`` extension).

        Returns
        -------
        dict
            ``{name, file, description, trigger_phrases, fields, content}``

        Raises
        ------
        FileNotFoundError
            If no matching template file exists.
        """
        path = self.templates_dir / f"{name}.template.md"
        if not path.is_file():
            raise FileNotFoundError(f"Template not found: {path}")

        meta = self._parse_front_matter(path)
        content = self._extract_body(path)

        return {
            "name": meta.get("name", name),
            "file": path.name,
            "description": meta.get("description", ""),
            "trigger_phrases": meta.get("trigger_phrases", []),
            "fields": meta.get("fields", []),
            "content": content,
        }

    def prepare_execution(self, template_name: str, params: dict) -> str:
        """Generate a Claude prompt that executes the template with given parameters.

        The returned string is a self-contained prompt that can be pasted into
        a Claude Code session for execution.

        Parameters
        ----------
        template_name : str
            Template slug.
        params : dict
            Key-value pairs matching the template's field definitions.

        Returns
        -------
        str
            A formatted prompt string ready for Claude Code.
        """
        template = self.get_template(template_name)
        content = template["content"]

        # Substitute any {{field}} placeholders with provided params
        for key, value in params.items():
            content = content.replace("{{" + key + "}}", str(value))

        # Build the prompt
        lines = [
            f"# Task: Execute template '{template['name']}'",
            f"# Description: {template['description']}",
            f"# Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Parameters",
        ]

        for key, value in params.items():
            lines.append(f"- **{key}**: {value}")

        lines.extend(
            [
                "",
                "## Instructions",
                "",
                content,
            ]
        )

        # Append case directory context
        lines.extend(
            [
                "",
                f"## Case directory: {self.case_dir}",
                "",
                "Use files from the case directory for evidence and reference. "
                "All output should be saved within the case directory structure.",
            ]
        )

        return "\n".join(lines)

    def list_entities(self) -> list[str]:
        """List all entities with existing PA (Predictive Analysis) reports.

        Scans case_dir for entity subdirectories that contain PA report files.
        """
        entities: list[str] = []
        if not self.case_dir.is_dir():
            return entities

        for item in sorted(self.case_dir.iterdir()):
            if not item.is_dir():
                continue
            # Check for PA reports (files matching *pa_report* or *PA*)
            pa_files = (
                list(item.glob("*pa_report*"))
                + list(item.glob("*PA_report*"))
                + list(item.glob("*predictive_analysis*"))
            )
            if pa_files:
                entities.append(item.name)

        return entities

    def list_matters(self) -> list[str]:
        """List all active matters.

        Scans case_dir for matter subdirectories (directories containing a
        ``matter.json`` or ``matter.yaml`` config file).
        """
        matters: list[str] = []
        if not self.case_dir.is_dir():
            return matters

        for item in sorted(self.case_dir.iterdir()):
            if not item.is_dir():
                continue
            if (item / "matter.json").is_file() or (item / "matter.yaml").is_file():
                matters.append(item.name)

        return matters

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_front_matter(path: Path) -> dict:
        """Parse YAML front-matter from a Markdown template file.

        Front-matter is delimited by ``---`` on the first line and a closing
        ``---``.  Returns an empty dict if no front-matter is found.
        """
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.error("Cannot read template %s: %s", path, exc)
            return {}

        if not text.startswith("---"):
            return {}

        end = text.find("---", 3)
        if end == -1:
            return {}

        front = text[3:end].strip()

        # Try YAML parser first, fall back to simple key-value parsing
        try:
            import yaml  # type: ignore[import-untyped]

            data = yaml.safe_load(front)
            return data if isinstance(data, dict) else {}
        except ImportError:
            pass
        except Exception as exc:
            logger.warning("YAML parse error in %s: %s", path, exc)

        # Simple fallback parser for key: value lines
        result: dict[str, Any] = {}
        for line in front.splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                if value.startswith("[") and value.endswith("]"):
                    value = [v.strip().strip("\"'") for v in value[1:-1].split(",")]
                result[key] = value
        return result

    @staticmethod
    def _extract_body(path: Path) -> str:
        """Extract the body content (everything after front-matter) from a template."""
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return ""

        if not text.startswith("---"):
            return text

        end = text.find("---", 3)
        if end == -1:
            return text

        return text[end + 3 :].strip()


# ---------------------------------------------------------------------------
# DraftGuardian — 7-gate quality filter
# ---------------------------------------------------------------------------


class DraftGuardian:
    """7-gate quality filter for outbound communications.

    Each gate performs a specific check on draft text before it is sent.
    All gates must pass for the draft to be considered safe to send.

    Gates:
        1. **Classify** — Determine communication type
        2. **Evidence Check** — Flag unverified claims
        3. **Standards Verification** — Ensure statute/rule citations
        4. **Discipline Check** — Detect emotional language
        5. **Separation Check** — Prevent cross-matter references
        6. **Guardrails** — Catch fabricated content and placeholders
        7. **Trigger Check** — Flag threshold keywords requiring review
    """

    def __init__(
        self,
        case_dir: Union[str, Path],
        config: Optional[dict] = None,
    ) -> None:
        self.case_dir = Path(case_dir)
        self._config = config or {}

        # Load word lists from config or use defaults
        self._emotional_words = self._config.get("emotional_words", _DEFAULT_EMOTIONAL_WORDS)
        self._trigger_keywords = self._config.get("trigger_keywords", _DEFAULT_TRIGGER_KEYWORDS)
        self._placeholder_patterns = [
            re.compile(p, re.IGNORECASE) for p in self._config.get("placeholder_patterns", _PLACEHOLDER_PATTERNS)
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_gates(self, draft_text: str, recipient_type: str) -> dict:
        """Run all 7 gates on a draft communication.

        Parameters
        ----------
        draft_text : str
            The full text of the draft communication.
        recipient_type : str
            One of: ``internal``, ``external-adversary``, ``external-ally``,
            ``submission`` (court filing).

        Returns
        -------
        dict
            {
                "passed": bool,
                "gates": [{name, passed, notes}, ...],
                "warnings": [str],
                "blocked_phrases": [str],
                "classification": str,
                "checked_at": str (ISO timestamp),
            }
        """
        gates: list[dict] = []
        warnings: list[str] = []
        blocked_phrases: list[str] = []

        # Gate 1: Classify
        g1 = self._gate_classify(draft_text, recipient_type)
        gates.append(g1)

        # Gate 2: Evidence Check
        g2 = self._gate_evidence_check(draft_text)
        gates.append(g2)

        # Gate 3: Standards Verification
        g3 = self._gate_standards_verification(draft_text, recipient_type)
        gates.append(g3)

        # Gate 4: Discipline Check (emotional language)
        g4 = self._gate_discipline_check(draft_text)
        gates.append(g4)
        if not g4["passed"]:
            blocked_phrases.extend(g4.get("found_words", []))

        # Gate 5: Separation Check (cross-matter references)
        g5 = self._gate_separation_check(draft_text)
        gates.append(g5)

        # Gate 6: Guardrails (fabricated content, placeholders)
        g6 = self._gate_guardrails(draft_text)
        gates.append(g6)
        if not g6["passed"]:
            blocked_phrases.extend(g6.get("found_placeholders", []))

        # Gate 7: Trigger Check (threshold keywords)
        g7 = self._gate_trigger_check(draft_text)
        gates.append(g7)
        if not g7["passed"]:
            warnings.extend(f"Trigger keyword found: '{kw}'" for kw in g7.get("found_triggers", []))

        all_passed = all(g["passed"] for g in gates)

        return {
            "passed": all_passed,
            "gates": gates,
            "warnings": warnings,
            "blocked_phrases": blocked_phrases,
            "classification": recipient_type,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_emotional_words(self) -> list[str]:
        """Words that fail the glacier/discipline check."""
        return list(self._emotional_words)

    # ------------------------------------------------------------------
    # Individual gates
    # ------------------------------------------------------------------

    def _gate_classify(self, text: str, recipient_type: str) -> dict:
        """Gate 1: Classify the communication type."""
        valid_types = {"internal", "external-adversary", "external-ally", "submission"}
        passed = recipient_type in valid_types
        notes = (
            f"Classified as: {recipient_type}"
            if passed
            else f"Unknown recipient type: {recipient_type}. Must be one of: {', '.join(sorted(valid_types))}"
        )
        return {"name": "Classify", "passed": passed, "notes": notes}

    def _gate_evidence_check(self, text: str) -> dict:
        """Gate 2: Check for references to unverified claims.

        Flags phrases like 'I believe', 'it seems', 'probably',
        'I think', 'it appears' which suggest unsubstantiated assertions.
        """
        unverified_patterns = [
            r"\bI believe\b",
            r"\bit seems\b",
            r"\bprobably\b",
            r"\bI think\b",
            r"\bit appears\b",
            r"\blikely\b",
            r"\bpresumably\b",
            r"\bapparently\b",
            r"\bI assume\b",
            r"\bmight be\b",
            r"\bcould be\b",
        ]
        found: list[str] = []
        text_lower = text.lower()
        for pattern in unverified_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found.extend(matches)

        passed = len(found) == 0
        notes = (
            "No unverified claim indicators found"
            if passed
            else f"Found {len(found)} unverified claim indicator(s): {', '.join(found[:5])}"
        )
        return {"name": "Evidence Check", "passed": passed, "notes": notes}

    def _gate_standards_verification(self, text: str, recipient_type: str) -> dict:
        """Gate 3: Verify statute/rule citations are present for submissions.

        Only enforced for 'submission' and 'external-adversary' types.
        """
        if recipient_type not in ("submission", "external-adversary"):
            return {
                "name": "Standards Verification",
                "passed": True,
                "notes": f"Not required for {recipient_type} communications",
            }

        # Look for common legal citation patterns
        citation_patterns = [
            r"\bF\.S\.\s*\d+",  # Florida Statute
            r"\bFla\.\s*Stat\.",  # Florida Statute alt
            r"\b\d+\s*U\.S\.C\.",  # US Code
            r"\bFed\.\s*R\.\s*Civ\.\s*P\.",  # Federal Rules
            r"\bFla\.\s*R\.\s*Civ\.\s*P\.",  # Florida Rules
            r"\bFla\.\s*Fam\.\s*L\.\s*R\.",  # Florida Family Law Rules
            r"\b\d+\s*F\.\s*\d+d\s+\d+",  # Federal Reporter
            r"\b\d+\s*So\.\s*\d+d\s+\d+",  # Southern Reporter
            r"\bSection\s+\d+",  # Generic section reference
            r"\bRule\s+\d+",  # Generic rule reference
        ]

        found_citations = False
        for pattern in citation_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                found_citations = True
                break

        return {
            "name": "Standards Verification",
            "passed": found_citations,
            "notes": (
                "Legal citations found"
                if found_citations
                else "No statute or rule citations detected. Submissions should cite applicable law."
            ),
        }

    def _gate_discipline_check(self, text: str) -> dict:
        """Gate 4: Detect emotional language (glacier discipline).

        Scans for words from the emotional words list. All communications
        should maintain professional, measured tone.
        """
        text_lower = text.lower()
        found_words: list[str] = []

        for word in self._emotional_words:
            # Match whole words only
            pattern = r"\b" + re.escape(word) + r"\b"
            if re.search(pattern, text_lower):
                found_words.append(word)

        passed = len(found_words) == 0
        notes = (
            "Tone is measured and professional"
            if passed
            else f"Emotional language detected ({len(found_words)} word(s)): {', '.join(found_words[:5])}"
        )
        return {
            "name": "Discipline Check",
            "passed": passed,
            "notes": notes,
            "found_words": found_words,
        }

    def _gate_separation_check(self, text: str) -> dict:
        """Gate 5: Check for cross-matter references.

        Each communication should relate to a single matter. References to
        other matters risk confusion or waiver.
        """
        matters = self._load_matter_names()
        if len(matters) < 2:
            return {
                "name": "Separation Check",
                "passed": True,
                "notes": "Fewer than 2 matters; separation check not applicable",
            }

        text_lower = text.lower()
        referenced_matters: list[str] = []
        for matter in matters:
            if matter.lower() in text_lower:
                referenced_matters.append(matter)

        passed = len(referenced_matters) <= 1
        notes = (
            "Single-matter communication"
            if passed
            else f"Cross-matter references detected: {', '.join(referenced_matters)}"
        )
        return {
            "name": "Separation Check",
            "passed": passed,
            "notes": notes,
        }

    def _gate_guardrails(self, text: str) -> dict:
        """Gate 6: Check for fabricated content and placeholders."""
        found_placeholders: list[str] = []

        for pattern in self._placeholder_patterns:
            matches = pattern.findall(text)
            found_placeholders.extend(matches)

        passed = len(found_placeholders) == 0
        notes = (
            "No placeholders or fabricated content markers found"
            if passed
            else f"Found {len(found_placeholders)} placeholder(s): {', '.join(found_placeholders[:5])}"
        )
        return {
            "name": "Guardrails",
            "passed": passed,
            "notes": notes,
            "found_placeholders": found_placeholders,
        }

    def _gate_trigger_check(self, text: str) -> dict:
        """Gate 7: Check for threshold keywords requiring extra review.

        These keywords are not necessarily blocked, but require explicit
        acknowledgment before sending.
        """
        text_lower = text.lower()
        found_triggers: list[str] = []

        for keyword in self._trigger_keywords:
            if keyword.lower() in text_lower:
                found_triggers.append(keyword)

        passed = len(found_triggers) == 0
        notes = (
            "No trigger keywords found" if passed else f"Trigger keywords requiring review: {', '.join(found_triggers)}"
        )
        return {
            "name": "Trigger Check",
            "passed": passed,
            "notes": notes,
            "found_triggers": found_triggers,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_matter_names(self) -> list[str]:
        """Load matter names from the case directory."""
        matters: list[str] = []
        if not self.case_dir.is_dir():
            return matters

        for item in sorted(self.case_dir.iterdir()):
            if not item.is_dir():
                continue
            if (item / "matter.json").is_file() or (item / "matter.yaml").is_file():
                matters.append(item.name)

        return matters
