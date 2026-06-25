"""
End-to-end test: SSE Agent Collector with golden dataset samples.
Tests 5 representative samples from different query categories.
"""

import asyncio
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(__file__))

from evaluation.collectors.sse_agent_collector import SSEAgentCollector

# ─── Agent endpoint configuration (matching the curl) ──────────────
ENDPOINT_CONFIG = {
    "endpoint_url": "https://wlyd-hw-base-api.10000da.vip/corp-map-app/v3/chat/simple",
    "method": "POST",
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
    "timeout": 60,
    "retry_times": 2,
    "sse_event_field": "text",
    "sse_done_marker": "finish",
    "default_user_id": "2044624489342554114",
    "default_conv_id": "1144308167",
}

# ─── Golden dataset samples (from 黄金数据集构造.xlsx, Sheet: 单轮) ──
SAMPLES = [
    {
        "id": 1,
        "category": "企业工商查询",
        "query": "帮我查一下成都环智网络科技有限公司的参保人数和曾用名",
        "expected_keywords": ["成都环智", "工商", "法定代表人"],
    },
    {
        "id": 2,
        "category": "企业状态查询",
        "query": "查一下\"上海觅古文化传播有限公司\"的工商状态是否正常",
        "expected_keywords": ["上海觅古", "存续", "登记状态"],
    },
    {
        "id": 3,
        "category": "价格预测",
        "query": "猪肉价格近期会反弹吗？",
        "expected_keywords": ["猪肉", "价格"],
    },
    {
        "id": 4,
        "category": "商机推荐",
        "query": "最近有什么商机？",
        "expected_keywords": ["商机"],
    },
    {
        "id": 5,
        "category": "企业简称查询",
        "query": "查华为",
        "expected_keywords": ["华为"],
    },
]


def print_header(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_result(sample_id, category, query, output, latency_ms, error, keywords_found):
    status = "PASS" if output and not error else "FAIL"
    color = "\033[92m" if status == "PASS" else "\033[91m"
    reset = "\033[0m"

    print(f"\n  [{color}{status}{reset}] Sample #{sample_id} — {category}")
    print(f"  Query: {query}")
    if error:
        print(f"  Error: {error}")
    if output:
        print(f"  Output ({len(output)} chars, {latency_ms}ms):")
        # Show first 300 chars
        preview = output[:300].replace("\n", " ")
        print(f"    {preview}...")
    if keywords_found:
        print(f"  Keywords matched: {', '.join(keywords_found)}")
    print(f"  Latency: {latency_ms}ms")


async def run_tests():
    print_header("SSE Agent Collector — Golden Dataset E2E Test")
    print(f"  Endpoint: {ENDPOINT_CONFIG['endpoint_url']}")
    print(f"  Samples: {len(SAMPLES)}")
    print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    collector = SSEAgentCollector(ENDPOINT_CONFIG)

    passed = 0
    failed = 0
    results_summary = []

    for i, sample in enumerate(SAMPLES):
        # Use unique convId per sample to avoid conversation context mixing
        sample_config = {**ENDPOINT_CONFIG, "default_conv_id": str(1144308240 + i)}
        test_collector = SSEAgentCollector(sample_config)

        print(f"\n  [{i+1}/{len(SAMPLES)}] Testing: {sample['query'][:50]}...")
        result = await test_collector.collect(sample["query"])

        output = result["output"]
        error = result["error"]
        latency = result["latency_ms"]

        # Check keyword matches
        keywords_found = []
        for kw in sample["expected_keywords"]:
            if kw.lower() in output.lower():
                keywords_found.append(kw)

        if output and not error:
            passed += 1
        else:
            failed += 1

        print_result(
            sample["id"], sample["category"], sample["query"],
            output, latency, error, keywords_found,
        )

        results_summary.append({
            "id": sample["id"],
            "category": sample["category"],
            "query": sample["query"],
            "status": "PASS" if output and not error else "FAIL",
            "output_length": len(output),
            "latency_ms": latency,
            "error": error,
            "keywords_matched": keywords_found,
        })

        # Brief pause between requests to be polite
        if i < len(SAMPLES) - 1:
            await asyncio.sleep(1)

    # ─── Summary ────────────────────────────────────────────────────
    print_header("Test Summary")
    total = passed + failed
    print(f"  Total:  {total}")
    print(f"  Passed: \033[92m{passed}\033[0m")
    print(f"  Failed: \033[91m{failed}\033[0m")
    print(f"  Rate:   {passed/total*100:.0f}%")

    # Average latency
    latencies = [r["latency_ms"] for r in results_summary if r["status"] == "PASS"]
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        print(f"  Avg Latency: {avg_latency:.0f}ms")

    # Output lengths
    lengths = [r["output_length"] for r in results_summary if r["status"] == "PASS"]
    if lengths:
        print(f"  Avg Output:  {sum(lengths)/len(lengths):.0f} chars")

    print(f"\n  {'=' * 60}")
    if failed == 0:
        print("  \033[92m All tests PASSED! Pipeline is working correctly.\033[0m")
    else:
        print(f"  \033[91m {failed} test(s) FAILED. Check errors above.\033[0m")
    print(f"  {'=' * 60}\n")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
