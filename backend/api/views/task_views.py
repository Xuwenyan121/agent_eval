"""
Evaluation Task API Views
==========================
CRUD + progress tracking + stop + comparison for evaluation tasks.
"""

import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from evaluation.models import EvaluationTask, EvaluationResult
from evaluation.task_status import TaskStatus, get_task_summary
from evaluation.tasks import run_evaluation_task
from api.serializers import (
    EvaluationTaskSerializer,
    EvaluationTaskListSerializer,
    EvaluationTaskCreateSerializer,
)

logger = logging.getLogger(__name__)


class EvaluationTaskViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for evaluation tasks.

    list:       GET    /api/v1/tasks/
    create:     POST   /api/v1/tasks/
    read:       GET    /api/v1/tasks/{id}/
    update:     PUT    /api/v1/tasks/{id}/
    delete:     DELETE /api/v1/tasks/{id}/
    run:        POST   /api/v1/tasks/{id}/run/
    stop:       POST   /api/v1/tasks/{id}/stop/
    progress:   GET    /api/v1/tasks/{id}/progress/
    compare:    POST   /api/v1/tasks/compare/
    """
    queryset = EvaluationTask.objects.all().select_related("agent", "dataset").order_by("-created_at")
    serializer_class = EvaluationTaskSerializer
    lookup_field = "id"

    def get_serializer_class(self):
        if self.action == "create":
            return EvaluationTaskCreateSerializer
        if self.action == "list":
            return EvaluationTaskListSerializer
        return EvaluationTaskSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        agent_id = self.request.query_params.get("agent")
        if agent_id:
            qs = qs.filter(agent_id=agent_id)
        dataset_id = self.request.query_params.get("dataset")
        if dataset_id:
            qs = qs.filter(dataset_id=dataset_id)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)
        return qs

    def perform_create(self, serializer):
        task = serializer.save(status="pending")
        logger.info("Created evaluation task: %s (%s)", task.name, task.id)

    @action(detail=True, methods=["post"], url_path="run")
    def run_task(self, request, id=None):
        """
        Start the evaluation task.

        POST /api/v1/tasks/{id}/run/
        """
        task = self.get_object()

        if task.status not in ("pending", "failed", "cancelled"):
            return Response(
                {"error": f"Task is already {task.status}. Cannot start."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Dispatch Celery task
        from django.conf import settings as _settings
        if getattr(_settings, "CELERY_TASK_ALWAYS_EAGER", False) and getattr(_settings, "USE_LOCAL_DB", False):
            # Local dev: run synchronously without Celery result backend
            run_evaluation_task.apply(args=[str(task.id)])
            return Response({
                "status": "started",
                "task_id": str(task.id),
                "celery_task_id": None,
            })

        result = run_evaluation_task.delay(str(task.id))

        # Store Celery task ID → Django task UUID mapping for progress queries
        from django.core.cache import cache
        cache.set(f"celery_task_id:{str(task.id)}", result.id, timeout=86400)

        return Response({
            "status": "started",
            "task_id": str(task.id),
            "celery_task_id": result.id,
        })

    @action(detail=True, methods=["post"], url_path="stop")
    def stop_task(self, request, id=None):
        """
        Stop a running evaluation task.

        POST /api/v1/tasks/{id}/stop/
        """
        task = self.get_object()

        if task.status != "running":
            return Response(
                {"error": f"Task is not running (status={task.status})"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Revoke the Celery task — use Celery task ID, not Django UUID
        from django.core.cache import cache
        celery_task_id = cache.get(f"celery_task_id:{str(task.id)}") or str(task.id)
        TaskStatus.revoke_task(celery_task_id, terminate=True)

        # Mark as cancelled
        task.status = "cancelled"
        task.save(update_fields=["status"])
        TaskStatus.clear_progress(str(task.id))

        return Response({"status": "cancelled", "task_id": str(task.id)})

    @action(detail=True, methods=["get"], url_path="progress")
    def get_progress(self, request, id=None):
        """
        Get real-time progress of the task.

        GET /api/v1/tasks/{id}/progress/
        """
        task = self.get_object()
        summary = get_task_summary(str(task.id))
        return Response(summary)

    @action(detail=False, methods=["post"], url_path="compare")
    def compare_tasks(self, request):
        """
        Compare results of multiple evaluation tasks.

        POST /api/v1/tasks/compare/
        Body: {"task_ids": ["uuid1", "uuid2"]}
        """
        task_ids = request.data.get("task_ids", [])
        if len(task_ids) < 2:
            return Response(
                {"error": "At least 2 task IDs required for comparison"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comparison = []
        for tid in task_ids:
            try:
                task = EvaluationTask.objects.select_related("agent", "dataset").get(id=tid)

                # Get per-metric averages
                results = EvaluationResult.objects.filter(task=task)
                metric_scores = {}
                for r in results:
                    for metric_name, data in (r.metric_results or {}).items():
                        score = data.get("score")
                        if score is not None:
                            metric_scores.setdefault(metric_name, []).append(score)

                metric_averages = {
                    k: round(sum(v) / len(v), 4) if v else 0.0
                    for k, v in metric_scores.items()
                }

                comparison.append({
                    "task_id": str(task.id),
                    "task_name": task.name,
                    "agent_name": task.agent.name,
                    "dataset_name": task.dataset.name,
                    "status": task.status,
                    "overall_score": task.average_score,
                    "badcase_count": task.badcase_count,
                    "total_samples": task.result_count,
                    "avg_latency_ms": task.avg_latency_ms,
                    "metric_averages": metric_averages,
                    "duration_seconds": task.duration_seconds,
                })
            except EvaluationTask.DoesNotExist:
                comparison.append({
                    "task_id": tid,
                    "error": "Task not found",
                })

        return Response({"comparison": comparison})
