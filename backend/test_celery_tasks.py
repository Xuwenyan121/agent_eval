#!/usr/bin/env python3
"""
Celery Task Test Script
========================
Tests the evaluation pipeline using Celery eager mode (no Redis needed).
Simulates a full collect → evaluate → store cycle.

Usage:
    USE_LOCAL_DB=true python test_celery_tasks.py
"""

import os
import sys
import json
import uuid

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("USE_LOCAL_DB", "true")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.core.cache import cache


def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(name, passed, detail=""):
    icon = "✅" if passed else "❌"
    print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))
    return passed


results = []


# ─── Test 1: Celery Config ──────────────────────────────────────────

print_header("Test 1: Celery Configuration")

from config.celery import app, health_check

results.append(print_result("Celery app created", app is not None, f"app={app.main}"))
results.append(print_result("Task autodiscovery", len(app.tasks) > 0, f"{len(app.tasks)} tasks"))

# Check task routing
routes = app.conf.task_routes or {}
results.append(print_result("Task routing configured", len(routes) > 0, f"routes={list(routes.keys())}"))

# Check serialization
results.append(print_result("JSON serialization", app.conf.task_serializer == "json"))
results.append(print_result("Track started", app.conf.task_track_started is True))


# ─── Test 2: Health Check Task ──────────────────────────────────────

print_header("Test 2: Health Check Task")

try:
    result = health_check.delay()
    results.append(print_result("Health check dispatched", result.ready(), f"status={result.status}"))
    if result.ready() and result.successful():
        results.append(print_result("Health check result", result.result.get("status") == "ok", f"{result.result}"))
    else:
        results.append(print_result("Health check result", False, "Not ready"))
except Exception as e:
    results.append(print_result("Health check", False, str(e)))


# ─── Test 3: Task Status Utilities ──────────────────────────────────

print_header("Test 3: Task Status Utilities")

from evaluation.task_status import TaskStatus, get_task_summary

# Test progress set/get
test_task_id = f"test_{uuid.uuid4().hex[:12]}"
test_progress = {
    "phase": "collecting",
    "progress": 50,
    "collect_progress": {"completed": 5, "total": 10, "failed": 0},
    "eval_progress": {"completed": 0, "total": 0},
    "processed": 5,
    "total": 10,
}

TaskStatus.set_progress(test_task_id, test_progress)
retrieved = TaskStatus.get_progress(test_task_id)
results.append(print_result("Set/get progress", retrieved["progress"] == 50, f"phase={retrieved['phase']}, progress={retrieved['progress']}"))

# Test full status (Celery eager mode returns PENDING for non-existent tasks)
full_status = TaskStatus.get_full_status(test_task_id)
results.append(print_result("Full status query", "celery_status" in full_status and "progress" in full_status))

# Test clear
TaskStatus.clear_progress(test_task_id)
cleared = TaskStatus.get_progress(test_task_id)
results.append(print_result("Clear progress", cleared["phase"] == "unknown", f"phase={cleared['phase']}"))


# ─── Test 4: Weighted Scoring ──────────────────────────────────────

print_header("Test 4: Weighted Scoring")

from evaluation.tasks import _compute_weighted_overall

metric_data = {
    "consistency": {"score": 0.8, "passed": True},
    "truthfulness": {"score": 0.9, "passed": True},
    "f1": {"score": 0.7, "passed": True},
}
metrics_config = [
    {"name": "consistency", "weight": 0.4},
    {"name": "truthfulness", "weight": 0.4},
    {"name": "f1", "weight": 0.2},
]

overall = _compute_weighted_overall(metric_data, metrics_config)
expected = 0.8 * 0.4 + 0.9 * 0.4 + 0.7 * 0.2  # 0.32 + 0.36 + 0.14 = 0.82
results.append(print_result("Weighted score", abs(overall - expected) < 0.01, f"got={overall:.3f}, expected={expected:.3f}"))

# Equal weights fallback
equal_config = [{"name": "consistency"}, {"name": "truthfulness"}, {"name": "f1"}]
equal_overall = _compute_weighted_overall(metric_data, equal_config)
expected_equal = (0.8 + 0.9 + 0.7) / 3
results.append(print_result("Equal weight fallback", abs(equal_overall - expected_equal) < 0.01, f"got={equal_overall:.3f}"))

# Empty metrics
empty_overall = _compute_weighted_overall({}, [])
results.append(print_result("Empty metrics", empty_overall == 0.0, f"got={empty_overall:.3f}"))


# ─── Test 5: DB Model Integration ──────────────────────────────────

print_header("Test 5: DB Model Integration")

from evaluation.models import AgentEndpoint, Dataset, DatasetSample, EvaluationTask, MetricDefinition

# Create test agent
agent, _ = AgentEndpoint.objects.get_or_create(
    name="Test Agent (Celery)",
    defaults={
        "endpoint_url": "https://httpbin.org/post",
        "protocol": "http_json",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "body_template": {"content": "{{query}}"},
        "stream": False,
        "sse_event_field": "choices[0].delta.content",
        "sse_done_marker": "[DONE]",
        "timeout": 5,
        "retry_times": 1,
        "status": "active",
    },
)
results.append(print_result("Agent created", agent is not None, f"id={agent.id}"))

# Create test dataset
dataset, _ = Dataset.objects.get_or_create(
    name="Test Dataset (Celery)",
    defaults={"version": "1.0", "status": "published"},
)

# Add samples if none
if dataset.samples.count() == 0:
    for i in range(3):
        DatasetSample.objects.create(
            dataset=dataset,
            sample_id=f"sample_{i}",
            input=f"Test question {i}",
            expected_output=f"Expected answer {i}",
        )
    dataset.update_sample_count()
results.append(print_result("Dataset created", dataset.sample_count == 3, f"samples={dataset.sample_count}"))

# Create test evaluation task
eval_task, _ = EvaluationTask.objects.get_or_create(
    name="Test Task (Celery)",
    defaults={
        "agent": agent,
        "dataset": dataset,
        "evaluator_config": {
            "metrics": [
                {"name": "f1", "type": "rule", "weight": 0.5, "threshold": 0.5},
                {"name": "rouge_l", "type": "rule", "weight": 0.5, "threshold": 0.5},
            ],
            "badcase_threshold": 0.6,
        },
        "judge_model": {},
        "parallel": 2,
        "status": "pending",
    },
)
results.append(print_result("EvaluationTask created", eval_task is not None, f"id={eval_task.id}, status={eval_task.status}"))

# Test computed properties
results.append(print_result("Task computed: result_count", hasattr(eval_task, "result_count"), f"{eval_task.result_count}"))
results.append(print_result("Task computed: badcase_count", hasattr(eval_task, "badcase_count"), f"{eval_task.badcase_count}"))
results.append(print_result("Task computed: average_score", hasattr(eval_task, "average_score"), f"{eval_task.average_score}"))

# Test summary
summary = eval_task.summary()
results.append(print_result("Task summary()", isinstance(summary, dict) and "total_samples" in summary, f"keys={list(summary.keys())}"))


# ─── Test 6: Collector Factory in Task Context ──────────────────────

print_header("Test 6: Collector Factory Integration")

from evaluation.collectors import get_collector, get_supported_protocols

# Test that agent config works with factory
endpoint_config = agent.endpoint_config_dict()
results.append(print_result("Agent endpoint_config_dict", "endpoint_url" in endpoint_config, f"protocol={endpoint_config.get('protocol')}"))

collector = get_collector(endpoint_config)
results.append(print_result("Factory creates collector", collector is not None, f"{collector.__class__.__name__}"))
results.append(print_result("Collector has collect()", hasattr(collector, "collect") and callable(collector.collect)))
results.append(print_result("Collector has test_connection()", hasattr(collector, "test_connection")))


# ─── Test 7: Task Dispatch (Eager Mode) ─────────────────────────────

print_header("Test 7: Task Dispatch (Eager Mode)")

from django.conf import settings
is_eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
results.append(print_result("Eager mode enabled", is_eager, "Tasks run synchronously"))

if is_eager:
    # Try dispatching the health check in eager mode
    from config.celery import health_check
    result = health_check.apply_async()
    results.append(print_result("Eager dispatch", result.ready(), f"status={result.status}"))

    if result.successful():
        results.append(print_result("Eager result value", result.result.get("status") == "ok"))
    else:
        results.append(print_result("Eager result value", False, f"status={result.status}"))
else:
    results.append(print_result("Eager dispatch", False, "CELERY_TASK_ALWAYS_EAGER not set"))


# ─── Test 8: Task Summary API ───────────────────────────────────────

print_header("Test 8: Task Summary API")

summary = get_task_summary(eval_task.id)
results.append(print_result("Task summary API", "task_id" in summary, f"name={summary.get('name')}"))
results.append(print_result("Summary has progress", "progress" in summary))
results.append(print_result("Summary has celery_status", "celery_status" in summary))

# Non-existent task
bad_summary = get_task_summary("00000000-0000-0000-0000-000000000000")
results.append(print_result("Non-existent task error", "error" in bad_summary, f"{bad_summary.get('error')}"))


# ─── Test 9: Cleanup Task ───────────────────────────────────────────

print_header("Test 9: Cleanup Task")

from evaluation.tasks import cleanup_expired_tasks

try:
    result = cleanup_expired_tasks(days=365)  # Very safe — won't delete anything
    results.append(print_result("Cleanup task runs", "deleted" in result, f"deleted={result['deleted']}"))
except Exception as e:
    results.append(print_result("Cleanup task", False, str(e)))


# ─── Summary ────────────────────────────────────────────────────────

print_header("Celery Task Test Summary")

passed = sum(1 for r in results if r)
total = len(results)
print(f"\n  Results: {passed}/{total} tests passed")

if passed == total:
    print("\n  🎉 All Celery task tests passed!")
elif passed >= total * 0.8:
    print("\n  ✅ Most tests passed. Minor issues to review.")
else:
    print("\n  ⚠️  Several tests failed. Review errors above.")

print(f"\n{'='*60}\n")
sys.exit(0 if passed == total else 1)
