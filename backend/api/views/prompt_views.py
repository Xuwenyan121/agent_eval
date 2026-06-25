"""
Judge Prompt API Views
=======================
CRUD for LLM judge prompt templates + dry-run testing.
"""

import logging
import time

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from evaluation.models import JudgePrompt
from api.serializers import (
    JudgePromptSerializer,
    JudgePromptListSerializer,
    PromptDryRunSerializer,
)

logger = logging.getLogger(__name__)


class JudgePromptViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for Judge Prompt templates.

    list:       GET  /api/v1/prompts/
    create:     POST /api/v1/prompts/
    retrieve:   GET  /api/v1/prompts/{id}/
    update:     PUT  /api/v1/prompts/{id}/
    partial:    PATCH /api/v1/prompts/{id}/
    destroy:    DELETE /api/v1/prompts/{id}/
    duplicate:  POST /api/v1/prompts/{id}/duplicate/
    preview:    POST /api/v1/prompts/{id}/preview/
    """
    queryset = JudgePrompt.objects.all()
    serializer_class = JudgePromptSerializer
    lookup_field = "id"

    def get_serializer_class(self):
        if self.action == "list":
            return JudgePromptListSerializer
        return JudgePromptSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        language = self.request.query_params.get("language")
        if language:
            qs = qs.filter(language=language)
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ("true", "1"))
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(display_name__icontains=search) | qs.filter(name__icontains=search)
        return qs

    @action(detail=True, methods=["post"], url_path="duplicate")
    def duplicate(self, request, id=None):
        """Clone an existing prompt with a new name."""
        original = self.get_object()
        new_name = request.data.get("name", f"{original.name}_copy")

        if JudgePrompt.objects.filter(name=new_name).exists():
            return Response(
                {"error": f"Prompt with name '{new_name}' already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        clone = JudgePrompt.objects.create(
            name=new_name,
            display_name=f"{original.display_name} (副本)",
            description=original.description,
            system_prompt=original.system_prompt,
            criteria=original.criteria,
            evaluation_steps=original.evaluation_steps,
            scoring_rubric=original.scoring_rubric,
            few_shot_examples=original.few_shot_examples,
            variables=original.variables,
            category=original.category,
            language=original.language,
            version=1,
            is_active=True,
        )
        serializer = JudgePromptSerializer(clone)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="preview")
    def preview(self, request, id=None):
        """Render the assembled prompt text with optional sample variables."""
        prompt = self.get_object()
        sample = request.data.get("sample", {})

        assembled = prompt.build_criteria_text()

        # Replace template variables with sample data if provided
        rendered = assembled
        if sample:
            for var_name in prompt.variables or ["input", "actual_output", "expected_output"]:
                placeholder = "{{" + var_name + "}}"
                if placeholder in rendered:
                    rendered = rendered.replace(placeholder, str(sample.get(var_name, f"<{var_name}>")))

        return Response({
            "prompt_id": str(prompt.id),
            "name": prompt.name,
            "assembled_criteria": assembled,
            "rendered_prompt": rendered,
            "system_prompt": prompt.system_prompt,
            "evaluation_steps": prompt.evaluation_steps,
            "scoring_rubric": prompt.scoring_rubric,
        })


@api_view(["POST"])
def prompt_dry_run(request):
    """
    Run a judge prompt against sample data with a real LLM call.

    POST /api/v1/prompts/dry-run/
    Body: {
        "prompt_id": "uuid-or-null",
        "criteria": "fallback criteria",
        "evaluation_steps": [...],
        "sample": {"input": "...", "actual_output": "...", "expected_output": "..."},
        "judge_model": {"model": "gpt-4o", "api_base": "...", "api_key": "..."}
    }
    """
    serializer = PromptDryRunSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    prompt_id = data.get("prompt_id")
    criteria = data.get("criteria", "")
    evaluation_steps = data.get("evaluation_steps", [])
    sample = data["sample"]
    judge_model = data["judge_model"]

    # Resolve criteria from prompt library or use inline
    rendered_criteria = criteria
    system_prompt = ""
    prompt_name = "inline"

    if prompt_id:
        try:
            prompt = JudgePrompt.objects.get(id=prompt_id)
            rendered_criteria = prompt.build_criteria_text()
            system_prompt = prompt.system_prompt
            prompt_name = prompt.name
            if not evaluation_steps:
                evaluation_steps = prompt.evaluation_steps
        except JudgePrompt.DoesNotExist:
            return Response(
                {"error": f"Prompt '{prompt_id}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

    # Build GEval metric and run
    try:
        from deepeval.metrics import GEval
        try:
            from deepeval.test_case import SingleTurnParams as EvalParams
        except ImportError:
            from deepeval.test_case import LLMTestCaseParams as EvalParams
        from deepeval.test_case import LLMTestCase
        from evaluation.judge_model import get_judge_endpoint

        judge_endpoint = get_judge_endpoint(judge_model)
        if not judge_endpoint:
            return Response(
                {"error": "Judge model endpoint could not be resolved"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build evaluation_steps for GEval
        geval_steps = evaluation_steps if evaluation_steps else None

        metric = GEval(
            name=f"dry_run_{prompt_name}",
            criteria=rendered_criteria,
            evaluation_params=[
                EvalParams.INPUT,
                EvalParams.ACTUAL_OUTPUT,
                EvalParams.EXPECTED_OUTPUT,
            ],
            threshold=0.0,
            model=judge_endpoint,
            strict_mode=False,
            async_mode=False,
        )

        if geval_steps:
            metric.evaluation_steps = geval_steps

        test_case = LLMTestCase(
            input=sample.get("input", ""),
            actual_output=sample.get("actual_output", ""),
            expected_output=sample.get("expected_output", ""),
        )

        start = time.monotonic()
        metric.measure(test_case)
        latency = int((time.monotonic() - start) * 1000)

        return Response({
            "prompt_name": prompt_name,
            "score": metric.score,
            "reason": metric.reason if hasattr(metric, "reason") else "",
            "is_successful": metric.is_successful(),
            "rendered_criteria": rendered_criteria,
            "system_prompt": system_prompt,
            "latency_ms": latency,
        })

    except ImportError as e:
        return Response(
            {"error": f"DeepEval not available: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        logger.exception("Prompt dry-run failed")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
