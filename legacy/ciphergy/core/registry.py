"""
Version registry manager for Ciphergy Pipeline.

Wraps ``.ciphergy/registry.json`` with thread-safe load/save, version
tracking, file hash verification, and history logging.
"""

import fcntl
import hashlib
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class VersionEntry:
    """A single version record in the registry."""

    version: str
    timestamp: str
    sha256: str = ""
    notes: str = ""


@dataclass
class HistoryEntry:
    """An entry in the change history."""

    version: str
    timestamp: str
    action: str
    details: str = ""


@dataclass
class MonitoredFile:
    """A file tracked for staleness detection."""

    path: str
    sha256: str
    last_checked: str


@dataclass
class RegistryData:
    """Full registry state."""

    project: str = "ciphergy-pipeline"
    current_version: str = "0.0.0"
    versions: Dict[str, VersionEntry] = field(default_factory=dict)
    history: List[HistoryEntry] = field(default_factory=list)
    monitored_files: Dict[str, MonitoredFile] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class Registry:
    """Thread-safe registry manager backed by ``.ciphergy/registry.json``.

    Parameters
    ----------
    base_dir : str or Path, optional
        Project root directory.  Defaults to cwd.
    """

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self._base = Path(base_dir) if base_dir else Path.cwd()
        self._dir = self._base / ".ciphergy"
        self._path = self._dir / "registry.json"
        self._data: Optional[RegistryData] = None
        logger.debug("Registry path: %s", self._path)

    # ------------------------------------------------------------------
    # File locking helpers
    # ------------------------------------------------------------------

    def _ensure_dir(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

    def _lock_path(self) -> Path:
        return self._dir / "registry.lock"

    # ------------------------------------------------------------------
    # Load / Save (thread-safe via file lock)
    # ------------------------------------------------------------------

    def load(self) -> RegistryData:
        """Load registry from disk.  Creates default if missing.

        Returns
        -------
        RegistryData
        """
        self._ensure_dir()
        lock_file = self._lock_path()

        try:
            with open(lock_file, "w") as lf:
                fcntl.flock(lf, fcntl.LOCK_SH)
                try:
                    if self._path.is_file():
                        raw = json.loads(self._path.read_text(encoding="utf-8"))
                        self._data = self._deserialize(raw)
                        logger.debug("Registry loaded: version=%s", self._data.current_version)
                    else:
                        self._data = RegistryData()
                        logger.info("No registry found; initialized default")
                finally:
                    fcntl.flock(lf, fcntl.LOCK_UN)
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Corrupt registry, reinitializing: %s", exc)
            self._data = RegistryData()

        return self._data

    def save(self) -> None:
        """Persist the current registry state to disk (exclusive lock)."""
        if self._data is None:
            raise RuntimeError("Cannot save: registry not loaded. Call load() first.")

        self._ensure_dir()
        lock_file = self._lock_path()

        with open(lock_file, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                raw = self._serialize(self._data)
                self._path.write_text(
                    json.dumps(raw, indent=2, default=str) + "\n",
                    encoding="utf-8",
                )
                logger.debug("Registry saved: version=%s", self._data.current_version)
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize(data: RegistryData) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "project": data.project,
            "current_version": data.current_version,
            "versions": {k: asdict(v) for k, v in data.versions.items()},
            "history": [asdict(h) for h in data.history],
            "monitored_files": {k: asdict(m) for k, m in data.monitored_files.items()},
        }
        return result

    @staticmethod
    def _deserialize(raw: Dict[str, Any]) -> RegistryData:
        versions = {}
        for k, v in raw.get("versions", {}).items():
            versions[k] = VersionEntry(**v)

        history = [HistoryEntry(**h) for h in raw.get("history", [])]

        monitored = {}
        for k, m in raw.get("monitored_files", {}).items():
            monitored[k] = MonitoredFile(**m)

        return RegistryData(
            project=raw.get("project", "ciphergy-pipeline"),
            current_version=raw.get("current_version", "0.0.0"),
            versions=versions,
            history=history,
            monitored_files=monitored,
        )

    # ------------------------------------------------------------------
    # Version management
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> RegistryData:
        if self._data is None:
            return self.load()
        return self._data

    def get_version(self) -> str:
        """Return the current version string."""
        data = self._ensure_loaded()
        return data.current_version

    def set_version(self, version: str, *, notes: str = "", sha256: str = "") -> None:
        """Set the current version and record it.

        Parameters
        ----------
        version : str
            Semantic version string (e.g. ``1.2.3``).
        notes : str
            Release notes.
        sha256 : str
            Optional hash of the release artifact.
        """
        data = self._ensure_loaded()
        now = datetime.now(timezone.utc).isoformat()

        entry = VersionEntry(
            version=version,
            timestamp=now,
            sha256=sha256,
            notes=notes,
        )
        data.versions[version] = entry
        data.current_version = version

        self.add_to_history(version, "set_version", notes or f"Set version to {version}")
        self.save()
        logger.info("Version set to %s", version)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def add_to_history(self, version: str, action: str, details: str = "") -> None:
        """Append an entry to the change history."""
        data = self._ensure_loaded()
        now = datetime.now(timezone.utc).isoformat()
        data.history.append(HistoryEntry(
            version=version,
            timestamp=now,
            action=action,
            details=details,
        ))

    def get_history(self, limit: int = 50) -> List[HistoryEntry]:
        """Return the most recent history entries."""
        data = self._ensure_loaded()
        return list(reversed(data.history[-limit:]))

    # ------------------------------------------------------------------
    # Monitored files
    # ------------------------------------------------------------------

    def get_monitored_files(self) -> Dict[str, MonitoredFile]:
        """Return all monitored file entries."""
        data = self._ensure_loaded()
        return dict(data.monitored_files)

    def monitor_file(self, path: str) -> None:
        """Add or update a file in the monitoring list.

        Computes the current SHA-256 and stores it for later staleness checks.
        """
        data = self._ensure_loaded()
        file_path = Path(path)
        if not file_path.is_file():
            logger.warning("Cannot monitor non-existent file: %s", path)
            return

        sha = self.compute_hash(path)
        now = datetime.now(timezone.utc).isoformat()
        data.monitored_files[path] = MonitoredFile(
            path=path, sha256=sha, last_checked=now,
        )
        self.save()
        logger.debug("Now monitoring: %s (sha256=%s)", path, sha[:16])

    def is_stale(self, path: str) -> bool:
        """Check if a monitored file has changed since last recorded hash.

        Returns True if the file's current hash differs from the stored hash,
        or if the file is not monitored.
        """
        data = self._ensure_loaded()
        entry = data.monitored_files.get(path)
        if entry is None:
            return True  # unknown = stale

        current_hash = self.compute_hash(path)
        stale = current_hash != entry.sha256
        if stale:
            logger.info("File is stale: %s", path)
        return stale

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    @staticmethod
    def compute_hash(path: str, algorithm: str = "sha256") -> str:
        """Compute the hex digest of a file.

        Parameters
        ----------
        path : str
            File path.
        algorithm : str
            Hash algorithm (default: sha256).

        Returns
        -------
        str
            Hex digest string.
        """
        h = hashlib.new(algorithm)
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"Cannot hash: {path}")

        with open(file_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def verify_hash(path: str, expected: str, algorithm: str = "sha256") -> bool:
        """Verify a file's hash matches the expected value.

        Returns
        -------
        bool
            True if the hash matches.
        """
        try:
            actual = Registry.compute_hash(path, algorithm)
            return actual == expected
        except FileNotFoundError:
            return False
