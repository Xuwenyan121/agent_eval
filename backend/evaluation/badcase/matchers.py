"""
BadCase Collection Matchers
============================
Each matcher takes an EvaluationResult and returns True if it matches the rule.
"""
import json
import random
import logging

logger = logging.getLogger(__name__)


class BaseMatcher:
    """Base class for all matchers."""

    def __init__(self, parameters: dict):
        self.params = parameters

    def matches(self, result) -> bool:
        raise NotImplementedError

    def reason(self, result) -> str:
        """Return a human-readable reason why this result matched."""
        return f"Matched by {self.__class__.__name__}"

    @staticmethod
    def _get_metric_score(result, metric_name: str) -> float:
        """Extract a metric's score from an EvaluationResult."""
        if not result.metric_results:
            return 0.0
        data = result.metric_results.get(metric_name, {})
        if isinstance(data, dict):
            return float(data.get("score", 0.0))
        return 0.0

    @staticmethod
    def _metric_names(result) -> set:
        """Return all metric names in the result."""
        if not result.metric_results:
            return set()
        return set(k.lower().strip() for k in result.metric_results.keys())

    def _format_reason(self, template: str, **kwargs) -> str:
        return template.format(**kwargs)


class ScoreBelowMatcher(BaseMatcher):
    """Match results where overall_score < threshold."""

    def matches(self, result) -> bool:
        threshold = float(self.params.get("threshold", 0.6))
        inclusive = self.params.get("inclusive", True)
        if inclusive:
            return result.overall_score <= threshold
        return result.overall_score < threshold

    def reason(self, result) -> str:
        return f"overall_score={result.overall_score:.3f} <= {self.params.get('threshold', 0.6)}"


class ScoreAboveMatcher(BaseMatcher):
    """Match results where overall_score >= threshold (spot check high scores)."""

    def matches(self, result) -> bool:
        threshold = float(self.params.get("threshold", 0.9))
        if result.overall_score < threshold:
            return False
        sample_rate = float(self.params.get("sample_rate", 0.2))
        if sample_rate >= 1.0:
            return True
        return random.random() < sample_rate

    def reason(self, result) -> str:
        return f"High-score spot check: overall_score={result.overall_score:.3f} (sample_rate={self.params.get('sample_rate', 0.2)})"


class MetricBelowMatcher(BaseMatcher):
    """Match results where a specific metric's score < threshold."""

    def matches(self, result) -> bool:
        metric_name = self.params.get("metric_name", "")
        threshold = float(self.params.get("threshold", 0.5))
        inclusive = self.params.get("inclusive", True)
        score = self._get_metric_score(result, metric_name)
        if inclusive:
            return score <= threshold
        return score < threshold

    def reason(self, result) -> str:
        metric_name = self.params.get("metric_name", "")
        score = self._get_metric_score(result, metric_name)
        return f"{metric_name}={score:.3f} <= {self.params.get('threshold', 0.5)}"


class MetricAboveMatcher(BaseMatcher):
    """Match results where a specific metric's score >= threshold (spot check)."""

    def matches(self, result) -> bool:
        metric_name = self.params.get("metric_name", "")
        threshold = float(self.params.get("threshold", 0.9))
        score = self._get_metric_score(result, metric_name)
        if score < threshold:
            return False
        sample_rate = float(self.params.get("sample_rate", 0.2))
        if sample_rate >= 1.0:
            return True
        return random.random() < sample_rate

    def reason(self, result) -> str:
        metric_name = self.params.get("metric_name", "")
        score = self._get_metric_score(result, metric_name)
        return f"{metric_name}={score:.3f} high-score spot check"


class BoundaryMatcher(BaseMatcher):
    """Match results where overall_score is in [lower, upper]."""

    def matches(self, result) -> bool:
        lower = float(self.params.get("lower", 0.55))
        upper = float(self.params.get("upper", 0.65))
        return lower <= result.overall_score <= upper

    def reason(self, result) -> str:
        return f"boundary sample: overall_score={result.overall_score:.3f} in [{self.params.get('lower', 0.55)}, {self.params.get('upper', 0.65)}]"


class RandomSamplingMatcher(BaseMatcher):
    """Randomly sample results at the configured rate."""

    def matches(self, result) -> bool:
        sample_rate = float(self.params.get("sample_rate", 0.1))
        return random.random() < sample_rate

    def reason(self, result) -> str:
        return f"random sampling (rate={self.params.get('sample_rate', 0.1)})"


class ErrorMatcher(BaseMatcher):
    """Match results that have an error."""

    def matches(self, result) -> bool:
        if not result.error:
            return False
        error_contains = self.params.get("error_contains")
        if error_contains:
            return error_contains.lower() in result.error.lower()
        return True

    def reason(self, result) -> str:
        return f"error: {result.error[:100]}"


class HighLatencyMatcher(BaseMatcher):
    """Match results where latency_ms > threshold."""

    def matches(self, result) -> bool:
        threshold_ms = int(self.params.get("threshold_ms", 5000))
        return result.latency_ms > threshold_ms

    def reason(self, result) -> str:
        return f"high latency: {result.latency_ms}ms > {self.params.get('threshold_ms', 5000)}ms"


class LowLatencyMatcher(BaseMatcher):
    """Match results where latency_ms < threshold (suspected cache hits)."""

    def matches(self, result) -> bool:
        threshold_ms = int(self.params.get("threshold_ms", 500))
        if result.latency_ms <= 0:
            return False
        return result.latency_ms < threshold_ms

    def reason(self, result) -> str:
        return f"low latency (suspected cache): {result.latency_ms}ms < {self.params.get('threshold_ms', 500)}ms"


class ScoreVarianceMatcher(BaseMatcher):
    """Match results where the variance between metric scores is > threshold."""

    def matches(self, result) -> bool:
        min_variance = float(self.params.get("min_variance", 0.5))
        if not result.metric_results:
            return False
        scores = []
        for v in result.metric_results.values():
            if isinstance(v, dict) and "score" in v:
                scores.append(float(v["score"]))
        if len(scores) < 2:
            return False
        variance = max(scores) - min(scores)
        return variance > min_variance

    def reason(self, result) -> str:
        scores = []
        for v in (result.metric_results or {}).values():
            if isinstance(v, dict) and "score" in v:
                scores.append(float(v["score"]))
        variance = max(scores) - min(scores) if len(scores) >= 2 else 0
        return f"score variance={variance:.3f} > {self.params.get('min_variance', 0.5)}"


# ─── Matcher registry ──────────────────────────────────────────────────────

MATCHER_REGISTRY = {
    "score_below": ScoreBelowMatcher,
    "score_above": ScoreAboveMatcher,
    "metric_below": MetricBelowMatcher,
    "metric_above": MetricAboveMatcher,
    "boundary": BoundaryMatcher,
    "random": RandomSamplingMatcher,
    "error": ErrorMatcher,
    "high_latency": HighLatencyMatcher,
    "low_latency": LowLatencyMatcher,
    "score_variance": ScoreVarianceMatcher,
    # "stratified" and "custom" are reserved for Phase 3
}


def get_matcher(rule) -> BaseMatcher:
    """
    Return the appropriate Matcher instance for a BadCaseCollectionRule.

    Args:
        rule: BadCaseCollectionRule instance or dict with 'rule_type' and 'parameters'.

    Returns:
        BaseMatcher instance.

    Raises:
        ValueError: If the rule_type is not recognized.
    """
    # Accept both model instances and dicts
    if hasattr(rule, "rule_type"):
        rule_type = rule.rule_type
        parameters = rule.parameters or {}
    else:
        rule_type = rule.get("rule_type", "")
        parameters = rule.get("parameters", {})

    matcher_cls = MATCHER_REGISTRY.get(rule_type)
    if not matcher_cls:
        raise ValueError(f"Unknown rule type: {rule_type}")
    return matcher_cls(parameters)