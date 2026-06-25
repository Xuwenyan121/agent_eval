#!/usr/bin/env python3
"""
Metrics Test Script
====================
Tests all rule metrics and the metrics builder without requiring Django or LLM.

Usage:
    python test_metrics.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from deepeval.test_case import LLMTestCase

# ─── Test Helpers ───────────────────────────────────────────────────

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_result(name, passed, detail=""):
    icon = "✅" if passed else "❌"
    print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))
    return passed

results = []

# ─── Sample Test Cases ──────────────────────────────────────────────

# Case 1: Perfect match (Chinese)
perfect_case = LLMTestCase(
    input="北京有哪些著名的景点？",
    actual_output="北京著名的景点有故宫、长城、天坛、颐和园等。",
    expected_output="北京著名的景点有故宫、长城、天坛、颐和园等。",
)

# Case 2: Partial match (Chinese)
partial_case = LLMTestCase(
    input="北京有哪些著名的景点？",
    actual_output="北京有故宫和长城，都是很好的旅游景点。",
    expected_output="北京著名的景点有故宫、长城、天坛、颐和园等。",
)

# Case 3: No match
mismatch_case = LLMTestCase(
    input="天气怎么样？",
    actual_output="今天天气晴朗，适合外出。",
    expected_output="推荐您去故宫博物院参观。",
)

# ─── Test 1: F1 Metric ─────────────────────────────────────────────

print_header("Test 1: F1 Metric")
from evaluation.metrics.rule_metrics import F1Metric

f1 = F1Metric(threshold=0.5)

score = f1.measure(perfect_case)
results.append(print_result("F1 perfect match", score >= 0.9, f"score={score:.3f}, {f1.reason}"))

score = f1.measure(partial_case)
results.append(print_result("F1 partial match", 0.2 <= score <= 0.8, f"score={score:.3f}, {f1.reason}"))

score = f1.measure(mismatch_case)
results.append(print_result("F1 mismatch", score < 0.3, f"score={score:.3f}, {f1.reason}"))

# ─── Test 2: Exact Match ──────────────────────────────────────────

print_header("Test 2: Exact Match")
from evaluation.metrics.rule_metrics import ExactMatchMetric

em = ExactMatchMetric()

score = em.measure(perfect_case)
results.append(print_result("ExactMatch perfect", score == 1.0, f"score={score:.3f}"))

score = em.measure(partial_case)
results.append(print_result("ExactMatch partial", score == 0.0, f"score={score:.3f}"))

# ─── Test 3: ROUGE-L ──────────────────────────────────────────────

print_header("Test 3: ROUGE-L")
from evaluation.metrics.rule_metrics import RougeLMetric

rouge = RougeLMetric(threshold=0.5)

score = rouge.measure(perfect_case)
results.append(print_result("ROUGE-L perfect", score >= 0.9, f"score={score:.3f}, {rouge.reason}"))

score = rouge.measure(partial_case)
results.append(print_result("ROUGE-L partial", 0.2 <= score <= 0.8, f"score={score:.3f}, {rouge.reason}"))

# ─── Test 4: BLEU ─────────────────────────────────────────────────

print_header("Test 4: BLEU")
from evaluation.metrics.rule_metrics import BLEUMetric

bleu = BLEUMetric(threshold=0.3)

score = bleu.measure(perfect_case)
results.append(print_result("BLEU perfect", score >= 0.8, f"score={score:.3f}, {bleu.reason}"))

score = bleu.measure(partial_case)
results.append(print_result("BLEU partial", 0.0 < score < 0.8, f"score={score:.3f}, {bleu.reason}"))

# ─── Test 5: String Similarity ────────────────────────────────────

print_header("Test 5: String Similarity")
from evaluation.metrics.rule_metrics import StringSimilarityMetric

sim = StringSimilarityMetric(threshold=0.7)

score = sim.measure(perfect_case)
results.append(print_result("StringSim perfect", score >= 0.9, f"score={score:.3f}, {sim.reason}"))

score = sim.measure(partial_case)
results.append(print_result("StringSim partial", 0.3 <= score <= 0.8, f"score={score:.3f}, {sim.reason}"))

# ─── Test 6: Length Ratio ─────────────────────────────────────────

print_header("Test 6: Length Ratio")
from evaluation.metrics.rule_metrics import LengthRatioMetric

lr = LengthRatioMetric(threshold=0.5)

score = lr.measure(perfect_case)
results.append(print_result("LengthRatio perfect", score >= 0.9, f"score={score:.3f}, {lr.reason}"))

score = lr.measure(partial_case)
results.append(print_result("LengthRatio partial", score > 0.0, f"score={score:.3f}, {lr.reason}"))

# ─── Test 7: Keyword Coverage ─────────────────────────────────────

print_header("Test 7: Keyword Coverage")
from evaluation.metrics.rule_metrics import KeywordCoverageMetric

# Auto-extract keywords from expected
kw = KeywordCoverageMetric(threshold=0.5)

score = kw.measure(perfect_case)
results.append(print_result("KeywordCov perfect", score >= 0.8, f"score={score:.3f}, {kw.reason}"))

score = kw.measure(partial_case)
results.append(print_result("KeywordCov partial", 0.1 <= score <= 0.8, f"score={score:.3f}, {kw.reason}"))

# With explicit keywords
kw_explicit = KeywordCoverageMetric(
    threshold=0.5,
    params={"keywords": ["故宫", "长城", "天坛"]},
)
score = kw_explicit.measure(partial_case)
has_gugong = "故宫" in partial_case.actual_output
has_changcheng = "长城" in partial_case.actual_output
results.append(print_result(
    "KeywordCov explicit",
    (has_gugong and has_changcheng and score > 0.5) or (not has_gugong and not has_changcheng),
    f"score={score:.3f}, {kw_explicit.reason}",
))

# ─── Test 8: Metric Registry ──────────────────────────────────────

print_header("Test 8: Metric Registry & Builder")
from evaluation.metrics_builder import (
    RULE_METRIC_REGISTRY,
    list_rule_metrics,
    list_all_metric_types,
    validate_evaluator_config,
)

all_rule = list_rule_metrics()
results.append(print_result("Rule metrics count", len(all_rule) == 7, f"{all_rule}"))

all_types = list_all_metric_types()
results.append(print_result("Metric types", "rule" in all_types and "deepeval_builtin" in all_types, f"types={list(all_types.keys())}"))

# Registry check
for name in all_rule:
    cls = RULE_METRIC_REGISTRY.get(name)
    results.append(print_result(f"Registry: {name}", cls is not None, cls.__name__ if cls else "MISSING"))

# ─── Test 9: Config Validation ────────────────────────────────────

print_header("Test 9: Config Validation")

# Valid config
valid_cfg = {
    "metrics": [
        {"name": "f1", "type": "rule", "weight": 0.3, "threshold": 0.5},
        {"name": "rouge_l", "type": "rule", "weight": 0.3, "threshold": 0.5},
        {"name": "exact_match", "type": "rule", "weight": 0.4, "threshold": 0.8},
    ],
    "parallel": 5,
}
v = validate_evaluator_config(valid_cfg)
results.append(print_result("Valid config", v["valid"], f"errors={v['errors']}"))

# Invalid: empty
v = validate_evaluator_config({"metrics": []})
results.append(print_result("Empty metrics rejected", not v["valid"]))

# Invalid: bad rule name
bad_cfg = {
    "metrics": [{"name": "nonexistent_metric", "type": "rule", "weight": 1.0}],
}
v = validate_evaluator_config(bad_cfg)
results.append(print_result("Bad rule name rejected", not v["valid"]))

# Weight warning
weight_cfg = {
    "metrics": [
        {"name": "f1", "type": "rule", "weight": 0.3},
        {"name": "rouge_l", "type": "rule", "weight": 0.3},
    ],
}
v = validate_evaluator_config(weight_cfg)
results.append(print_result("Weight warning", len(v["warnings"]) > 0, f"warnings={v['warnings']}"))

# ─── Test 10: Build Rule Metrics ──────────────────────────────────

print_header("Test 10: Build Rule Metrics")
from evaluation.metrics_builder import build_metrics

# Build only rule metrics (no judge needed)
rule_config = {
    "metrics": [
        {"name": "f1", "type": "rule", "weight": 0.25, "threshold": 0.5},
        {"name": "rouge_l", "type": "rule", "weight": 0.25, "threshold": 0.5},
        {"name": "exact_match", "type": "rule", "weight": 0.2, "threshold": 0.8},
        {"name": "bleu", "type": "rule", "weight": 0.15, "threshold": 0.3},
        {"name": "string_similarity", "type": "rule", "weight": 0.15, "threshold": 0.6},
    ],
}

try:
    built = build_metrics(rule_config)
    results.append(print_result("Built 5 rule metrics", len(built) == 5, f"got {len(built)}"))
except Exception as e:
    results.append(print_result("Built 5 rule metrics", False, str(e)))
    built = []

# ─── Test 11: Dry Runner ──────────────────────────────────────────

print_header("Test 11: Metric Dry Runner")
from evaluation.metrics_dryrun import MetricDryRunner

if built:
    dry = MetricDryRunner(built)
    samples = [
        {
            "input": "北京有哪些著名的景点？",
            "actual_output": "北京著名的景点有故宫、长城、天坛、颐和园等。",
            "expected_output": "北京著名的景点有故宫、长城、天坛、颐和园等。",
        },
        {
            "input": "推荐一个餐厅",
            "actual_output": "推荐海底捞火锅",
            "expected_output": "我推荐你去海底捞，服务非常好。",
        },
    ]

    try:
        dry_result = dry.run(samples, max_samples=2)
        results.append(print_result("Dry run completed", "total_samples" in dry_result, f"samples={dry_result['total_samples']}"))
        results.append(print_result("Dry run has results", len(dry_result["results"]) > 0))

        if dry_result["results"]:
            r0 = dry_result["results"][0]
            results.append(print_result("Sample 0 has metrics", len(r0["metrics"]) > 0, f"{list(r0['metrics'].keys())}"))
            results.append(print_result("Sample 0 overall_score", 0 <= r0["overall_score"] <= 1, f"score={r0['overall_score']:.3f}"))

        summary = dry_result["summary"]
        results.append(print_result("Summary avg_score", 0 <= summary["avg_score"] <= 1, f"avg={summary['avg_score']:.3f}"))
        results.append(print_result("Summary pass_rate", 0 <= summary["pass_rate"] <= 1, f"rate={summary['pass_rate']:.3f}"))

    except Exception as e:
        results.append(print_result("Dry run", False, str(e)))
        import traceback; traceback.print_exc()
else:
    results.append(print_result("Dry run", False, "No metrics built"))

# ─── Test 12: DeepEval Built-in Registry ──────────────────────────

print_header("Test 12: DeepEval Built-in Registry")
from evaluation.metrics.deepeval_builtin import (
    list_deepeval_metrics,
    is_deepeval_builtin,
    get_deepeval_metric_class,
)

builtin_names = list_deepeval_metrics()
results.append(print_result("Built-in metrics listed", len(builtin_names) > 0, f"count={len(builtin_names)}"))

results.append(print_result("answer_relevancy is builtin", is_deepeval_builtin("answer_relevancy")))
results.append(print_result("faithfulness is builtin", is_deepeval_builtin("faithfulness")))
results.append(print_result("fake_metric not builtin", not is_deepeval_builtin("fake_metric")))

# ─── Summary ───────────────────────────────────────────────────────

print_header("Metrics Test Summary")

passed = sum(1 for r in results if r)
total = len(results)
print(f"\n  Results: {passed}/{total} tests passed")

if passed == total:
    print("\n  🎉 All metric tests passed!")
elif passed >= total * 0.8:
    print("\n  ✅ Most tests passed. Minor issues to review.")
else:
    print("\n  ⚠️  Several tests failed. Review errors above.")

print(f"\n{'='*60}\n")
sys.exit(0 if passed == total else 1)
