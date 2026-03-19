"""File modification watcher for cache invalidation."""

from pathlib import Path
from typing import Union


class FileWatcher:
    """Tracks file modification times. Returns True if file changed since last check."""

    def __init__(self) -> None:
        self._mtimes: dict[str, float] = {}

    def has_changed(self, path: Union[str, Path]) -> bool:
        """Check if file was modified since last check.

        Returns True if:
        - File has never been checked before
        - File mtime is newer than last recorded mtime
        - File no longer exists (treats deletion as a change)

        Returns False if file mtime matches last recorded value.
        """
        path_str = str(path)
        p = Path(path_str)

        if not p.exists():
            # If we were tracking it and it disappeared, that is a change.
            # If we never tracked it, there is nothing to read.
            return path_str in self._mtimes

        try:
            current_mtime = p.stat().st_mtime
        except OSError:
            return path_str in self._mtimes

        last_mtime = self._mtimes.get(path_str)
        if last_mtime is None:
            return True
        return current_mtime != last_mtime

    def mark_read(self, path: Union[str, Path]) -> None:
        """Mark file as read at current mtime."""
        path_str = str(path)
        p = Path(path_str)
        try:
            self._mtimes[path_str] = p.stat().st_mtime
        except OSError:
            # File gone — remove from tracking
            self._mtimes.pop(path_str, None)

    def forget(self, path: Union[str, Path]) -> None:
        """Stop tracking a file."""
        self._mtimes.pop(str(path), None)

    def clear(self) -> None:
        """Clear all tracked files."""
        self._mtimes.clear()
