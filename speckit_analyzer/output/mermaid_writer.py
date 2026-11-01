"""Mermaid graph writer for dependency visualization."""

from pathlib import Path
from typing import Optional

from ..parser.models import AnalysisResult


def write_mermaid_graph(result: AnalysisResult, filepath: Path) -> None:
    """Write enhanced Mermaid graph with scores and delegation info."""
    filepath.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "```mermaid",
        "graph TD",
        "",
    ]

    for task in result.tasks:
        if not task.score:
            continue

        color = get_task_color(task)
        shape = "rect" if not task.delegable else "rounded"
        label = f"{task.id}\\nC:{task.score.complexity} L:{task.score.est_loc//100}k CTX:{task.score.context_tokens//1000}k"

        if task.delegable:
            label += "\\n🎯 DELEGABLE"

        lines.append(f'    {task.id}["{label}"]:::task_{color}')

    lines.append("")

    for from_id, to_id in result.graph.edges:
        if from_id in result.graph.nodes and to_id in result.graph.nodes:
            lines.append(f"    {from_id} --> {to_id}")

    lines.extend([
        "",
        "    classDef task_green fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;",
        "    classDef task_yellow fill:#fff8e1,stroke:#f57f17,stroke-width:2px;",
        "    classDef task_red fill:#ffebee,stroke:#c62828,stroke-width:2px;",
        "    classDef task_blue fill:#e3f2fd,stroke:#1565c0,stroke-width:2px;",
        "```",
    ])

    filepath.write_text('\n'.join(lines))


def get_task_color(task) -> str:
    """Get color class for task based on score and delegability."""
    if not task.score:
        return "blue"

    if task.delegable:
        return "green"

    complexity = task.score.complexity
    context = task.score.context_tokens

    if complexity > 7 or context > 200000:
        return "red"
    elif complexity > 5 or context > 100000:
        return "yellow"
    else:
        return "blue"


def write_mermaid_phases(result: AnalysisResult, filepath: Path) -> None:
    """Write Mermaid graph grouped by phases."""
    filepath.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "```mermaid",
        "graph TD",
        "",
    ]

    phases = {}
    for task in result.tasks:
        if task.phase not in phases:
            phases[task.phase] = []
        phases[task.phase].append(task)

    for phase_num in sorted(phases.keys()):
        lines.append(f"    subgraph Phase_{phase_num}[Phase {phase_num}]")
        for task in sorted(phases[phase_num], key=lambda t: t.id):
            color = get_task_color(task)
            label = f"{task.id}\\nC:{task.score.complexity if task.score else '?'} L:{task.score.est_loc//100 if task.score else '?'}k CTX:{task.score.context_tokens//1000 if task.score else '?'}k"
            if task.delegable:
                label += "\\n🎯"
            lines.append(f'        {task.id}["{label}"]:::task_{color}')
        lines.append("    end")
        lines.append("")

    for from_id, to_id in result.graph.edges:
        if from_id in result.graph.nodes and to_id in result.graph.nodes:
            lines.append(f"    {from_id} --> {to_id}")

    lines.extend([
        "",
        "    classDef task_green fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;",
        "    classDef task_yellow fill:#fff8e1,stroke:#f57f17,stroke-width:2px;",
        "    classDef task_red fill:#ffebee,stroke:#c62828,stroke-width:2px;",
        "    classDef task_blue fill:#e3f2fd,stroke:#1565c0,stroke-width:2px;",
        "```",
    ])

    filepath.write_text('\n'.join(lines))