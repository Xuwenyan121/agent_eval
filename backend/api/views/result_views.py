"""
Result, Trace & BadCase API Views
===================================
Query evaluation results, traces, and manage badcase feedback.
"""

import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse

from evaluation.models import EvaluationResult, Trace, BadCaseFeedback
from api.serializers import (
    EvaluationResultSerializer,
    EvaluationResultListSerializer,
    TraceSerializer,
    BadCaseFeedbackSerializer,
    BadCaseFeedbackCreateSerializer,
)

logger = logging.getLogger(__name__)


class EvaluationResultViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only access to evaluation results.

    list:   GET /api/v1/results/
    read:   GET /api/v1/results/{id}/
    """
    queryset = EvaluationResult.objects.all().select_related("task").order_by("-created_at")
    serializer_class = EvaluationResultSerializer
    lookup_field = "id"

    def get_serializer_class(self):
        if self.action == "list":
            return EvaluationResultListSerializer
        return EvaluationResultSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        task_id = self.request.query_params.get("task")
        if task_id:
            qs = qs.filter(task_id=task_id)
        is_badcase = self.request.query_params.get("is_badcase")
        if is_badcase is not None:
            qs = qs.filter(is_badcase=is_badcase.lower() == "true")
        min_score = self.request.query_params.get("min_score")
        if min_score:
            qs = qs.filter(overall_score__gte=float(min_score))
        max_score = self.request.query_params.get("max_score")
        if max_score:
            qs = qs.filter(overall_score__lte=float(max_score))
        # Sorting
        ordering = self.request.query_params.get("ordering", "-overall_score")
        if ordering in ("overall_score", "-overall_score", "latency_ms", "-latency_ms"):
            qs = qs.order_by(ordering)
        return qs

    @action(detail=False, methods=["get"], url_path="badcases")
    def list_badcases(self, request):
        """
        List all bad cases across tasks (or filter by task).

        GET /api/v1/results/badcases/?task={task_id}
        """
        qs = self.get_queryset().filter(is_badcase=True)
        serializer = EvaluationResultListSerializer(qs[:100], many=True)
        return Response({
            "count": qs.count(),
            "results": serializer.data,
        })

    @action(detail=False, methods=["get"], url_path="export")
    def export_badcases(self, request):
        """
        Export bad cases as JSONL for the specified task.

        GET /api/v1/results/export/?task={task_id}
        """
        task_id = request.query_params.get("task")
        if not task_id:
            return Response(
                {"error": "task parameter required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        import json
        badcases = EvaluationResult.objects.filter(
            task_id=task_id, is_badcase=True,
        ).order_by("overall_score")

        lines = []
        for bc in badcases:
            lines.append(json.dumps({
                "input": bc.input,
                "expected_output": bc.expected_output,
                "actual_output": bc.actual_output,
                "overall_score": bc.overall_score,
                "metric_results": bc.metric_results,
                "latency_ms": bc.latency_ms,
            }, ensure_ascii=False))

        content = "\n".join(lines)
        response = HttpResponse(content, content_type="application/x-ndjson")
        response["Content-Disposition"] = f'attachment; filename="badcases_{task_id}.jsonl"'
        return response


class TraceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only access to execution traces.

    list:   GET /api/v1/traces/
    read:   GET /api/v1/traces/{id}/
    """
    queryset = Trace.objects.all().select_related("task").order_by("-created_at")
    serializer_class = TraceSerializer
    lookup_field = "trace_id"

    def get_queryset(self):
        qs = super().get_queryset()
        task_id = self.request.query_params.get("task")
        if task_id:
            qs = qs.filter(task_id=task_id)
        trace_id = self.request.query_params.get("trace_id")
        if trace_id:
            qs = qs.filter(trace_id=trace_id)
        return qs


class BadCaseFeedbackViewSet(viewsets.ModelViewSet):
    """
    CRUD for badcase feedback/annotations.

    list:   GET    /api/v1/feedback/
    create: POST   /api/v1/feedback/
    read:   GET    /api/v1/feedback/{id}/
    update: PUT    /api/v1/feedback/{id}/
    delete: DELETE /api/v1/feedback/{id}/
    """
    queryset = BadCaseFeedback.objects.all().select_related("result", "result__task").order_by("-created_at")
    serializer_class = BadCaseFeedbackSerializer
    lookup_field = "id"

    def get_serializer_class(self):
        if self.action == "create":
            return BadCaseFeedbackCreateSerializer
        return BadCaseFeedbackSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        task_id = self.request.query_params.get("task")
        if task_id:
            qs = qs.filter(result__task_id=task_id)
        result_id = self.request.query_params.get("result")
        if result_id:
            qs = qs.filter(result_id=result_id)
        return qs
