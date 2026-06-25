"""
Celery tasks: orchestrates the full evaluation pipeline.
  1. Collection: call Agent endpoint concurrently (supports SSE/JSON/OpenAI protocols)
  2. Evaluation: DeepEval scoring on collected LLMTestCases
  3. Storage: persist results + traces to database
  4. Tracking: log to MLflow (non-blocking, best-effort)
"""

import asyncio
import logging
import uuid
import time

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


# ─── Progress Helpers ────────────────────────────────────────────────

def _update_progress(task_id: str, phase: str, collect_done: int, collect_total: int,
                     collect_failed: int, eval_done: int, eval_total: int):
    """Update real-time progress in cache for frontend polling."""
    total = collect_total + eval_total
    done = collect_done + eval_done
    progress = int(done / total * 100) if total else 0
    cache.set(f"task_progress:{task_id}", {
        "phase": phase,
        "progress": progress,
        "collect_progress": {
            "completed": collect_done,
            "total": collect_total,
            "failed": collect_failed,
        },
        "eval_progress": {
            "completed": eval_done,
            "total": eval_total,
        },
        "processed": done,
        "total": total,
        "updated_at": time.time(),
    }, timeout=3600)


# ─── Weighted Scoring ────────────────────────────────────────────────

def _compute_weighted_overall(metric_data: dict, metrics_config: list) -> float:
    """
    Compute weighted overall score from per-metric results.
    Falls back to simple average if no weights configured.
    """
    weight_map = {m["name"]: m.get("weight", 1.0) for m in metrics_config}
    weighted_sum = 0.0
    weight_sum = 0.0
    for metric_name, data in metric_data.items():
        score = data.get("score")
        if score is None:
            continue
        w = weight_map.get(metric_name, 1.0)
        weighted_sum += score * w
        weight_sum += w
    return weighted_sum / weight_sum if weight_sum > 0 else 0.0


# ─── MLflow Tracking (Non-blocking) ─────────────────────────────────

def _log_to_mlflow(task, metric_aggregates: dict, overall: float):
    """
    Log evaluation results to MLflow Tracking.
    Failures are silently ignored — MLflow is supplementary.
    """
    try:
        import mlflow
        from django.conf import settings

        mlflow.set_tracking_uri(
            getattr(settings, "MLFLOW_TRACKING_URI", None) or "http://localhost:5000"
        )

        experiment_name = f"agent_eval/{task.agent.name}"
        mlflow.set_experiment(experiment_name)

        with mlflow.start_run(run_name=task.name) as run:
            mlflow.log_params({
                "agent_name": task.agent.name,
                "agent_endpoint": task.agent.endpoint_url,
                "dataset_name": task.dataset.name,
                "dataset_version": task.dataset.version,
                "judge_model": task.judge_model.get("model", "unknown"),
                "sample_count": task.evaluation_results.count(),
                "badcase_threshold": task.evaluator_config.get("badcase_threshold", 0.6),
                "task_id": str(task.id),
            })
            mlflow.set_tags({
                "type": "agent_evaluation",
                "agent_id": str(task.agent_id),
                "dataset_id": str(task.dataset_id),
            })
            mlflow.log_metric("overall_score", overall)
            for metric_name, avg_score in metric_aggregates.items():
                mlflow.log_metric(f"dim_{metric_name}", avg_score)

            task.mlflow_run_id = run.info.run_id
            task.save(update_fields=["mlflow_run_id"])

        logger.info("MLflow run logged: %s", run.info.run_id)

    except ImportError:
        logger.debug("MLflow not installed, skipping tracking")
    except Exception as e:
        logger.warning("MLflow logging failed (non-blocking): %s", e)


# ─── Main Evaluation Task ────────────────────────────────────────────

@shared_task(bind=True, max_retries=2, acks_late=True)
def run_evaluation_task(self, task_id: str):
    """
    Execute the full evaluation pipeline:
    1. Collect: concurrently call Agent endpoint (auto-detects protocol)
    2. Evaluate: run DeepEval metrics on collected test cases
    3. Store: persist results and traces to database
    4. Track: log summary to MLflow (best-effort)
    """
    from evaluation.models import EvaluationTask, EvaluationResult, Trace
    from evaluation.collectors import get_collector
    from evaluation.metrics_builder import build_metrics
    from evaluation.task_status import TaskStatus

    try:
        task = EvaluationTask.objects.get(id=task_id)
    except EvaluationTask.DoesNotExist:
        logger.error("EvaluationTask not found: %s", task_id)
        return {"status": "error", "message": f"Task {task_id} not found"}

    # Mark as running
    task.status = "running"
    task.started_at = timezone.now()
    task.save(update_fields=["status", "started_at"])
    logger.info("Starting evaluation: task=%s (%s)", task.name, task_id)

    try:
        result = _run_pipeline(task, task_id)
        # Clear progress cache on success
        TaskStatus.clear_progress(task_id)
        return result
    except Exception as e:
        logger.error("Evaluation pipeline failed: task=%s, error=%s", task.name, e, exc_info=True)
        task.status = "failed"
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "completed_at"])
        TaskStatus.clear_progress(task_id)
        raise


def _run_pipeline(task, task_id: str) -> dict:
    """Internal pipeline execution logic."""
    from evaluation.models import EvaluationResult, Trace
    from evaluation.collectors import get_collector
    from evaluation.metrics_builder import build_metrics
    from deepeval import evaluate
    from deepeval.test_case import LLMTestCase

    # ── Setup ──
    samples = list(
        task.dataset.samples.all()[:task.limit] if task.limit else task.dataset.samples.all()
    )
    total_samples = len(samples)
    logger.info("Pipeline setup: %d samples, parallel=%d", total_samples, task.parallel)

    # Use collector factory to auto-detect protocol
    endpoint_config = task.agent.endpoint_config_dict()
    collector = get_collector(endpoint_config)
    logger.info("Using collector: %s (protocol=%s)", collector.__class__.__name__, endpoint_config.get("protocol", "http_sse"))

    metrics = build_metrics(task.evaluator_config, task.judge_model)
    test_cases = []

    _update_progress(task_id, "collecting", 0, total_samples, 0, 0, 0)

    # ── ConvId strategy ──
    strategy = getattr(task, "conv_id_strategy", "dataset") or "dataset"
    shared_conv_id = str(int(time.time() * 1000))  # numeric timestamp-based
    logger.info("ConvId strategy: %s", strategy)

    # ── Phase 1: Collection ──
    async def collect_all():
        sem = asyncio.Semaphore(task.parallel)
        results = []
        done_count = 0
        fail_count = 0

        async def collect_one(sample):
            nonlocal done_count, fail_count
            async with sem:
                # Build sample_vars based on conv_id_strategy
                sample_vars = {}
                if strategy == "isolated":
                    # Each sample gets a unique numeric convId
                    sample_vars["conv_id"] = str(int(time.time() * 1000) + hash(sample.sample_id) % 100000)
                elif strategy == "shared":
                    sample_vars["conv_id"] = shared_conv_id
                # else "dataset": don't set conv_id — let _render() use the dataset's value
                result = await collector.collect(sample.input, sample_vars)
                if result["error"]:
                    fail_count += 1
                    logger.warning("Collection failed for sample %s: %s", sample.sample_id, result["error"])
                else:
                    done_count += 1
                results.append((sample, result))
                # Update progress every 5 samples or at the end
                if len(results) % 5 == 0 or len(results) == total_samples:
                    _update_progress(task_id, "collecting", done_count, total_samples,
                                     fail_count, 0, 0)

        await asyncio.gather(*[collect_one(s) for s in samples])
        return results

    collected = asyncio.run(collect_all())
    logger.info("Collection complete: %d success, %d failed", total_samples - sum(1 for _, r in collected if r["error"]), sum(1 for _, r in collected if r["error"]))

    # Build DeepEval test cases from collected results
    error_count = 0
    for sample, result in collected:
        if result["error"]:
            EvaluationResult.objects.create(
                task=task, sample_id=sample.sample_id, input=sample.input,
                actual_output="", error=result["error"], is_badcase=True,
                overall_score=0.0,
            )
            error_count += 1
            continue

        tc = LLMTestCase(
            input=sample.input,
            actual_output=result["output"],
            expected_output=sample.expected_output or "",
            context=sample.context if sample.context else None,
            retrieval_context=sample.retrieval_context if sample.retrieval_context else None,
        )
        tc._sample_ref = sample
        tc._collect_result = result
        # Attach meta data for MetaValidationMetric
        tc._actual_meta = result.get("meta") or {}
        tc._expected_meta = getattr(sample, "expected_meta", None) or {}
        test_cases.append(tc)

    _update_progress(task_id, "evaluating", total_samples - error_count,
                     total_samples, error_count, 0, len(test_cases))

    # ── Phase 2: Evaluation ──
    if not test_cases:
        logger.warning("No valid test cases to evaluate")
        task.status = "completed"
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "completed_at"])
        return {"status": "completed", "samples": 0, "errors": error_count}

    logger.info("Evaluating %d test cases with %d metrics", len(test_cases), len(metrics))
    eval_results = evaluate(test_cases=test_cases, metrics=metrics)

    # ── Phase 3: Storage ──
    _update_progress(task_id, "storing", total_samples - error_count,
                     total_samples, error_count, len(test_cases), len(test_cases))

    metrics_config = task.evaluator_config.get("metrics", [])
    metric_aggregates = {}
    badcase_threshold = task.evaluator_config.get("badcase_threshold", 0.6)

    stored_count = 0
    for tc, result in zip(test_cases, eval_results.test_results):
        metric_data = {}
        for mr in result.metrics_data:
            metric_data[mr.name] = {
                "score": mr.score,
                "passed": mr.success,
                "reason": mr.reason,
            }

        overall = _compute_weighted_overall(metric_data, metrics_config)
        collected_result = tc._collect_result

        # Aggregate per-metric scores for MLflow
        for name, data in metric_data.items():
            if data.get("score") is not None:
                metric_aggregates.setdefault(name, []).append(data["score"])

        # Store trace
        collected_meta = collected_result.get("meta") or {}
        trace_spans = [{
            "type": "agent.collect",
            "duration_ms": collected_result["latency_ms"],
            "chunks": len(collected_result["chunks"]),
            "output": collected_result["output"][:500],
        }]
        # Add meta span if available (agentId, convId, title from event: meta)
        if collected_meta:
            trace_spans.append({
                "type": "agent.meta",
                "agent_id": collected_meta.get("agentId", ""),
                "conv_id": collected_meta.get("convId", ""),
                "title": collected_meta.get("title", ""),
                "user_msg_id": collected_meta.get("userMsgId", ""),
                "ai_msg_id": collected_meta.get("aiMsgId", ""),
            })

        trace = Trace.objects.create(
            trace_id=uuid.uuid4().hex,
            task=task,
            sample_id=tc._sample_ref.sample_id,
            spans=trace_spans,
            trace_data=collected_meta,  # Store full meta as trace_data
            final_output=collected_result["output"],
            raw_sse_chunks=collected_result["chunks"][:20],
            total_duration_ms=collected_result["latency_ms"],
        )

        EvaluationResult.objects.create(
            task=task,
            sample_id=tc._sample_ref.sample_id,
            input=tc.input,
            expected_output=tc.expected_output or "",
            actual_output=tc.actual_output,
            context=tc.context or [],
            retrieval_context=tc.retrieval_context or [],
            metric_results=metric_data,
            overall_score=overall,
            is_badcase=overall < badcase_threshold,
            trace_id=trace.trace_id,
            latency_ms=collected_result["latency_ms"],
        )
        stored_count += 1

    # Mark complete
    task.status = "completed"
    task.completed_at = timezone.now()
    task.save(update_fields=["status", "completed_at"])

    # Update dataset sample count
    task.dataset.update_sample_count()

    logger.info("Storage complete: %d results stored", stored_count)

    # ── Phase 4: MLflow Tracking (non-blocking) ──
    if metric_aggregates:
        avg_aggregates = {k: sum(v) / len(v) for k, v in metric_aggregates.items()}
        overall_avg = sum(avg_aggregates.values()) / len(avg_aggregates) if avg_aggregates else 0.0
        _log_to_mlflow(task, avg_aggregates, overall_avg)

    logger.info(
        "Pipeline completed: task=%s, evaluated=%d, errors=%d, stored=%d",
        task.name, len(test_cases), error_count, stored_count,
    )
    return {
        "status": "completed",
        "samples": len(test_cases),
        "errors": error_count,
        "stored": stored_count,
    }


# ─── Batch Evaluation Task ──────────────────────────────────────────

@shared_task(bind=True)
def run_batch_evaluation(self, task_ids: list):
    """
    Run multiple evaluation tasks sequentially.
    Useful for comparing agent versions on the same dataset.
    """
    from evaluation.models import EvaluationTask

    results = []
    for tid in task_ids:
        try:
            task = EvaluationTask.objects.get(id=tid)
            if task.status not in ("pending", "created"):
                results.append({"task_id": str(tid), "status": "skipped", "reason": f"Already {task.status}"})
                continue
            result = run_evaluation_task(tid)
            results.append({"task_id": str(tid), "status": "completed", "result": result})
        except Exception as e:
            results.append({"task_id": str(tid), "status": "failed", "error": str(e)})

    return {"batch_results": results}


# ─── Maintenance Tasks ──────────────────────────────────────────────

@shared_task
def cleanup_expired_tasks(days: int = 30):
    """
    Clean up evaluation results older than N days.
    Called periodically via Celery Beat.
    """
    from evaluation.models import EvaluationTask, EvaluationResult, Trace
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(days=days)
    old_tasks = EvaluationTask.objects.filter(created_at__lt=cutoff, status="completed")
    count = old_tasks.count()

    if count > 0:
        task_ids = list(old_tasks.values_list("id", flat=True))
        Trace.objects.filter(task_id__in=task_ids).delete()
        EvaluationResult.objects.filter(task_id__in=task_ids).delete()
        old_tasks.delete()
        logger.info("Cleaned up %d expired tasks (older than %d days)", count, days)

    return {"deleted": count, "days": days}
