"""CLI entry point for speckit analyzer."""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .parser import parse_tasks_file
from .parser.speckit_parser import build_dependency_graph
from .scoring import score_all_tasks, Calibrator, CalibrationWeights
from .graph import compute_critical_path, propagate_context
from .context import package_delegation_context
from .enricher import enrich_tasks_file
from .output import (
    write_json,
    write_markdown_reports,
    write_mermaid_graph,
    write_mermaid_phases,
    write_stats_csv,
    write_stats_parquet,
    write_threshold_analysis,
)
from .stats import StatsCollector, collect_analysis_stats
from .parser.models import AnalysisResult, ThresholdImpact

app = typer.Typer(name="speckit-analyze", help="Analyze speckit tasks.md for scoring, delegation, and dependency analysis")
console = Console()


@app.command()
def analyze(
    tasks_file: Path = typer.Argument(..., help="Path to tasks.md file"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory for analysis artifacts"),
    thresholds: str = typer.Option("complexity=3", "--threshold", "-t", help="Delegation threshold (complexity=3)"),
    calibrate: bool = typer.Option(False, "--calibrate", "-c", help="Calibrate from completed tasks"),
    enrich: bool = typer.Option(False, "--enrich", "-e", help="Enrich tasks.md with scores"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output JSON to stdout"),
    sweep: bool = typer.Option(False, "--sweep", "-s", help="Perform threshold sweep"),
    stats_history: bool = typer.Option(False, "--stats-history", help="Update stats history"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Analyze a tasks.md file."""
    if not tasks_file.exists():
        console.print(f"[red]Error: {tasks_file} not found[/red]")
        raise typer.Exit(1)

    project_root = tasks_file.parent.parent.parent
    console.print(f"[blue]Analyzing: {tasks_file}[/blue]")
    console.print(f"[blue]Project root: {project_root}[/blue]")

    threshold_dict = parse_thresholds(thresholds)
    console.print(f"[blue]Thresholds: {threshold_dict}[/blue]")

    tasks, mermaid_raw = parse_tasks_file(tasks_file)
    console.print(f"[green]Parsed {len(tasks)} tasks[/green]")

    graph = build_dependency_graph(tasks, mermaid_raw)
    console.print(f"[green]Built dependency graph with {len(graph.edges)} edges[/green]")

    if calibrate:
        calibrator = Calibrator(project_root)
        weights = calibrator.calibrate(tasks)
        console.print(f"[green]Calibrated weights: {len(weights.velocity_by_module)} modules[/green]")
        velocity_overrides = weights.velocity_by_module
    else:
        velocity_overrides = None

    score_all_tasks(tasks, graph, project_root, velocity_overrides)
    console.print(f"[green]Scored all tasks[/green]")

    # Set delegable flag based on complexity threshold only
    complexity_threshold = threshold_dict.get("complexity", 3)
    for task in tasks:
        if task.score:
            task.delegable = task.score.complexity <= complexity_threshold
            if task.delegable:
                task.context_package_path = f"analysis/delegation_package/{task.id}/"

    propagate_context(graph, project_root)
    console.print(f"[green]Propagated context[/green]")

    cp_analysis = compute_critical_path(graph)
    console.print(f"[green]Critical path: {' → '.join(cp_analysis.path[:5])}{'...' if len(cp_analysis.path) > 5 else ''}[/green]")

    result = build_analysis_result(tasks, graph, threshold_dict, cp_analysis, tasks_file)

    # Compute threshold impact for reporting
    from .stats.threshold_sweep import sweep_thresholds
    result.stats.threshold_impact = sweep_thresholds([t for t in tasks if t.score])

    collect_analysis_stats(result)
    write_threshold_analysis(result, output_dir or tasks_file.parent / "analysis")

    if sweep:
        console.print("[yellow]Performing threshold sweep...[/yellow]")
        # Already computed above

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(result, output_dir / "analysis.json")
        write_markdown_reports(result, output_dir)
        write_mermaid_graph(result, output_dir / "dependency_graph.mmd")
        write_mermaid_phases(result, output_dir / "dependency_graph_phases.mmd")
        write_stats_csv(result, output_dir / "stats_history.csv")
        write_stats_parquet(result, output_dir / "stats_history.parquet")

        delegable_tasks = [t for t in tasks if t.delegable]
        for task in delegable_tasks:
            package_delegation_context(task, graph, project_root, output_dir)
        console.print(f"[green]Created {len(delegable_tasks)} delegation packages[/green]")

        console.print(f"[green]Output written to {output_dir}[/green]")

    if enrich:
        enrich_tasks_file(tasks_file, result, threshold_dict)
        console.print(f"[green]Enriched {tasks_file} with scores[/green]")

    if stats_history:
        collector = StatsCollector()
        collector.add_run(result)
        console.print(f"[green]Updated stats history[/green]")

    if json_output:
        console.print_json(data=json.loads(write_json(result, Path("/dev/null"))))

    print_summary(result, threshold_dict)


def parse_thresholds(thresholds: str) -> dict:
    """Parse threshold string like 'complexity=5,context=100000'."""
    result = {}
    for part in thresholds.split(","):
        if "=" in part:
            k, v = part.split("=")
            result[k.strip()] = int(v.strip())
    return result


def build_analysis_result(
    tasks: list,
    graph,
    thresholds: dict,
    cp_analysis,
    tasks_file: Path
) -> AnalysisResult:
    """Build AnalysisResult from components."""
    from .parser.models import AnalysisResult, DelegationSummary, AnalysisStats

    delegable_tasks = [t for t in tasks if t.delegable]
    non_delegable = [t for t in tasks if not t.delegable]

    delegation_summary = DelegationSummary(
        total_tasks=len(tasks),
        delegable=len(delegable_tasks),
        non_delegable_complexity=sum(1 for t in non_delegable if t.score and t.score.complexity > thresholds.get("complexity", 3)),
    )

    for task in delegable_tasks:
        delegation_summary.delegable_by_phase[task.phase] = delegation_summary.delegable_by_phase.get(task.phase, 0) + 1
        delegation_summary.delegable_by_module[task.module] = delegation_summary.delegable_by_module.get(task.module, 0) + 1
        delegation_summary.delegable_by_priority[task.priority.value] = delegation_summary.delegable_by_priority.get(task.priority.value, 0) + 1

    stats = AnalysisStats(
        tasks_file=str(tasks_file),
    )

    return AnalysisResult(
        tasks=tasks,
        graph=graph,
        thresholds_used=thresholds,
        delegation_summary=delegation_summary,
        critical_path_analysis=cp_analysis,
        stats=stats,
    )


def print_summary(result: AnalysisResult, thresholds: dict) -> None:
    """Print analysis summary to console."""
    ds = result.delegation_summary
    cp = result.critical_path_analysis

    table = Table(title="Analysis Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Tasks", str(ds.total_tasks))
    table.add_row("Delegable", f"{ds.delegable} ({ds.delegable/max(ds.total_tasks,1)*100:.1f}%)")
    table.add_row("Non-Delegable (Complexity > 3)", str(ds.non_delegable_complexity))
    table.add_row("Critical Path Length", f"{cp.total_days:.1f} days")
    table.add_row("Parallelizable Days", f"{cp.parallelizable_days:.1f} days")
    table.add_row("Bottlenecks", str(len(cp.bottleneck_tasks)))

    console.print(table)

    if cp.parallelization_opportunities:
        opp_table = Table(title="Parallelization Opportunities")
        opp_table.add_column("Phase", style="cyan")
        opp_table.add_column("Tasks", style="green")
        opp_table.add_column("Days Saved", style="yellow")
        opp_table.add_column("Risk", style="red")

        for op in cp.parallelization_opportunities:
            opp_table.add_row(str(op.phase), ", ".join(op.tasks), f"{op.estimated_days_saved:.1f}", op.risk)

        console.print(opp_table)

    if ds.delegable > 0:
        console.print(Panel(
            f"[green]✅ {ds.delegable} tasks can be delegated to small LLMs[/green]\n"
            f"Delegation packages created in analysis/delegation_package/T###/",
            title="Delegation Ready"
        ))


@app.command()
def compare(
    file1: Path = typer.Argument(..., help="First analysis JSON"),
    file2: Path = typer.Argument(..., help="Second analysis JSON"),
):
    """Compare two analysis results."""
    with open(file1) as f:
        data1 = json.load(f)
    with open(file2) as f:
        data2 = json.load(f)

    console.print(f"[blue]Comparing {file1} vs {file2}[/blue]")

    tasks1 = {t["id"]: t for t in data1.get("tasks", [])}
    tasks2 = {t["id"]: t for t in data2.get("tasks", [])}

    all_ids = set(tasks1.keys()) | set(tasks2.keys())

    table = Table(title="Task Comparison")
    table.add_column("Task ID", style="cyan")
    table.add_column("Complexity Δ", style="yellow")
    table.add_column("LOC Δ", style="yellow")
    table.add_column("Context Δ", style="yellow")
    table.add_column("Delegable Δ", style="green")

    for tid in sorted(all_ids):
        t1 = tasks1.get(tid)
        t2 = tasks2.get(tid)

        if t1 and t2:
            s1 = t1.get("score", {})
            s2 = t2.get("score", {})
            c_delta = (s2.get("complexity", 0) - s1.get("complexity", 0))
            loc_delta = (s2.get("est_loc", 0) - s1.get("est_loc", 0))
            ctx_delta = (s2.get("context_tokens", 0) - s1.get("context_tokens", 0))
            d1 = t1.get("delegable", False)
            d2 = t2.get("delegable", False)
            d_delta = "✅→❌" if d1 and not d2 else "❌→✅" if not d1 and d2 else "→"

            table.add_row(tid, f"{c_delta:+d}", f"{loc_delta:+,}", f"{ctx_delta:+,}", d_delta)
        elif t1:
            table.add_row(tid, "REMOVED", "", "", "")
        else:
            table.add_row(tid, "ADDED", "", "", "")

    console.print(table)


if __name__ == "__main__":
    app()