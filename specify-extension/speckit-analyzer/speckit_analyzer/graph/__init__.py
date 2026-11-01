"""Graph analysis package for dependency graphs."""

from .builder import build_dependency_graph, topological_sort, detect_cycles
from .critical_path import compute_critical_path, find_parallel_groups, CriticalPathAnalysis, ParallelOpportunity
from .context_propagation import propagate_context, compute_upstream_downstream

__all__ = [
    "build_dependency_graph",
    "topological_sort",
    "detect_cycles",
    "compute_critical_path",
    "find_parallel_groups",
    "CriticalPathAnalysis",
    "ParallelOpportunity",
    "propagate_context",
    "compute_upstream_downstream",
]