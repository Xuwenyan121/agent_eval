from django.urls import path, include
from rest_framework.routers import DefaultRouter

from api.views import (
    AgentEndpointViewSet,
    DatasetViewSet,
    EvaluationTaskViewSet,
    EvaluationResultViewSet,
    TraceViewSet,
    BadCaseFeedbackViewSet,
    BadCaseCollectionRuleViewSet,
    MetricDefinitionViewSet,
    metric_dry_run,
    JudgePromptViewSet,
    prompt_dry_run,
    JudgeModelViewSet,
    model_test,
)

router = DefaultRouter()
router.register(r"agents", AgentEndpointViewSet, basename="agent")
router.register(r"datasets", DatasetViewSet, basename="dataset")
router.register(r"tasks", EvaluationTaskViewSet, basename="task")
router.register(r"results", EvaluationResultViewSet, basename="result")
router.register(r"traces", TraceViewSet, basename="trace")
router.register(r"feedback", BadCaseFeedbackViewSet, basename="feedback")
router.register(r"badcase-rules", BadCaseCollectionRuleViewSet, basename="badcase-rule")
router.register(r"metrics", MetricDefinitionViewSet, basename="metric")
router.register(r"prompts", JudgePromptViewSet, basename="prompt")
router.register(r"judge-models", JudgeModelViewSet, basename="judge-model")

urlpatterns = [
    path("metrics/dry-run/", metric_dry_run, name="metric-dry-run"),
    path("prompts/dry-run/", prompt_dry_run, name="prompt-dry-run"),
    path("judge-models/test/", model_test, name="model-test"),
    path("", include(router.urls)),
]