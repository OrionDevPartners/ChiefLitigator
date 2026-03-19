"""
Ciphergy Pipeline — User Feedback Collection

Collects, stores, and analyzes user feedback on pipeline outputs.
Identifies consistently low-rated areas to drive self-improvement.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FeedbackEntry:
    """A single user feedback record."""

    output_id: str
    rating: float  # 1.0 to 5.0
    category: str = ""  # e.g., "evidence_quality", "analysis_depth", "accuracy"
    notes: str = ""
    timestamp: str = ""
    trigger: str = ""
    execution_id: str = ""
    tags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a serializable dict."""
        return {
            "output_id": self.output_id,
            "rating": self.rating,
            "category": self.category,
            "notes": self.notes,
            "timestamp": self.timestamp,
            "trigger": self.trigger,
            "execution_id": self.execution_id,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeedbackEntry":
        """Create from a dict."""
        return cls(
            output_id=data.get("output_id", ""),
            rating=data.get("rating", 3.0),
            category=data.get("category", ""),
            notes=data.get("notes", ""),
            timestamp=data.get("timestamp", ""),
            trigger=data.get("trigger", ""),
            execution_id=data.get("execution_id", ""),
            tags=data.get("tags", []),
        )


@dataclass
class FeedbackSummary:
    """Aggregated feedback statistics."""

    total_entries: int = 0
    average_rating: float = 0.0
    rating_distribution: Dict[str, int] = field(default_factory=dict)
    category_averages: Dict[str, float] = field(default_factory=dict)
    trend: str = ""  # improving, declining, stable
    time_range: str = ""


@dataclass
class WeakArea:
    """An area identified as consistently low-rated."""

    category: str
    avg_rating: float
    count: int
    recent_trend: str  # improving, declining, stable
    sample_notes: List[str] = field(default_factory=list)
    suggested_action: str = ""


class FeedbackCollector:
    """
    Collects and analyzes user feedback on Ciphergy pipeline outputs.

    Feedback is stored in .ciphergy/feedback.json. Analysis methods
    aggregate patterns and identify areas needing improvement.
    """

    def __init__(self, project_root: Optional[str] = None) -> None:
        """
        Initialize the feedback collector.

        Args:
            project_root: Root directory of the Ciphergy project.
        """
        self._project_root = Path(project_root) if project_root else Path.cwd()
        self._data_dir = self._project_root / ".ciphergy"
        self._feedback_path = self._data_dir / "feedback.json"
        self._entries: List[FeedbackEntry] = []
        self._load()

    # ── Collection ──────────────────────────────────────────────────

    def collect(
        self,
        output_id: str,
        rating: float,
        notes: str = "",
        category: str = "",
        trigger: str = "",
        execution_id: str = "",
        tags: Optional[List[str]] = None,
    ) -> FeedbackEntry:
        """
        Collect a feedback entry for a pipeline output.

        Args:
            output_id: Unique identifier for the output being rated.
            rating: Rating from 1.0 (poor) to 5.0 (excellent).
            notes: Optional free-text feedback.
            category: Output category (e.g., "evidence_quality", "analysis_depth").
            trigger: The cascade trigger that produced this output.
            execution_id: Related execution ID.
            tags: Optional tags for categorization.

        Returns:
            The stored FeedbackEntry.

        Raises:
            ValueError: If rating is out of range.
        """
        if not 1.0 <= rating <= 5.0:
            raise ValueError(f"Rating must be between 1.0 and 5.0, got {rating}")

        entry = FeedbackEntry(
            output_id=output_id,
            rating=rating,
            category=category,
            notes=notes,
            trigger=trigger,
            execution_id=execution_id,
            tags=tags or [],
        )

        self._entries.append(entry)
        self._save()

        logger.info(
            "Feedback collected: output=%s rating=%.1f category=%s",
            output_id,
            rating,
            category,
        )
        return entry

    def collect_batch(self, entries: List[Dict[str, Any]]) -> List[FeedbackEntry]:
        """
        Collect multiple feedback entries at once.

        Args:
            entries: List of dicts with feedback data.

        Returns:
            List of stored FeedbackEntry objects.
        """
        results: List[FeedbackEntry] = []
        for entry_data in entries:
            try:
                entry = self.collect(
                    output_id=entry_data["output_id"],
                    rating=entry_data["rating"],
                    notes=entry_data.get("notes", ""),
                    category=entry_data.get("category", ""),
                    trigger=entry_data.get("trigger", ""),
                    execution_id=entry_data.get("execution_id", ""),
                    tags=entry_data.get("tags"),
                )
                results.append(entry)
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping invalid feedback entry: %s", exc)
        return results

    # ── Analysis ────────────────────────────────────────────────────

    def analyze_feedback(self) -> FeedbackSummary:
        """
        Aggregate feedback patterns into a summary.

        Returns:
            FeedbackSummary with statistics and trends.
        """
        if not self._entries:
            return FeedbackSummary()

        ratings = [e.rating for e in self._entries]
        avg = sum(ratings) / len(ratings)

        # Rating distribution
        distribution: Dict[str, int] = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        for r in ratings:
            bucket = str(int(min(5, max(1, round(r)))))
            distribution[bucket] = distribution.get(bucket, 0) + 1

        # Category averages
        category_ratings: Dict[str, List[float]] = {}
        for entry in self._entries:
            if entry.category:
                category_ratings.setdefault(entry.category, []).append(entry.rating)

        category_averages = {cat: round(sum(rats) / len(rats), 2) for cat, rats in category_ratings.items()}

        # Trend analysis (compare first half to second half)
        trend = "stable"
        if len(ratings) >= 10:
            mid = len(ratings) // 2
            first_half_avg = sum(ratings[:mid]) / mid
            second_half_avg = sum(ratings[mid:]) / (len(ratings) - mid)
            diff = second_half_avg - first_half_avg
            if diff > 0.3:
                trend = "improving"
            elif diff < -0.3:
                trend = "declining"

        # Time range
        timestamps = [e.timestamp for e in self._entries if e.timestamp]
        time_range = ""
        if timestamps:
            time_range = f"{min(timestamps)} to {max(timestamps)}"

        return FeedbackSummary(
            total_entries=len(self._entries),
            average_rating=round(avg, 2),
            rating_distribution=distribution,
            category_averages=category_averages,
            trend=trend,
            time_range=time_range,
        )

    def get_weak_areas(self, threshold: float = 3.0, min_samples: int = 3) -> List[WeakArea]:
        """
        Identify consistently low-rated output categories.

        Args:
            threshold: Categories with avg rating below this are "weak".
            min_samples: Minimum feedback entries needed to consider a category.

        Returns:
            List of WeakArea objects sorted by average rating (worst first).
        """
        # Group by category
        category_entries: Dict[str, List[FeedbackEntry]] = {}
        for entry in self._entries:
            if entry.category:
                category_entries.setdefault(entry.category, []).append(entry)

        weak_areas: List[WeakArea] = []

        for category, entries in category_entries.items():
            if len(entries) < min_samples:
                continue

            ratings = [e.rating for e in entries]
            avg = sum(ratings) / len(ratings)

            if avg >= threshold:
                continue

            # Trend for this category
            trend = "stable"
            if len(ratings) >= 6:
                mid = len(ratings) // 2
                first_avg = sum(ratings[:mid]) / mid
                second_avg = sum(ratings[mid:]) / (len(ratings) - mid)
                diff = second_avg - first_avg
                if diff > 0.3:
                    trend = "improving"
                elif diff < -0.3:
                    trend = "declining"

            # Sample notes from low-rated entries
            low_entries = sorted(entries, key=lambda e: e.rating)[:5]
            sample_notes = [e.notes for e in low_entries if e.notes][:3]

            # Suggest action based on pattern
            action = self._suggest_action(category, avg, trend, sample_notes)

            weak_areas.append(
                WeakArea(
                    category=category,
                    avg_rating=round(avg, 2),
                    count=len(entries),
                    recent_trend=trend,
                    sample_notes=sample_notes,
                    suggested_action=action,
                )
            )

        # Sort by average rating (worst first)
        weak_areas.sort(key=lambda w: w.avg_rating)
        return weak_areas

    def get_feedback_for_output(self, output_id: str) -> List[FeedbackEntry]:
        """
        Get all feedback entries for a specific output.

        Args:
            output_id: The output identifier.

        Returns:
            List of FeedbackEntry objects for this output.
        """
        return [e for e in self._entries if e.output_id == output_id]

    def get_feedback_by_category(self, category: str) -> List[FeedbackEntry]:
        """
        Get all feedback entries for a specific category.

        Args:
            category: The category to filter by.

        Returns:
            List of FeedbackEntry objects.
        """
        return [e for e in self._entries if e.category == category]

    def get_recent(self, count: int = 20) -> List[FeedbackEntry]:
        """
        Get the most recent feedback entries.

        Args:
            count: Number of entries to return.

        Returns:
            List of the most recent FeedbackEntry objects.
        """
        return self._entries[-count:]

    # ── Statistics ──────────────────────────────────────────────────

    def category_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """
        Get a breakdown of feedback by category.

        Returns:
            Dict mapping category names to their statistics.
        """
        breakdown: Dict[str, Dict[str, Any]] = {}

        for entry in self._entries:
            cat = entry.category or "uncategorized"
            if cat not in breakdown:
                breakdown[cat] = {"count": 0, "ratings": [], "tags": set()}
            breakdown[cat]["count"] += 1
            breakdown[cat]["ratings"].append(entry.rating)
            breakdown[cat]["tags"].update(entry.tags)

        # Compute averages
        for cat, data in breakdown.items():
            ratings = data["ratings"]
            data["avg_rating"] = round(sum(ratings) / len(ratings), 2)
            data["min_rating"] = min(ratings)
            data["max_rating"] = max(ratings)
            data["tags"] = list(data["tags"])
            del data["ratings"]

        return breakdown

    def trigger_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """
        Get a breakdown of feedback by cascade trigger.

        Returns:
            Dict mapping trigger names to their statistics.
        """
        breakdown: Dict[str, Dict[str, Any]] = {}

        for entry in self._entries:
            trigger = entry.trigger or "unknown"
            if trigger not in breakdown:
                breakdown[trigger] = {"count": 0, "ratings": []}
            breakdown[trigger]["count"] += 1
            breakdown[trigger]["ratings"].append(entry.rating)

        for trigger, data in breakdown.items():
            ratings = data["ratings"]
            data["avg_rating"] = round(sum(ratings) / len(ratings), 2)
            del data["ratings"]

        return breakdown

    # ── Private helpers ─────────────────────────────────────────────

    def _suggest_action(self, category: str, avg_rating: float, trend: str, sample_notes: List[str]) -> str:
        """Generate a suggested action for a weak area."""
        if avg_rating < 2.0:
            return (
                f"CRITICAL: {category} outputs are consistently poor (avg {avg_rating:.1f}). "
                f"Review WDC panel weights and confidence thresholds for this category."
            )
        elif trend == "declining":
            return (
                f"WARNING: {category} quality is declining (avg {avg_rating:.1f}). "
                f"Check for recent config changes or data source issues."
            )
        elif trend == "improving":
            return (
                f"IMPROVING: {category} is getting better (avg {avg_rating:.1f}) but still below threshold. "
                f"Continue current improvements."
            )
        else:
            return (
                f"Investigate {category} quality (avg {avg_rating:.1f}). "
                f"Consider increasing confidence weight or adding verification steps."
            )

    def _load(self) -> None:
        """Load feedback entries from disk."""
        if not self._feedback_path.exists():
            return

        try:
            with open(self._feedback_path) as f:
                data = json.load(f)

            self._entries = [FeedbackEntry.from_dict(entry) for entry in data.get("entries", [])]
            logger.info("Loaded %d feedback entries", len(self._entries))
        except Exception as exc:
            logger.warning("Failed to load feedback: %s", exc)

    def _save(self) -> None:
        """Persist feedback entries to disk."""
        self._data_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "version": 1,
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_entries": len(self._entries),
            "entries": [entry.to_dict() for entry in self._entries],
        }

        try:
            with open(self._feedback_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            logger.error("Failed to save feedback: %s", exc)

    def clear(self) -> None:
        """Clear all feedback entries. Use with caution."""
        self._entries.clear()
        self._save()
        logger.warning("All feedback entries cleared")

    def export_csv(self, output_path: Optional[str] = None) -> str:
        """
        Export feedback to CSV format.

        Args:
            output_path: File path for the CSV. Defaults to .ciphergy/feedback_export.csv.

        Returns:
            The path to the exported file.
        """
        path = Path(output_path) if output_path else self._data_dir / "feedback_export.csv"
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = ["output_id,rating,category,trigger,timestamp,notes"]
        for entry in self._entries:
            # Escape notes for CSV
            notes_escaped = entry.notes.replace('"', '""')
            lines.append(
                f'{entry.output_id},{entry.rating},{entry.category},{entry.trigger},{entry.timestamp},"{notes_escaped}"'
            )

        path.write_text("\n".join(lines))
        logger.info("Exported %d entries to %s", len(self._entries), path)
        return str(path)

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return f"<FeedbackCollector entries={len(self._entries)} path={self._feedback_path}>"
