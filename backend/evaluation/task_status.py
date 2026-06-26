"""
Task Status & Progress Utilities
=================================
Query task status, progress, and results from both Celery and Django cache.
"""

import logging
from typing import Optional
from django.core.cache import cache

logger = logging.getLogger(__name__)


class TaskStatus:
    """
    Unified interface to query task status from Celery backend and Redis cache.
    """

    # Status constants
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    REVOKED = "revoked"

    @staticmethod
    def get_progress(task_id: str) -> dict:
        """
        Get real-time progress from Redis cache (set by _update_progress in tasks.py).

        Returns:
            {
                "phase": "collecting" | "evaluating" | "storing" | "completed",
                "progress": int (0-100),
                "collect_progress": {"completed": int, "total": int, "failed": int},
                "eval_progress": {"completed": int, "total": int},
                "processed": int,
                "total": int,
            }
            or {"phase": "unknown", "progress": 0} if not found
        """
        progress = cache.get(f"task_progress:{task_id}")
        if progress:
            return progress
        return {"phase": "unknown", "progress": 0}

    @staticmethod
    def get_celery_status(task_id: str) -> dict:
        """
        Query Celery AsyncResult for task state.

        Returns:
            {
                "status": "PENDING" | "STARTED" | "SUCCESS" | "FAILURE" | "REVOKED",
                "result": any (return value on SUCCESS, exception on FAILURE),
                "traceback": str | None,
                "ready": bool,
            }
        """
        try:
            from celery.result import AsyncResult
            from config.celery import app

            result = AsyncResult(task_id, app=app)
            response = {
                "status": result.status,
                "ready": result.ready(),
                "result": None,
                "traceback": None,
            }

            if result.ready():
                if result.successful():
                    response["result"] = result.result
                else:
                    response["result"] = str(result.result) if result.result else None
                    response["traceback"] = result.traceback

            return response
        except Exception as e:
            logger.warning("Failed to query Celery status for %s: %s", task_id, e)
            return {
                "status": "UNKNOWN",
                "ready": False,
                "result": None,
                "traceback": None,
                "error": str(e),
            }

    @staticmethod
    def _resolve_celery_task_id(task_id: str) -> str:
        """
        Resolve the Celery task ID from the Django task UUID.
        The Celery task ID is stored in cache when the task is dispatched.
        Falls back to the original task_id if no mapping exists (backward compat).
        """
        celery_task_id = cache.get(f"celery_task_id:{task_id}")
        return celery_task_id if celery_task_id else task_id

    @staticmethod
    def get_full_status(task_id: str) -> dict:
        """
        Combine Celery status + Redis progress for complete task state.

        Returns:
            {
                "celery_status": {...},  # from get_celery_status()
                "progress": {...},       # from get_progress()
                "is_running": bool,
                "is_completed": bool,
                "is_failed": bool,
            }
        """
        celery_task_id = TaskStatus._resolve_celery_task_id(task_id)
        celery_status = TaskStatus.get_celery_status(celery_task_id)
        progress = TaskStatus.get_progress(task_id)

        return {
            "celery_status": celery_status,
            "progress": progress,
            "is_running": celery_status["status"] in ("STARTED", "PENDING"),
            "is_completed": celery_status["status"] == "SUCCESS",
            "is_failed": celery_status["status"] == "FAILURE",
        }

    @staticmethod
    def set_progress(task_id: str, progress_data: dict, timeout: int = 3600):
        """
        Set progress in Redis cache (used by tasks.py internally).
        """
        cache.set(f"task_progress:{task_id}", progress_data, timeout=timeout)

    @staticmethod
    def clear_progress(task_id: str):
        """
        Clear progress data from cache (call after task completion).
        """
        cache.delete(f"task_progress:{task_id}")

    @staticmethod
    def revoke_task(task_id: str, terminate: bool = False):
        """
        Revoke a running or pending task.

        Args:
            task_id: Celery task ID
            terminate: if True, send SIGTERM to running worker
        """
        from config.celery import app
        app.control.revoke(task_id, terminate=terminate)
        logger.info("Revoked task: %s (terminate=%s)", task_id, terminate)


def get_task_summary(task_id: str) -> dict:
    """
    Get a human-readable summary of task status for API responses.
    Combines Django model state with Celery/Redis data.
    """
    from evaluation.models import EvaluationTask

    try:
        task = EvaluationTask.objects.get(id=task_id)
    except EvaluationTask.DoesNotExist:
        return {"error": "Task not found"}

    status = TaskStatus.get_full_status(task_id)

    return {
        "task_id": str(task.id),
        "name": task.name,
        "status": task.status,
        "celery_status": status["celery_status"]["status"],
        "progress": status["progress"],
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "sample_count": task.result_count,
        "badcase_count": task.badcase_count,
        "average_score": task.average_score,
        "avg_latency_ms": task.avg_latency_ms,
    }
