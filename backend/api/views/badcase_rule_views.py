"""
BadCase Collection Rule API Views
==================================
CRUD + test (dry-run) for BadCase collection rules.
"""

import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from evaluation.models import BadCaseCollectionRule, EvaluationTask
from evaluation.badcase.collector import BadCaseCollector
from api.serializers import (
    BadCaseCollectionRuleSerializer,
    BadCaseCollectionRuleCreateSerializer,
)

logger = logging.getLogger(__name__)


class BadCaseCollectionRuleViewSet(viewsets.ModelViewSet):
    """
    CRUD for BadCase collection rules.

    list:       GET    /api/v1/badcase-rules/
    create:     POST   /api/v1/badcase-rules/
    read:       GET    /api/v1/badcase-rules/{id}/
    update:     PUT    /api/v1/badcase-rules/{id}/
    partial:    PATCH  /api/v1/badcase-rules/{id}/
    delete:     DELETE /api/v1/badcase-rules/{id}/
    test:       POST   /api/v1/badcase-rules/{id}/test/
    """
    queryset = BadCaseCollectionRule.objects.all().order_by("-priority", "-created_at")
    serializer_class = BadCaseCollectionRuleSerializer
    lookup_field = "id"

    def get_serializer_class(self):
        if self.action == "create":
            return BadCaseCollectionRuleCreateSerializer
        return BadCaseCollectionRuleSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        rule_type = self.request.query_params.get("rule_type")
        if rule_type:
            qs = qs.filter(rule_type=rule_type)
        enabled = self.request.query_params.get("enabled")
        if enabled is not None:
            qs = qs.filter(enabled=enabled.lower() == "true")
        return qs

    @action(detail=True, methods=["post"], url_path="test")
    def test_rule(self, request, id=None):
        """
        Dry-run a collection rule against a completed task's results.

        POST /api/v1/badcase-rules/{id}/test/
        Body: {"task_id": "uuid-of-completed-task"}
        """
        rule = self.get_object()
        task_id = request.data.get("task_id")
        if not task_id:
            return Response(
                {"error": "task_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            task = EvaluationTask.objects.get(id=task_id)
        except EvaluationTask.DoesNotExist:
            return Response(
                {"error": "Task not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        collector = BadCaseCollector(task, [rule])
        collected = collector.collect()

        results = []
        for rule_key, matched_results in collected.items():
            from evaluation.badcase.matchers import get_matcher
            matcher = get_matcher(rule)
            for r in matched_results:
                results.append({
                    "sample_id": r.sample_id,
                    "overall_score": r.overall_score,
                    "reason": matcher.reason(r),
                    "input_preview": (r.input or "")[:100],
                })

        return Response({
            "rule_id": str(rule.id),
            "rule_name": rule.name,
            "rule_type": rule.rule_type,
            "task_id": str(task.id),
            "task_name": task.name,
            "total_results": len(collector.results),
            "matched_count": len(results),
            "results": results,
        })