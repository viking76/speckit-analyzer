"""Calibration from ground truth (completed tasks with actual implementation)."""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from scipy import stats
import numpy as np

from .heuristics import HeuristicScorer
from ..parser.models import Task, TaskActual, TaskStatus


@dataclass
class CalibrationWeights:
    velocity_by_module: dict[str, float] = field(default_factory=dict)
    pattern_factors: dict[str, float] = field(default_factory=dict)
    complexity_keyword_weights: dict[str, float] = field(default_factory=dict)
    correlations: dict[str, float] = field(default_factory=dict)

    @classmethod
    def default(cls) -> "CalibrationWeights":
        return cls(
            velocity_by_module={
                "trainer": 120, "model_manager": 100, "data_generator": 90,
                "parser": 80, "ui": 100, "cli": 110, "core": 90,
                "system": 70, "research": 30, "testing": 60, "docs": 40,
                "deployment": 50, "config": 150,
            },
            pattern_factors={
                "implement": 1.0, "create": 1.0, "add": 0.8,
                "refactor": 1.5, "optimize": 1.3, "improve": 1.2,
                "fix": 0.6, "debug": 0.5, "test": 0.6,
                "document": 0.3, "research": 0.2, "evaluate": 0.3,
                "configure": 0.4, "setup": 0.5, "integrate": 1.1,
            },
            complexity_keyword_weights={},
            correlations={}
        )


class Calibrator:
    def __init__(self, project_root: Path):
        self.project_root = project_root

    def calibrate(self, tasks: list[Task]) -> CalibrationWeights:
        completed = [
            t for t in tasks
            if t.status == TaskStatus.COMPLETED and t.implementation_path
        ]

        if len(completed) < 3:
            return CalibrationWeights.default()

        actuals = []
        for task in completed:
            actual = self._extract_actuals(task)
            if actual:
                actuals.append(actual)

        if len(actuals) < 3:
            return CalibrationWeights.default()

        velocity = self._calibrate_velocity(completed, actuals)
        patterns = self._calibrate_patterns(completed, actuals)
        complexity_kw = self._calibrate_complexity_keywords(completed, actuals)
        correlations = self._compute_correlations(completed, actuals)

        return CalibrationWeights(
            velocity_by_module=velocity,
            pattern_factors=patterns,
            complexity_keyword_weights=complexity_kw,
            correlations=correlations
        )

    def _extract_actuals(self, task: Task) -> Optional[TaskActual]:
        path = self.project_root / task.implementation_path
        if not path.exists():
            return None

        actual_loc = 0
        actual_complexity = 1

        if path.is_file() and path.suffix == '.py':
            actual_loc = self._count_loc(path)
            actual_complexity = self._cyclomatic_complexity(path)
        elif path.is_dir():
            for py_file in path.rglob("*.py"):
                actual_loc += self._count_loc(py_file)
                actual_complexity = max(actual_complexity, self._cyclomatic_complexity(py_file))

        if actual_loc == 0:
            return None

        actual_context = self._estimate_actual_context(path)

        return TaskActual(
            task_id=task.id,
            actual_loc=actual_loc,
            actual_complexity=actual_complexity,
            actual_context_tokens=actual_context
        )

    def _count_loc(self, filepath: Path) -> int:
        try:
            content = filepath.read_text(encoding='utf-8')
            lines = content.split('\n')
            code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
            return len(code_lines)
        except Exception:
            return 0

    def _cyclomatic_complexity(self, filepath: Path) -> int:
        try:
            content = filepath.read_text(encoding='utf-8')
            tree = ast.parse(content)
            complexity = 1
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.ExceptHandler)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    complexity += 1
            return complexity
        except Exception:
            return 1

    def _estimate_actual_context(self, path: Path) -> int:
        tokens = 0
        try:
            if path.is_file():
                tokens += len(path.read_text(encoding='utf-8')) // 4
            elif path.is_dir():
                for py_file in path.rglob("*.py"):
                    tokens += len(py_file.read_text(encoding='utf-8')) // 4
        except Exception:
            pass
        return tokens

    def _calibrate_velocity(self, completed: list[Task], actuals: list[TaskActual]) -> dict[str, float]:
        velocity = {}
        module_data = {}

        for task, actual in zip(completed, actuals):
            module = task.module
            if module not in module_data:
                module_data[module] = {"loc": [], "days": []}
            module_data[module]["loc"].append(actual.actual_loc)
            module_data[module]["days"].append(task.estimate_days)

        for module, data in module_data.items():
            if data["days"] and sum(data["days"]) > 0:
                velocity[module] = sum(data["loc"]) / sum(data["days"])
            else:
                velocity[module] = 100

        return velocity

    def _calibrate_patterns(self, completed: list[Task], actuals: list[TaskActual]) -> dict[str, float]:
        patterns = {}
        pattern_data = {}

        for task, actual in zip(completed, actuals):
            for pattern in HeuristicScorer.PATTERN_FACTORS:
                if pattern in task.description.lower():
                    if pattern not in pattern_data:
                        pattern_data[pattern] = {"loc": [], "base_loc": []}
                    base_vel = HeuristicScorer.DEFAULT_VELOCITY.get(task.module, 100)
                    base_loc = base_vel * task.estimate_days
                    pattern_data[pattern]["loc"].append(actual.actual_loc)
                    pattern_data[pattern]["base_loc"].append(base_loc)

        for pattern, data in pattern_data.items():
            if data["base_loc"] and sum(data["base_loc"]) > 0:
                patterns[pattern] = sum(data["loc"]) / sum(data["base_loc"])
            else:
                patterns[pattern] = 1.0

        defaults = HeuristicScorer.PATTERN_FACTORS.copy()
        defaults.update(patterns)
        return defaults

    def _calibrate_complexity_keywords(self, completed: list[Task], actuals: list[TaskActual]) -> dict[str, float]:
        kw_weights = {}
        for kw in HeuristicScorer.COMPLEXITY_KEYWORDS:
            kw_weights[kw] = 1.0

        kw_data = {}
        for task, actual in zip(completed, actuals):
            text = (task.description + " " + " ".join(task.acceptance_criteria)).lower()
            for kw in HeuristicScorer.COMPLEXITY_KEYWORDS:
                if kw in text:
                    if kw not in kw_data:
                        kw_data[kw] = {"complexity": [], "count": []}
                    kw_data[kw]["complexity"].append(actual.actual_complexity)
                    kw_data[kw]["count"].append(1)

        for kw, data in kw_data.items():
            if data["complexity"]:
                avg_complexity = np.mean(data["complexity"])
                kw_weights[kw] = max(0.5, min(3.0, avg_complexity / 5.0))

        return kw_weights

    def _compute_correlations(self, completed: list[Task], actuals: list[TaskActual]) -> dict[str, float]:
        correlations = {}

        pred_complexity = []
        actual_complexity = []
        pred_loc = []
        actual_loc = []
        pred_context = []
        actual_context = []

        scorer = HeuristicScorer()
        graph = None

        for task, actual in zip(completed, actuals):
            score = scorer.score_task(task, graph, self.project_root)
            pred_complexity.append(score.complexity)
            actual_complexity.append(actual.actual_complexity)
            pred_loc.append(score.est_loc)
            actual_loc.append(actual.actual_loc)
            pred_context.append(score.context_tokens)
            actual_context.append(actual.actual_context_tokens)

        if len(pred_complexity) >= 3:
            try:
                correlations["complexity"] = float(stats.pearsonr(pred_complexity, actual_complexity)[0])
                correlations["loc"] = float(stats.pearsonr(pred_loc, actual_loc)[0])
                correlations["context"] = float(stats.pearsonr(pred_context, actual_context)[0])
            except Exception:
                correlations["complexity"] = 0.0
                correlations["loc"] = 0.0
                correlations["context"] = 0.0

        return correlations