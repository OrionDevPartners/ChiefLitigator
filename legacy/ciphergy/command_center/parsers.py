"""Markdown parsing utilities for case repo files."""

import re
from typing import Optional


def parse_md_table(text: str) -> list[dict]:
    """Parse a markdown table into a list of dicts.

    Handles standard GFM tables:
        | Header1 | Header2 |
        |---------|---------|
        | val1    | val2    |

    Returns a list of dicts keyed by the cleaned header names.
    Skips the separator row (dashes/colons).
    """
    lines = text.strip().splitlines()
    table_lines: list[str] = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            table_lines.append(stripped)
            in_table = True
        elif in_table:
            # Table ended
            break

    if len(table_lines) < 2:
        return []

    def split_row(row: str) -> list[str]:
        # Remove leading/trailing pipe, split on pipe, strip each cell
        cells = row.strip("|").split("|")
        return [c.strip() for c in cells]

    headers = split_row(table_lines[0])

    rows: list[dict] = []
    for line in table_lines[1:]:
        # Skip separator rows (all dashes, colons, spaces)
        if re.match(r"^[\s|:\-]+$", line):
            continue
        cells = split_row(line)
        row: dict = {}
        for i, header in enumerate(headers):
            key = _clean_header(header)
            row[key] = cells[i] if i < len(cells) else ""
        rows.append(row)

    return rows


def parse_all_md_tables(text: str) -> list[list[dict]]:
    """Parse ALL markdown tables from a text block.

    Returns a list of tables, where each table is a list of row dicts.
    """
    lines = text.splitlines()
    tables: list[list[dict]] = []
    current_table_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            current_table_lines.append(stripped)
        else:
            if current_table_lines:
                table = _parse_table_lines(current_table_lines)
                if table:
                    tables.append(table)
                current_table_lines = []

    # Handle table at end of text
    if current_table_lines:
        table = _parse_table_lines(current_table_lines)
        if table:
            tables.append(table)

    return tables


def _parse_table_lines(table_lines: list[str]) -> list[dict]:
    """Parse a collected set of table lines into row dicts."""
    if len(table_lines) < 2:
        return []

    def split_row(row: str) -> list[str]:
        cells = row.strip("|").split("|")
        return [c.strip() for c in cells]

    headers = split_row(table_lines[0])

    rows: list[dict] = []
    for line in table_lines[1:]:
        if re.match(r"^[\s|:\-]+$", line):
            continue
        cells = split_row(line)
        row: dict = {}
        for i, header in enumerate(headers):
            key = _clean_header(header)
            row[key] = cells[i] if i < len(cells) else ""
        rows.append(row)
    return rows


def _clean_header(header: str) -> str:
    """Clean a markdown table header into a dict key.

    Strips bold markers, leading #, extra whitespace.
    Lowercases and replaces spaces/special chars with underscores.
    """
    h = header.strip()
    # Remove bold/italic markers
    h = re.sub(r"\*+", "", h)
    # Remove leading #
    h = h.lstrip("#").strip()
    # Lowercase
    h = h.lower()
    # Replace non-alphanumeric with underscore
    h = re.sub(r"[^a-z0-9]+", "_", h)
    # Strip leading/trailing underscores
    h = h.strip("_")
    return h or "col"


def parse_md_sections(text: str, max_level: int = 6) -> dict:
    """Parse markdown into sections by heading level.

    Returns a nested dict:
        {
            "_content": "text before first heading",
            "Section Name": {
                "_content": "text under this heading",
                "_level": 2,
                "Subsection": { ... }
            }
        }

    Only headings up to max_level are parsed.
    """
    lines = text.splitlines()
    root: dict = {"_content": "", "_level": 0}
    stack: list[dict] = [root]

    current_content_lines: list[str] = []

    def flush_content() -> None:
        content = "\n".join(current_content_lines).strip()
        if stack:
            stack[-1]["_content"] = content
        current_content_lines.clear()

    heading_re = re.compile(r"^(#{1,6})\s+(.+)$")

    for line in lines:
        m = heading_re.match(line)
        if m:
            level = len(m.group(1))
            if level > max_level:
                current_content_lines.append(line)
                continue

            flush_content()

            title = m.group(2).strip()
            # Remove trailing # if present
            title = re.sub(r"\s+#+\s*$", "", title)

            section: dict = {"_content": "", "_level": level}

            # Pop stack until we find a parent with lower level
            while len(stack) > 1 and stack[-1]["_level"] >= level:
                stack.pop()

            parent = stack[-1]
            parent[title] = section
            stack.append(section)
            current_content_lines = []
        else:
            current_content_lines.append(line)

    flush_content()
    return root


def extract_scores(text: str) -> list[tuple[str, int]]:
    """Extract name + percentage score pairs from text.

    Looks for patterns like:
        - "Something: 85%"
        - "| Something | 85% |"
        - "**85%**"
        - "Overall Confidence: 85%"
        - "Confidence: 85%"

    Returns list of (label, score) tuples.
    """
    results: list[tuple[str, int]] = []

    # Pattern 1: table rows with a percentage column
    # | label | ... | NN% | ...
    table_row_re = re.compile(
        r"\|\s*\*{0,2}([^|*]+?)\*{0,2}\s*\|"  # first cell (label)
        r"(?:[^|]*\|)*?"                         # skip intermediate cells
        r"\s*\*{0,2}(\d{1,3})%\*{0,2}\s*\|"     # cell with NN%
    )
    for m in table_row_re.finditer(text):
        label = m.group(1).strip()
        score = int(m.group(2))
        if label and 0 <= score <= 100:
            results.append((label, score))

    if results:
        return results

    # Pattern 2: "Label: NN%" or "Label — NN%" or "**Label** NN%"
    inline_re = re.compile(
        r"(?:\*{0,2})([A-Za-z][^:\n]{2,60})(?:\*{0,2})"
        r"[\s:—\-]+(\d{1,3})%"
    )
    for m in inline_re.finditer(text):
        label = m.group(1).strip().strip("*")
        score = int(m.group(2))
        if 0 <= score <= 100:
            results.append((label, score))

    return results


def extract_percentage(text: str) -> Optional[int]:
    """Extract the first percentage value from text. Returns None if not found."""
    m = re.search(r"(\d{1,3})%", text)
    if m:
        val = int(m.group(1))
        if 0 <= val <= 100:
            return val
    return None


def parse_timeline(text: str) -> list[dict]:
    """Parse a chronological timeline table from a Person Analysis report.

    Expects the Section 0 table format:
        | # | Date | Time | Event | Source | Evidentiary Value |

    Returns list of dicts with those keys.
    """
    return parse_md_table(text)


def parse_contradictions(text: str) -> list[dict]:
    """Parse contradictions log from a Person Analysis report.

    Expects the Section 4A table format:
        | # | Statement/Action A | Statement/Action B | Contradiction |

    Returns list of dicts with those keys.
    """
    return parse_md_table(text)


def parse_action_items(text: str) -> list[dict]:
    """Parse action item tables from markdown.

    Handles tables with columns like:
        | # | Action | Matter | Deadline | Status |

    Also handles checklist items:
        - [ ] Item text
        - [x] Completed item

    Returns list of dicts with action, deadline, status, matter fields.
    """
    items: list[dict] = []

    # Try table parsing first
    tables = parse_all_md_tables(text)
    for table in tables:
        for row in table:
            # Look for action-like tables (have action or gap or question column)
            action_key = None
            for key in row:
                if key in ("action", "gap", "question", "evidence_item"):
                    action_key = key
                    break
            if action_key:
                items.append(row)

    # Also parse checklist items
    checklist_re = re.compile(r"^[-*]\s+\[([ xX])\]\s+(.+)$", re.MULTILINE)
    for m in checklist_re.finditer(text):
        done = m.group(1).lower() == "x"
        items.append({
            "action": m.group(2).strip(),
            "status": "DONE" if done else "OPEN",
        })

    return items


def parse_alert_blocks(text: str) -> list[dict]:
    """Parse RED ALERT code blocks from _RED_ALERTS.md.

    Extracts structured data from blocks like:
        ```
        === RED ALERT -- EVIDENCE THRESHOLD: AIRTIGHT ===
        CLAIM: COUNT IV -- Elder Exploitation
        CONFIDENCE: 98% (LETHAL)
        STATUS: LOCKED
        ...
        ```

    Returns list of alert dicts.
    """
    alerts: list[dict] = []
    # Find code blocks containing RED ALERT
    block_re = re.compile(r"```\s*\n(.*?)```", re.DOTALL)

    for block_match in block_re.finditer(text):
        block = block_match.group(1)
        if "RED ALERT" not in block and "ALERT" not in block:
            continue

        alert: dict = {"raw": block.strip()}

        # Parse key-value pairs from the block
        kv_re = re.compile(r"^([A-Z][A-Z _]+):\s*(.+)$", re.MULTILINE)
        for kv in kv_re.finditer(block):
            key = kv.group(1).strip().lower().replace(" ", "_")
            val = kv.group(2).strip()
            alert[key] = val

        # Extract rating from header line
        header_re = re.compile(r"===.*?THRESHOLD:\s*(\w+)\s*===")
        hm = header_re.search(block)
        if hm:
            alert["threshold"] = hm.group(1)

        # Extract confidence percentage
        if "confidence" in alert:
            pct = extract_percentage(alert["confidence"])
            if pct is not None:
                alert["confidence_pct"] = pct

        alerts.append(alert)

    return alerts


def parse_questions(text: str) -> list[dict]:
    """Parse questions from _QUESTIONS_FOR_BO.md.

    Looks for tables with columns: #, Question, Context, Deadline, Status.
    Returns list of question dicts.
    """
    tables = parse_all_md_tables(text)
    questions: list[dict] = []
    for table in tables:
        for row in table:
            if "question" in row:
                questions.append(row)
    return questions


def parse_diff_entries(text: str) -> list[dict]:
    """Parse diff entries from a DIFF/ session file.

    Each diff entry starts with '## Diff' and contains key-value pairs
    with bold labels: **File:**, **Action:**, etc.

    Returns list of diff dicts.
    """
    entries: list[dict] = []

    # Split on ## Diff headings
    sections = re.split(r"^##\s+Diff\b[^\n]*", text, flags=re.MULTILINE)

    for section in sections[1:]:  # Skip text before first ## Diff
        entry: dict = {}

        # Parse bold key-value pairs: - **Key:** Value
        kv_re = re.compile(r"\*\*([^*]+?):\*\*\s*(.+)")
        for m in kv_re.finditer(section):
            key = m.group(1).strip().lower().replace(" ", "_")
            val = m.group(2).strip()
            # Strip backticks from file paths
            val = val.strip("`")
            entry[key] = val

        if entry:
            entries.append(entry)

    return entries


def strip_md_formatting(text: str) -> str:
    """Strip common markdown formatting from text.

    Removes: bold (**), italic (*), inline code (`), links [text](url) -> text.
    """
    # Links: [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Bold/italic
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    # Inline code
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text
