"""
Metric Dry-Run Utility
=======================
Run a quick evaluation on sample data to validate metric configuration
before launching a full evaluation task. Useful for:
  - Testing rule metrics without LLM cost
  - Verifying metric weights produce reasonable scores
  - Debugging metric configuration errors
"""

import logging
import time
from typing import Optional

from deepeval.test_case import LLMTestCase
from deepeval.metrics import BaseMetric

logger = logging.getLogger(__name__)


class MetricDryRunner:
    """
    Runs a dry-run evaluation on a few sample pairs to validate metrics.
    """

    def __init__(self, metrics: list):
        """
        Args:
            metrics: list of BaseMetric instances (from build_metrics())
        """
        self.metrics = metrics

    def run(
        self,
        samples: list[dict],
        max_samples: int = 3,
    ) -> dict:
        """
        Run dry-run evaluation on sample data.

        Args:
            samples: list of dicts with keys:
                - input: the query/input text
                - actual_output: the agent's response
                - expected_output: the ground truth answer (optional)
            max_samples: limit number of samples to process

        Returns:
            {
                "total_samples": int,
                "results": [
                    {
                        "sample_index": int,
                        "metrics": {
                            "metric_name": {
                                "score": float,
                                "passed": bool,
                                "reason": str,
                            }
                        },
                        "overall_score": float,
                        "latency_ms": int,
                    }
                ],
                "summary": {
                    "avg_score": float,
                    "pass_rate": float,
                    "metrics_summary": {
                        "metric_name": {
                            "avg_score": float,
                            "min_score": float,
                            "max_score": float,
                        }
                    }
                },
                "errors": list,
            }
        """
        from deepeval import evaluate

        samples = samples[:max_samples]
        results = []
        errors = []

        for i, sample in enumerate(samples):
            test_case = LLMTestCase(
                input=sample.get("input", ""),
                actual_output=sample.get("actual_output", ""),
                expected_output=sample.get("expected_output"),
            )
            # Attach meta data for MetaValidationMetric (from dry-run sample)
            test_case._actual_meta = sample.get("actual_meta") or {}
            test_case._expected_meta = sample.get("expected_meta") or {}

            start = time.monotonic()
            try:
                # Run each metric individually for detailed results
                sample_metrics = {}
                for metric in self.metrics:
                    metric_name = getattr(metric, "__name__", metric.__class__.__name__)
                    try:
                        score = metric.measure(test_case)
                        sample_metrics[metric_name] = {
                            "score": float(score),
                            "passed": metric.is_successful(),
                            "reason": getattr(metric, "reason", ""),
                        }
                    except Exception as e:
                        sample_metrics[metric_name] = {
                            "score": 0.0,
                            "passed": False,
                            "reason": f"Error: {e}",
                        }
                        errors.append({
                            "sample_index": i,
                            "metric": metric_name,
                            "error": str(e),
                        })

                # Compute weighted overall score
                overall = self._compute_overall(sample_metrics)
                latency = int((time.monotonic() - start) * 1000)

                results.append({
                    "sample_index": i,
                    "metrics": sample_metrics,
                    "overall_score": overall,
                    "latency_ms": latency,
                })

            except Exception as e:
                errors.append({"sample_index": i, "error": str(e)})
                logger.error("Dry-run sample %d failed: %s", i, e)

        summary = self._compute_summary(results)

        return {
            "total_samples": len(samples),
            "results": results,
            "summary": summary,
            "errors": errors,
        }

    def _compute_overall(self, sample_metrics: dict) -> float:
        """Compute weighted average score across metrics."""
        if not sample_metrics:
            return 0.0

        scores = [m["score"] for m in sample_metrics.values()]
        return sum(scores) / len(scores) if scores else 0.0

    def _compute_summary(self, results: list) -> dict:
        """Compute aggregate summary across all samples."""
        if not results:
            return {"avg_score": 0.0, "pass_rate": 0.0, "metrics_summary": {}}

        overall_scores = [r["overall_score"] for r in results]

        # Per-metric aggregation
        metrics_agg = {}
        for r in results:
            for name, m in r["metrics"].items():
                if name not in metrics_agg:
                    metrics_agg[name] = []
                metrics_agg[name].append(m["score"])

        metrics_summary = {}
        for name, scores in metrics_agg.items():
            metrics_summary[name] = {
                "avg_score": round(sum(scores) / len(scores), 4),
                "min_score": round(min(scores), 4),
                "max_score": round(max(scores), 4),
            }

        total_checks = sum(len(r["metrics"]) for r in results)
        passed_checks = sum(
            1 for r in results for m in r["metrics"].values() if m["passed"]
        )

        return {
            "avg_score": round(sum(overall_scores) / len(overall_scores), 4),
            "pass_rate": round(passed_checks / total_checks, 4) if total_checks > 0 else 0.0,
            "metrics_summary": metrics_summary,
        }
