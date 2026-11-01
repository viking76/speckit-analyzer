"""Package delegation context for small LLMs."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json

from ..parser.models import Task, DependencyGraph
from .minimizer import MinimalContext, minimize_context


@dataclass
class DelegationPackage:
    task_id: str
    context: MinimalContext
    metadata: dict = field(default_factory=dict)
    package_path: Optional[Path] = None


def package_delegation_context(
    task: Task,
    graph: DependencyGraph,
    project_root: Path,
    output_dir: Path,
    max_tokens: int = 100000
) -> DelegationPackage:
    """Create a delegation package for a task."""
    context = minimize_context(task, graph, project_root, max_tokens)

    package_dir = output_dir / f"delegation_package" / task.id
    package_dir.mkdir(parents=True, exist_ok=True)

    context_file = package_dir / "context.md"
    interfaces_file = package_dir / "interfaces.json"
    refs_dir = package_dir / "refs"
    refs_dir.mkdir(exist_ok=True)

    write_context_markdown(context, context_file)
    write_interfaces_json(context, interfaces_file)
    write_reference_snippets(context, refs_dir)
    write_tests_markdown(context, package_dir / "tests.md")

    metadata = {
        "task_id": task.id,
        "phase": task.phase,
        "module": task.module,
        "priority": task.priority.value,
        "estimate_days": task.estimate_days,
        "complexity": task.score.complexity if task.score else 0,
        "est_loc": task.score.est_loc if task.score else 0,
        "context_tokens": context.total_tokens,
        "delegable": task.delegable,
        "dependencies": task.dependencies,
        "acceptance_criteria": task.acceptance_criteria,
        "upstream_context_files": task.upstream_context,
        "downstream_impact": task.downstream_impact,
    }

    metadata_file = package_dir / "metadata.json"
    metadata_file.write_text(json.dumps(metadata, indent=2))

    pkg = DelegationPackage(
        task_id=task.id,
        context=context,
        metadata=metadata,
        package_path=package_dir
    )

    return pkg


def write_context_markdown(context: MinimalContext, filepath: Path) -> None:
    """Write context as markdown."""
    lines = [
        f"# Delegation Context: {context.task_id}",
        "",
        "## Description",
        context.description,
        "",
        "## Acceptance Criteria",
    ]
    for i, crit in enumerate(context.acceptance_criteria, 1):
        lines.append(f"{i}. {crit}")

    if context.required_interfaces:
        lines.extend(["", "## Required Interfaces (from upstream)"])
        for name, sig in context.required_interfaces.items():
            lines.append(f"### {name}")
            lines.append(f"```python\n{sig}\n```")

    if context.shared_config:
        lines.extend(["", "## Shared Configuration"])
        for fname, content in context.shared_config.items():
            lines.append(f"### {fname}")
            lines.append(f"```\n{content[:1000]}\n```")

    lines.extend(["", f"## Total Estimated Tokens: {context.total_tokens}"])

    filepath.write_text('\n'.join(lines))


def write_interfaces_json(context: MinimalContext, filepath: Path) -> None:
    """Write interfaces as JSON."""
    data = {
        "task_id": context.task_id,
        "interfaces": context.required_interfaces
    }
    filepath.write_text(json.dumps(data, indent=2))


def write_reference_snippets(context: MinimalContext, refs_dir: Path) -> None:
    """Write reference snippets as individual files."""
    for i, snippet in enumerate(context.reference_snippets):
        snippet_file = refs_dir / f"ref_{i+1}_{Path(snippet['file']).stem}.py"
        content = f"# Source: {snippet['file']} (lines {snippet['lines']})\n# Relevance: {snippet['relevance']}\n# Tokens: {snippet['tokens']}\n\n{snippet['content']}"
        snippet_file.write_text(content)


def write_tests_markdown(context: MinimalContext, filepath: Path) -> None:
    """Write test patterns as markdown."""
    lines = [
        f"# Test Patterns for {context.task_id}",
        "",
        "## Expected Test Patterns",
    ]
    for pattern in context.test_patterns:
        lines.append(f"### Pattern")
        lines.append(f"```python\n{pattern}\n```")

    if not context.test_patterns:
        lines.append("No specific test patterns found. Follow project conventions.")

    filepath.write_text('\n'.join(lines))