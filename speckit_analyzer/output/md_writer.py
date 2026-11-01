"""Markdown report writers for analysis results."""

from pathlib import Path
from typing import Optional

from ..parser.models import AnalysisResult


def write_markdown_reports(result: AnalysisResult, output_dir: Path) -> None:
    """Write all markdown reports."""
    output_dir.mkdir(parents=True, exist_ok=True)

    write_task_tree(result, output_dir / "task_tree.md")
    write_task_list_csv(result, output_dir / "task_list.csv")
    write_critical_path(result, output_dir / "critical_path.md")
    write_delegation_packages_index(result, output_dir / "delegation_packages" / "index.md")


def write_task_tree(result: AnalysisResult, filepath: Path) -> None:
    """Write visual task tree with scores."""
    lines = [
        f"# Task Tree Analysis",
        f"**File**: {result.stats.tasks_file}",
        f"**Analyzed**: {result.stats.timestamp}",
        f"**Thresholds**: Complexity ≤ {result.thresholds_used.get('complexity', 5)}, Context ≤ {result.thresholds_used.get('context_tokens', 100000):,} tokens",
        "",
        "## Tasks by Phase",
        "",
    ]

    phases = {}
    for task in result.tasks:
        if task.phase not in phases:
            phases[task.phase] = []
        phases[task.phase].append(task)

    for phase_num in sorted(phases.keys()):
        lines.append(f"### Phase {phase_num}")
        lines.append("")

        for task in sorted(phases[phase_num], key=lambda t: t.id):
            score_str = ""
            if task.score:
                score_str = f" [C:{task.score.complexity} LOC:{task.score.est_loc:,} CTX:{task.score.context_tokens:,}]"

            delegable_str = " 🎯" if task.delegable else ""
            status_str = f" ({task.status.value})" if task.status.value != "PENDING" else ""

            deps_str = f" → {', '.join(task.dependencies)}" if task.dependencies else ""
            lines.append(f"- **{task.id}**: {task.description}{score_str}{delegable_str}{status_str}{deps_str}")

        lines.append("")

    if result.graph.critical_path:
        lines.extend([
            "## Critical Path",
            "",
            " → ".join(result.graph.critical_path),
            f"**Total Duration**: {result.critical_path_analysis.total_days:.1f} days",
            "",
        ])

    if result.critical_path_analysis.parallelization_opportunities:
        lines.extend(["## Parallelization Opportunities", ""])
        for op in result.critical_path_analysis.parallelization_opportunities:
            lines.append(f"- **Phase {op.phase}**: {', '.join(op.tasks)} (save ~{op.estimated_days_saved:.1f} days, risk: {op.risk})")
        lines.append("")

    filepath.write_text('\n'.join(lines))


def write_task_list_csv(result: AnalysisResult, filepath: Path) -> None:
    """Write task list as CSV."""
    import csv

    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "phase", "module", "priority", "estimate_days",
            "status", "dependencies", "parallel", "user_story",
            "complexity", "est_loc", "context_tokens", "delegable",
            "context_package", "upstream_context", "downstream_impact"
        ])

        for task in sorted(result.tasks, key=lambda t: t.id):
            score = task.score
            writer.writerow([
                task.id,
                task.phase,
                task.module,
                task.priority.value,
                task.estimate_days,
                task.status.value,
                ";".join(task.dependencies),
                task.parallel,
                task.user_story or "",
                score.complexity if score else "",
                score.est_loc if score else "",
                score.context_tokens if score else "",
                task.delegable,
                task.context_package_path or "",
                ";".join(task.upstream_context),
                ";".join(task.downstream_impact),
            ])


def write_critical_path(result: AnalysisResult, filepath: Path) -> None:
    """Write critical path analysis."""
    cp = result.critical_path_analysis

    lines = [
        f"# Critical Path Analysis",
        f"**File**: {result.stats.tasks_file}",
        f"**Analyzed**: {result.stats.timestamp}",
        "",
        f"## Critical Path",
        "",
        " → ".join(cp.path) if cp.path else "No critical path found",
        "",
        f"**Total Duration**: {cp.total_days:.1f} days",
        f"**Parallelizable Days**: {cp.parallelizable_days:.1f} days",
        f"**Effective Duration (with parallelization)**: {cp.total_days - cp.parallelizable_days:.1f} days",
        "",
        "## Bottleneck Tasks",
        "",
    ]

    if cp.bottleneck_tasks:
        for bt in cp.bottleneck_tasks:
            lines.append(f"- {bt} (downstream dependents > 3)")
    else:
        lines.append("No significant bottlenecks detected.")

    lines.extend(["", "## Parallelization Opportunities", ""])

    if cp.parallelization_opportunities:
        for op in cp.parallelization_opportunities:
            lines.append(f"### Phase {op.phase} (Risk: {op.risk})")
            lines.append(f"**Tasks**: {', '.join(op.tasks)}")
            lines.append(f"**Estimated Days Saved**: {op.estimated_days_saved:.1f}")
            lines.append("")
    else:
        lines.append("No parallelization opportunities found.")

    filepath.write_text('\n'.join(lines))


def write_delegation_packages_index(result: AnalysisResult, filepath: Path) -> None:
    """Write index of delegation packages."""
    filepath.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Delegation Packages Index",
        f"**Generated**: {result.stats.timestamp}",
        f"**Thresholds**: Complexity ≤ {result.thresholds_used.get('complexity', 5)}, Context ≤ {result.thresholds_used.get('context_tokens', 100000):,} tokens",
        "",
        f"## Summary",
        f"- **Total Tasks**: {result.delegation_summary.total_tasks}",
        f"- **Delegable**: {result.delegation_summary.delegable}",
        f"- **Non-Delegable (Complexity)**: {result.delegation_summary.non_delegable_complexity}",
        f"- **Non-Delegable (Context)**: {result.delegation_summary.non_delegable_context}",
        f"- **Non-Delegable (Both)**: {result.delegation_summary.non_delegable_both}",
        "",
        "## Packages",
        "",
    ]

    delegable_tasks = [t for t in result.tasks if t.delegable and t.context_package_path]
    for task in sorted(delegable_tasks, key=lambda t: t.id):
        score = task.score
        lines.append(f"- **{task.id}**: `{task.context_package_path}/` (C:{score.complexity}, LOC:{score.est_loc:,}, CTX:{score.context_tokens:,})")

    filepath.write_text('\n'.join(lines))