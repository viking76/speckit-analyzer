"""Statistical output writers for threshold analysis and history tracking."""

import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd

from ..parser.models import AnalysisResult, ThresholdMetrics


def write_stats_csv(result: AnalysisResult, filepath: Path, append: bool = True) -> None:
    """Write stats to CSV history file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)

    row = {
        "run_id": "",
        "timestamp": result.stats.timestamp,
        "tasks_file": result.stats.tasks_file,
        "total_tasks": result.stats.total_tasks,
        "completed_tasks": result.stats.completed_tasks,
        "threshold_complexity": result.thresholds_used.get("complexity", 5),
        "threshold_context": result.thresholds_used.get("context_tokens", 100000),
        "delegable": result.delegation_summary.delegable,
        "precision": "",
        "recall": "",
        "f1": "",
        "avg_complexity_delegable": 0.0,
        "avg_context_delegable": 0.0,
    }

    if result.delegation_summary.delegable > 0:
        delegable_tasks = [t for t in result.tasks if t.delegable and t.score]
        if delegable_tasks:
            row["avg_complexity_delegable"] = sum(t.score.complexity for t in delegable_tasks) / len(delegable_tasks)
            row["avg_context_delegable"] = sum(t.score.context_tokens for t in delegable_tasks) / len(delegable_tasks)

    file_exists = filepath.exists()
    with open(filepath, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def write_stats_parquet(result: AnalysisResult, filepath: Path) -> None:
    """Write stats to Parquet for efficient analysis."""
    filepath.parent.mkdir(parents=True, exist_ok=True)

    row = {
        "timestamp": result.stats.timestamp,
        "tasks_file": result.stats.tasks_file,
        "total_tasks": result.stats.total_tasks,
        "completed_tasks": result.stats.completed_tasks,
        "completion_rate": result.stats.completion_rate,
        "threshold_complexity": result.thresholds_used.get("complexity", 5),
        "threshold_context": result.thresholds_used.get("context_tokens", 100000),
        "delegable": result.delegation_summary.delegable,
        "non_delegable_complexity": result.delegation_summary.non_delegable_complexity,
        "non_delegable_context": result.delegation_summary.non_delegable_context,
        "non_delegable_both": result.delegation_summary.non_delegable_both,
        "complexity_distribution": json.dumps(result.stats.complexity_distribution),
        "loc_distribution": json.dumps(result.stats.loc_distribution),
        "context_distribution": json.dumps(result.stats.context_distribution),
        "complexity_vs_actual_loc": result.stats.complexity_vs_actual_loc,
        "estimate_vs_actual_days": result.stats.estimate_vs_actual_days,
        "context_vs_actual_tokens": result.stats.context_vs_actual_tokens,
    }

    df = pd.DataFrame([row])

    if filepath.exists():
        existing = pd.read_parquet(filepath)
        df = pd.concat([existing, df], ignore_index=True)

    df.to_parquet(filepath, index=False)


def write_threshold_analysis(result: AnalysisResult, output_dir: Path) -> None:
    """Write threshold analysis report."""
    output_dir.mkdir(parents=True, exist_ok=True)

    write_threshold_analysis_md(result, output_dir / "threshold_analysis.md")
    write_threshold_analysis_csv(result, output_dir / "threshold_analysis.csv")


def write_threshold_analysis_md(result: AnalysisResult, filepath: Path) -> None:
    """Write threshold analysis as markdown."""
    ti = result.stats.threshold_impact

    lines = [
        f"# Threshold Impact Analysis",
        f"**File**: {result.stats.tasks_file}",
        f"**Analyzed**: {result.stats.timestamp}",
        f"**Current Thresholds**: Complexity ≤ {result.thresholds_used.get('complexity', 5)}, Context ≤ {result.thresholds_used.get('context_tokens', 100000):,} tokens",
        "",
    ]

    if ti.complexity_thresholds:
        lines.extend([
            "## Complexity Threshold Sweep (Context fixed at 100k)",
            "",
            "| Threshold | Delegable | Precision | Recall | F1 | FP | FN | Avg Complexity | Avg Context |",
            "|-----------|-----------|-----------|--------|-----|----|----|----------------|-------------|",
        ])

        for thresh in sorted(ti.complexity_thresholds.keys()):
            m = ti.complexity_thresholds[thresh]
            prec = f"{m.precision:.2f}" if m.precision is not None else "N/A"
            rec = f"{m.recall:.2f}" if m.recall is not None else "N/A"
            f1 = f"{m.f1:.2f}" if m.f1 is not None else "N/A"
            lines.append(
                f"| {thresh} | {m.delegable_count} | {prec} | {rec} | {f1} | "
                f"{m.false_positives} | {m.false_negatives} | "
                f"{m.avg_complexity_delegable:.1f} | {m.avg_context_tokens_delegable:,.0f} |"
            )

        lines.append("")

    if ti.context_thresholds:
        lines.extend([
            "## Context Threshold Sweep (Complexity fixed at 5)",
            "",
            "| Threshold | Delegable | Precision | Recall | F1 | FP | FN | Avg Complexity | Avg Context |",
            "|-----------|-----------|-----------|--------|-----|----|----|----------------|-------------|",
        ])

        for thresh in sorted(ti.context_thresholds.keys()):
            m = ti.context_thresholds[thresh]
            prec = f"{m.precision:.2f}" if m.precision is not None else "N/A"
            rec = f"{m.recall:.2f}" if m.recall is not None else "N/A"
            f1 = f"{m.f1:.2f}" if m.f1 is not None else "N/A"
            lines.append(
                f"| {thresh:,} | {m.delegable_count} | {prec} | {rec} | {f1} | "
                f"{m.false_positives} | {m.false_negatives} | "
                f"{m.avg_complexity_delegable:.1f} | {m.avg_context_tokens_delegable:,.0f} |"
            )

        lines.append("")

    if ti.combined_thresholds:
        lines.extend([
            "## Combined Threshold Sweep",
            "",
            "| Complexity | Context | Delegable | Precision | Recall | F1 |",
            "|------------|---------|-----------|-----------|--------|-----|",
        ])

        for (c_thresh, ctx_thresh), m in sorted(ti.combined_thresholds.items()):
            prec = f"{m.precision:.2f}" if m.precision is not None else "N/A"
            rec = f"{m.recall:.2f}" if m.recall is not None else "N/A"
            f1 = f"{m.f1:.2f}" if m.f1 is not None else "N/A"
            lines.append(
                f"| {c_thresh} | {ctx_thresh:,} | {m.delegable_count} | {prec} | {rec} | {f1} |"
            )

    lines.extend([
        "## Recommendation",
        "",
        f"- **Current F1**: {ti.complexity_thresholds.get(result.thresholds_used.get('complexity', 5), ThresholdMetrics()).f1 if ti.complexity_thresholds.get(result.thresholds_used.get('complexity', 5), ThresholdMetrics()).f1 is not None else 'N/A'}",
        f"- **Optimal Complexity Threshold**: {find_optimal_threshold(ti.complexity_thresholds, 'f1')}",
        f"- **Optimal Context Threshold**: {find_optimal_threshold(ti.context_thresholds, 'f1')}",
    ])

    filepath.write_text('\n'.join(lines))


def write_threshold_analysis_csv(result: AnalysisResult, filepath: Path) -> None:
    """Write threshold analysis as CSV."""
    ti = result.stats.threshold_impact

    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "threshold_type", "threshold_value", "delegable_count",
            "precision", "recall", "f1", "false_positives", "false_negatives",
            "avg_complexity_delegable", "avg_context_delegable"
        ])

        for thresh, m in sorted(ti.complexity_thresholds.items()):
            writer.writerow([
                "complexity", thresh, m.delegable_count,
                m.precision, m.recall, m.f1,
                m.false_positives, m.false_negatives,
                m.avg_complexity_delegable, m.avg_context_tokens_delegable
            ])

        for thresh, m in sorted(ti.context_thresholds.items()):
            writer.writerow([
                "context", thresh, m.delegable_count,
                m.precision, m.recall, m.f1,
                m.false_positives, m.false_negatives,
                m.avg_complexity_delegable, m.avg_context_tokens_delegable
            ])

        for (c_thresh, ctx_thresh), m in sorted(ti.combined_thresholds.items()):
            writer.writerow([
                "combined", f"{c_thresh},{ctx_thresh}", m.delegable_count,
                m.precision, m.recall, m.f1,
                m.false_positives, m.false_negatives,
                m.avg_complexity_delegable, m.avg_context_tokens_delegable
            ])


def find_optimal_threshold(thresholds: dict, objective: str = "f1") -> str:
    """Find optimal threshold for given objective."""
    if not thresholds:
        return "N/A"

    best = max(thresholds.items(), key=lambda x: getattr(x[1], objective, 0) or 0)
    return str(best[0])


def compute_threshold_impact(
    result: AnalysisResult,
    ground_truth: Optional[dict] = None
) -> None:
    """Compute threshold impact metrics for all thresholds."""
    from ..parser.models import ThresholdMetrics, ThresholdImpact

    tasks_with_scores = [t for t in result.tasks if t.score]

    if not tasks_with_scores:
        return

    complexity_range = range(1, 11)
    context_range = [25000, 50000, 75000, 100000, 150000, 200000, 300000]

    complexity_metrics = {}
    for c_thresh in complexity_range:
        delegable = [t for t in tasks_with_scores
                     if t.score.complexity <= c_thresh
                     and t.score.context_tokens <= result.thresholds_used.get("context_tokens", 100000)]
        metrics = compute_metrics(delegable, tasks_with_scores, ground_truth, c_thresh, "complexity")
        complexity_metrics[c_thresh] = metrics

    context_metrics = {}
    for ctx_thresh in context_range:
        delegable = [t for t in tasks_with_scores
                     if t.score.complexity <= result.thresholds_used.get("complexity", 5)
                     and t.score.context_tokens <= ctx_thresh]
        metrics = compute_metrics(delegable, tasks_with_scores, ground_truth, ctx_thresh, "context")
        context_metrics[ctx_thresh] = metrics

    combined_metrics = {}
    for c_thresh in [3, 4, 5, 6, 7]:
        for ctx_thresh in [50000, 80000, 100000, 150000]:
            delegable = [t for t in tasks_with_scores
                         if t.score.complexity <= c_thresh
                         and t.score.context_tokens <= ctx_thresh]
            metrics = compute_metrics(delegable, tasks_with_scores, ground_truth, (c_thresh, ctx_thresh), "combined")
            combined_metrics[(c_thresh, ctx_thresh)] = metrics

    result.stats.threshold_impact = ThresholdImpact(
        complexity_thresholds=complexity_metrics,
        context_thresholds=context_metrics,
        combined_thresholds=combined_metrics
    )


def compute_metrics(
    delegable: list,
    all_tasks: list,
    ground_truth: Optional[dict],
    threshold_key,
    threshold_type: str
) -> ThresholdMetrics:
    """Compute precision, recall, F1 for a threshold."""
    delegable_count = len(delegable)

    avg_complexity = sum(t.score.complexity for t in delegable) / max(delegable_count, 1)
    avg_context = sum(t.score.context_tokens for t in delegable) / max(delegable_count, 1)

    if not ground_truth:
        return ThresholdMetrics(
            delegable_count=delegable_count,
            avg_complexity_delegable=avg_complexity,
            avg_context_tokens_delegable=avg_context
        )

    tp = fp = fn = 0
    for task in all_tasks:
        is_delegable = task in delegable
        actual_simple = ground_truth.get(task.id, {}).get("actual_complexity", 10) <= 5

        if is_delegable and actual_simple:
            tp += 1
        elif is_delegable and not actual_simple:
            fp += 1
        elif not is_delegable and actual_simple:
            fn += 1

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 0.001)

    return ThresholdMetrics(
        delegable_count=delegable_count,
        precision=precision,
        recall=recall,
        f1=f1,
        false_positives=fp,
        false_negatives=fn,
        avg_complexity_delegable=avg_complexity,
        avg_context_tokens_delegable=avg_context
    )