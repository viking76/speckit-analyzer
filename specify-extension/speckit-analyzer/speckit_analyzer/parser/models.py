"""Core data models for speckit analyzer."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from pathlib import Path


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


class Priority(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass
class TaskScore:
    complexity: int = 1
    est_loc: int = 0
    context_tokens: int = 0
    confidence: float = 0.5
    complexity_breakdown: dict = field(default_factory=dict)
    loc_breakdown: dict = field(default_factory=dict)
    context_breakdown: dict = field(default_factory=dict)


@dataclass
class Task:
    id: str
    phase: int
    module: str
    priority: Priority
    dependencies: list[str] = field(default_factory=list)
    estimate_days: float = 1.0
    description: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    implementation_path: Optional[str] = None
    parallel: bool = False
    user_story: Optional[str] = None

    score: Optional[TaskScore] = None
    upstream_context: list[str] = field(default_factory=list)
    downstream_impact: list[str] = field(default_factory=list)
    critical_path_weight: float = 0.0
    delegable: bool = False
    context_package_path: Optional[str] = None


@dataclass
class DependencyGraph:
    nodes: dict[str, Task] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)
    mermaid_raw: Optional[str] = None

    topological_order: list[str] = field(default_factory=list)
    critical_path: list[str] = field(default_factory=list)
    parallel_groups: list[list[str]] = field(default_factory=list)
    cycles: list[list[str]] = field(default_factory=list)


@dataclass
class DelegationSummary:
    total_tasks: int = 0
    delegable: int = 0
    non_delegable_complexity: int = 0
    non_delegable_context: int = 0
    non_delegable_both: int = 0
    delegable_by_phase: dict[int, int] = field(default_factory=dict)
    delegable_by_module: dict[str, int] = field(default_factory=dict)
    delegable_by_priority: dict[str, int] = field(default_factory=dict)


@dataclass
class ParallelOpportunity:
    phase: int
    tasks: list[str] = field(default_factory=list)
    estimated_days_saved: float = 0.0
    risk: str = "medium"


@dataclass
class CriticalPathAnalysis:
    path: list[str] = field(default_factory=list)
    total_days: float = 0.0
    parallelizable_days: float = 0.0
    bottleneck_tasks: list[str] = field(default_factory=list)
    parallelization_opportunities: list[ParallelOpportunity] = field(default_factory=list)


@dataclass
class ThresholdMetrics:
    delegable_count: int = 0
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    false_positives: int = 0
    false_negatives: int = 0
    avg_context_tokens_delegable: float = 0.0
    avg_complexity_delegable: float = 0.0


@dataclass
class ThresholdImpact:
    complexity_thresholds: dict[int, ThresholdMetrics] = field(default_factory=dict)
    context_thresholds: dict[int, ThresholdMetrics] = field(default_factory=dict)
    combined_thresholds: dict[tuple[int, int], ThresholdMetrics] = field(default_factory=dict)


@dataclass
class AnalysisStats:
    timestamp: str = ""
    tasks_file: str = ""
    total_tasks: int = 0
    completed_tasks: int = 0
    completion_rate: float = 0.0

    complexity_distribution: dict[int, int] = field(default_factory=dict)
    loc_distribution: dict[str, int] = field(default_factory=dict)
    context_distribution: dict[str, int] = field(default_factory=dict)

    complexity_vs_actual_loc: Optional[float] = None
    estimate_vs_actual_days: Optional[float] = None
    context_vs_actual_tokens: Optional[float] = None

    threshold_impact: ThresholdImpact = field(default_factory=ThresholdImpact)


@dataclass
class AnalysisResult:
    tasks: list[Task] = field(default_factory=list)
    graph: DependencyGraph = field(default_factory=DependencyGraph)
    thresholds_used: dict = field(default_factory=dict)
    delegation_summary: DelegationSummary = field(default_factory=DelegationSummary)
    critical_path_analysis: CriticalPathAnalysis = field(default_factory=CriticalPathAnalysis)
    stats: AnalysisStats = field(default_factory=AnalysisStats)


@dataclass
class TaskActual:
    task_id: str
    actual_loc: int
    actual_complexity: int
    actual_context_tokens: int