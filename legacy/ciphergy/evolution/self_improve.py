"""
Ciphergy Pipeline — Self-Improvement System

Tracks performance metrics, identifies bottlenecks, and suggests
configuration improvements using Bedrock AI. Maintains an append-only
evolution log and respects GUARDRAILS.md hard constraints.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecutionRecord:
    """Record of a single cascade or pipeline execution."""

    execution_id: str
    trigger: str
    start_time: float
    end_time: float
    duration_seconds: float
    success: bool
    error: Optional[str] = None
    steps_completed: int = 0
    steps_total: int = 0
    files_changed: int = 0
    model_calls: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics."""

    total_executions: int = 0
    successful: int = 0
    failed: int = 0
    avg_duration_seconds: float = 0.0
    p95_duration_seconds: float = 0.0
    error_rate: float = 0.0
    most_common_errors: List[Dict[str, Any]] = field(default_factory=list)
    slowest_triggers: List[Dict[str, Any]] = field(default_factory=list)
    model_call_total: int = 0


@dataclass
class Improvement:
    """A suggested improvement to the pipeline configuration."""

    improvement_id: str
    category: str  # performance, accuracy, reliability, coverage
    description: str
    target: str  # config key or file to modify
    current_value: Any = None
    suggested_value: Any = None
    confidence: float = 0.0  # 0.0 to 1.0
    rationale: str = ""
    applied: bool = False
    applied_at: Optional[str] = None
    guardrail_check: bool = True  # True if it passes guardrail validation


@dataclass
class EvolutionLogEntry:
    """An append-only log entry for the evolution system."""

    timestamp: str
    action: str  # analyze, suggest, apply, reject, rollback
    details: Dict[str, Any] = field(default_factory=dict)


class EvolutionEngine:
    """
    Self-improvement engine for Ciphergy Pipeline.

    Tracks execution metrics, analyzes performance bottlenecks,
    suggests configuration improvements via Bedrock AI, and applies
    approved changes while respecting guardrail constraints.
    """

    MODEL_ID = "us.anthropic.claude-sonnet-4-6-20250514-v1:0"

    def __init__(
        self,
        project_root: Optional[str] = None,
        model_id: Optional[str] = None,
        region: str = "us-east-1",
    ) -> None:
        """
        Initialize the evolution engine.

        Args:
            project_root: Root directory of the Ciphergy project.
            model_id: Bedrock model ID for AI suggestions.
            region: AWS region for Bedrock.
        """
        self._project_root = Path(project_root) if project_root else Path.cwd()
        self._data_dir = self._project_root / ".ciphergy"
        self._model_id = model_id or self.MODEL_ID
        self._region = region
        self._bedrock_client: Any = None

        # Internal stores
        self._executions: List[ExecutionRecord] = []
        self._improvements: List[Improvement] = []
        self._evolution_log: List[EvolutionLogEntry] = []
        self._guardrails: Dict[str, Any] = {}

        # Load persisted state
        self._load_state()
        self._load_guardrails()

    # ── Tracking ────────────────────────────────────────────────────

    def record_execution(
        self,
        execution_id: str,
        trigger: str,
        start_time: float,
        end_time: float,
        success: bool,
        error: Optional[str] = None,
        steps_completed: int = 0,
        steps_total: int = 0,
        files_changed: int = 0,
        model_calls: int = 0,
    ) -> ExecutionRecord:
        """
        Record a pipeline execution for performance tracking.

        Args:
            execution_id: Unique identifier for this execution.
            trigger: The cascade trigger name.
            start_time: Monotonic start time (time.monotonic()).
            end_time: Monotonic end time.
            success: Whether the execution succeeded.
            error: Error message if failed.
            steps_completed: Number of steps completed.
            steps_total: Total number of steps.
            files_changed: Number of files changed.
            model_calls: Number of AI model invocations.

        Returns:
            The recorded ExecutionRecord.
        """
        record = ExecutionRecord(
            execution_id=execution_id,
            trigger=trigger,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=round(end_time - start_time, 3),
            success=success,
            error=error,
            steps_completed=steps_completed,
            steps_total=steps_total,
            files_changed=files_changed,
            model_calls=model_calls,
        )
        self._executions.append(record)
        self._save_state()

        logger.info(
            "Recorded execution %s: trigger=%s duration=%.1fs success=%s",
            execution_id,
            trigger,
            record.duration_seconds,
            success,
        )
        return record

    def record_user_override(self, execution_id: str, original: Any, override: Any, reason: str = "") -> None:
        """
        Record when a user overrides an AI recommendation.

        Args:
            execution_id: Related execution ID.
            original: The original AI recommendation.
            override: What the user changed it to.
            reason: Why the user overrode.
        """
        self._append_log(
            "user_override",
            {
                "execution_id": execution_id,
                "original": str(original),
                "override": str(override),
                "reason": reason,
            },
        )

    def record_panel_disagreement(
        self, execution_id: str, topic: str, model_votes: Dict[str, str], final_decision: str
    ) -> None:
        """
        Record when WDC panel models disagree.

        Args:
            execution_id: Related execution ID.
            topic: What the disagreement was about.
            model_votes: Dict mapping model names to their positions.
            final_decision: The final consensus decision.
        """
        unique_positions = set(model_votes.values())
        self._append_log(
            "panel_disagreement",
            {
                "execution_id": execution_id,
                "topic": topic,
                "model_votes": model_votes,
                "final_decision": final_decision,
                "disagreement_level": len(unique_positions) / max(len(model_votes), 1),
            },
        )

    # ── Analysis ────────────────────────────────────────────────────

    def analyze_performance(self) -> PerformanceMetrics:
        """
        Analyze accumulated execution records and return performance metrics.

        Returns:
            PerformanceMetrics with aggregated statistics.
        """
        if not self._executions:
            return PerformanceMetrics()

        durations = [e.duration_seconds for e in self._executions]
        successful = [e for e in self._executions if e.success]
        failed = [e for e in self._executions if not e.success]

        # Error frequency
        error_counts: Dict[str, int] = {}
        for e in failed:
            error_key = (e.error or "unknown")[:100]
            error_counts[error_key] = error_counts.get(error_key, 0) + 1

        most_common_errors = sorted(
            [{"error": k, "count": v} for k, v in error_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:5]

        # Slowest triggers
        trigger_durations: Dict[str, List[float]] = {}
        for e in self._executions:
            trigger_durations.setdefault(e.trigger, []).append(e.duration_seconds)

        slowest_triggers = sorted(
            [
                {"trigger": t, "avg_duration": round(sum(d) / len(d), 2), "count": len(d)}
                for t, d in trigger_durations.items()
            ],
            key=lambda x: x["avg_duration"],
            reverse=True,
        )[:5]

        # P95 duration
        sorted_durations = sorted(durations)
        p95_index = int(len(sorted_durations) * 0.95)
        p95 = sorted_durations[min(p95_index, len(sorted_durations) - 1)]

        metrics = PerformanceMetrics(
            total_executions=len(self._executions),
            successful=len(successful),
            failed=len(failed),
            avg_duration_seconds=round(sum(durations) / len(durations), 2),
            p95_duration_seconds=round(p95, 2),
            error_rate=round(len(failed) / len(self._executions), 3),
            most_common_errors=most_common_errors,
            slowest_triggers=slowest_triggers,
            model_call_total=sum(e.model_calls for e in self._executions),
        )

        self._append_log(
            "analyze",
            {
                "metrics": {
                    "total": metrics.total_executions,
                    "error_rate": metrics.error_rate,
                    "avg_duration": metrics.avg_duration_seconds,
                }
            },
        )

        return metrics

    # ── Improvement suggestions ─────────────────────────────────────

    def suggest_improvements(self) -> List[Improvement]:
        """
        Analyze performance and suggest configuration improvements.

        Uses Bedrock AI when available, falls back to rule-based heuristics.

        Returns:
            List of Improvement suggestions.
        """
        metrics = self.analyze_performance()

        try:
            suggestions = self._ai_suggest(metrics)
            if suggestions:
                self._improvements.extend(suggestions)
                self._save_state()
                return suggestions
        except Exception as exc:
            logger.info("AI suggestions unavailable (%s). Using heuristics.", exc)

        suggestions = self._heuristic_suggest(metrics)
        self._improvements.extend(suggestions)
        self._save_state()
        return suggestions

    def apply_improvement(self, improvement: Improvement) -> bool:
        """
        Apply a suggested improvement to the configuration.

        Validates against guardrails before applying. All changes are
        logged to the append-only evolution log.

        Args:
            improvement: The improvement to apply.

        Returns:
            True if applied successfully, False if blocked by guardrails.
        """
        # Guardrail check
        if not self._check_guardrails(improvement):
            improvement.guardrail_check = False
            self._append_log(
                "reject",
                {
                    "improvement_id": improvement.improvement_id,
                    "reason": "blocked by guardrails",
                },
            )
            logger.warning(
                "Improvement %s blocked by guardrails: %s",
                improvement.improvement_id,
                improvement.description,
            )
            return False

        # Load current config
        config = self._load_config()
        if config is None:
            logger.error("Cannot load config for improvement application")
            return False

        # Apply the change
        try:
            self._apply_config_change(config, improvement)
            self._save_config(config)

            improvement.applied = True
            improvement.applied_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            self._append_log(
                "apply",
                {
                    "improvement_id": improvement.improvement_id,
                    "target": improvement.target,
                    "old_value": str(improvement.current_value),
                    "new_value": str(improvement.suggested_value),
                },
            )

            self._save_state()
            logger.info("Applied improvement: %s", improvement.description)
            return True

        except Exception as exc:
            self._append_log(
                "apply_failed",
                {
                    "improvement_id": improvement.improvement_id,
                    "error": str(exc),
                },
            )
            logger.error("Failed to apply improvement %s: %s", improvement.improvement_id, exc)
            return False

    # ── User feedback integration ───────────────────────────────────

    def adjust_from_feedback(self, weak_areas: List[Dict[str, Any]]) -> List[Improvement]:
        """
        Generate improvements based on user feedback patterns.

        Args:
            weak_areas: Output from FeedbackCollector.get_weak_areas().

        Returns:
            List of suggested improvements addressing weak areas.
        """
        suggestions: List[Improvement] = []
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

        for i, area in enumerate(weak_areas):
            category = area.get("category", "unknown")
            avg_rating = area.get("avg_rating", 0)
            count = area.get("count", 0)

            if avg_rating < 3.0 and count >= 3:
                suggestion = Improvement(
                    improvement_id=f"feedback-{timestamp}-{i}",
                    category="accuracy",
                    description=f"Improve {category} outputs (avg rating: {avg_rating:.1f} from {count} reviews)",
                    target=f"confidence_monitor.categories.{category}.weight",
                    current_value=None,
                    suggested_value="increase by 0.1",
                    confidence=min(0.9, 0.5 + (count * 0.05)),
                    rationale=f"Users consistently rate {category} outputs low ({avg_rating:.1f}/5). "
                    f"Increasing confidence weight will trigger more thorough analysis.",
                )
                suggestions.append(suggestion)

        self._append_log(
            "feedback_analysis",
            {
                "weak_areas_count": len(weak_areas),
                "suggestions_generated": len(suggestions),
            },
        )

        return suggestions

    # ── AI-powered suggestions ──────────────────────────────────────

    def _ai_suggest(self, metrics: PerformanceMetrics) -> Optional[List[Improvement]]:
        """Use Bedrock to suggest improvements based on metrics."""
        if self._bedrock_client is None:
            try:
                import boto3

                session = boto3.Session(region_name=self._region)
                self._bedrock_client = session.client("bedrock-runtime", region_name=self._region)
            except ImportError:
                return None

        # Load current config for context
        config = self._load_config()
        config_summary = json.dumps(config, indent=2, default=str)[:2000] if config else "unavailable"

        # Load recent evolution log
        recent_log = self._evolution_log[-20:] if self._evolution_log else []
        log_summary = json.dumps([{"action": e.action, "details": e.details} for e in recent_log], indent=2)[:1000]

        prompt = f"""Analyze this Ciphergy Pipeline performance data and suggest improvements.

PERFORMANCE METRICS:
- Total executions: {metrics.total_executions}
- Error rate: {metrics.error_rate:.1%}
- Average duration: {metrics.avg_duration_seconds}s
- P95 duration: {metrics.p95_duration_seconds}s
- Most common errors: {json.dumps(metrics.most_common_errors)}
- Slowest triggers: {json.dumps(metrics.slowest_triggers)}

CURRENT CONFIG (excerpt):
{config_summary}

RECENT EVOLUTION LOG:
{log_summary}

GUARDRAILS (cannot override):
{json.dumps(self._guardrails, indent=2, default=str)[:1000]}

Suggest 1-5 specific, actionable improvements. For each:
- improvement_id: unique ID
- category: performance|accuracy|reliability|coverage
- description: what to change
- target: config key path (dot notation)
- suggested_value: the new value
- confidence: 0.0-1.0
- rationale: why this will help

Respond with ONLY valid JSON: {{"improvements": [...]}}"""

        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt}],
            }
        )

        response = self._bedrock_client.invoke_model(
            modelId=self._model_id,
            body=body,
            accept="application/json",
            contentType="application/json",
        )

        response_body = json.loads(response["body"].read())
        content = response_body.get("content", [])
        text = content[0].get("text", "") if content else ""

        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        data = json.loads(text)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

        improvements = []
        for i, item in enumerate(data.get("improvements", [])):
            imp = Improvement(
                improvement_id=item.get("improvement_id", f"ai-{timestamp}-{i}"),
                category=item.get("category", "performance"),
                description=item.get("description", ""),
                target=item.get("target", ""),
                suggested_value=item.get("suggested_value"),
                confidence=item.get("confidence", 0.5),
                rationale=item.get("rationale", ""),
            )
            improvements.append(imp)

        self._append_log("ai_suggest", {"count": len(improvements)})
        return improvements

    # ── Heuristic suggestions ───────────────────────────────────────

    def _heuristic_suggest(self, metrics: PerformanceMetrics) -> List[Improvement]:
        """Generate rule-based improvement suggestions."""
        suggestions: List[Improvement] = []
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        idx = 0

        # High error rate
        if metrics.error_rate > 0.2:
            suggestions.append(
                Improvement(
                    improvement_id=f"heuristic-{timestamp}-{idx}",
                    category="reliability",
                    description=f"Error rate is {metrics.error_rate:.0%}. Increase retry count and add error recovery.",
                    target="pipeline.max_retries",
                    current_value=3,
                    suggested_value=5,
                    confidence=0.8,
                    rationale="High error rate suggests transient failures. More retries help.",
                )
            )
            idx += 1

        # Slow executions
        if metrics.avg_duration_seconds > 60:
            suggestions.append(
                Improvement(
                    improvement_id=f"heuristic-{timestamp}-{idx}",
                    category="performance",
                    description=f"Average execution time is {metrics.avg_duration_seconds:.0f}s. Consider parallel step execution.",
                    target="pipeline.parallel_steps",
                    current_value=False,
                    suggested_value=True,
                    confidence=0.7,
                    rationale="Serial step execution is a bottleneck when durations exceed 60s.",
                )
            )
            idx += 1

        # Many model calls
        if metrics.model_call_total > 100 and metrics.total_executions > 0:
            avg_calls = metrics.model_call_total / metrics.total_executions
            if avg_calls > 10:
                suggestions.append(
                    Improvement(
                        improvement_id=f"heuristic-{timestamp}-{idx}",
                        category="performance",
                        description=f"Average {avg_calls:.0f} model calls per execution. Enable response caching.",
                        target="pipeline.cache_model_responses",
                        current_value=False,
                        suggested_value=True,
                        confidence=0.75,
                        rationale="Caching repeated model calls reduces latency and cost.",
                    )
                )
                idx += 1

        # Slowest trigger optimization
        for trigger_info in metrics.slowest_triggers[:2]:
            if trigger_info["avg_duration"] > 120:
                suggestions.append(
                    Improvement(
                        improvement_id=f"heuristic-{timestamp}-{idx}",
                        category="performance",
                        description=f"Trigger '{trigger_info['trigger']}' averages {trigger_info['avg_duration']:.0f}s. Review step list for unnecessary operations.",
                        target=f"cascades.{trigger_info['trigger']}.steps",
                        confidence=0.6,
                        rationale="Long-running triggers should be audited for step reduction.",
                    )
                )
                idx += 1

        if not suggestions:
            suggestions.append(
                Improvement(
                    improvement_id=f"heuristic-{timestamp}-0",
                    category="coverage",
                    description="System performing well. Consider adding more cascade triggers for comprehensive monitoring.",
                    target="cascades",
                    confidence=0.4,
                    rationale="No performance issues detected. Expansion recommended.",
                )
            )

        self._append_log("heuristic_suggest", {"count": len(suggestions)})
        return suggestions

    # ── Guardrails ──────────────────────────────────────────────────

    def _load_guardrails(self) -> None:
        """Load guardrails from GUARDRAILS.md or config."""
        guardrails_path = self._project_root / "GUARDRAILS.md"
        if guardrails_path.exists():
            try:
                content = guardrails_path.read_text()
                # Parse guardrails into structured format
                self._guardrails = self._parse_guardrails(content)
            except Exception as exc:
                logger.warning("Failed to load guardrails: %s", exc)

        # Also check config-based guardrails
        config_guardrails = self._project_root / "config" / "guardrails.json"
        if config_guardrails.exists():
            try:
                with open(config_guardrails) as f:
                    self._guardrails.update(json.load(f))
            except Exception as exc:
                logger.warning("Failed to load config guardrails: %s", exc)

    def _parse_guardrails(self, content: str) -> Dict[str, Any]:
        """Parse GUARDRAILS.md into a structured dict."""
        guardrails: Dict[str, Any] = {"hard_constraints": [], "raw": content[:2000]}
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("- NEVER") or line.startswith("- MUST") or line.startswith("- ALWAYS"):
                guardrails["hard_constraints"].append(line)
        return guardrails

    def _check_guardrails(self, improvement: Improvement) -> bool:
        """
        Check if an improvement violates any guardrails.

        Args:
            improvement: The improvement to validate.

        Returns:
            True if the improvement is safe to apply.
        """
        # Never modify guardrails themselves
        if "guardrail" in improvement.target.lower():
            return False

        # Never remove security configurations
        if improvement.suggested_value is None and "security" in improvement.target.lower():
            return False

        # Never disable authentication
        if improvement.target.lower() in ("auth.enabled", "auth.required") and improvement.suggested_value is False:
            return False

        # Low confidence improvements should not be auto-applied
        if improvement.confidence < 0.3:
            logger.info(
                "Improvement %s has low confidence (%.2f). Requires manual review.",
                improvement.improvement_id,
                improvement.confidence,
            )
            return False

        return True

    # ── Config helpers ──────────────────────────────────────────────

    def _load_config(self) -> Optional[Dict[str, Any]]:
        """Load the ciphergy.yaml config."""
        config_path = self._project_root / "config" / "ciphergy.yaml"
        if not config_path.exists():
            return None

        try:
            import yaml as yaml_mod

            with open(config_path) as f:
                return yaml_mod.safe_load(f)
        except ImportError:
            try:
                with open(config_path) as f:
                    return json.load(f)
            except Exception:
                return None

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save the ciphergy.yaml config."""
        config_path = self._project_root / "config" / "ciphergy.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            import yaml as yaml_mod

            with open(config_path, "w") as f:
                yaml_mod.dump(config, f, default_flow_style=False, sort_keys=False)
        except ImportError:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

    def _apply_config_change(self, config: Dict[str, Any], improvement: Improvement) -> None:
        """Apply a config change using dot-notation target path."""
        parts = improvement.target.split(".")
        obj = config

        for part in parts[:-1]:
            if part not in obj:
                obj[part] = {}
            obj = obj[part]

        if parts:
            obj[parts[-1]] = improvement.suggested_value

    # ── State persistence ───────────────────────────────────────────

    def _load_state(self) -> None:
        """Load persisted evolution state."""
        state_path = self._data_dir / "evolution_state.json"
        if not state_path.exists():
            return

        try:
            with open(state_path) as f:
                data = json.load(f)

            self._executions = [ExecutionRecord(**rec) for rec in data.get("executions", [])]
            self._evolution_log = [EvolutionLogEntry(**entry) for entry in data.get("evolution_log", [])]
        except Exception as exc:
            logger.warning("Failed to load evolution state: %s", exc)

    def _save_state(self) -> None:
        """Persist evolution state."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        state_path = self._data_dir / "evolution_state.json"

        data = {
            "executions": [
                {
                    "execution_id": e.execution_id,
                    "trigger": e.trigger,
                    "start_time": e.start_time,
                    "end_time": e.end_time,
                    "duration_seconds": e.duration_seconds,
                    "success": e.success,
                    "error": e.error,
                    "steps_completed": e.steps_completed,
                    "steps_total": e.steps_total,
                    "files_changed": e.files_changed,
                    "model_calls": e.model_calls,
                    "timestamp": e.timestamp,
                }
                for e in self._executions[-1000:]  # Keep last 1000
            ],
            "evolution_log": [
                {"timestamp": entry.timestamp, "action": entry.action, "details": entry.details}
                for entry in self._evolution_log[-5000:]  # Keep last 5000
            ],
        }

        try:
            with open(state_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            logger.error("Failed to save evolution state: %s", exc)

    def _append_log(self, action: str, details: Dict[str, Any]) -> None:
        """Append to the evolution log (append-only)."""
        entry = EvolutionLogEntry(
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            action=action,
            details=details,
        )
        self._evolution_log.append(entry)

        # Also append to the file-based log (true append-only)
        log_path = self._data_dir / "evolution_log.jsonl"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps({"timestamp": entry.timestamp, "action": action, "details": details}) + "\n")
        except Exception as exc:
            logger.warning("Failed to append to evolution log file: %s", exc)

    # ── Reporting ───────────────────────────────────────────────────

    def get_evolution_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the evolution system state.

        Returns:
            Dict with metrics, recent improvements, and log stats.
        """
        metrics = self.analyze_performance()
        return {
            "metrics": {
                "total_executions": metrics.total_executions,
                "error_rate": metrics.error_rate,
                "avg_duration": metrics.avg_duration_seconds,
                "p95_duration": metrics.p95_duration_seconds,
            },
            "improvements": {
                "total_suggested": len(self._improvements),
                "applied": sum(1 for i in self._improvements if i.applied),
                "pending": sum(1 for i in self._improvements if not i.applied),
            },
            "evolution_log_entries": len(self._evolution_log),
            "guardrails_loaded": bool(self._guardrails),
        }
