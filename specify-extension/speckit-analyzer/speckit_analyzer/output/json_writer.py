"""JSON output writer for analysis results."""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from ..parser.models import AnalysisResult, Task, TaskScore, DependencyGraph


def write_json(result: AnalysisResult, filepath: Path, indent: int = 2) -> None:
    """Write analysis result as JSON."""
    data = serialize_result(result)
    filepath.write_text(json.dumps(data, indent=indent, default=str))


def write_json_stream(result: AnalysisResult) -> str:
    """Return analysis result as JSON string."""
    data = serialize_result(result)
    return json.dumps(data, indent=2, default=str)


def serialize_result(result: AnalysisResult) -> dict:
    """Serialize AnalysisResult to dict."""
    return {
        "meta": {
            "analyzed_at": result.stats.timestamp,
            "tasks_file": result.stats.tasks_file,
            "version": "0.1.0",
            "thresholds": result.thresholds_used,
        },
        "tasks": [serialize_task(t) for t in result.tasks],
        "graph": serialize_graph(result.graph),
        "critical_path": serialize_critical_path(result.critical_path_analysis),
        "delegation_summary": serialize_delegation_summary(result.delegation_summary),
        "stats": serialize_stats(result.stats),
    }


def serialize_task(task: Task) -> dict:
    """Serialize Task to dict."""
    return {
        "id": task.id,
        "phase": task.phase,
        "module": task.module,
        "priority": task.priority.value,
        "dependencies": task.dependencies,
        "estimate_days": task.estimate_days,
        "description": task.description,
        "acceptance_criteria": task.acceptance_criteria,
        "status": task.status.value,
        "implementation_path": task.implementation_path,
        "parallel": task.parallel,
        "user_story": task.user_story,
        "score": serialize_score(task.score) if task.score else None,
        "upstream_context": task.upstream_context,
        "downstream_impact": task.downstream_impact,
        "critical_path_weight": task.critical_path_weight,
        "delegable": task.delegable,
        "context_package_path": task.context_package_path,
    }


def serialize_score(score: TaskScore) -> dict:
    """Serialize TaskScore to dict."""
    return {
        "complexity": score.complexity,
        "est_loc": score.est_loc,
        "context_tokens": score.context_tokens,
        "confidence": score.confidence,
        "complexity_breakdown": score.complexity_breakdown,
        "loc_breakdown": score.loc_breakdown,
        "context_breakdown": score.context_breakdown,
    }


def serialize_graph(graph: DependencyGraph) -> dict:
    """Serialize DependencyGraph to dict."""
    return {
        "nodes": list(graph.nodes.keys()),
        "edges": graph.edges,
        "topological_order": graph.topological_order,
        "critical_path": graph.critical_path,
        "parallel_groups": graph.parallel_groups,
        "cycles": graph.cycles,
    }


def serialize_critical_path(cp: "CriticalPathAnalysis") -> dict:
    """Serialize CriticalPathAnalysis to dict."""
    from ..parser.models import CriticalPathAnalysis
    return {
        "path": cp.path,
        "total_days": cp.total_days,
        "parallelizable_days": cp.parallelizable_days,
        "bottleneck_tasks": cp.bottleneck_tasks,
        "parallelization_opportunities": [
            {
                "phase": op.phase,
                "tasks": op.tasks,
                "estimated_days_saved": op.estimated_days_saved,
                "risk": op.risk,
            }
            for op in cp.parallelization_opportunities
        ],
    }


def serialize_delegation_summary(ds) -> dict:
    """Serialize DelegationSummary to dict."""
    return {
        "total_tasks": ds.total_tasks,
        "delegable": ds.delegable,
        "non_delegable_complexity": ds.non_delegable_complexity,
        "non_delegable_context": ds.non_delegable_context,
        "non_delegable_both": ds.non_delegable_both,
        "delegable_by_phase": ds.delegable_by_phase,
        "delegable_by_module": ds.delegable_by_module,
        "delegable_by_priority": ds.delegable_by_priority,
    }


def serialize_stats(stats) -> dict:
    """Serialize AnalysisStats to dict."""
    return {
        "timestamp": stats.timestamp,
        "tasks_file": stats.tasks_file,
        "total_tasks": stats.total_tasks,
        "completed_tasks": stats.completed_tasks,
        "completion_rate": stats.completion_rate,
        "complexity_distribution": stats.complexity_distribution,
        "loc_distribution": stats.loc_distribution,
        "context_distribution": stats.context_distribution,
        "complexity_vs_actual_loc": stats.complexity_vs_actual_loc,
        "estimate_vs_actual_days": stats.estimate_vs_actual_days,
        "context_vs_actual_tokens": stats.context_vs_actual_tokens,
        "threshold_impact": serialize_threshold_impact(stats.threshold_impact),
    }


def serialize_threshold_impact(ti) -> dict:
    """Serialize ThresholdImpact to dict."""
    return {
        "complexity_thresholds": {
            str(k): serialize_threshold_metrics(v)
            for k, v in ti.complexity_thresholds.items()
        },
        "context_thresholds": {
            str(k): serialize_threshold_metrics(v)
            for k, v in ti.context_thresholds.items()
        },
        "combined_thresholds": {
            f"{k[0]},{k[1]}": serialize_threshold_metrics(v)
            for k, v in ti.combined_thresholds.items()
        },
    }


def serialize_threshold_metrics(tm) -> dict:
    """Serialize ThresholdMetrics to dict."""
    return {
        "delegable_count": tm.delegable_count,
        "precision": tm.precision,
        "recall": tm.recall,
        "f1": tm.f1,
        "false_positives": tm.false_positives,
        "false_negatives": tm.false_negatives,
        "avg_context_tokens_delegable": tm.avg_context_tokens_delegable,
        "avg_complexity_delegable": tm.avg_complexity_delegable,
    }