"""Heuristic scoring for task complexity, LOC, and context estimation."""

import re
from pathlib import Path
from typing import Optional

from ..parser.models import Task, TaskScore, DependencyGraph


class HeuristicScorer:
    DEFAULT_VELOCITY = {
        "trainer": 120, "model_manager": 100, "data_generator": 90,
        "parser": 80, "ui": 100, "cli": 110, "core": 90,
        "system": 70, "research": 30, "testing": 60, "docs": 40,
        "deployment": 50, "config": 150, "data": 80,
        "ui/cli": 100, "ui/components": 90, "model": 90,
    }

    PATTERN_FACTORS = {
        "implement": 1.0, "create": 1.0, "add": 0.8,
        "refactor": 1.5, "optimize": 1.3, "improve": 1.2,
        "fix": 0.6, "debug": 0.5, "test": 0.6,
        "document": 0.3, "research": 0.2, "evaluate": 0.3,
        "configure": 0.4, "setup": 0.5, "integrate": 1.1,
        "build": 1.0, "design": 0.7, "analyze": 0.5,
    }

    COMPLEXITY_KEYWORDS = {
        "async": 1, "await": 1, "thread": 2, "multiprocess": 2,
        "recursive": 2, "dynamic": 1, "polymorph": 1, "abstract": 1,
        "generic": 1, "decorator": 1, "metaclass": 2, "contextlib": 1,
        "generator": 1, "coroutine": 2, "callback": 1, "event": 1,
        "pipeline": 1, "stream": 1, "batch": 1, "cache": 1,
        "retry": 1, "fallback": 1, "circuit": 2, "timeout": 1,
        "lock": 1, "mutex": 1, "semaphore": 1, "race": 2,
        "deadlock": 2, "concurrent": 2, "parallel": 1, "distributed": 3,
        "grpc": 1, "protobuf": 1, "serializ": 1, "deserializ": 1,
        "encrypt": 1, "decrypt": 1, "auth": 1, "oauth": 1,
        "migration": 2, "schema": 1, "transaction": 1, "rollback": 1,
        "orm": 1, "query": 1, "index": 1, "optimize": 1,
    }

    MODULE_BASE_COMPLEXITY = {
        "trainer": 3, "model_manager": 2, "core": 2,
        "parser": 1, "config": 1, "ui": 2, "cli": 1,
        "research": 1, "testing": 1, "docs": 0,
        "deployment": 2, "system": 2, "data": 1,
        "data_generator": 2, "data/parsers": 2,
    }

    def __init__(self, velocity_overrides: Optional[dict] = None):
        self.velocity = {**self.DEFAULT_VELOCITY, **(velocity_overrides or {})}

    def score_task(
        self,
        task: Task,
        graph: DependencyGraph,
        project_root: Path,
        velocity_overrides: Optional[dict] = None
    ) -> TaskScore:
        velocity = {**self.velocity, **(velocity_overrides or {})}

        complexity = self._estimate_complexity(task, graph)
        est_loc = self._estimate_loc(task, velocity)
        context_tokens = self._estimate_context(task, graph, project_root)
        confidence = self._compute_confidence(task)

        return TaskScore(
            complexity=complexity,
            est_loc=est_loc,
            context_tokens=context_tokens,
            confidence=confidence,
            complexity_breakdown=self._complexity_breakdown(task, graph),
            loc_breakdown=self._loc_breakdown(task, velocity),
            context_breakdown=self._context_breakdown(task, graph, project_root),
        )

    def _estimate_complexity(self, task: Task, graph: DependencyGraph) -> int:
        score = 1
        breakdown = {}

        text = (task.description + " " + " ".join(task.acceptance_criteria)).lower()

        kw_score = 0
        for kw, weight in self.COMPLEXITY_KEYWORDS.items():
            if kw in text:
                kw_score += weight
        breakdown["keywords"] = kw_score
        score += kw_score

        criteria_score = min(len(task.acceptance_criteria), 8) * 0.5
        breakdown["criteria"] = round(criteria_score, 1)
        score += criteria_score

        upstream_count = len(task.dependencies)
        deps_score = min(upstream_count, 5) * 0.8
        breakdown["dependencies"] = round(deps_score, 1)
        score += deps_score

        module_base = self.MODULE_BASE_COMPLEXITY.get(task.module, 1)
        breakdown["module_base"] = module_base
        score += module_base

        pattern_score = 0
        for pattern, factor in self.PATTERN_FACTORS.items():
            if pattern in task.description.lower():
                pattern_score = (factor - 1) * 2
                breakdown["pattern"] = round(pattern_score, 1)
                break
        score += pattern_score

        phase_factor = {0: 0.5, 1: 0.5, 2: 1.0, 3: 1.0, 4: 0.5}.get(task.phase, 0)
        breakdown["phase"] = round(phase_factor, 1)
        score += phase_factor

        final = max(1, min(10, round(score)))
        breakdown["total_raw"] = round(score, 1)
        breakdown["final"] = final

        return final

    def _complexity_breakdown(self, task: Task, graph: DependencyGraph) -> dict:
        return self._estimate_complexity(task, graph)

    def _estimate_loc(self, task: Task, velocity: dict) -> int:
        base_velocity = velocity.get(task.module, 100)

        pattern_factor = 1.0
        for pattern, factor in self.PATTERN_FACTORS.items():
            if pattern in task.description.lower():
                pattern_factor = factor
                break

        criteria_factor = 1.0 + min(len(task.acceptance_criteria), 10) * 0.05

        deps_factor = 1.0 + min(len(task.dependencies), 5) * 0.1

        est_days = task.estimate_days

        base_loc = base_velocity * est_days
        final_loc = int(base_loc * pattern_factor * criteria_factor * deps_factor)

        return max(10, final_loc)

    def _loc_breakdown(self, task: Task, velocity: dict) -> dict:
        base_velocity = velocity.get(task.module, 100)
        pattern_factor = 1.0
        for pattern, factor in self.PATTERN_FACTORS.items():
            if pattern in task.description.lower():
                pattern_factor = factor
                break

        criteria_factor = 1.0 + min(len(task.acceptance_criteria), 10) * 0.05
        deps_factor = 1.0 + min(len(task.dependencies), 5) * 0.1

        return {
            "base_velocity": base_velocity,
            "estimate_days": task.estimate_days,
            "pattern_factor": pattern_factor,
            "criteria_factor": round(criteria_factor, 2),
            "deps_factor": round(deps_factor, 2),
            "base_loc": base_velocity * task.estimate_days,
        }

    def _estimate_context(
        self,
        task: Task,
        graph: DependencyGraph,
        project_root: Path
    ) -> int:
        tokens = 0
        breakdown = {}

        own_files = self._get_implementation_files(task, project_root)
        own_tokens = sum(self._estimate_file_tokens(f) for f in own_files)
        tokens += own_tokens
        breakdown["own_implementation"] = own_tokens

        upstream_files = set()
        for dep_id in task.dependencies:
            if dep_id in graph.nodes:
                dep_task = graph.nodes[dep_id]
                upstream_files.update(self._get_implementation_files(dep_task, project_root))
        upstream_tokens = sum(self._estimate_file_tokens(f) for f in upstream_files)
        tokens += min(upstream_tokens, 50000)
        breakdown["upstream"] = min(upstream_tokens, 50000)

        specs_tokens = self._estimate_specs_tokens(task, project_root)
        tokens += specs_tokens
        breakdown["specs"] = specs_tokens

        config_tokens = self._estimate_config_tokens(project_root)
        tokens += config_tokens
        breakdown["config"] = config_tokens

        return tokens

    def _context_breakdown(self, task: Task, graph: DependencyGraph, project_root: Path) -> dict:
        return self._estimate_context(task, graph, project_root)

    def _get_implementation_files(self, task: Task, project_root: Path) -> list[Path]:
        files = []
        if task.implementation_path:
            path = project_root / task.implementation_path
            if path.exists():
                if path.is_file():
                    files.append(path)
                elif path.is_dir():
                    files.extend(path.rglob("*.py"))
        return files

    def _estimate_file_tokens(self, filepath: Path) -> int:
        try:
            content = filepath.read_text(encoding='utf-8')
            return len(content) // 4
        except Exception:
            return 1000

    def _estimate_specs_tokens(self, task: Task, project_root: Path) -> int:
        spec_paths = [
            project_root / "spec.md",
            project_root / "plan.md",
            project_root / "data-model.md",
        ]
        tokens = 0
        for p in spec_paths:
            if p.exists():
                tokens += len(p.read_text(encoding='utf-8')) // 4
        return min(tokens, 30000)

    def _estimate_config_tokens(self, project_root: Path) -> int:
        config_files = [
            "pyproject.toml", "requirements.txt", "setup.py",
            "config.py", "settings.py", ".env.example",
        ]
        tokens = 0
        for cf in config_files:
            path = project_root / cf
            if path.exists():
                tokens += len(path.read_text(encoding='utf-8')) // 4
        return min(tokens, 10000)

    def _compute_confidence(self, task: Task) -> float:
        confidence = 0.5

        if task.implementation_path:
            confidence += 0.2

        if task.acceptance_criteria:
            confidence += min(len(task.acceptance_criteria) * 0.03, 0.15)

        if task.estimate_days > 0:
            confidence += 0.1

        if task.module in self.MODULE_BASE_COMPLEXITY:
            confidence += 0.05

        return min(1.0, confidence)


def score_all_tasks(
    tasks: list[Task],
    graph: DependencyGraph,
    project_root: Path,
    velocity_overrides: Optional[dict] = None
) -> list[Task]:
    scorer = HeuristicScorer(velocity_overrides)
    for task in tasks:
        task.score = scorer.score_task(task, graph, project_root, velocity_overrides)
    return tasks