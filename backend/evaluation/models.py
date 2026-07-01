import uuid
from django.db import models
from django.db.models import Avg, Count, Sum, Q
from django.utils import timezone


class AgentEndpoint(models.Model):
    """Agent HTTP/SSE endpoint configuration."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="Agent display name")
    endpoint_url = models.CharField(max_length=500, help_text="Full URL of the agent endpoint")
    protocol = models.CharField(
        max_length=20,
        choices=[
            ("http_sse", "HTTP + SSE Streaming"),
            ("http_json", "HTTP JSON Response"),
            ("openai_compat", "OpenAI Compatible"),
        ],
        default="http_sse",
    )
    method = models.CharField(max_length=10, default="POST")
    headers = models.JSONField(default=dict, blank=True, help_text="Request header template with {{var}} support")
    body_template = models.JSONField(default=dict, blank=True, help_text="Request body template with {{var}} support")
    stream = models.BooleanField(default=True, help_text="Whether to expect streaming SSE response")
    sse_event_field = models.CharField(
        max_length=100,
        default="choices[0].delta.content",
        help_text="JSONPath to extract content from SSE event",
    )
    sse_done_marker = models.CharField(
        max_length=50,
        default="[DONE]",
        help_text="SSE stream termination marker",
    )
    default_user_id = models.CharField(max_length=100, default="test_user", blank=True)
    default_conv_id = models.CharField(max_length=100, default="1000000001", blank=True)
    cache_user = models.CharField(max_length=100, default="", blank=True)
    timeout = models.IntegerField(default=60, help_text="Request timeout in seconds")
    retry_times = models.IntegerField(default=3, help_text="Number of retries on failure")
    verify_ssl = models.BooleanField(default=True, help_text="Verify SSL certificate (disable for self-signed certs)")
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("inactive", "Inactive")],
        default="active",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agent_endpoints"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.protocol})"

    def endpoint_config_dict(self) -> dict:
        """Return config dict for collector factory."""
        return {
            "endpoint_url": self.endpoint_url,
            "protocol": self.protocol,
            "method": self.method,
            "headers": self.headers,
            "body_template": self.body_template,
            "stream": self.stream,
            "sse_event_field": self.sse_event_field,
            "sse_done_marker": self.sse_done_marker,
            "timeout": self.timeout,
            "retry_times": self.retry_times,
            "default_user_id": self.default_user_id,
            "default_conv_id": self.default_conv_id,
            "cache_user": self.cache_user,
            "verify_ssl": self.verify_ssl,
        }

    @property
    def task_count(self) -> int:
        return self.tasks.count()

    @property
    def latest_task(self):
        return self.tasks.first()


class Dataset(models.Model):
    """Gold standard evaluation dataset."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    data_type = models.CharField(
        max_length=20,
        choices=[
            ("qa", "QA Pairs"),
            ("image_text", "Image + Text"),
            ("e2e", "End-to-End"),
            ("regression", "Regression Tests"),
        ],
        default="qa",
    )
    version = models.CharField(max_length=20, default="v1.0")
    file_path = models.CharField(max_length=500, blank=True, help_text="S3/OSS path to dataset file")
    sample_count = models.IntegerField(default=0)
    tags = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"),
            ("published", "Published"),
            ("archived", "Archived"),
        ],
        default="draft",
    )
    created_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="datasets"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "datasets"
        ordering = ["-created_at"]
        unique_together = [("name", "version")]

    def __str__(self):
        return f"{self.name} ({self.version}) - {self.sample_count} samples"

    def update_sample_count(self):
        """Sync sample_count with actual sample rows."""
        self.sample_count = self.samples.count()
        self.save(update_fields=["sample_count"])


class DatasetSample(models.Model):
    """Individual sample within a dataset, aligned with DeepEval LLMTestCase."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="samples")
    sample_id = models.CharField(max_length=50, help_text="Unique sample identifier within dataset")
    input = models.TextField(help_text="LLMTestCase.input - the question/prompt")
    expected_output = models.TextField(blank=True, default="", help_text="LLMTestCase.expected_output - gold answer")
    expected_meta = models.JSONField(
        default=dict, blank=True,
        help_text="Expected SSE meta fields for validation, e.g. {\"agentId\": \"xxx\", \"title_contains\": \"keyword\"}"
    )
    context = models.JSONField(default=list, blank=True, help_text="LLMTestCase.context - reference documents")
    retrieval_context = models.JSONField(default=list, blank=True, help_text="LLMTestCase.retrieval_context")
    additional_tools_output = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True, help_text="Scene/difficulty tags")
    notes = models.TextField(blank=True, default="", help_text="Annotation notes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dataset_samples"
        ordering = ["sample_id"]
        unique_together = [("dataset", "sample_id")]

    def __str__(self):
        return f"{self.sample_id}: {self.input[:50]}..."


class EvaluationTask(models.Model):
    """Evaluation task execution configuration and status."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    agent = models.ForeignKey(AgentEndpoint, on_delete=models.CASCADE, related_name="tasks")
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="tasks")
    judge_model = models.JSONField(
        default=dict,
        help_text='Judge model config: {"model": "gpt-4o", "api_base": "...", "api_key": "<encrypted>"}',
    )
    evaluator_config = models.JSONField(
        default=dict,
        help_text="Metrics config with weights, thresholds, and criteria",
    )
    parallel = models.IntegerField(default=10, help_text="Max concurrent agent calls")
    limit = models.IntegerField(null=True, blank=True, help_text="Limit sample count (null = all)")
    conv_id_strategy = models.CharField(
        max_length=20,
        choices=[
            ("dataset", "Use dataset convId (multi-turn for same convId)"),
            ("isolated", "Unique convId per sample (all single-turn)"),
            ("shared", "All samples share one convId (one session)"),
        ],
        default="dataset",
        help_text="How convId is assigned: dataset-driven, per-sample isolated, or shared session",
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("running", "Running"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        default="pending",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    report_path = models.CharField(max_length=500, blank=True, default="")
    mlflow_run_id = models.CharField(max_length=100, blank=True, default="", help_text="MLflow tracking run ID")
    created_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "evaluation_tasks"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} [{self.status}]"

    @property
    def duration_seconds(self) -> float:
        """Task execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

    @property
    def result_count(self) -> int:
        return self.evaluation_results.count()

    @property
    def badcase_count(self) -> int:
        return self.evaluation_results.filter(is_badcase=True).count()

    @property
    def average_score(self) -> float:
        agg = self.evaluation_results.aggregate(avg=Avg("overall_score"))
        return round(agg["avg"] or 0.0, 4)

    @property
    def avg_latency_ms(self) -> float:
        agg = self.evaluation_results.filter(latency_ms__gt=0).aggregate(avg=Avg("latency_ms"))
        return round(agg["avg"] or 0.0, 1)

    @property
    def error_count(self) -> int:
        return self.evaluation_results.exclude(error="").count()

    def summary(self) -> dict:
        """Quick summary for API responses."""
        return {
            "total_samples": self.result_count,
            "average_score": self.average_score,
            "badcase_count": self.badcase_count,
            "error_count": self.error_count,
            "avg_latency_ms": self.avg_latency_ms,
            "duration_seconds": self.duration_seconds,
        }


class EvaluationResult(models.Model):
    """Per-sample evaluation result."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(EvaluationTask, on_delete=models.CASCADE, related_name="evaluation_results")
    sample_id = models.CharField(max_length=50)
    input = models.TextField(blank=True, default="")
    expected_output = models.TextField(blank=True, default="")
    actual_output = models.TextField(blank=True, default="", help_text="Aggregated agent response")
    context = models.JSONField(default=list, blank=True)
    retrieval_context = models.JSONField(default=list, blank=True)
    metric_results = models.JSONField(
        default=dict,
        help_text='Per-metric results: {"metric_name": {"score": 0.85, "passed": true, "reason": "..."}}',
    )
    overall_score = models.FloatField(default=0.0, help_text="Weighted overall score")
    is_badcase = models.BooleanField(default=False, help_text="overall_score < badcase_threshold")
    trace_id = models.CharField(max_length=100, blank=True, default="", db_index=True)
    latency_ms = models.IntegerField(default=0, help_text="Agent response latency in milliseconds")
    error = models.TextField(blank=True, default="", help_text="Collection/evaluation error message")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "evaluation_results"
        ordering = ["-overall_score"]
        indexes = [
            models.Index(fields=["task", "is_badcase"]),
            models.Index(fields=["task", "-overall_score"]),
        ]

    def __str__(self):
        return f"{self.sample_id}: score={self.overall_score:.3f} badcase={self.is_badcase}"

    @property
    def score_breakdown(self) -> list:
        """Return metric results as a sorted list for API responses."""
        return sorted(
            [
                {"name": k, **v}
                for k, v in (self.metric_results or {}).items()
            ],
            key=lambda x: x.get("score", 0),
            reverse=True,
        )


class Trace(models.Model):
    """Agent interaction trace stored as PostgreSQL JSONB."""

    trace_id = models.CharField(max_length=100, primary_key=True)
    task = models.ForeignKey(EvaluationTask, on_delete=models.CASCADE, related_name="traces")
    sample_id = models.CharField(max_length=50)
    trace_data = models.JSONField(default=dict, blank=True, help_text="OpenTelemetry/DeepEval trace payload")
    spans = models.JSONField(default=list, blank=True, help_text="Step array: [{type, duration_ms, output, ...}]")
    raw_sse_chunks = models.JSONField(default=list, blank=True, help_text="Raw SSE chunks for debugging")
    final_output = models.TextField(blank=True, default="")
    total_tokens = models.IntegerField(default=0)
    total_duration_ms = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "traces"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Trace {self.trace_id} ({self.sample_id})"


class BadCaseCollectionRule(models.Model):
    """BadCase collection rule definition with flexible dimensions."""

    RULE_TYPES = [
        ("score_below", "Score Below Threshold"),
        ("score_above", "Score Above Threshold (Spot Check)"),
        ("metric_below", "Per-Metric Below Threshold"),
        ("metric_above", "Per-Metric Above Threshold"),
        ("boundary", "Boundary Samples"),
        ("random", "Random Sampling"),
        ("stratified", "Stratified Sampling"),
        ("error", "Error Samples"),
        ("high_latency", "High Latency"),
        ("low_latency", "Low Latency (Suspected Cache)"),
        ("score_variance", "Score Variance (Judge Disagreement)"),
        ("custom", "Custom Expression"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    rule_type = models.CharField(max_length=30, choices=RULE_TYPES)
    parameters = models.JSONField(default=dict, help_text="Rule parameters (threshold, sample_rate, etc.)")
    target_dataset = models.ForeignKey(
        Dataset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="collection_rules",
    )
    auto_collect = models.BooleanField(
        default=False,
        help_text="Whether to auto-trigger collection when a linked task completes",
    )
    enabled = models.BooleanField(default=True)
    priority = models.IntegerField(default=0, help_text="Higher priority rules run first")
    max_count = models.IntegerField(null=True, blank=True, help_text="Max samples to collect per run (null = unlimited)")
    created_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "badcase_collection_rules"
        ordering = ["-priority", "-created_at"]

    def __str__(self):
        return f"{self.name} ({self.rule_type}) priority={self.priority}"


class BadCaseCollectionRecord(models.Model):
    """Audit log for each collection execution."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    task = models.ForeignKey(
        EvaluationTask, on_delete=models.CASCADE, related_name="collection_records",
    )
    rules_snapshot = models.JSONField(help_text="Snapshot of rules applied during this run")
    total_results = models.IntegerField(help_text="Total evaluation results in the task")
    collected_count = models.IntegerField(default=0, help_text="Total BadCase samples collected this run")
    new_feedback_count = models.IntegerField(default=0, help_text="New BadCaseFeedback records created")
    status = models.CharField(
        max_length=20,
        choices=[
            ("running", "Running"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="running",
    )
    error_message = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "badcase_collection_records"
        ordering = ["-started_at"]

    def __str__(self):
        return f"Collection for {self.task.name} [{self.status}] - {self.collected_count} badcases"


class BadCaseFeedback(models.Model):
    """BadCase feedback and annotation tracking."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    result = models.ForeignKey(EvaluationResult, on_delete=models.CASCADE, related_name="feedbacks")
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="badcase_feedbacks")
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending Review"),
            ("reviewing", "Under Review"),
            ("resolved", "Resolved"),
            ("dismissed", "Dismissed"),
        ],
        default="pending",
    )
    reviewer = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="reviews"
    )
    review_comment = models.TextField(blank=True, default="")

    # ── Collection tracking (new) ──────────────────────────────────
    collection_rule = models.ForeignKey(
        BadCaseCollectionRule, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="feedbacks",
    )
    collection_record = models.ForeignKey(
        BadCaseCollectionRecord, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="feedbacks",
    )
    matched_rules = models.JSONField(
        default=list, blank=True,
        help_text='Rules that matched: [{"rule_id": "...", "rule_name": "...", "reason": "..."}]',
    )

    # ── Migration tracking (new) ───────────────────────────────────
    migrated_to_sample = models.ForeignKey(
        DatasetSample, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="source_feedbacks",
    )
    migrated_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "badcase_feedbacks"
        ordering = ["-created_at"]

    def __str__(self):
        return f"BadCase {self.result.sample_id} [{self.status}]"


class MetricDefinition(models.Model):
    """Metric definition registry with weight configuration."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, help_text="Metric identifier (e.g. 'truthfulness')")
    display_name = models.CharField(max_length=100, help_text="Human-readable name")
    category = models.CharField(
        max_length=20,
        choices=[
            ("business_dim", "Business Dimension (G-Eval)"),
            ("ml_metric", "Traditional ML Metric (Rule-based)"),
            ("multimodal", "Multimodal Metric (Reserved)"),
        ],
        default="business_dim",
    )
    type = models.CharField(
        max_length=20,
        choices=[
            ("g_eval", "G-Eval (LLM-as-Judge)"),
            ("rule", "Rule-based"),
            ("custom", "Custom"),
            ("multimodal", "Multimodal (Reserved)"),
        ],
        default="g_eval",
    )
    criteria = models.TextField(blank=True, default="", help_text="G-Eval scoring criteria text")
    rule_class = models.CharField(max_length=100, blank=True, default="", help_text="Rule metric class name")
    rule_params = models.JSONField(default=dict, blank=True, help_text="Rule metric parameters")
    default_params = models.JSONField(default=dict, blank=True, help_text="Default parameters for this metric")
    weight = models.FloatField(default=1.0, help_text="Weight for overall score aggregation")
    default_threshold = models.FloatField(default=0.6, help_text="Default pass/fail threshold")
    enabled = models.BooleanField(default=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "metric_definitions"
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.display_name} ({self.name}) weight={self.weight}"


class JudgePrompt(models.Model):
    """
    Custom LLM Judge prompt template for G-Eval scoring.

    Stores structured prompt designs including criteria text, evaluation steps,
    scoring rubric, and few-shot examples.  Referenced by evaluator_config via
    prompt_id when building GEval metrics.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text="Prompt identifier (e.g. 'correctness_zh')")
    display_name = models.CharField(max_length=200, help_text="Human-readable name")
    description = models.TextField(blank=True, default="", help_text="What this prompt evaluates")

    # ─── Core prompt content ────────────────────────────────────────
    system_prompt = models.TextField(
        blank=True, default="",
        help_text="System role instruction sent to the judge LLM (optional)",
    )
    criteria = models.TextField(
        help_text="Main evaluation criteria text — replaces GEval criteria",
    )
    evaluation_steps = models.JSONField(
        default=list, blank=True,
        help_text='Ordered scoring steps: ["1. Read the input", "2. Compare outputs", ...]',
    )

    # ─── Scoring rubric ─────────────────────────────────────────────
    scoring_rubric = models.JSONField(
        default=dict, blank=True,
        help_text='Score-level descriptions: {"1": "completely wrong", "3": "partial", "5": "perfect"}',
    )

    # ─── Few-shot examples ──────────────────────────────────────────
    few_shot_examples = models.JSONField(
        default=list, blank=True,
        help_text='Example evaluations: [{input, actual_output, expected_output, score, reason}]',
    )

    # ─── Template variables ─────────────────────────────────────────
    variables = models.JSONField(
        default=list, blank=True,
        help_text='Variable names used in the prompt: ["input", "actual_output", "expected_output"]',
    )

    # ─── Metadata ───────────────────────────────────────────────────
    category = models.CharField(
        max_length=30,
        choices=[
            ("general", "通用"),
            ("correctness", "正确性"),
            ("relevance", "相关性"),
            ("faithfulness", "忠实度"),
            ("safety", "安全性"),
            ("domain_specific", "领域专用"),
        ],
        default="general",
    )
    language = models.CharField(
        max_length=10,
        choices=[("zh", "中文"), ("en", "English")],
        default="zh",
    )
    version = models.IntegerField(default=1, help_text="Prompt version for tracking iterations")
    is_active = models.BooleanField(default=True, help_text="Whether this prompt is available for use")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "judge_prompts"
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.display_name} ({self.name}) v{self.version}"

    def build_criteria_text(self) -> str:
        """
        Assemble the full criteria text for GEval by combining
        criteria, evaluation_steps, and scoring_rubric.
        """
        parts = [self.criteria]

        if self.evaluation_steps:
            parts.append("\n评估步骤：")
            for i, step in enumerate(self.evaluation_steps, 1):
                parts.append(f"{i}. {step}")

        if self.scoring_rubric:
            parts.append("\n评分标准：")
            for score, desc in sorted(self.scoring_rubric.items(), key=lambda x: float(x[0]) if x[0].replace(".", "").isdigit() else 0):
                parts.append(f"- {score}分: {desc}")

        return "\n".join(parts)


class JudgeModel(models.Model):
    """
    Saved LLM judge model configuration preset.

    Stores reusable model endpoint configurations (model name, API base URL,
    API key, extra params) so users don't have to re-enter them every time
    they create a task or run a dry-run.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text="Config identifier (e.g. 'gpt4o_prod')")
    display_name = models.CharField(max_length=200, help_text="Human-readable name (e.g. 'GPT-4o Production')")
    description = models.TextField(blank=True, default="", help_text="Notes about this model config")

    # ─── Endpoint configuration ─────────────────────────────────────
    model = models.CharField(
        max_length=200,
        help_text="Model identifier (e.g. 'gpt-4o', 'deepseek-chat', 'qwen-max')",
    )
    api_base = models.URLField(
        max_length=500, blank=True, default="",
        help_text="OpenAI-compatible API base URL (e.g. https://api.openai.com/v1)",
    )
    api_key = models.TextField(
        blank=True, default="",
        help_text="API key (stored encrypted in production, plain in dev)",
    )
    extra_params = models.JSONField(
        default=dict, blank=True,
        help_text='Additional parameters: {"temperature": 0.1, "max_tokens": 4096, ...}',
    )

    # ─── Metadata ───────────────────────────────────────────────────
    provider = models.CharField(
        max_length=50,
        choices=[
            ("openai", "OpenAI"),
            ("azure", "Azure OpenAI"),
            ("deepseek", "DeepSeek"),
            ("qwen", "通义千问"),
            ("zhipu", "智谱 AI"),
            ("moonshot", "Moonshot"),
            ("custom", "自定义"),
        ],
        default="custom",
        help_text="Model provider for display/filtering",
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the default judge model for new tasks",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "judge_models"
        ordering = ["-is_default", "provider", "name"]

    def __str__(self):
        return f"{self.display_name} ({self.model})"

    def to_config(self) -> dict:
        """Return a dict compatible with get_judge_endpoint()."""
        cfg = {"model": self.model}
        if self.api_base:
            cfg["api_base"] = self.api_base
        if self.api_key:
            cfg["api_key"] = self.api_key
        if self.extra_params:
            cfg["extra_params"] = self.extra_params
        return cfg

    def save(self, *args, **kwargs):
        # Ensure only one default at a time
        if self.is_default:
            JudgeModel.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)