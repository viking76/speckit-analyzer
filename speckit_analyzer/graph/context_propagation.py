"""Context propagation up and down the dependency graph."""

from ..parser.models import Task, DependencyGraph
from .builder import get_upstream, get_downstream, get_direct_upstream, get_direct_downstream


def propagate_context(graph: DependencyGraph, project_root, max_depth: int = 3) -> None:
    """Propagate context information up and down the dependency graph."""
    for task in graph.nodes.values():
        upstream_files = collect_upstream_context(task, graph, project_root, max_depth)
        downstream_impact = collect_downstream_impact(task, graph, max_depth)
        task.upstream_context = upstream_files
        task.downstream_impact = downstream_impact


def collect_upstream_context(task: Task, graph: DependencyGraph, project_root, max_depth: int) -> list[str]:
    """Collect files from upstream dependencies that provide context."""
    files = set()
    visited = set()
    queue = [(dep_id, 0) for dep_id in get_direct_upstream(graph, task.id)]

    while queue:
        dep_id, depth = queue.pop(0)
        if depth >= max_depth or dep_id in visited:
            continue
        visited.add(dep_id)

        if dep_id in graph.nodes:
            dep_task = graph.nodes[dep_id]
            impl_files = get_implementation_files(dep_task, project_root)
            files.update(str(f.relative_to(project_root)) for f in impl_files)

            for upstream_dep in get_direct_upstream(graph, dep_id):
                queue.append((upstream_dep, depth + 1))

    return sorted(files)


def collect_downstream_impact(task: Task, graph: DependencyGraph, max_depth: int) -> list[str]:
    """Collect tasks that depend on this task (downstream impact)."""
    impact = set()
    visited = set()
    queue = [(dep_id, 0) for dep_id in get_direct_downstream(graph, task.id)]

    while queue:
        dep_id, depth = queue.pop(0)
        if depth >= max_depth or dep_id in visited:
            continue
        visited.add(dep_id)
        impact.add(dep_id)

        for downstream_dep in get_direct_downstream(graph, dep_id):
            queue.append((downstream_dep, depth + 1))

    return sorted(impact)


def get_implementation_files(task: Task, project_root) -> list:
    """Get implementation files for a task."""
    from pathlib import Path
    files = []
    if task.implementation_path:
        path = project_root / task.implementation_path
        if path.exists():
            if path.is_file():
                files.append(path)
            elif path.is_dir():
                files.extend(path.rglob("*.py"))
    return files


def compute_upstream_downstream(graph: DependencyGraph) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Compute upstream and downstream for all tasks."""
    upstream_map = {}
    downstream_map = {}

    for task_id in graph.nodes:
        upstream_map[task_id] = get_upstream(graph, task_id)
        downstream_map[task_id] = get_downstream(graph, task_id)

    return upstream_map, downstream_map