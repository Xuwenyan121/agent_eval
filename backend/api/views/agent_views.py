"""
Agent Endpoint API Views
=========================
CRUD + connectivity test for agent endpoints.
"""

import asyncio
import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from evaluation.models import AgentEndpoint
from evaluation.collectors import get_collector
from api.serializers import (
    AgentEndpointSerializer,
    AgentEndpointListSerializer,
    AgentTestResultSerializer,
)

logger = logging.getLogger(__name__)


class AgentEndpointViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for agent endpoints.

    list:   GET    /api/v1/agents/
    create: POST   /api/v1/agents/
    read:   GET    /api/v1/agents/{id}/
    update: PUT    /api/v1/agents/{id}/
    delete: DELETE /api/v1/agents/{id}/
    test:   POST   /api/v1/agents/{id}/test/
    """
    queryset = AgentEndpoint.objects.all()
    serializer_class = AgentEndpointSerializer
    lookup_field = "id"

    def get_serializer_class(self):
        if self.action == "list":
            return AgentEndpointListSerializer
        return AgentEndpointSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        # Search by name
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)
        return qs

    @action(detail=True, methods=["post"], url_path="test")
    def test_connection(self, request, id=None):
        """
        Test connectivity to the agent endpoint.
        Sends a test query and returns protocol verification results.

        POST /api/v1/agents/{id}/test/
        Body: {"test_query": "hello"} (optional)
        """
        agent = self.get_object()
        test_query = request.data.get("test_query", "hello")

        try:
            endpoint_config = agent.endpoint_config_dict()
            collector = get_collector(endpoint_config)
            # Run async test_connection in sync context
            result = asyncio.run(collector.test_connection(test_query))
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Agent test failed: %s — %s", agent.name, e)
            return Response(
                {
                    "status": "offline",
                    "latency_ms": 0,
                    "sample_output": "",
                    "sse_chunks_received": 0,
                    "protocol_verified": False,
                    "error": str(e),
                },
                status=status.HTTP_200_OK,
            )

    @action(detail=False, methods=["get"], url_path="protocols")
    def list_protocols(self, request):
        """
        List supported agent protocols.

        GET /api/v1/agents/protocols/
        """
        from evaluation.collectors import get_supported_protocols
        protocols = [
            {"value": p, "label": p.replace("_", " ").title()}
            for p in get_supported_protocols()
        ]
        return Response(protocols)
