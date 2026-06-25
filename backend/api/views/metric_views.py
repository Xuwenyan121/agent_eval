"""
Metric Definition & Dry-Run API Views
=======================================
List metric definitions and run metric dry-run tests.
"""

import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from evaluation.models import MetricDefinition
from evaluation.metrics_builder import (
    build_metrics,
    validate_evaluator_config,
    list_all_metric_types,
    list_rule_metrics,
)
from evaluation.metrics_dryrun import MetricDryRunner
from api.serializers import MetricDefinitionSerializer

logger = logging.getLogger(__name__)


class MetricDefinitionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only access to metric definitions.

    list:   GET /api/v1/metrics/
    read:   GET /api/v1/metrics/{id}/
    types:  GET /api/v1/metrics/types/
    """
    queryset = MetricDefinition.objects.filter(enabled=True).order_by("category", "name")
    serializer_class = MetricDefinitionSerializer
    lookup_field = "id"

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        metric_type = self.request.query_params.get("type")
        if metric_type:
            qs = qs.filter(type=metric_type)
        return qs

    @action(detail=False, methods=["get"], url_path="types")
    def list_types(self, request):
        """
        List all available metric types and identifiers.

        GET /api/v1/metrics/types/
        """
        return Response(list_all_metric_types())


@api_view(["POST"])
def metric_dry_run(request):
    """
    Run a metric dry-run on sample data.

    POST /api/v1/metrics/dry-run/
    Body: {
        "metrics": [
            {"name": "f1", "type": "rule", "weight": 0.5, "threshold": 0.5},
            ...
        ],
        "samples": [
            {"input": "...", "actual_output": "...", "expected_output": "..."},
            ...
        ],
        "judge_model": {} (optional)
    }
    """
    evaluator_config = request.data.get("metrics", [])
    samples = request.data.get("samples", [])
    judge_model = request.data.get("judge_model", {})

    if not evaluator_config:
        return Response(
            {"error": "At least one metric required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not samples:
        return Response(
            {"error": "At least one sample required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate config first
    config = {"metrics": evaluator_config}
    validation = validate_evaluator_config(config)
    if not validation["valid"]:
        return Response(
            {"error": "Invalid metric configuration", "details": validation["errors"]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        metrics = build_metrics(config, judge_model if judge_model else None)
    except Exception as e:
        return Response(
            {"error": f"Failed to build metrics: {e}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    runner = MetricDryRunner(metrics)
    result = runner.run(samples, max_samples=min(len(samples), 5))

    return Response({
        "validation": validation,
        "results": result,
    })
