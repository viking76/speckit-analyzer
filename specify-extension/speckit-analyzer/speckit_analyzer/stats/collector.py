"""Statistics collector for analysis runs."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

import numpy as np
from scipy import stats

from ..parser.models import AnalysisResult, Task, ThresholdImpact, ThresholdMetrics


@dataclass
class RunStats:
    timestamp: str
    tasks_file: str
    total_tasks: int
    completed_tasks: int
    completion_rate: float
    threshold_complexity: int
    threshold_context: int
    delegable: int
    non_delegable_complexity: int
    non_delegable_context: int
    non_delegable_both: int
    avg_complexity: float
    avg_loc: float
    avg_context: float
    complexity_vs_actual_loc: Optional[float] = None
    estimate_vs_actual_days: Optional[float] = None
    context_vs_actual_tokens: Optional[float] = None


class StatsCollector:
    """Collect and aggregate statistics across analysis runs."""

    def __init__(self, history_file: Optional[Path] = None):
        self.history_file = history_file or Path("analysis/stats_history.json")
        self.runs: list[RunStats] = []
        self.load_history()

    def load_history(self) -> None:
        """Load historical stats from file."""
        if self.history_file.exists():
            try:
                data = json.loads(self.history_file.read_text())
                self.runs = [RunStats(**r) for r in data]
            except Exception:
                self.runs = []

    def save_history(self) -> None:
        """Save historical stats to file."""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "timestamp": r.timestamp,
                "tasks_file": r.tasks_file,
                "total_tasks": r.total_tasks,
                "completed_tasks": r.completed_tasks,
                "completion_rate": r.completion_rate,
                "threshold_complexity": r.threshold_complexity,
                "threshold_context": r.threshold_context,
                "delegable": r.delegable,
                "non_delegable_complexity": r.non_delegable_complexity,
                "non_delegable_context": r.non_delegable_context,
                "non_delegable_both": r.non_delegable_both,
                "avg_complexity": r.avg_complexity,
                "avg_loc": r.avg_loc,
                "avg_context": r.avg_context,
                "complexity_vs_actual_loc": r.complexity_vs_actual_loc,
                "estimate_vs_actual_days": r.estimate_vs_actual_days,
                "context_vs_actual_tokens": r.context_vs_actual_tokens,
            }
            for r in self.runs
        ]
        self.history_file.write_text(json.dumps(data, indent=2))

    def add_run(self, result: AnalysisResult) -> RunStats:
        """Add a new analysis run to history."""
        tasks_with_scores = [t for t in result.tasks if t.score]

        avg_complexity = np.mean([t.score.complexity for t in tasks_with_scores]) if tasks_with_scores else 0
        avg_loc = np.mean([t.score.est_loc for t in tasks_with_scores]) if tasks_with_scores else 0
        avg_context = np.mean([t.score.context_tokens for t in tasks_with_scores]) if tasks_with_scores else 0

        run = RunStats(
            timestamp=result.stats.timestamp,
            tasks_file=result.stats.tasks_file,
            total_tasks=result.stats.total_tasks,
            completed_tasks=result.stats.completed_tasks,
            completion_rate=result.stats.completion_rate,
            threshold_complexity=result.thresholds_used.get("complexity", 5),
            threshold_context=result.thresholds_used.get("context_tokens", 100000),
            delegable=result.delegation_summary.delegable,
            non_delegable_complexity=result.delegation_summary.non_delegable_complexity,
            non_delegable_context=result.delegation_summary.non_delegable_context,
            non_delegable_both=result.delegation_summary.non_delegable_both,
            avg_complexity=avg_complexity,
            avg_loc=avg_loc,
            avg_context=avg_context,
            complexity_vs_actual_loc=result.stats.complexity_vs_actual_loc,
            estimate_vs_actual_days=result.stats.estimate_vs_actual_days,
            context_vs_actual_tokens=result.stats.context_vs_actual_tokens,
        )

        self.runs.append(run)
        self.save_history()
        return run

    def get_trends(self, tasks_file: Optional[str] = None) -> dict:
        """Compute trends across runs."""
        runs = [r for r in self.runs if tasks_file is None or r.tasks_file == tasks_file]

        if len(runs) < 2:
            return {"message": "Need at least 2 runs for trend analysis"}

        trends = {}
        for field in ["delegable", "avg_complexity", "avg_loc", "avg_context", "completion_rate"]:
            values = [getattr(r, field) for r in runs]
            if len(values) >= 2:
                slope, intercept, r_value, p_value, std_err = stats.linregress(range(len(values)), values)
                trends[field] = {
                    "slope": slope,
                    "r_squared": r_value ** 2,
                    "p_value": p_value,
                    "trend": "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable",
                }

        return trends

    def get_summary(self, tasks_file: Optional[str] = None) -> dict:
        """Get summary statistics."""
        runs = [r for r in self.runs if tasks_file is None or r.tasks_file == tasks_file]

        if not runs:
            return {}

        return {
            "total_runs": len(runs),
            "avg_delegable": np.mean([r.delegable for r in runs]),
            "avg_complexity": np.mean([r.avg_complexity for r in runs]),
            "avg_loc": np.mean([r.avg_loc for r in runs]),
            "avg_context": np.mean([r.avg_context for r in runs]),
            "avg_completion_rate": np.mean([r.completion_rate for r in runs]),
            "latest_run": runs[-1].timestamp if runs else None,
        }


def collect_analysis_stats(result: AnalysisResult, ground_truth: Optional[dict] = None) -> None:
    """Collect all statistics for an analysis result."""
    from ..output.stats_writer import compute_threshold_impact

    compute_threshold_impact(result, ground_truth)

    tasks_with_scores = [t for t in result.tasks if t.score]

    if tasks_with_scores:
        result.stats.complexity_distribution = {}
        for t in tasks_with_scores:
            c = t.score.complexity
            result.stats.complexity_distribution[c] = result.stats.complexity_distribution.get(c, 0) + 1

        result.stats.loc_distribution = {}
        for t in tasks_with_scores:
            loc = t.score.est_loc
            if loc < 100:
                bucket = "0-100"
            elif loc < 300:
                bucket = "100-300"
            elif loc < 500:
                bucket = "300-500"
            elif loc < 1000:
                bucket = "500-1000"
            else:
                bucket = "1000+"
            result.stats.loc_distribution[bucket] = result.stats.loc_distribution.get(bucket, 0) + 1

        result.stats.context_distribution = {}
        for t in tasks_with_scores:
            ctx = t.score.context_tokens
            if ctx < 50000:
                bucket = "0-50k"
            elif ctx < 100000:
                bucket = "50k-100k"
            elif ctx < 200000:
                bucket = "100k-200k"
            elif ctx < 500000:
                bucket = "200k-500k"
            else:
                bucket = "500k+"
            result.stats.context_distribution[bucket] = result.stats.context_distribution.get(bucket, 0) + 1

    result.stats.timestamp = datetime.now().isoformat()
    result.stats.tasks_file = result.stats.tasks_file or "unknown"
    result.stats.total_tasks = len(result.tasks)
    result.stats.completed_tasks = sum(1 for t in result.tasks if t.status.value == "COMPLETED")
    result.stats.completion_rate = result.stats.completed_tasks / max(result.stats.total_tasks, 1)

    delegable_tasks = [t for t in result.tasks if t.delegable]
    result.delegation_summary.total_tasks = len(result.tasks)
    result.delegation_summary.delegable = len(delegable_tasks)
    result.delegation_summary.non_delegable_complexity = sum(
        1 for t in result.tasks if not t.delegable and t.score and t.score.complexity > result.thresholds_used.get("complexity", 5)
    )
    result.delegation_summary.non_delegable_context = sum(
        1 for t in result.tasks if not t.delegable and t.score and t.score.context_tokens > result.thresholds_used.get("context_tokens", 100000)
    )
    result.delegation_summary.non_delegable_both = sum(
        1 for t in result.tasks if not t.delegable and t.score
        and t.score.complexity > result.thresholds_used.get("complexity", 5)
        and t.score.context_tokens > result.thresholds_used.get("context_tokens", 100000)
    )