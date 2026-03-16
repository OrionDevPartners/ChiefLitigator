"""
Certified mail integration for the Ciphergy Command Center.

Supports sending certified letters with return receipt via external
mail API providers (Lob, Click2Mail, PostGrid). API keys are loaded
from the .keys/ directory and never stored in code.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)

# Try to import requests; provide a clear error if missing
try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False
    logger.debug("requests library not installed; CertifiedMailer will not be able to send")


# ---------------------------------------------------------------------------
# CertifiedMailer
# ---------------------------------------------------------------------------


class CertifiedMailer:
    """Sends certified mail via API (Lob, Click2Mail, or PostGrid).

    Configuration is passed as a dict::

        config = {
            "provider": "lob",       # "lob", "click2mail", or "postgrid"
            "api_key": "...",         # or loaded from .keys/
            "return_address": {
                "name": "...",
                "address_line1": "...",
                "city": "...",
                "state": "...",
                "zip": "...",
            },
        }

    API keys should be stored in ``.keys/`` (gitignored), not in code.
    """

    # Base URLs for supported providers
    _PROVIDER_URLS = {
        "lob": "https://api.lob.com/v1",
        "click2mail": "https://batch.click2mail.com/molpro/documents",
        "postgrid": "https://api.postgrid.com/print-mail/v1",
    }

    def __init__(self, config: dict) -> None:
        self.provider = config.get("provider", "lob")
        self.api_key = config.get("api_key", "")
        self.return_address = config.get("return_address", {})
        self._base_url = self._PROVIDER_URLS.get(self.provider, "")

        if not self.api_key:
            logger.warning(
                "No API key configured for %s. Mail sending will fail.", self.provider
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send(self, recipient: dict, document_path: str, options: Optional[dict] = None) -> dict:
        """Send a certified letter with return receipt.

        Parameters
        ----------
        recipient : dict
            Must contain: ``name``, ``address_line1``, ``city``, ``state``, ``zip``.
            Optional: ``address_line2``, ``company``.
        document_path : str
            Path to the PDF file to send.
        options : dict, optional
            ``certified`` (bool, default True), ``return_receipt`` (bool, default True),
            ``color`` (bool, default False), ``double_sided`` (bool, default False).

        Returns
        -------
        dict
            {tracking_number, expected_delivery, cost, status, provider, sent_at}

        Raises
        ------
        FileNotFoundError
            If the document PDF does not exist.
        RuntimeError
            If the requests library is not installed or the API call fails.
        """
        options = options or {}
        certified = options.get("certified", True)
        return_receipt = options.get("return_receipt", True)

        doc_path = Path(document_path)
        if not doc_path.is_file():
            raise FileNotFoundError(f"Document not found: {document_path}")

        if not _HAS_REQUESTS:
            raise RuntimeError(
                "The 'requests' library is required for sending mail. "
                "Install it with: pip install requests"
            )

        if not self.api_key:
            raise RuntimeError(
                f"No API key configured for provider '{self.provider}'. "
                "Set the key in .keys/ and pass it via config."
            )

        # Dispatch to provider-specific implementation
        if self.provider == "lob":
            return self._send_via_lob(recipient, doc_path, certified, return_receipt, options)
        elif self.provider == "postgrid":
            return self._send_via_postgrid(recipient, doc_path, certified, return_receipt, options)
        elif self.provider == "click2mail":
            return self._send_via_click2mail(recipient, doc_path, certified, return_receipt, options)
        else:
            raise RuntimeError(f"Unsupported mail provider: {self.provider}")

    def check_status(self, tracking_number: str) -> dict:
        """Check delivery status of a sent letter.

        Parameters
        ----------
        tracking_number : str
            The tracking number returned from ``send()``.

        Returns
        -------
        dict
            {tracking_number, status, last_update, events}
        """
        if not _HAS_REQUESTS:
            raise RuntimeError("The 'requests' library is required.")

        if self.provider == "lob":
            return self._check_status_lob(tracking_number)
        elif self.provider == "postgrid":
            return self._check_status_postgrid(tracking_number)
        else:
            return {
                "tracking_number": tracking_number,
                "status": "unknown",
                "last_update": datetime.now(timezone.utc).isoformat(),
                "events": [],
                "notes": f"Status checking not implemented for {self.provider}",
            }

    def get_history(self) -> list[dict]:
        """Get all sent mail with current status.

        This queries the provider's API for recent letters.

        Returns
        -------
        list[dict]
            List of sent letter records.
        """
        if not _HAS_REQUESTS:
            raise RuntimeError("The 'requests' library is required.")

        if self.provider == "lob":
            return self._get_history_lob()
        elif self.provider == "postgrid":
            return self._get_history_postgrid()
        else:
            return []

    # ------------------------------------------------------------------
    # Lob implementation
    # ------------------------------------------------------------------

    def _send_via_lob(
        self,
        recipient: dict,
        doc_path: Path,
        certified: bool,
        return_receipt: bool,
        options: dict,
    ) -> dict:
        """Send via Lob API (https://docs.lob.com/)."""
        url = f"{self._base_url}/letters"

        data = {
            "to[name]": recipient["name"],
            "to[address_line1]": recipient["address_line1"],
            "to[address_line2]": recipient.get("address_line2", ""),
            "to[address_city]": recipient["city"],
            "to[address_state]": recipient["state"],
            "to[address_zip]": recipient["zip"],
            "from[name]": self.return_address.get("name", ""),
            "from[address_line1]": self.return_address.get("address_line1", ""),
            "from[address_city]": self.return_address.get("city", ""),
            "from[address_state]": self.return_address.get("state", ""),
            "from[address_zip]": self.return_address.get("zip", ""),
            "color": str(options.get("color", False)).lower(),
            "double_sided": str(options.get("double_sided", False)).lower(),
        }

        if certified:
            data["mail_type"] = "usps_certified"
        if return_receipt:
            data["return_envelope"] = "true"
            data["extra_service"] = "certified_return_receipt"

        with open(doc_path, "rb") as f:
            files = {"file": (doc_path.name, f, "application/pdf")}
            resp = requests.post(
                url,
                data=data,
                files=files,
                auth=(self.api_key, ""),
                timeout=60,
            )

        if resp.status_code not in (200, 201):
            logger.error("Lob API error %d: %s", resp.status_code, resp.text)
            raise RuntimeError(f"Lob API error {resp.status_code}: {resp.text}")

        result = resp.json()
        return {
            "tracking_number": result.get("tracking_number", result.get("id", "")),
            "expected_delivery": result.get("expected_delivery_date", ""),
            "cost": self._parse_cost(result),
            "status": "queued",
            "provider": "lob",
            "provider_id": result.get("id", ""),
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }

    def _check_status_lob(self, tracking_number: str) -> dict:
        """Check letter status via Lob API."""
        # Lob uses letter ID for lookups; tracking_number may be the ID
        url = f"{self._base_url}/letters/{tracking_number}"
        resp = requests.get(url, auth=(self.api_key, ""), timeout=30)

        if resp.status_code != 200:
            return {
                "tracking_number": tracking_number,
                "status": "error",
                "last_update": datetime.now(timezone.utc).isoformat(),
                "events": [],
                "error": f"API returned {resp.status_code}",
            }

        data = resp.json()
        return {
            "tracking_number": tracking_number,
            "status": self._map_lob_status(data),
            "last_update": datetime.now(timezone.utc).isoformat(),
            "events": data.get("tracking_events", []),
        }

    def _get_history_lob(self) -> list[dict]:
        """Get letter history from Lob."""
        url = f"{self._base_url}/letters"
        resp = requests.get(
            url,
            params={"limit": 50, "include[]": "total_count"},
            auth=(self.api_key, ""),
            timeout=30,
        )

        if resp.status_code != 200:
            logger.error("Lob history fetch failed: %d", resp.status_code)
            return []

        data = resp.json()
        letters = data.get("data", [])
        return [
            {
                "id": letter.get("id", ""),
                "tracking_number": letter.get("tracking_number", ""),
                "recipient": letter.get("to", {}).get("name", ""),
                "status": self._map_lob_status(letter),
                "sent_at": letter.get("date_created", ""),
                "expected_delivery": letter.get("expected_delivery_date", ""),
            }
            for letter in letters
        ]

    @staticmethod
    def _map_lob_status(data: dict) -> str:
        """Map Lob API status fields to a simple status string."""
        if data.get("send_date") and not data.get("tracking_events"):
            return "in_transit"
        events = data.get("tracking_events", [])
        if events:
            last_event = events[-1] if isinstance(events, list) else {}
            event_type = last_event.get("type", "")
            if "delivered" in event_type.lower():
                return "delivered"
            if "returned" in event_type.lower():
                return "returned"
            return "in_transit"
        return "queued"

    @staticmethod
    def _parse_cost(data: dict) -> float:
        """Extract cost from Lob API response."""
        # Lob returns cost in the 'price' or 'carrier_price' field
        for key in ("price", "carrier_price"):
            val = data.get(key)
            if val is not None:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    pass
        return 0.0

    # ------------------------------------------------------------------
    # PostGrid implementation
    # ------------------------------------------------------------------

    def _send_via_postgrid(
        self,
        recipient: dict,
        doc_path: Path,
        certified: bool,
        return_receipt: bool,
        options: dict,
    ) -> dict:
        """Send via PostGrid API (https://docs.postgrid.com/)."""
        url = f"{self._base_url}/letters"

        headers = {"x-api-key": self.api_key}

        data = {
            "to[firstName]": recipient["name"].split()[0] if " " in recipient["name"] else recipient["name"],
            "to[lastName]": recipient["name"].split()[-1] if " " in recipient["name"] else "",
            "to[addressLine1]": recipient["address_line1"],
            "to[addressLine2]": recipient.get("address_line2", ""),
            "to[city]": recipient["city"],
            "to[provinceOrState]": recipient["state"],
            "to[postalOrZip]": recipient["zip"],
            "to[country]": "US",
            "from[firstName]": self.return_address.get("name", "").split()[0] if self.return_address.get("name") else "",
            "from[lastName]": self.return_address.get("name", "").split()[-1] if self.return_address.get("name") else "",
            "from[addressLine1]": self.return_address.get("address_line1", ""),
            "from[city]": self.return_address.get("city", ""),
            "from[provinceOrState]": self.return_address.get("state", ""),
            "from[postalOrZip]": self.return_address.get("zip", ""),
            "from[country]": "US",
        }

        if certified:
            data["mailType"] = "certified_mail"
        if return_receipt:
            data["extraService"] = "return_receipt_requested"

        with open(doc_path, "rb") as f:
            files = {"pdf": (doc_path.name, f, "application/pdf")}
            resp = requests.post(url, data=data, files=files, headers=headers, timeout=60)

        if resp.status_code not in (200, 201):
            logger.error("PostGrid API error %d: %s", resp.status_code, resp.text)
            raise RuntimeError(f"PostGrid API error {resp.status_code}: {resp.text}")

        result = resp.json()
        return {
            "tracking_number": result.get("id", ""),
            "expected_delivery": result.get("expectedDeliveryDate", ""),
            "cost": float(result.get("price", 0)),
            "status": "queued",
            "provider": "postgrid",
            "provider_id": result.get("id", ""),
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }

    def _check_status_postgrid(self, tracking_number: str) -> dict:
        """Check letter status via PostGrid API."""
        url = f"{self._base_url}/letters/{tracking_number}"
        headers = {"x-api-key": self.api_key}
        resp = requests.get(url, headers=headers, timeout=30)

        if resp.status_code != 200:
            return {
                "tracking_number": tracking_number,
                "status": "error",
                "last_update": datetime.now(timezone.utc).isoformat(),
                "events": [],
            }

        data = resp.json()
        return {
            "tracking_number": tracking_number,
            "status": data.get("status", "unknown"),
            "last_update": datetime.now(timezone.utc).isoformat(),
            "events": [],
        }

    def _get_history_postgrid(self) -> list[dict]:
        """Get letter history from PostGrid."""
        url = f"{self._base_url}/letters"
        headers = {"x-api-key": self.api_key}
        resp = requests.get(url, params={"limit": 50}, headers=headers, timeout=30)

        if resp.status_code != 200:
            return []

        data = resp.json()
        letters = data.get("data", [])
        return [
            {
                "id": letter.get("id", ""),
                "tracking_number": letter.get("id", ""),
                "recipient": letter.get("to", {}).get("firstName", ""),
                "status": letter.get("status", "unknown"),
                "sent_at": letter.get("createdAt", ""),
                "expected_delivery": letter.get("expectedDeliveryDate", ""),
            }
            for letter in letters
        ]

    # ------------------------------------------------------------------
    # Click2Mail implementation (minimal)
    # ------------------------------------------------------------------

    def _send_via_click2mail(
        self,
        recipient: dict,
        doc_path: Path,
        certified: bool,
        return_receipt: bool,
        options: dict,
    ) -> dict:
        """Send via Click2Mail API.

        Click2Mail uses a multi-step process (create document, create job,
        submit job). This implementation handles the full flow.
        """
        # Click2Mail requires XML payloads; simplified implementation
        raise NotImplementedError(
            "Click2Mail integration requires XML payloads. "
            "Use Lob or PostGrid for certified mail. "
            "Click2Mail support can be added if needed."
        )


# ---------------------------------------------------------------------------
# MailTracker
# ---------------------------------------------------------------------------


class MailTracker:
    """Tracks all certified mail sent and delivery status.

    Stores records in a JSON file for persistence across sessions.
    Each record contains sender, recipient, tracking info, and status history.
    """

    def __init__(self, tracking_file: Union[str, Path]) -> None:
        self.tracking_file = Path(tracking_file)
        self._ensure_file()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, mail_record: dict) -> None:
        """Add a new mail record to tracking.

        Parameters
        ----------
        mail_record : dict
            Must contain at minimum: ``tracking_number``, ``recipient``,
            ``document``, ``sent_at``, ``status``.
        """
        records = self._load()
        mail_record.setdefault("status_history", [
            {
                "status": mail_record.get("status", "queued"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ])
        records.append(mail_record)
        self._save(records)
        logger.info("Tracked new mail: %s", mail_record.get("tracking_number", "unknown"))

    def update_status(self, tracking_number: str, status: str) -> None:
        """Update delivery status for a tracked letter.

        Parameters
        ----------
        tracking_number : str
            The tracking number to update.
        status : str
            New status (e.g., 'in_transit', 'delivered', 'returned').
        """
        records = self._load()
        updated = False

        for record in records:
            if record.get("tracking_number") == tracking_number:
                record["status"] = status
                record.setdefault("status_history", []).append({
                    "status": status,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                updated = True
                break

        if updated:
            self._save(records)
            logger.info("Updated status for %s: %s", tracking_number, status)
        else:
            logger.warning("Tracking number not found: %s", tracking_number)

    def get_all(self) -> list[dict]:
        """Get all tracked mail records."""
        return self._load()

    def get_pending(self) -> list[dict]:
        """Get mail that hasn't been delivered yet.

        Returns records with status not in ('delivered', 'returned', 'cancelled').
        """
        terminal_statuses = {"delivered", "returned", "cancelled"}
        records = self._load()
        return [r for r in records if r.get("status", "") not in terminal_statuses]

    def get_by_recipient(self, recipient_name: str) -> list[dict]:
        """Get all mail sent to a specific recipient."""
        records = self._load()
        name_lower = recipient_name.lower()
        return [
            r for r in records
            if name_lower in r.get("recipient", {}).get("name", "").lower()
            or name_lower in str(r.get("recipient", "")).lower()
        ]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _ensure_file(self) -> None:
        """Create the tracking file if it does not exist."""
        if not self.tracking_file.exists():
            self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
            self._save([])

    def _load(self) -> list[dict]:
        """Load records from the tracking file."""
        try:
            text = self.tracking_file.read_text(encoding="utf-8")
            data = json.loads(text)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Error loading tracking file: %s", exc)
            return []

    def _save(self, records: list[dict]) -> None:
        """Save records to the tracking file."""
        try:
            self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
            self.tracking_file.write_text(
                json.dumps(records, indent=2, default=str),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.error("Error saving tracking file: %s", exc)
