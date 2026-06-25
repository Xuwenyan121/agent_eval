"""
DeepEval Built-in Metric Registry
==================================
Maps metric names to DeepEval's built-in metric classes.
These metrics use LLM-as-Judge internally (different from G-Eval custom dims).
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy import registry — only import when needed
_DEEPEVAL_METRIC_MAP = {
    # Answer quality metrics
    "answer_relevancy": ("deepeval.metrics", "AnswerRelevancyMetric"),
    "faithfulness": ("deepeval.metrics", "FaithfulnessMetric"),
    "contextual_relevancy": ("deepeval.metrics", "ContextualRelevancyMetric"),
    "contextual_precision": ("deepeval.metrics", "ContextualPrecisionMetric"),
    "contextual_recall": ("deepeval.metrics", "ContextualRecallMetric"),

    # Hallucination / toxicity
    "hallucination": ("deepeval.metrics", "HallucinationMetric"),
    "answer_correctness": ("deepeval.metrics", "AnswerCorrectnessMetric"),

    # Conversational metrics
    "conversation_relevancy": ("deepeval.metrics", "ConversationRelevancyMetric"),
    "conversation_completeness": ("deepeval.metrics", "ConversationCompletenessMetric"),

    # Knowledge retention
    "knowledge_retention": ("deepeval.metrics", "KnowledgeRetentionMetric"),

    # Summarization
    "summarization": ("deepeval.metrics", "SummarizationMetric"),

    # Bias / toxicity
    "bias": ("deepeval.metrics", "BiasMetric"),
    "toxicity": ("deepeval.metrics", "ToxicityMetric"),
}


def get_deepeval_metric_class(metric_name: str):
    """
    Dynamically import and return a DeepEval built-in metric class.

    Args:
        metric_name: e.g. "answer_relevancy", "faithfulness"

    Returns:
        The metric class, or None if not found/importable
    """
    entry = _DEEPEVAL_METRIC_MAP.get(metric_name)
    if not entry:
        return None

    module_path, class_name = entry
    try:
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, class_name, None)
    except (ImportError, AttributeError) as e:
        logger.warning("Cannot import DeepEval metric %s: %s", metric_name, e)
        return None


def list_deepeval_metrics() -> list:
    """Return list of available DeepEval built-in metric names."""
    return list(_DEEPEVAL_METRIC_MAP.keys())


def is_deepeval_builtin(metric_name: str) -> bool:
    """Check if a metric name is a known DeepEval built-in."""
    return metric_name in _DEEPEVAL_METRIC_MAP
