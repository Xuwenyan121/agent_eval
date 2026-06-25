"""
Judge Model configuration CRUD + connectivity test endpoint.
"""

import time
import logging
import httpx
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from evaluation.models import JudgeModel
from api.serializers.serializers import (
    JudgeModelSerializer,
    JudgeModelListSerializer,
    ModelTestSerializer,
)

logger = logging.getLogger(__name__)


class JudgeModelViewSet(viewsets.ModelViewSet):
    """
    CRUD for saved judge model configurations.

    list:   GET  /api/v1/judge-models/
    create: POST /api/v1/judge-models/
    read:   GET  /api/v1/judge-models/{id}/
    update: PUT  /api/v1/judge-models/{id}/
    delete: DELETE /api/v1/judge-models/{id}/
    """
    queryset = JudgeModel.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return JudgeModelListSerializer
        return JudgeModelSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        provider = self.request.query_params.get("provider")
        if provider:
            qs = qs.filter(provider=provider)
        active_only = self.request.query_params.get("is_active")
        if active_only == "true":
            qs = qs.filter(is_active=True)
        return qs

    @action(detail=True, methods=["post"], url_path="set-default")
    def set_default(self, request, pk=None):
        """Set this model as the default judge model."""
        obj = self.get_object()
        obj.is_default = True
        obj.save()  # save() handles clearing other defaults
        return Response({"status": "ok", "default_model": obj.display_name})

    @action(detail=True, methods=["post"], url_path="duplicate")
    def duplicate(self, request, pk=None):
        """Clone a model configuration."""
        original = self.get_object()
        new_name = f"{original.name}_copy"
        counter = 1
        while JudgeModel.objects.filter(name=new_name).exists():
            new_name = f"{original.name}_copy{counter}"
            counter += 1

        clone = JudgeModel(
            name=new_name,
            display_name=f"{original.display_name} (副本)",
            description=original.description,
            model=original.model,
            api_base=original.api_base,
            api_key=original.api_key,
            extra_params=original.extra_params.copy() if original.extra_params else {},
            provider=original.provider,
            is_default=False,
            is_active=True,
        )
        clone.save()
        serializer = JudgeModelSerializer(clone)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def model_test(request):
    """
    Test connectivity to a model endpoint.

    Body: {
        "model_id": "uuid-or-null",
        "model": "gpt-4o",
        "api_base": "https://api.openai.com/v1",
        "api_key": "sk-..."
    }

    Sends a minimal chat completion request and returns latency + response.
    """
    serializer = ModelTestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    # Resolve model config from saved preset or inline
    model_name = data.get("model", "")
    api_base = data.get("api_base", "")
    api_key = data.get("api_key", "")

    if data.get("model_id"):
        try:
            preset = JudgeModel.objects.get(id=data["model_id"])
            model_name = model_name or preset.model
            api_base = api_base or preset.api_base
            api_key = api_key or preset.api_key
        except JudgeModel.DoesNotExist:
            return Response({"error": "Model preset not found"}, status=status.HTTP_404_NOT_FOUND)

    if not model_name:
        return Response({"error": "Model name is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Build the test request
    base_url = api_base.rstrip("/") if api_base else "https://api.openai.com/v1"
    test_url = f"{base_url}/chat/completions"

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Hello, respond with 'OK' to confirm connectivity."}],
        "max_tokens": 10,
        "temperature": 0,
    }

    start = time.time()
    try:
        with httpx.Client(timeout=30.0, http2=True) as client:
            resp = client.post(test_url, json=payload, headers=headers)
        latency_ms = int((time.time() - start) * 1000)

        if resp.status_code == 200:
            body = resp.json()
            reply = ""
            try:
                reply = body["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                reply = str(body)[:200]

            return Response({
                "success": True,
                "latency_ms": latency_ms,
                "response": reply,
                "model": model_name,
                "api_base": base_url,
            })
        else:
            return Response({
                "success": False,
                "latency_ms": latency_ms,
                "status_code": resp.status_code,
                "error": resp.text[:500],
                "model": model_name,
                "api_base": base_url,
            })

    except httpx.TimeoutException:
        latency_ms = int((time.time() - start) * 1000)
        return Response({
            "success": False,
            "latency_ms": latency_ms,
            "error": "Connection timed out (30s)",
            "model": model_name,
            "api_base": base_url,
        }, status=status.HTTP_408_REQUEST_TIMEOUT)

    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        logger.exception("Model test failed")
        return Response({
            "success": False,
            "latency_ms": latency_ms,
            "error": str(e),
            "model": model_name,
            "api_base": base_url,
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
