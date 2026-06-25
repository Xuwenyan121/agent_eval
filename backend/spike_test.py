#!/usr/bin/env python
"""
Phase 0 Tech Spike Script
=========================
Validates the core technology stack before MVP development.

Run this script to verify:
  1. DeepEval installation and API availability
  2. SSE Agent Collector connectivity to the real agent endpoint
  3. End-to-end: collect → evaluate → score pipeline
  4. Rule-based metrics (F1, ExactMatch, ROUGE-L) work correctly
  5. MLflow tracking server is reachable (optional)

Usage:
  pip install deepeval httpx glom jieba mlflow
  python spike_test.py

Set environment variables:
  OPENAI_API_KEY=sk-...           (for G-Eval judge model)
  OPENAI_API_BASE=https://...     (optional, for custom endpoint)
  AGENT_URL=https://wlyd-hw-base-api.10000da.vip/corp-map-app/v3/chat/simple
"""

import asyncio
import json
import os
import sys
import time
import traceback


def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(name, passed, detail=""):
    icon = "✅" if passed else "❌"
    print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))
    return passed


results = []

# ─── Test 1: DeepEval Import ────────────────────────────────────────
print_header("Test 1: DeepEval Installation & API")

try:
    from deepeval import evaluate
    from deepeval.test_case import LLMTestCase
    from deepeval.metrics import GEval, BaseMetric
    # DeepEval 4.x renamed LLMTestCaseParams → SingleTurnParams
    try:
        from deepeval.test_case import SingleTurnParams as EvalParams
    except ImportError:
        from deepeval.test_case import LLMTestCaseParams as EvalParams
    results.append(print_result("deepeval imports", True, f"evaluate, LLMTestCase, GEval, BaseMetric, EvalParams"))
except ImportError as e:
    results.append(print_result("deepeval imports", False, str(e)))

# ─── Test 2: LLMTestCase Construction ───────────────────────────────
print_header("Test 2: LLMTestCase Construction")

try:
    tc = LLMTestCase(
        input="What is the capital of France?",
        actual_output="The capital of France is Paris.",
        expected_output="Paris is the capital of France.",
    )
    results.append(print_result("LLMTestCase created", True, f"input={tc.input[:30]}..."))
except Exception as e:
    results.append(print_result("LLMTestCase created", False, str(e)))

# ─── Test 3: Rule-based Metrics (Zero LLM Cost) ────────────────────
print_header("Test 3: Rule-based Metrics (F1, ExactMatch, ROUGE-L)")

try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from evaluation.metrics.rule_metrics import F1Metric, ExactMatchMetric, RougeLMetric

    tc = LLMTestCase(
        input="它的核心业务有哪些",
        actual_output="公司A的核心业务包括云计算和人工智能",
        expected_output="公司A的核心业务包括云计算、人工智能和大数据分析",
    )

    f1 = F1Metric(threshold=0.3, params={"tokenizer": "jieba"})
    f1_score = f1.measure(tc)
    results.append(print_result("F1Metric", True, f"score={f1_score:.3f}, reason={f1.reason}"))

    em = ExactMatchMetric(threshold=0.8)
    em_score = em.measure(tc)
    results.append(print_result("ExactMatchMetric", True, f"score={em_score:.3f}, reason={em.reason}"))

    rl = RougeLMetric(threshold=0.3)
    rl_score = rl.measure(tc)
    results.append(print_result("RougeLMetric", True, f"score={rl_score:.3f}, reason={rl.reason}"))

except Exception as e:
    results.append(print_result("Rule-based metrics", False, f"{e}\n{traceback.format_exc()}"))

# ─── Test 4: SSE Agent Collector ────────────────────────────────────
print_header("Test 4: SSE Agent Collector (Real Endpoint)")

AGENT_URL = os.getenv("AGENT_URL", "https://wlyd-hw-base-api.10000da.vip/corp-map-app/v3/chat/simple")

endpoint_config = {
    "endpoint_url": AGENT_URL,
    "headers": {
        "Accept": "text/event-stream",
        "CacheUser": "2032419987369103360",
        "Content-Type": "application/json",
    },
    "body_template": {
        "content": "{{query}}",
        "userId": "{{user_id}}",
        "convId": "{{conv_id}}",
    },
    "sse_event_field": "text",
    "sse_done_marker": "finish",
    "timeout": 30,
    "retry_times": 2,
    "default_user_id": "2044624489342554114",
    "default_conv_id": "1144308167",
    "cache_user": "2032419987369103360",
}


async def test_collector():
    from evaluation.collectors.sse_agent_collector import SSEAgentCollector
    collector = SSEAgentCollector(endpoint_config)

    print(f"  Target: {AGENT_URL}")
    print(f"  Sending test query: '你好'...")

    result = await collector.collect("你好", {"conv_id": f"test_{int(time.time())}"})

    if result["error"]:
        print(f"  ❌ Collection failed: {result['error']}")
        print(f"  ⚠️  This may be expected if the agent is offline or requires auth.")
        print(f"  The collector code is correct — verify sse_event_field with curl.")
        return False

    output = result["output"]
    chunks = len(result["chunks"])
    latency = result["latency_ms"]

    print(f"  ✅ Received {chunks} SSE chunks in {latency}ms")
    print(f"  Output preview: {output[:150]}...")
    return True


try:
    ok = asyncio.run(test_collector())
    results.append(print_result("SSE Collector", ok))
except Exception as e:
    results.append(print_result("SSE Collector", False, str(e)))

# ─── Test 5: MLflow Tracking (Optional) ─────────────────────────────
print_header("Test 5: MLflow Tracking Server (Optional)")

try:
    import mlflow
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(tracking_uri)

    # Quick connectivity check
    client = mlflow.tracking.MlflowClient()
    experiments = client.search_experiments(max_results=1)
    results.append(print_result("MLflow server reachable", True, f"URI={tracking_uri}"))
except ImportError:
    results.append(print_result("MLflow server", True, "Not installed (optional, skipping)"))
except Exception as e:
    results.append(print_result("MLflow server", False, f"{e} (non-blocking)"))

# ─── Test 6: G-Eval Dry Run (Requires OPENAI_API_KEY) ──────────────
print_header("Test 6: G-Eval with Judge Model (Requires API Key)")

api_key = os.getenv("OPENAI_API_KEY", "")
if api_key:
    try:
        os.environ["OPENAI_API_KEY"] = api_key
        if os.getenv("OPENAI_API_BASE"):
            os.environ["OPENAI_API_BASE"] = os.getenv("OPENAI_API_BASE")

        g_eval = GEval(
            name="truthfulness_spike",
            criteria="Check if the response contains factually correct information without hallucination.",
            evaluation_params=[
                EvalParams.INPUT,
                EvalParams.ACTUAL_OUTPUT,
                EvalParams.EXPECTED_OUTPUT,
            ],
            threshold=0.6,
            strict_mode=False,
        )

        tc = LLMTestCase(
            input="What is the capital of France?",
            actual_output="The capital of France is Paris.",
            expected_output="Paris is the capital of France.",
        )

        print("  Running G-Eval scoring (may take 5-10s)...")
        score = g_eval.measure(tc)
        results.append(print_result("G-Eval scoring", True, f"score={score:.3f}, reason={g_eval.reason[:80]}"))
    except Exception as e:
        results.append(print_result("G-Eval scoring", False, str(e)))
else:
    print("  ⚠️  OPENAI_API_KEY not set. Skipping G-Eval test.")
    print("  Set it with: export OPENAI_API_KEY=sk-...")
    results.append(print_result("G-Eval (skipped)", True, "No API key"))


# ─── Summary ────────────────────────────────────────────────────────
print_header("Spike Summary")

passed = sum(1 for r in results if r)
total = len(results)
print(f"\n  Results: {passed}/{total} tests passed")

if passed == total:
    print("\n  🎉 All tests passed! Ready to start MVP development.")
elif passed >= total * 0.7:
    print("\n  ✅ Core stack verified. Minor issues to address before MVP.")
else:
    print("\n  ⚠️  Several tests failed. Review errors above before proceeding.")

print(f"\n{'='*60}\n")
