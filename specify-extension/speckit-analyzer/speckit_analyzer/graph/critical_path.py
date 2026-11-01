"""Critical path analysis for task scheduling."""

import networkx as nx
from typing import Optional
from dataclasses import dataclass, field

from ..parser.models import Task, DependencyGraph, CriticalPathAnalysis, ParallelOpportunity
from .builder import get_upstream, get_downstream, topological_sort


def compute_critical_path(graph: DependencyGraph) -> CriticalPathAnalysis:
    """Compute critical path using longest path in DAG weighted by estimate_days."""
    G = nx.DiGraph()
    for task_id, task in graph.nodes.items():
        G.add_node(task_id, weight=task.estimate_days)
    G.add_edges_from(graph.edges)

    try:
        topo_order = topological_sort(graph)
        if not topo_order:
            return CriticalPathAnalysis()

        dist = {node: 0.0 for node in G.nodes()}
        prev = {node: None for node in G.nodes()}

        for node in topo_order:
            node_weight = graph.nodes[node].estimate_days
            for succ in G.successors(node):
                if dist[node] + node_weight > dist[succ]:
                    dist[succ] = dist[node] + node_weight
                    prev[succ] = node

        end_node = max(dist, key=dist.get)
        path = []
        current = end_node
        while current is not None:
            path.append(current)
            current = prev[current]
        path.reverse()

        total_days = sum(graph.nodes[n].estimate_days for n in path)

        bottleneck_tasks = []
        for task_id, task in graph.nodes.items():
            downstream = get_downstream(graph, task_id)
            if len(downstream) > 3:
                bottleneck_tasks.append(task_id)

        parallel_ops = find_parallel_groups(graph)

        return CriticalPathAnalysis(
            path=path,
            total_days=total_days,
            parallelizable_days=sum(op.estimated_days_saved for op in parallel_ops),
            bottleneck_tasks=bottleneck_tasks,
            parallelization_opportunities=parallel_ops
        )
    except Exception:
        return CriticalPathAnalysis()


def find_parallel_groups(graph: DependencyGraph) -> list[ParallelOpportunity]:
    """Find tasks that can run in parallel within each phase."""
    opportunities = []

    phases = {}
    for task in graph.nodes.values():
        if task.phase not in phases:
            phases[task.phase] = []
        phases[task.phase].append(task)

    for phase_num, phase_tasks in phases.items():
        if len(phase_tasks) < 2:
            continue

        parallelizable = []
        for task in phase_tasks:
            upstream_in_phase = [
                u for u in get_upstream(graph, task.id)
                if u in [t.id for t in phase_tasks]
            ]
            if not upstream_in_phase:
                parallelizable.append(task)

        if len(parallelizable) >= 2:
            task_ids = [t.id for t in parallelizable]
            total_days = sum(t.estimate_days for t in parallelizable)
            max_days = max(t.estimate_days for t in parallelizable)
            saved = total_days - max_days

            risk = "low"
            if any(t.priority.value == "High" for t in parallelizable):
                risk = "medium"
            if len(parallelizable) > 4:
                risk = "high"

            opportunities.append(ParallelOpportunity(
                phase=phase_num,
                tasks=task_ids,
                estimated_days_saved=saved,
                risk=risk
            ))

    return opportunities


def compute_critical_path_weights(graph: DependencyGraph) -> dict[str, float]:
    """Compute critical path weight for each task (how much it affects total duration)."""
    G = nx.DiGraph()
    for task_id, task in graph.nodes.items():
        G.add_node(task_id, weight=task.estimate_days)
    G.add_edges_from(graph.edges)

    topo_order = topological_sort(graph)

    forward = {node: 0.0 for node in G.nodes()}
    for node in topo_order:
        node_weight = graph.nodes[node].estimate_days
        for succ in G.successors(node):
            forward[succ] = max(forward[succ], forward[node] + node_weight)

    backward = {node: 0.0 for node in G.nodes()}
    reverse_topo = list(reversed(topo_order))
    for node in reverse_topo:
        node_weight = graph.nodes[node].estimate_days
        for pred in G.predecessors(node):
            backward[pred] = max(backward[pred], backward[node] + node_weight)

    total_duration = max(forward.values()) if forward else 0.0

    weights = {}
    for node in G.nodes():
        weights[node] = (forward[node] + backward[node] + graph.nodes[node].estimate_days) / max(total_duration, 1.0)

    return weights