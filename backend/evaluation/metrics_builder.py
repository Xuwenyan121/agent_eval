"""
Metrics Builder: constructs the list of DeepEval metrics from evaluator_config.
Supports:
  - G-Eval (custom LLM-as-Judge) business dimensions
  - Rule-based metrics (zero LLM cost): F1, ExactMatch, ROUGE-L, BLEU, etc.
  - DeepEval built-in metrics: AnswerRelevancy, Faithfulness, etc.
"""

import logging
from deepeval.metrics import GEval, BaseMetric

# DeepEval 4.x renamed LLMTestCaseParams → SingleTurnParams
try:
    from deepeval.test_case import SingleTurnParams as EvalParams
except ImportError:
    from deepeval.test_case import LLMTestCaseParams as EvalParams

from evaluation.metrics.rule_metrics import (
    F1Metric,
    ExactMatchMetric,
    RougeLMetric,
    BLEUMetric,
    StringSimilarityMetric,
    LengthRatioMetric,
    KeywordCoverageMetric,
    MetaValidationMetric,
)
from evaluation.metrics.deepeval_builtin import (
    get_deepeval_metric_class,
    is_deepeval_builtin,
)

logger = logging.getLogger(__name__)

# ─── Rule Metric Registry ───────────────────────────────────────────

RULE_METRIC_REGISTRY: dict[str, type] = {
    "f1": F1Metric,
    "exact_match": ExactMatchMetric,
    "rouge_l": RougeLMetric,
    "bleu": BLEUMetric,
    "string_similarity": StringSimilarityMetric,
    "length_ratio": LengthRatioMetric,
    "keyword_coverage": KeywordCoverageMetric,
    "meta_validation": MetaValidationMetric,
}

# Display name → snake_case key mapping for normalization
_RULE_METRIC_ALIASES: dict[str, str] = {
    "keyword coverage": "keyword_coverage",
    "keywordcoverage": "keyword_coverage",
    "meta validation": "meta_validation",
    "metavalidation": "meta_validation",
    "string similarity": "string_similarity",
    "stringsimilarity": "string_similarity",
    "exact match": "exact_match",
    "exactmatch": "exact_match",
    "length ratio": "length_ratio",
    "lengthratio": "length_ratio",
    "rouge-l": "rouge_l",
    "rougel": "rouge_l",
    "rouge l": "rouge_l",
    "f1 score": "f1",
    "f1score": "f1",
}


def _normalize_rule_metric_name(name: str) -> str:
    """Normalize a rule metric display name to its registry key."""
    if name in RULE_METRIC_REGISTRY:
        return name  # already a valid key
    lower = name.lower().strip()
    return _RULE_METRIC_ALIASES.get(lower, name)


def list_rule_metrics() -> list:
    """Return list of available rule metric identifiers."""
    return list(RULE_METRIC_REGISTRY.keys())


def list_all_metric_types() -> dict:
    """Return a categorized summary of all available metrics."""
    from evaluation.metrics.deepeval_builtin import list_deepeval_metrics
    return {
        "g_eval": ["custom criteria — uses LLM-as-Judge with configurable criteria text"],
        "rule": list_rule_metrics(),
        "deepeval_builtin": list_deepeval_metrics(),
    }


# ─── Main Builder ───────────────────────────────────────────────────

def build_metrics(evaluator_config: dict, judge_model: dict = None) -> list:
    """
    Build a list of DeepEval metrics from the task's evaluator_config.

    Args:
        evaluator_config: dict with "metrics" list, each containing:
            - name: metric identifier
            - type: "g_eval" | "rule" | "deepeval_builtin"
            - category: "business_dim" | "ml_metric"
            - criteria: (for g_eval) scoring criteria text
            - threshold: pass/fail threshold
            - weight: weight for overall score
            - params: additional parameters

        judge_model: dict with model/api_base/api_key for the judge LLM.
                     Optional — only needed for g_eval and deepeval_builtin.

    Returns:
        List of DeepEval metric instances ready for evaluate()

    Raises:
        ValueError: if no valid metrics can be built
    """
    metrics = []
    errors = []

    for m_cfg in evaluator_config.get("metrics", []):
        # Support both {name, type} and legacy {type} formats
        name = m_cfg.get("name") or m_cfg.get("type", "")
        if not name:
            errors.append({"name": "<unknown>", "error": "Metric entry has neither 'name' nor 'type'"})
            continue

        threshold = m_cfg.get("threshold", 0.6)
        metric_type = m_cfg.get("type", None)
        params = m_cfg.get("params", {})

        # Normalize rule metric names (e.g. "Keyword Coverage" → "keyword_coverage")
        if metric_type == "rule":
            name = _normalize_rule_metric_name(name)
            m_cfg["name"] = name  # update for downstream usage

        # Validate type against MetricDefinition registry to catch mismatches
        # (e.g. meta_validation configured as "g_eval" but registered as "rule")
        resolved = _resolve_metric_type(name)
        if resolved:
            registered_type = resolved["type"]
            if metric_type in ("g_eval", "rule", "deepeval_builtin") and registered_type != metric_type:
                logger.warning(
                    "Metric '%s' configured as type='%s' but registry says type='%s', correcting to registry type",
                    name, metric_type, registered_type,
                )
                metric_type = registered_type
            elif metric_type not in ("g_eval", "rule", "deepeval_builtin"):
                metric_type = registered_type
            # Fill in criteria from registry if missing
            if metric_type == "g_eval" and not m_cfg.get("criteria"):
                m_cfg.setdefault("criteria", resolved.get("criteria", ""))
            # Fill in rule params from registry if missing
            if metric_type == "rule" and not params.get("rule_class"):
                params.setdefault("rule_class", resolved.get("rule_class", ""))
        elif metric_type not in ("g_eval", "rule", "deepeval_builtin"):
            # Not in registry and not a valid type — default to g_eval (LLM-as-Judge)
            logger.info("Unrecognized metric type '%s' for '%s', defaulting to g_eval", metric_type, name)
            metric_type = "g_eval"

        try:
            metric = _build_single_metric(name, metric_type, threshold, params,
                                           m_cfg, judge_model)
            if metric is not None:
                metrics.append(metric)
                logger.debug("Built metric: %s (type=%s, threshold=%.2f)", name, metric_type, threshold)
        except Exception as e:
            error_msg = f"Failed to build metric '{name}': {e}"
            logger.error(error_msg)
            errors.append({"name": name, "error": str(e)})

    if not metrics:
        raise ValueError(
            f"No valid metrics could be built from config. Errors: {errors}"
        )

    logger.info(
        "Built %d metrics: %d g_eval, %d rule, %d deepeval_builtin",
        len(metrics),
        sum(1 for m_cfg in evaluator_config.get("metrics", []) if m_cfg.get("type") == "g_eval"),
        sum(1 for m_cfg in evaluator_config.get("metrics", []) if m_cfg.get("type") == "rule"),
        sum(1 for m_cfg in evaluator_config.get("metrics", []) if m_cfg.get("type") == "deepeval_builtin"),
    )
    return metrics


def _resolve_metric_type(name: str):
    """
    Look up a metric name in the MetricDefinition table to resolve its type,
    criteria, and rule_class. Returns None if not found.
    """
    try:
        from evaluation.models import MetricDefinition
        obj = MetricDefinition.objects.filter(name=name).first()
        if obj:
            return {
                "type": obj.type,
                "criteria": obj.criteria,
                "rule_class": obj.rule_class,
            }
    except Exception:
        pass
    return None


def _build_single_metric(
    name: str,
    metric_type: str,
    threshold: float,
    params: dict,
    full_cfg: dict,
    judge_config: dict = None,
) -> BaseMetric:
    """Build a single metric instance."""

    if metric_type == "g_eval":
        return _build_g_eval(name, threshold, full_cfg, judge_config)

    elif metric_type == "rule":
        return _build_rule_metric(name, threshold, params)

    elif metric_type == "deepeval_builtin":
        return _build_deepeval_builtin(name, threshold, params, judge_config)

    else:
        logger.warning("Unknown metric type: %s for %s, skipping", metric_type, name)
        return None


def _build_g_eval(name: str, threshold: float, cfg: dict, judge_config: dict) -> GEval:
    """
    Build a G-Eval (LLM-as-Judge) metric.

    Supports two modes:
    1. prompt_id mode: loads criteria/evaluation_steps from JudgePrompt library
    2. criteria mode: uses inline criteria string (backward compatible)
    """
    from evaluation.judge_model import get_judge_model_instance

    # Create a properly configured model instance
    model_instance = get_judge_model_instance(judge_config)

    criteria = cfg.get("criteria", f"Evaluate {name}")
    evaluation_steps = None

    # Check if a JudgePrompt is referenced
    prompt_id = cfg.get("prompt_id")
    if prompt_id:
        try:
            from evaluation.models import JudgePrompt
            prompt = JudgePrompt.objects.get(id=prompt_id, is_active=True)
            criteria = prompt.build_criteria_text()
            if prompt.evaluation_steps:
                evaluation_steps = prompt.evaluation_steps
            logger.info(
                "Using JudgePrompt '%s' for metric '%s'", prompt.name, name,
            )
        except Exception as e:
            logger.warning(
                "Failed to load JudgePrompt %s for metric '%s': %s. Falling back to inline criteria.",
                prompt_id, name, e,
            )

    # Also support inline evaluation_steps
    if not evaluation_steps:
        evaluation_steps = cfg.get("evaluation_steps", None)

    metric = GEval(
        name=name,
        criteria=criteria,
        evaluation_params=[
            EvalParams.INPUT,
            EvalParams.ACTUAL_OUTPUT,
            EvalParams.EXPECTED_OUTPUT,
        ],
        threshold=threshold,
        model=model_instance,  # Pass model instance instead of string
        strict_mode=False,
        async_mode=True,
    )

    # Set evaluation_steps if provided
    if evaluation_steps:
        metric.evaluation_steps = evaluation_steps

    return metric


def _build_rule_metric(name: str, threshold: float, params: dict) -> BaseMetric:
    """Build a rule-based metric (zero LLM cost)."""
    rule_class_name = params.get("rule_class", name)
    rule_cls = RULE_METRIC_REGISTRY.get(rule_class_name)

    # If not found by key, try matching by class __name__ (case-insensitive)
    if rule_cls is None:
        for key, cls in RULE_METRIC_REGISTRY.items():
            if cls.__name__.lower() == rule_class_name.lower():
                rule_cls = cls
                logger.info(
                    "Resolved rule metric '%s' by class name '%s' → registry key '%s'",
                    name, rule_class_name, key,
                )
                break

    if rule_cls is None:
        raise ValueError(
            f"Unknown rule metric: '{rule_class_name}'. "
            f"Available: {list_rule_metrics()}"
        )

    return rule_cls(threshold=threshold, params=params)


def _build_deepeval_builtin(
    name: str, threshold: float, params: dict, judge_config: dict
) -> BaseMetric:
    """Build a DeepEval built-in metric (LLM-as-Judge, pre-defined criteria)."""
    from evaluation.judge_model import get_judge_model_instance

    if not judge_config:
        raise ValueError("DeepEval built-in metric requires judge_model configuration")

    metric_cls = get_deepeval_metric_class(name)
    if metric_cls is None:
        raise ValueError(f"Unknown DeepEval built-in: '{name}'")

    model_instance = get_judge_model_instance(judge_config)

    return metric_cls(
        threshold=threshold,
        model=model_instance,
        **{k: v for k, v in params.items() if k not in ("rule_class",)},
    )


# ─── Validation Utilities ──────────────────────────────────────────

def validate_evaluator_config(config: dict) -> dict:
    """
    Validate an evaluator config before building metrics.

    Returns:
        {"valid": bool, "errors": list, "warnings": list}
    """
    errors = []
    warnings = []
    metrics = config.get("metrics", [])

    if not metrics:
        errors.append("At least one metric must be configured")
        return {"valid": False, "errors": errors, "warnings": warnings}

    total_weight = 0.0
    for i, m in enumerate(metrics):
        prefix = f"Metric[{i}]"

        if "name" not in m:
            errors.append(f"{prefix}: 'name' is required")
            continue

        metric_type = m.get("type", "g_eval")
        if metric_type not in ("g_eval", "rule", "deepeval_builtin"):
            errors.append(f"{prefix}: unknown type '{metric_type}'")

        if metric_type == "g_eval" and not m.get("criteria") and not m.get("prompt_id"):
            warnings.append(f"{prefix} ({m['name']}): no criteria or prompt_id specified, using default")

        if metric_type == "rule":
            rule_name = _normalize_rule_metric_name(
                m.get("params", {}).get("rule_class", m["name"])
            )
            if rule_name not in RULE_METRIC_REGISTRY:
                errors.append(f"{prefix} ({m['name']}): unknown rule metric '{rule_name}'")

        if metric_type == "deepeval_builtin":
            if not is_deepeval_builtin(m["name"]):
                errors.append(f"{prefix} ({m['name']}): unknown DeepEval built-in")

        weight = m.get("weight", 1.0)
        if weight < 0:
            errors.append(f"{prefix} ({m['name']}): weight must be >= 0")
        total_weight += weight

    if abs(total_weight - 1.0) > 0.01:
        warnings.append(f"Total weight ({total_weight:.2f}) != 1.0, will be normalized")

    parallel = config.get("parallel", 1)
    if not isinstance(parallel, int) or parallel < 1 or parallel > 50:
        errors.append(f"parallel must be integer 1-50, got {parallel}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
