"""Statistics reporter for generating analysis reports."""

from pathlib import Path
from typing import Optional
import json

import pandas as pd
import numpy as np

from .collector import StatsCollector, RunStats


class StatsReporter:
    """Generate reports from collected statistics."""

    def __init__(self, collector: StatsCollector):
        self.collector = collector

    def generate_report(self, tasks_file: Optional[str] = None, output_dir: Optional[Path] = None) -> str:
        """Generate comprehensive statistics report."""
        runs = [r for r in self.collector.runs if tasks_file is None or r.tasks_file == tasks_file]

        if not runs:
            return "No data available for reporting."

        lines = [
            "# Speckit Analyzer Statistics Report",
            f"**Generated**: {pd.Timestamp.now().isoformat()}",
            f"**Runs Analyzed**: {len(runs)}",
            f"**Tasks File**: {tasks_file or 'All'}",
            "",
        ]

        summary = self.collector.get_summary(tasks_file)
        if summary:
            lines.extend([
                "## Summary",
                "",
                f"- **Total Runs**: {summary['total_runs']}",
                f"- **Avg Delegable Tasks**: {summary['avg_delegable']:.1f}",
                f"- **Avg Complexity**: {summary['avg_complexity']:.1f}",
                f"- **Avg LOC**: {summary['avg_loc']:,.0f}",
                f"- **Avg Context Tokens**: {summary['avg_context']:,.0f}",
                f"- **Avg Completion Rate**: {summary['avg_completion_rate']:.1%}",
                f"- **Latest Run**: {summary['latest_run']}",
                "",
            ])

        trends = self.collector.get_trends(tasks_file)
        if trends and "message" not in trends:
            lines.extend(["## Trends", ""])
            for field, trend in trends.items():
                direction = "📈" if trend["trend"] == "increasing" else "📉" if trend["trend"] == "decreasing" else "➡️"
                lines.append(f"- **{field}**: {direction} {trend['trend']} (slope: {trend['slope']:.4f}, R²: {trend['r_squared']:.3f}, p: {trend['p_value']:.3f})")
            lines.append("")

        lines.extend(["## Run History", ""])
        lines.append("| Timestamp | Tasks File | Total | Completed | Delegable | Avg Complexity | Avg LOC | Avg Context |")
        lines.append("|-----------|------------|-------|-----------|-----------|----------------|---------|-------------|")

        for run in runs[-20:]:
            lines.append(
                f"| {run.timestamp[:19]} | {run.tasks_file.split('/')[-2] if '/' in run.tasks_file else run.tasks_file} "
                f"| {run.total_tasks} | {run.completed_tasks} | {run.delegable} "
                f"| {run.avg_complexity:.1f} | {run.avg_loc:,.0f} | {run.avg_context:,.0f} |"
            )

        lines.append("")

        if len(runs) >= 3:
            lines.extend(["## Correlation Analysis", ""])
            complexity_vals = [r.avg_complexity for r in runs]
            loc_vals = [r.avg_loc for r in runs]
            context_vals = [r.avg_context for r in runs]
            delegable_vals = [r.delegable for r in runs]

            if len(set(complexity_vals)) > 1 and len(set(loc_vals)) > 1:
                corr = np.corrcoef(complexity_vals, loc_vals)[0, 1]
                lines.append(f"- **Complexity vs LOC**: {corr:.3f}")

            if len(set(complexity_vals)) > 1 and len(set(delegable_vals)) > 1:
                corr = np.corrcoef(complexity_vals, delegable_vals)[0, 1]
                lines.append(f"- **Complexity vs Delegable**: {corr:.3f}")

            if len(set(context_vals)) > 1 and len(set(delegable_vals)) > 1:
                corr = np.corrcoef(context_vals, delegable_vals)[0, 1]
                lines.append(f"- **Context vs Delegable**: {corr:.3f}")

            lines.append("")

        report = '\n'.join(lines)

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "stats_report.md").write_text(report)

        return report

    def export_csv(self, filepath: Path, tasks_file: Optional[str] = None) -> None:
        """Export run history as CSV."""
        runs = [r for r in self.collector.runs if tasks_file is None or r.tasks_file == tasks_file]

        data = [{
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
        } for r in runs]

        pd.DataFrame(data).to_csv(filepath, index=False)

    def export_parquet(self, filepath: Path, tasks_file: Optional[str] = None) -> None:
        """Export run history as Parquet."""
        runs = [r for r in self.collector.runs if tasks_file is None or r.tasks_file == tasks_file]

        data = [{
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
        } for r in runs]

        pd.DataFrame(data).to_parquet(filepath, index=False)


def generate_stats_report(collector: StatsCollector, tasks_file: Optional[str] = None) -> str:
    """Convenience function to generate stats report."""
    reporter = StatsReporter(collector)
    return reporter.generate_report(tasks_file)