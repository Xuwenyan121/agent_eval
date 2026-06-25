from django.contrib import admin
from evaluation.models import (
    AgentEndpoint, Dataset, DatasetSample, EvaluationTask,
    EvaluationResult, Trace, BadCaseFeedback, MetricDefinition,
)


@admin.register(AgentEndpoint)
class AgentEndpointAdmin(admin.ModelAdmin):
    list_display = ["name", "protocol", "status", "task_count", "created_at"]
    list_filter = ["protocol", "status"]
    search_fields = ["name", "endpoint_url"]
    readonly_fields = ["id", "created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("id", "name", "status")}),
        ("Endpoint", {"fields": (
            "endpoint_url", "protocol", "method", "stream",
            "timeout", "retry_times",
        )}),
        ("SSE Config", {"fields": (
            "sse_event_field", "sse_done_marker",
        ), "classes": ("collapse",)}),
        ("Templates", {"fields": (
            "headers", "body_template",
        ), "classes": ("collapse",)}),
        ("Defaults", {"fields": (
            "default_user_id", "default_conv_id", "cache_user",
        ), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


class DatasetSampleInline(admin.TabularInline):
    model = DatasetSample
    extra = 0
    readonly_fields = ["id", "created_at"]
    fields = ["sample_id", "input", "expected_output", "tags"]


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ["name", "version", "data_type", "sample_count", "status", "created_at"]
    list_filter = ["data_type", "status"]
    search_fields = ["name", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [DatasetSampleInline]
    actions = ["publish_datasets", "archive_datasets"]

    @admin.action(description="Mark selected datasets as Published")
    def publish_datasets(self, request, queryset):
        queryset.update(status="published")

    @admin.action(description="Mark selected datasets as Archived")
    def archive_datasets(self, request, queryset):
        queryset.update(status="archived")


@admin.register(DatasetSample)
class DatasetSampleAdmin(admin.ModelAdmin):
    list_display = ["sample_id", "dataset", "short_input", "short_expected", "created_at"]
    list_filter = ["dataset"]
    search_fields = ["sample_id", "input", "expected_output"]
    readonly_fields = ["id", "created_at"]

    @admin.display(description="Input (truncated)")
    def short_input(self, obj):
        return obj.input[:80] + "..." if len(obj.input) > 80 else obj.input

    @admin.display(description="Expected (truncated)")
    def short_expected(self, obj):
        return obj.expected_output[:80] + "..." if len(obj.expected_output) > 80 else obj.expected_output


class EvaluationResultInline(admin.TabularInline):
    model = EvaluationResult
    extra = 0
    readonly_fields = [
        "sample_id", "overall_score", "is_badcase", "latency_ms", "error",
    ]
    fields = ["sample_id", "overall_score", "is_badcase", "latency_ms"]
    can_delete = False
    max_num = 0
    show_change_link = True


@admin.register(EvaluationTask)
class EvaluationTaskAdmin(admin.ModelAdmin):
    list_display = [
        "name", "agent", "dataset", "status",
        "result_count_display", "avg_score_display", "created_at",
    ]
    list_filter = ["status", "agent"]
    search_fields = ["name"]
    readonly_fields = [
        "id", "started_at", "completed_at", "mlflow_run_id",
        "report_path", "created_at",
    ]
    inlines = [EvaluationResultInline]
    fieldsets = (
        (None, {"fields": ("id", "name", "status")}),
        ("Config", {"fields": (
            "agent", "dataset", "judge_model", "evaluator_config",
            "parallel", "limit",
        )}),
        ("Results", {"fields": (
            "started_at", "completed_at", "report_path", "mlflow_run_id",
        )}),
        ("Meta", {"fields": ("created_by", "created_at")}),
    )

    @admin.display(description="Results")
    def result_count_display(self, obj):
        return obj.evaluation_results.count()

    @admin.display(description="Avg Score")
    def avg_score_display(self, obj):
        return f"{obj.average_score:.3f}"


@admin.register(EvaluationResult)
class EvaluationResultAdmin(admin.ModelAdmin):
    list_display = [
        "sample_id", "task", "overall_score", "is_badcase",
        "latency_ms", "has_error", "created_at",
    ]
    list_filter = ["is_badcase", "task"]
    search_fields = ["sample_id", "input", "actual_output"]
    readonly_fields = ["id", "created_at"]
    raw_id_fields = ["task"]

    @admin.display(boolean=True, description="Error?")
    def has_error(self, obj):
        return bool(obj.error)


@admin.register(Trace)
class TraceAdmin(admin.ModelAdmin):
    list_display = ["trace_id", "task", "sample_id", "total_duration_ms", "created_at"]
    list_filter = ["task"]
    search_fields = ["trace_id", "sample_id"]
    readonly_fields = ["trace_id", "created_at"]
    raw_id_fields = ["task"]


@admin.register(BadCaseFeedback)
class BadCaseFeedbackAdmin(admin.ModelAdmin):
    list_display = ["result", "dataset", "status", "reviewer", "created_at"]
    list_filter = ["status", "dataset"]
    readonly_fields = ["id", "created_at"]
    raw_id_fields = ["result", "dataset", "reviewer"]
    actions = ["mark_resolved", "mark_dismissed"]

    @admin.action(description="Mark selected as Resolved")
    def mark_resolved(self, request, queryset):
        from django.utils import timezone
        queryset.update(status="resolved", resolved_at=timezone.now())

    @admin.action(description="Mark selected as Dismissed")
    def mark_dismissed(self, request, queryset):
        queryset.update(status="dismissed")


@admin.register(MetricDefinition)
class MetricDefinitionAdmin(admin.ModelAdmin):
    list_display = [
        "display_name", "name", "category", "type",
        "weight", "default_threshold", "enabled",
    ]
    list_filter = ["category", "type", "enabled"]
    search_fields = ["name", "display_name", "criteria"]
    readonly_fields = ["id", "created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("id", "name", "display_name", "enabled")}),
        ("Classification", {"fields": ("category", "type", "description")}),
        ("Config", {"fields": (
            "criteria", "rule_class", "rule_params",
            "default_params", "weight", "default_threshold",
        )}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
