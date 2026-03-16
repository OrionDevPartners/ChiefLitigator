"""Security layer for the Command Center."""

from pathlib import Path


class DeletionGuard:
    """Prevents file deletion on protected case directories."""

    def __init__(self, case_dir: str, protected_dirs: list[str]):
        self.case_dir = Path(case_dir)
        self.protected_dirs = protected_dirs

    def can_delete(self, file_path: str) -> tuple[bool, str]:
        """Check if a file can be deleted.

        Returns: (allowed: bool, reason: str)
        """
        path = Path(file_path)

        # Never delete case files in protected directories
        for protected in self.protected_dirs:
            protected_path = self.case_dir / protected
            try:
                path.relative_to(protected_path)
                return False, f"Protected directory: {protected}/"
            except ValueError:
                continue

        # Allow deletion of: DIFF/ files, temp files, .keys/ rotation
        if "DIFF/" in str(path) or "/tmp/" in str(path):
            return True, "Allowed: temporary/diff file"

        # Default: block
        return False, "Default: deletion blocked. Contact administrator."

    def log_attempt(self, file_path: str, allowed: bool, reason: str):
        """Log deletion attempt to security audit trail."""
        import datetime

        log_dir = self.case_dir / "DIFF"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"{datetime.date.today()}_security.md"

        with open(log_file, "a") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = "ALLOWED" if allowed else "BLOCKED"
            f.write(f"- `{timestamp}` | **DELETE {status}** | `{file_path}` | {reason}\n")
