"""Threshold sweeping for optimal delegation configuration."""

from typing import Optional
import numpy as np

from ..parser.models import Task, TaskScore, ThresholdMetrics, ThresholdImpact


class ThresholdSweeper:
    """Sweep thresholds to find optimal delegation configuration."""

    def __init__(self, ground_truth: Optional[dict] = None):
        self.ground_truth = ground_truth or {}

    def sweep_complexity(
        self,
        tasks: list[Task],
        context_threshold: int = 100000,
        complexity_range: range = range(1, 11)
    ) -> dict[int, ThresholdMetrics]:
        """Sweep complexity threshold with fixed context threshold."""
        results = {}
        all_tasks = [t for t in tasks if t.score]

        for c_thresh in complexity_range:
            delegable = [
                t for t in all_tasks
                if t.score.complexity <= c_thresh
                and t.score.context_tokens <= context_threshold
            ]
            metrics = self._compute_metrics(delegable, all_tasks, c_thresh)
            results[c_thresh] = metrics

        return results

    def sweep_context(
        self,
        tasks: list[Task],
        complexity_threshold: int = 5,
        context_range: list[int] = None
    ) -> dict[int, ThresholdMetrics]:
        """Sweep context threshold with fixed complexity threshold."""
        if context_range is None:
            context_range = [25000, 50000, 75000, 100000, 150000, 200000, 300000, 500000]

        results = {}
        all_tasks = [t for t in tasks if t.score]

        for ctx_thresh in context_range:
            delegable = [
                t for t in all_tasks
                if t.score.complexity <= complexity_threshold
                and t.score.context_tokens <= ctx_thresh
            ]
            metrics = self._compute_metrics(delegable, all_tasks, ctx_thresh)
            results[ctx_thresh] = metrics

        return results

    def sweep_2d(
        self,
        tasks: list[Task],
        complexity_range: range = range(1, 11),
        context_range: list[int] = None
    ) -> dict[tuple[int, int], ThresholdMetrics]:
        """Sweep both thresholds for complete grid."""
        if context_range is None:
            context_range = [50000, 80000, 100000, 150000, 200000]

        results = {}
        all_tasks = [t for t in tasks if t.score]

        for c_thresh in complexity_range:
            for ctx_thresh in context_range:
                delegable = [
                    t for t in all_tasks
                    if t.score.complexity <= c_thresh
                    and t.score.context_tokens <= ctx_thresh
                ]
                metrics = self._compute_metrics(delegable, all_tasks, (c_thresh, ctx_thresh))
                results[(c_thresh, ctx_thresh)] = metrics

        return results

    def find_optimal(
        self,
        metrics: dict,
        objective: str = "f1",
        min_delegable: int = 1
    ) -> tuple:
        """Find optimal threshold for given objective."""
        valid = {
            k: v for k, v in metrics.items()
            if v.delegable_count >= min_delegable and getattr(v, objective, None) is not None
        }

        if not valid:
            return None

        best_key = max(valid.keys(), key=lambda k: getattr(valid[k], objective) or 0)
        return best_key

    def _compute_metrics(
        self,
        delegable: list[Task],
        all_tasks: list[Task],
        threshold_key
    ) -> ThresholdMetrics:
        """Compute metrics for a threshold configuration."""
        delegable_count = len(delegable)

        if delegable_count == 0:
            return ThresholdMetrics(delegable_count=0)

        avg_complexity = np.mean([t.score.complexity for t in delegable])
        avg_context = np.mean([t.score.context_tokens for t in delegable])

        if not self.ground_truth:
            return ThresholdMetrics(
                delegable_count=delegable_count,
                avg_complexity_delegable=avg_complexity,
                avg_context_tokens_delegable=avg_context
            )

        tp = fp = fn = 0
        for task in all_tasks:
            is_delegable = task in delegable
            actual_simple = self.ground_truth.get(task.id, {}).get("actual_complexity", 10) <= 5

            if is_delegable and actual_simple:
                tp += 1
            elif is_delegable and not actual_simple:
                fp += 1
            elif not is_delegable and actual_simple:
                fn += 1

        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 0.001)

        return ThresholdMetrics(
            delegable_count=delegable_count,
            precision=precision,
            recall=recall,
            f1=f1,
            false_positives=fp,
            false_negatives=fn,
            avg_complexity_delegable=avg_complexity,
            avg_context_tokens_delegable=avg_context
        )


def sweep_thresholds(
    tasks: list[Task],
    ground_truth: Optional[dict] = None,
    complexity_range: range = range(1, 11),
    context_range: list[int] = None
) -> ThresholdImpact:
    """Convenience function to sweep all thresholds."""
    from ..parser.models import ThresholdImpact

    sweeper = ThresholdSweeper(ground_truth)

    # sweep_complexity uses context_threshold parameter
    ctx_thresh = context_range[-1] if context_range else 100000
    complexity_metrics = sweeper.sweep_complexity(tasks, context_threshold=ctx_thresh, complexity_range=complexity_range)
    context_metrics = sweeper.sweep_context(tasks, complexity_threshold=5, context_range=context_range)
    combined_metrics = sweeper.sweep_2d(tasks, complexity_range=complexity_range, context_range=context_range)

    return ThresholdImpact(
        complexity_thresholds=complexity_metrics,
        context_thresholds=context_metrics,
        combined_thresholds=combined_metrics
    )