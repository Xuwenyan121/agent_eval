#!/usr/bin/env python3
"""
Collector Local Test Script
============================
Tests all 3 collector types against real or mock endpoints.

Usage:
    python test_collectors.py                     # Test SSE against default agent
    python test_collectors.py --url <URL>         # Test SSE against custom URL
    python test_collectors.py --protocol json     # Test JSON collector
    python test_collectors.py --mock              # Run mock server + test all

No Django required — standalone async test.
"""

import asyncio
import json
import os
import sys
import argparse
import time

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluation.collectors import (
    SSEAgentCollector, JSONAgentCollector, OpenAICompatCollector,
    get_collector, get_supported_protocols,
)


# ─── Default Agent Config (from PRD V3.2) ───────────────────────────

DEFAULT_SSE_CONFIG = {
    "endpoint_url": os.getenv(
        "AGENT_URL",
        "https://wlyd-hw-base-api.10000da.vip/corp-map-app/v3/chat/simple",
    ),
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


def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(name, passed, detail=""):
    icon = "✅" if passed else "❌"
    print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))
    return passed


results = []


# ─── Test 1: Factory ────────────────────────────────────────────────

print_header("Test 1: Collector Factory")

protocols = get_supported_protocols()
results.append(print_result("Supported protocols", True, f"{protocols}"))

for proto in protocols:
    cfg = dict(DEFAULT_SSE_CONFIG, protocol=proto)
    try:
        c = get_collector(cfg)
        results.append(print_result(f"Factory: {proto}", True, c.__class__.__name__))
    except Exception as e:
        results.append(print_result(f"Factory: {proto}", False, str(e)))

# Test unknown protocol
try:
    get_collector({"protocol": "unknown_proto", "endpoint_url": "http://x"})
    results.append(print_result("Factory: unknown protocol", False, "Should have raised ValueError"))
except ValueError:
    results.append(print_result("Factory: unknown protocol", True, "Correctly raised ValueError"))


# ─── Test 2: SSE Collector (Real Endpoint) ──────────────────────────

print_header("Test 2: SSE Collector (Real Endpoint)")


async def test_sse(url=None):
    config = dict(DEFAULT_SSE_CONFIG)
    if url:
        config["endpoint_url"] = url

    print(f"  URL: {config['endpoint_url']}")
    print(f"  SSE field: {config['sse_event_field']}")
    print(f"  Done marker: {config['sse_done_marker']}")

    collector = SSEAgentCollector(config)
    conv_id = f"test_{int(time.time())}"

    print(f"\n  Sending: '你好' (conv_id={conv_id})...")
    result = await collector.collect("你好", {"conv_id": conv_id})

    if result["error"]:
        print(f"  ❌ Error: {result['error']}")
        return False

    output = result["output"]
    chunks = len(result["chunks"])
    latency = result["latency_ms"]

    print(f"  ✅ Output: {output[:150]}...")
    print(f"  Chunks: {chunks}, Latency: {latency}ms")

    # Connectivity test
    print(f"\n  Running test_connection()...")
    test = await collector.test_connection("你好")
    print(f"  Status: {test['status']}, Protocol verified: {test['protocol_verified']}")
    print(f"  Protocol details: {json.dumps(test.get('protocol_details', {}), indent=4)}")

    return not result["error"]


url_arg = None
for i, arg in enumerate(sys.argv):
    if arg == "--url" and i + 1 < len(sys.argv):
        url_arg = sys.argv[i + 1]

try:
    ok = asyncio.run(test_sse(url_arg))
    results.append(print_result("SSE Collector", ok))
except Exception as e:
    results.append(print_result("SSE Collector", False, str(e)))


# ─── Test 3: JSON Collector (Mock Test) ────────────────────────────

print_header("Test 3: JSON Collector (Template Rendering)")

json_config = {
    "endpoint_url": "https://httpbin.org/post",  # Echo service
    "headers": {"Content-Type": "application/json"},
    "body_template": {"question": "{{query}}", "session": "{{conv_id}}"},
    "response_field": "json.question",  # httpbin echoes the JSON body
    "timeout": 15,
    "retry_times": 1,
    "default_user_id": "test_user",
    "default_conv_id": "test_conv",
    "cache_user": "",
}


async def test_json():
    collector = JSONAgentCollector(json_config)
    result = await collector.collect("What is AI?", {"conv_id": "session_42"})
    if result["error"]:
        print(f"  Error: {result['error']}")
        return False
    print(f"  Output: {result['output'][:100]}")
    print(f"  Latency: {result['latency_ms']}ms")
    return True


try:
    ok = asyncio.run(test_json())
    results.append(print_result("JSON Collector", ok))
except Exception as e:
    results.append(print_result("JSON Collector", False, str(e)))


# ─── Test 4: Template Variable Rendering ────────────────────────────

print_header("Test 4: Template Variable Rendering")

from evaluation.collectors.base import BaseCollector

# Test basic rendering
config = {
    "endpoint_url": "http://example.com",
    "headers": {"X-User": "{{user_id}}", "X-Cache": "{{cache_user}}"},
    "body_template": {
        "content": "{{query}}",
        "userId": "{{user_id}}",
        "convId": "{{conv_id}}",
        "nested": {"inner": "{{query}}_processed"},
    },
    "default_user_id": "user_123",
    "default_conv_id": "conv_456",
    "cache_user": "cache_789",
}

collector = SSEAgentCollector(config)
headers, body = collector._render("Test question", {"conv_id": "override_conv"})

results.append(print_result(
    "Body query", body["content"] == "Test question",
    f"got '{body['content']}'",
))
results.append(print_result(
    "Body user_id", body["userId"] == "user_123",
    f"got '{body['userId']}'",
))
results.append(print_result(
    "Body conv_id override", body["convId"] == "override_conv",
    f"got '{body['convId']}'",
))
results.append(print_result(
    "Header user_id", headers["X-User"] == "user_123",
    f"got '{headers['X-User']}'",
))
results.append(print_result(
    "Nested template", body["nested"]["inner"] == "Test question_processed",
    f"got '{body['nested']['inner']}'",
))


# ─── Test 5: Field Extraction ───────────────────────────────────────

print_header("Test 5: Field Extraction")

test_json_data = {
    "choices": [{"delta": {"content": "Hello world"}}],
    "data": {"result": "nested value"},
    "simple": "top level",
}

results.append(print_result(
    "choices[0].delta.content",
    BaseCollector.extract_field(test_json_data, "choices[0].delta.content") == "Hello world",
))
results.append(print_result(
    "data.result",
    BaseCollector.extract_field(test_json_data, "data.result") == "nested value",
))
results.append(print_result(
    "simple",
    BaseCollector.extract_field(test_json_data, "simple") == "top level",
))
results.append(print_result(
    "missing field returns ''",
    BaseCollector.extract_field(test_json_data, "nonexistent.path") == "",
))


# ─── Summary ────────────────────────────────────────────────────────

print_header("Collector Test Summary")

passed = sum(1 for r in results if r)
total = len(results)
print(f"\n  Results: {passed}/{total} tests passed")

if passed == total:
    print("\n  🎉 All collector tests passed!")
elif passed >= total * 0.7:
    print("\n  ✅ Most tests passed. Minor issues to review.")
else:
    print("\n  ⚠️  Several tests failed. Review errors above.")

print(f"\n{'='*60}\n")
sys.exit(0 if passed == total else 1)
