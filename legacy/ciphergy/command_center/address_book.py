"""
Address book for the Ciphergy Command Center.

Manages known addresses for service of process and certified mail
communications. Stores contacts in a JSON file with full address
information and service history tracking.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


class AddressBook:
    """Manages known addresses for service and communications.

    Contact records are stored as::

        {
            "name": "Full Name",
            "company": "Optional Company",
            "role": "opposing_counsel | court_clerk | party | ...",
            "address_line1": "123 Main St",
            "address_line2": "Suite 100",
            "city": "Tampa",
            "state": "FL",
            "zip": "33601",
            "email": "optional@email.com",
            "phone": "optional phone",
            "matter": "associated matter name",
            "notes": "free text",
            "added_at": "ISO timestamp",
            "service_history": [
                {
                    "date": "ISO date",
                    "method": "certified_mail | hand_delivery | email | efiling",
                    "tracking_number": "if applicable",
                    "document": "document name or path",
                    "status": "delivered | pending | returned",
                }
            ]
        }
    """

    def __init__(self, book_file: Union[str, Path]) -> None:
        self.book_file = Path(book_file)
        self._ensure_file()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_all(self) -> list[dict]:
        """Return all contacts with addresses."""
        return self._load()

    def get(self, name: str) -> Optional[dict]:
        """Get a single contact by name (case-insensitive partial match).

        Returns the first matching contact, or None if not found.
        """
        contacts = self._load()
        name_lower = name.lower()

        # Exact match first
        for contact in contacts:
            if contact.get("name", "").lower() == name_lower:
                return contact

        # Partial match fallback
        for contact in contacts:
            if name_lower in contact.get("name", "").lower():
                return contact

        return None

    def add(self, contact: dict) -> None:
        """Add a contact to the address book.

        Parameters
        ----------
        contact : dict
            Must contain at least ``name`` and ``address_line1``.
            See class docstring for full schema.

        Raises
        ------
        ValueError
            If required fields are missing.
        """
        if not contact.get("name"):
            raise ValueError("Contact must have a 'name' field")
        if not contact.get("address_line1"):
            raise ValueError("Contact must have an 'address_line1' field")

        contacts = self._load()

        # Check for duplicate by name
        name_lower = contact["name"].lower()
        for existing in contacts:
            if existing.get("name", "").lower() == name_lower:
                logger.warning(
                    "Contact '%s' already exists. Use update() to modify.",
                    contact["name"],
                )
                raise ValueError(f"Contact '{contact['name']}' already exists")

        contact.setdefault("added_at", datetime.now(timezone.utc).isoformat())
        contact.setdefault("service_history", [])

        contacts.append(contact)
        self._save(contacts)
        logger.info("Added contact: %s", contact["name"])

    def update(self, name: str, updates: dict) -> None:
        """Update an existing contact's information.

        Parameters
        ----------
        name : str
            The contact name to update.
        updates : dict
            Fields to update. Will not overwrite ``service_history`` unless
            explicitly provided.

        Raises
        ------
        KeyError
            If the contact is not found.
        """
        contacts = self._load()
        name_lower = name.lower()
        found = False

        for contact in contacts:
            if contact.get("name", "").lower() == name_lower:
                for key, value in updates.items():
                    contact[key] = value
                contact["updated_at"] = datetime.now(timezone.utc).isoformat()
                found = True
                break

        if not found:
            raise KeyError(f"Contact not found: {name}")

        self._save(contacts)
        logger.info("Updated contact: %s", name)

    def remove(self, name: str) -> None:
        """Remove a contact from the address book.

        Parameters
        ----------
        name : str
            The contact name to remove.

        Raises
        ------
        KeyError
            If the contact is not found.
        """
        contacts = self._load()
        name_lower = name.lower()
        original_len = len(contacts)

        contacts = [c for c in contacts if c.get("name", "").lower() != name_lower]

        if len(contacts) == original_len:
            raise KeyError(f"Contact not found: {name}")

        self._save(contacts)
        logger.info("Removed contact: %s", name)

    def get_service_history(self, name: str) -> list[dict]:
        """Get mail/service history for a contact.

        Parameters
        ----------
        name : str
            Contact name to look up.

        Returns
        -------
        list[dict]
            Service history entries, newest first.
        """
        contact = self.get(name)
        if contact is None:
            return []

        history = contact.get("service_history", [])
        return sorted(history, key=lambda x: x.get("date", ""), reverse=True)

    def add_service_record(self, name: str, record: dict) -> None:
        """Add a service record to a contact's history.

        Parameters
        ----------
        name : str
            Contact name.
        record : dict
            Service record with ``date``, ``method``, ``document``, ``status``.
        """
        contacts = self._load()
        name_lower = name.lower()
        found = False

        for contact in contacts:
            if contact.get("name", "").lower() == name_lower:
                record.setdefault("date", datetime.now(timezone.utc).isoformat())
                contact.setdefault("service_history", []).append(record)
                found = True
                break

        if not found:
            logger.warning("Cannot add service record: contact '%s' not found", name)
            return

        self._save(contacts)
        logger.info("Added service record for %s: %s", name, record.get("method", "unknown"))

    def search(self, query: str) -> list[dict]:
        """Search contacts by name, company, role, or matter.

        Parameters
        ----------
        query : str
            Search term (case-insensitive).

        Returns
        -------
        list[dict]
            Matching contacts.
        """
        contacts = self._load()
        query_lower = query.lower()
        results = []

        for contact in contacts:
            searchable = " ".join([
                contact.get("name", ""),
                contact.get("company", ""),
                contact.get("role", ""),
                contact.get("matter", ""),
                contact.get("notes", ""),
            ]).lower()
            if query_lower in searchable:
                results.append(contact)

        return results

    def get_by_matter(self, matter: str) -> list[dict]:
        """Get all contacts associated with a specific matter.

        Parameters
        ----------
        matter : str
            Matter name (case-insensitive).

        Returns
        -------
        list[dict]
            Contacts linked to the matter.
        """
        contacts = self._load()
        matter_lower = matter.lower()
        return [
            c for c in contacts
            if matter_lower in c.get("matter", "").lower()
        ]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _ensure_file(self) -> None:
        """Create the address book file if it does not exist."""
        if not self.book_file.exists():
            self.book_file.parent.mkdir(parents=True, exist_ok=True)
            self._save([])

    def _load(self) -> list[dict]:
        """Load contacts from the JSON file."""
        try:
            text = self.book_file.read_text(encoding="utf-8")
            data = json.loads(text)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Error loading address book: %s", exc)
            return []

    def _save(self, contacts: list[dict]) -> None:
        """Save contacts to the JSON file."""
        try:
            self.book_file.parent.mkdir(parents=True, exist_ok=True)
            self.book_file.write_text(
                json.dumps(contacts, indent=2, default=str),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.error("Error saving address book: %s", exc)
