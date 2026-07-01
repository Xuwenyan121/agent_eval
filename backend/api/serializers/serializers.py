from rest_framework import serializers
from evaluation.models import (
    AgentEndpoint, Dataset, DatasetSample, EvaluationTask,
    EvaluationResult, Trace, BadCaseFeedback, MetricDefinition, JudgePrompt,
    JudgeModel, BadCaseCollectionRule, BadCaseCollectionRecord,
)


# ═══════════════════════════════════════════════════════════
# AgentEndpoint
# ═══════════════════════════════════════════════════════════

class AgentEndpointSerializer(serializers.ModelSerializer):
    task_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = AgentEndpoint
        fields = [
            "id", "name", "endpoint_url", "protocol", "method",
            "headers", "body_template", "stream",
            "sse_event_field", "sse_done_marker",
            "default_user_id", "default_conv_id", "cache_user",
            "timeout", "retry_times", "verify_ssl", "status",
            "task_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AgentEndpointListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    task_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = AgentEndpoint
        fields = [
            "id", "name", "endpoint_url", "protocol",
            "status", "task_count", "created_at",
        ]


class AgentTestResultSerializer(serializers.Serializer):
    """Response for agent connectivity test."""
    status = serializers.CharField()
    latency_ms = serializers.IntegerField()
    sample_output = serializers.CharField()
    sse_chunks_received = serializers.IntegerField()
    protocol_verified = serializers.BooleanField(default=True)
    error = serializers.CharField(allow_null=True, allow_blank=True)


# ═══════════════════════════════════════════════════════════
# Dataset + Samples
# ═══════════════════════════════════════════════════════════

class DatasetSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetSample
        fields = [
            "id", "dataset", "sample_id", "input", "expected_output", "expected_meta",
            "context", "retrieval_context", "additional_tools_output",
            "tags", "notes", "created_at",
        ]
        read_only_fields = ["id", "dataset", "created_at"]


class DatasetSampleUploadSerializer(serializers.Serializer):
    """For JSONL file upload: each line is one sample."""
    file = serializers.FileField(help_text="JSONL file with one sample per line")
    auto_sample_id = serializers.BooleanField(
        default=True, help_text="Auto-generate sample_id if missing"
    )


class DatasetSerializer(serializers.ModelSerializer):
    sample_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Dataset
        fields = [
            "id", "name", "data_type", "version", "file_path",
            "sample_count", "tags", "description", "status",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "sample_count", "file_path", "created_at", "updated_at"]


class DatasetDetailSerializer(DatasetSerializer):
    """Extended with recent samples preview."""
    recent_samples = DatasetSampleSerializer(source="samples", many=True, read_only=True)

    class Meta(DatasetSerializer.Meta):
        fields = DatasetSerializer.Meta.fields + ["recent_samples"]

    def get_fields(self):
        fields = super().get_fields()
        fields["recent_samples"].child_relation = None
        return fields


class DatasetVersionSerializer(serializers.Serializer):
    """For creating a new version of a dataset."""
    version = serializers.CharField(max_length=20)
    copy_samples = serializers.BooleanField(default=True)


# ═══════════════════════════════════════════════════════════
# EvaluationTask
# ═══════════════════════════════════════════════════════════

class MetricConfigSerializer(serializers.Serializer):
    """Single metric configuration within evaluator_config."""
    name = serializers.CharField()
    type = serializers.ChoiceField(choices=["g_eval", "rule", "custom"])
    category = serializers.ChoiceField(
        choices=["business_dim", "ml_metric", "multimodal"],
        required=False, default="business_dim",
    )
    criteria = serializers.CharField(required=False, default="", allow_blank=True)
    threshold = serializers.FloatField(required=False, default=0.6)
    weight = serializers.FloatField(required=False, default=1.0)
    params = serializers.DictField(required=False, default=dict)
    rule_class = serializers.CharField(required=False, default="")
    prompt_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class EvaluatorConfigSerializer(serializers.Serializer):
    """Full evaluator configuration structure."""
    metrics = MetricConfigSerializer(many=True)
    judge_model_config = serializers.DictField(required=False, default=dict)
    badcase_threshold = serializers.FloatField(required=False, default=0.6)


class EvaluationTaskCreateSerializer(serializers.ModelSerializer):
    """For creating a new evaluation task."""

    class Meta:
        model = EvaluationTask
        fields = [
            "id", "name", "agent", "dataset", "judge_model",
            "evaluator_config", "parallel", "limit",
            "conv_id_strategy",
        ]
        read_only_fields = ["id"]

    def validate_evaluator_config(self, value):
        metrics = value.get("metrics", [])
        if not metrics:
            raise serializers.ValidationError("At least one metric must be configured.")
        total_weight = sum(m.get("weight", 1.0) for m in metrics)
        if abs(total_weight - 1.0) > 0.1:
            raise serializers.ValidationError(
                f"Metric weights should sum to ~1.0, got {total_weight:.2f}"
            )
        return value

    def validate_parallel(self, value):
        if value < 1 or value > 50:
            raise serializers.ValidationError("Parallel must be between 1 and 50.")
        return value


class EvaluationTaskSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source="agent.name", read_only=True)
    dataset_name = serializers.CharField(source="dataset.name", read_only=True)
    result_count = serializers.IntegerField(read_only=True)
    average_score = serializers.FloatField(read_only=True)
    badcase_count = serializers.IntegerField(read_only=True)
    summary = serializers.DictField(read_only=True)

    class Meta:
        model = EvaluationTask
        fields = [
            "id", "name", "agent", "agent_name", "dataset", "dataset_name",
            "judge_model", "evaluator_config", "parallel", "limit",
            "conv_id_strategy",
            "status", "started_at", "completed_at",
            "report_path", "mlflow_run_id",
            "result_count", "average_score", "badcase_count",
            "summary", "created_at",
        ]
        read_only_fields = [
            "id", "status", "started_at", "completed_at",
            "report_path", "mlflow_run_id", "created_at",
        ]


class EvaluationTaskListSerializer(serializers.ModelSerializer):
    """Lightweight for list view."""
    agent_name = serializers.CharField(source="agent.name", read_only=True)
    dataset_name = serializers.CharField(source="dataset.name", read_only=True)
    result_count = serializers.IntegerField(read_only=True)
    average_score = serializers.FloatField(read_only=True)
    badcase_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = EvaluationTask
        fields = [
            "id", "name", "agent_name", "dataset_name",
            "status", "result_count", "average_score", "badcase_count",
            "started_at", "completed_at", "created_at",
        ]


class TaskProgressSerializer(serializers.Serializer):
    """Real-time progress response."""
    task_id = serializers.UUIDField()
    status = serializers.CharField()
    phase = serializers.CharField()
    progress = serializers.IntegerField()
    collect_progress = serializers.DictField()
    eval_progress = serializers.DictField()
    processed = serializers.IntegerField()
    total = serializers.IntegerField()
    estimated_remaining = serializers.IntegerField(allow_null=True)


# ═══════════════════════════════════════════════════════════
# EvaluationResult
# ═══════════════════════════════════════════════════════════

class EvaluationResultSerializer(serializers.ModelSerializer):
    score_breakdown = serializers.ListField(read_only=True)

    class Meta:
        model = EvaluationResult
        fields = [
            "id", "task", "sample_id", "input", "expected_output",
            "actual_output", "context", "retrieval_context",
            "metric_results", "score_breakdown",
            "overall_score", "is_badcase",
            "trace_id", "latency_ms", "error", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class EvaluationResultListSerializer(serializers.ModelSerializer):
    """Lightweight for table view, but includes fields for expand section."""

    class Meta:
        model = EvaluationResult
        fields = [
            "id", "sample_id", "overall_score", "is_badcase",
            "latency_ms", "error", "created_at",
            "input", "expected_output", "actual_output",
            "metric_results", "trace_id",
        ]


# ═══════════════════════════════════════════════════════════
# Trace
# ═══════════════════════════════════════════════════════════

class TraceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trace
        fields = [
            "trace_id", "task", "sample_id",
            "trace_data", "spans", "raw_sse_chunks",
            "final_output", "total_tokens", "total_duration_ms",
            "created_at",
        ]
        read_only_fields = fields


class TraceStepSerializer(serializers.Serializer):
    """Individual trace step."""
    type = serializers.CharField()
    duration_ms = serializers.IntegerField()
    chunks = serializers.IntegerField(required=False)
    output = serializers.CharField(required=False, allow_blank=True)


# ═══════════════════════════════════════════════════════════
# BadCaseFeedback
# ═══════════════════════════════════════════════════════════

class BadCaseFeedbackSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.username", read_only=True, default="")

    class Meta:
        model = BadCaseFeedback
        fields = [
            "id", "result", "dataset", "status",
            "reviewer", "reviewer_name", "review_comment",
            "created_at", "resolved_at",
        ]
        read_only_fields = ["id", "created_at", "resolved_at", "reviewer"]


class BadCaseFeedbackCreateSerializer(serializers.Serializer):
    """For submitting feedback on a BadCase result."""
    result_id = serializers.UUIDField()
    dataset_id = serializers.UUIDField()
    review_comment = serializers.CharField(required=False, default="", allow_blank=True)


class BadCaseExportSerializer(serializers.Serializer):
    """For exporting BadCases."""
    format = serializers.ChoiceField(choices=["jsonl", "csv"], default="jsonl")
    include_traces = serializers.BooleanField(default=False)


# ═══════════════════════════════════════════════════════════
# BadCaseCollectionRule (NEW)
# ═══════════════════════════════════════════════════════════

class BadCaseCollectionRuleSerializer(serializers.ModelSerializer):
    """Full serializer for BadCase collection rules."""

    class Meta:
        model = BadCaseCollectionRule
        fields = [
            "id", "name", "description", "rule_type", "parameters",
            "target_dataset", "auto_collect", "enabled", "priority",
            "max_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class BadCaseCollectionRuleCreateSerializer(serializers.ModelSerializer):
    """For creating a new BadCase collection rule."""

    class Meta:
        model = BadCaseCollectionRule
        fields = [
            "name", "description", "rule_type", "parameters",
            "target_dataset", "auto_collect", "enabled", "priority",
            "max_count",
        ]

    def validate_parameters(self, value):
        rule_type = self.initial_data.get("rule_type", "")
        if rule_type == "score_below" and "threshold" not in value:
            raise serializers.ValidationError("score_below requires 'threshold' in parameters")
        if rule_type == "metric_below" and "metric_name" not in value:
            raise serializers.ValidationError("metric_below requires 'metric_name' in parameters")
        return value


# ═══════════════════════════════════════════════════════════
# MetricDefinition
# ═══════════════════════════════════════════════════════════

class MetricDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetricDefinition
        fields = [
            "id", "name", "display_name", "category", "type",
            "criteria", "rule_class", "rule_params", "default_params",
            "weight", "default_threshold", "enabled", "description",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MetricDryRunSerializer(serializers.Serializer):
    """For testing a metric on a single sample."""
    input = serializers.CharField()
    actual_output = serializers.CharField()
    expected_output = serializers.CharField(required=False, default="")
    context = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class MetricDryRunResultSerializer(serializers.Serializer):
    """Result of a metric dry run."""
    metric = serializers.CharField()
    score = serializers.FloatField()
    passed = serializers.BooleanField()
    reason = serializers.CharField()
    latency_ms = serializers.IntegerField()


# ═══════════════════════════════════════════════════════════
# Comparison
# ═══════════════════════════════════════════════════════════

class TaskComparisonRequestSerializer(serializers.Serializer):
    """Request body for task comparison."""
    task_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=2, max_length=5,
        help_text="2-5 task IDs to compare",
    )


class TaskComparisonResultSerializer(serializers.Serializer):
    """Comparison result for multiple tasks."""
    task_id = serializers.UUIDField()
    task_name = serializers.CharField()
    agent_name = serializers.CharField()
    dataset_name = serializers.CharField()
    overall_score = serializers.FloatField()
    badcase_count = serializers.IntegerField()
    metric_averages = serializers.DictField(child=serializers.FloatField())
    duration_seconds = serializers.FloatField()


# ═══════════════════════════════════════════════════════════
# JudgePrompt
# ═══════════════════════════════════════════════════════════

class JudgePromptSerializer(serializers.ModelSerializer):
    """Full serializer for JudgePrompt CRUD."""
    assembled_criteria = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = JudgePrompt
        fields = [
            "id", "name", "display_name", "description",
            "system_prompt", "criteria", "evaluation_steps",
            "scoring_rubric", "few_shot_examples", "variables",
            "category", "language", "version", "is_active",
            "assembled_criteria",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "assembled_criteria"]

    def get_assembled_criteria(self, obj):
        """Return the fully assembled criteria text."""
        return obj.build_criteria_text()


class JudgePromptListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    class Meta:
        model = JudgePrompt
        fields = [
            "id", "name", "display_name", "description",
            "category", "language", "version", "is_active",
            "created_at", "updated_at",
        ]


class PromptDryRunSerializer(serializers.Serializer):
    """For testing a judge prompt against sample data."""
    prompt_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    criteria = serializers.CharField(required=False, default="", allow_blank=True)
    evaluation_steps = serializers.ListField(
        child=serializers.CharField(), required=False, default=list,
    )
    sample = serializers.DictField(
        help_text='Sample data: {input, actual_output, expected_output}',
    )
    judge_model = serializers.DictField(
        help_text='Judge model config: {model, api_base, api_key}',
    )

    def validate_sample(self, value):
        if not value.get("input") and not value.get("actual_output"):
            raise serializers.ValidationError("Sample must have at least 'input' or 'actual_output'")
        return value


# ═══════════════════════════════════════════════════════════
# JudgeModel (Model Config Presets)
# ═══════════════════════════════════════════════════════════

class JudgeModelSerializer(serializers.ModelSerializer):
    """Full serializer for JudgeModel CRUD."""
    masked_api_key = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = JudgeModel
        fields = [
            "id", "name", "display_name", "description",
            "model", "api_base", "api_key", "extra_params",
            "provider", "is_default", "is_active",
            "masked_api_key",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "masked_api_key"]
        extra_kwargs = {
            "api_key": {"write_only": True},
        }

    def get_masked_api_key(self, obj):
        """Return masked API key for display (show last 4 chars)."""
        key = obj.api_key
        if not key:
            return ""
        if len(key) <= 8:
            return "••••••••"
        return "•" * (len(key) - 4) + key[-4:]


class JudgeModelListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list/dropdown views."""
    masked_api_key = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = JudgeModel
        fields = [
            "id", "name", "display_name", "description",
            "model", "api_base", "provider",
            "is_default", "is_active", "masked_api_key",
            "created_at",
        ]

    def get_masked_api_key(self, obj):
        key = obj.api_key
        if not key:
            return ""
        if len(key) <= 8:
            return "••••••••"
        return "•" * (len(key) - 4) + key[-4:]


class ModelTestSerializer(serializers.Serializer):
    """For testing a model endpoint connectivity."""
    model_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    model = serializers.CharField(required=False, default="")
    api_base = serializers.CharField(required=False, default="", allow_blank=True)
    api_key = serializers.CharField(required=False, default="", allow_blank=True)

    def validate(self, attrs):
        if not attrs.get("model_id") and not attrs.get("model"):
            raise serializers.ValidationError("Either model_id or model name is required")
        return attrs