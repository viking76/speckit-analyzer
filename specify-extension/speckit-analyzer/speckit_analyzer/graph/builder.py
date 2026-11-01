"""Dependency graph builder and topological operations."""

import networkx as nx
from typing import Optional

from ..parser.models import Task, DependencyGraph
from ..parser.speckit_parser import parse_mermaid_edges


def build_dependency_graph(tasks: list[Task], mermaid_raw: Optional[str] = None) -> DependencyGraph:
    """Build dependency graph from tasks and optional mermaid."""
    graph = DependencyGraph()
    graph.nodes = {t.id: t for t in tasks}

    edges = set()
    for task in tasks:
        for dep in task.dependencies:
            edges.add((dep, task.id))

    if mermaid_raw:
        mermaid_edges = parse_mermaid_edges(mermaid_raw)
        for from_id, to_id in mermaid_edges:
            if from_id in graph.nodes and to_id in graph.nodes:
                edges.add((from_id, to_id))

    graph.edges = list(edges)
    graph.mermaid_raw = mermaid_raw

    graph.topological_order = topological_sort(graph)
    graph.cycles = detect_cycles(graph)

    return graph


def topological_sort(graph: DependencyGraph) -> list[str]:
    """Return topological order of tasks."""
    G = nx.DiGraph()
    G.add_nodes_from(graph.nodes.keys())
    G.add_edges_from(graph.edges)

    try:
        return list(nx.topological_sort(G))
    except nx.NetworkXUnfeasible:
        return list(graph.nodes.keys())


def detect_cycles(graph: DependencyGraph) -> list[list[str]]:
    """Detect cycles in the dependency graph."""
    G = nx.DiGraph()
    G.add_nodes_from(graph.nodes.keys())
    G.add_edges_from(graph.edges)

    try:
        cycles = list(nx.simple_cycles(G))
        return [list(c) for c in cycles]
    except Exception:
        return []


def get_upstream(graph: DependencyGraph, task_id: str) -> list[str]:
    """Get all upstream dependencies (transitive)."""
    G = nx.DiGraph()
    G.add_nodes_from(graph.nodes.keys())
    G.add_edges_from(graph.edges)

    try:
        return list(nx.ancestors(G, task_id))
    except Exception:
        return []


def get_downstream(graph: DependencyGraph, task_id: str) -> list[str]:
    """Get all downstream dependents (transitive)."""
    G = nx.DiGraph()
    G.add_nodes_from(graph.nodes.keys())
    G.add_edges_from(graph.edges)

    try:
        return list(nx.descendants(G, task_id))
    except Exception:
        return []


def get_direct_upstream(graph: DependencyGraph, task_id: str) -> list[str]:
    """Get direct upstream dependencies."""
    return [u for u, v in graph.edges if v == task_id]


def get_direct_downstream(graph: DependencyGraph, task_id: str) -> list[str]:
    """Get direct downstream dependents."""
    return [v for u, v in graph.edges if u == task_id]