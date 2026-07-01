"""
Evaluation Task API Views
==========================
CRUD + progress + stop + comparison + badcase collection/migration/stats
"""

import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from evaluation.models import EvaluationTask, EvaluationResult, BadCaseFeedback, BadCaseCollectionRecord
from evaluation.task_status import TaskStatus, get_task_summary
from evaluation.tasks import run_evaluation_task, collect_badcases_task
from api.serializers import (
    EvaluationTaskSerializer,
    EvaluationTaskListSerializer,
    EvaluationTaskCreateSerializer,
)

logger = logging.getLogger(__name__)


class EvaluationTaskViewSet(viewsets.ModelViewSet):
    queryset = EvaluationTask.objects.all().select_related("agent", "dataset").order_by("-created_at")
    serializer_class = EvaluationTaskSerializer
    lookup_field = "id"

    def get_serializer_class(self):
        if self.action == "create":
            return EvaluationTaskCreateSerializer
        if self.action == "list":
            return EvaluationTaskListSerializer
        return EvaluationTaskSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        sf = self.request.query_params.get("status")
        if sf:
            qs = qs.filter(status=sf)
        aid = self.request.query_params.get("agent")
        if aid:
            qs = qs.filter(agent_id=aid)
        did = self.request.query_params.get("dataset")
        if did:
            qs = qs.filter(dataset_id=did)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)
        return qs

    def perform_create(self, serializer):
        serializer.save(status="pending")

    @action(detail=True, methods=["post"], url_path="run")
    def run_task(self, request, id=None):
        from django.db import transaction
        with transaction.atomic():
            task = EvaluationTask.objects.select_for_update().get(id=id)
            if task.status not in ("pending", "failed", "cancelled"):
                return Response({"error": f"Task is already {task.status}"}, status=400)
            task.status = "running"
            task.save(update_fields=["status"])
        from django.conf import settings as s
        if getattr(s, "CELERY_TASK_ALWAYS_EAGER", False) and getattr(s, "USE_LOCAL_DB", False):
            run_evaluation_task.apply(args=[str(task.id)])
            return Response({"status": "started", "task_id": str(task.id)})
        result = run_evaluation_task.delay(str(task.id))
        from django.core.cache import cache
        cache.set(f"celery_task_id:{str(task.id)}", result.id, timeout=86400)
        return Response({"status": "started", "task_id": str(task.id), "celery_task_id": result.id})

    @action(detail=True, methods=["post"], url_path="stop")
    def stop_task(self, request, id=None):
        task = self.get_object()
        if task.status != "running":
            return Response({"error": f"Task is not running"}, status=400)
        from django.core.cache import cache
        cid = cache.get(f"celery_task_id:{str(task.id)}") or str(task.id)
        TaskStatus.revoke_task(cid, terminate=True)
        task.status = "cancelled"
        task.save(update_fields=["status"])
        TaskStatus.clear_progress(str(task.id))
        return Response({"status": "cancelled"})

    @action(detail=True, methods=["get"], url_path="progress")
    def get_progress(self, request, id=None):
        return Response(get_task_summary(str(id)))

    @action(detail=True, methods=["get"], url_path="badcase-analysis")
    def badcase_analysis(self, request, id=None):
        task = self.get_object()
        if task.status != "completed":
            return Response({"error": "Task is not completed yet."}, status=400)
        badcases = EvaluationResult.objects.filter(task=task, is_badcase=True).order_by("overall_score")
        RMN = {"f1","exact_match","rouge_l","bleu","string_similarity","length_ratio","keyword_coverage","meta_validation"}
        RMA = {"keyword coverage","keywordcoverage","meta validation","metavalidation","string similarity","stringsimilarity","exact match","exactmatch","length ratio","lengthratio","rouge-l","rougel","rouge l","f1 score","f1score"}
        def _r(mn):
            n = mn.lower().strip() if mn else ""
            return n in RMN or n in RMA
        def _c(r):
            if r.error: return "api_error"
            if r.metric_results:
                for mn, md in r.metric_results.items():
                    if isinstance(md, dict) and not md.get("passed", True) and _r(mn):
                        return "keyword_mismatch"
            return "low_score"
        def _b(r):
            it = {"sample_id": r.sample_id, "overall_score": r.overall_score, "error": r.error, "expected_output": r.expected_output, "actual_output": r.actual_output, "failed_metrics": []}
            if r.metric_results:
                for mn, md in r.metric_results.items():
                    if isinstance(md, dict) and not md.get("passed", True):
                        it["failed_metrics"].append({"name": mn, "score": md.get("score",0), "reason": md.get("reason",""), "is_rule": _r(mn)})
            return it
        cats = {"api_error":{"name":"接口报错","key":"api_error","items":[]},"keyword_mismatch":{"name":"关键词匹配失败","key":"keyword_mismatch","items":[]},"low_score":{"name":"评分不达标","key":"low_score","items":[]}}
        for bc in badcases:
            c = _c(bc)
            cats[c]["items"].append(_b(bc))
        result = []
        for c in cats.values():
            c["count"] = len(c["items"])
            result.append(c)
        return Response({"task_id": str(task.id), "task_name": task.name, "total_badcases": badcases.count(), "categories": result})

    @action(detail=False, methods=["post"], url_path="compare")
    def compare_tasks(self, request):
        task_ids = request.data.get("task_ids", [])
        if len(task_ids) < 2:
            return Response({"error": "At least 2 task IDs required"}, status=400)
        comparison = []
        for tid in task_ids:
            try:
                t = EvaluationTask.objects.select_related("agent","dataset").get(id=tid)
                results = EvaluationResult.objects.filter(task=t)
                ms = {}
                for r in results:
                    for mn, data in (r.metric_results or {}).items():
                        sc = data.get("score")
                        if sc is not None:
                            ms.setdefault(mn, []).append(sc)
                ma = {k: round(sum(v)/len(v),4) if v else 0.0 for k,v in ms.items()}
                comparison.append({"task_id": str(t.id),"task_name": t.name,"agent_name": t.agent.name,"dataset_name": t.dataset.name,"status": t.status,"overall_score": t.average_score,"badcase_count": t.badcase_count,"total_samples": t.result_count,"avg_latency_ms": t.avg_latency_ms,"metric_averages": ma,"duration_seconds": t.duration_seconds})
            except EvaluationTask.DoesNotExist:
                comparison.append({"task_id": tid, "error": "Task not found"})
        return Response({"comparison": comparison})

    # ── BadCase Collection ────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="badcases/collect")
    def collect_badcases(self, request, id=None):
        task = self.get_object()
        if task.status != "completed":
            return Response({"error": "Task must be completed"}, status=400)
        rule_ids = request.data.get("rule_ids") if request.data else None
        try:
            result = collect_badcases_task(str(task.id), rule_ids)
            return Response(result)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    @action(detail=True, methods=["get"], url_path="badcases")
    def list_badcases(self, request, id=None):
        task = self.get_object()
        qs = BadCaseFeedback.objects.filter(result__task=task).select_related(
            "result", "collection_rule", "collection_record"
        ).order_by("-created_at")
        sf = request.query_params.get("status")
        if sf: qs = qs.filter(status=sf)
        rid = request.query_params.get("rule_id")
        if rid: qs = qs.filter(collection_rule_id=rid)
        smin = request.query_params.get("score_min")
        if smin: qs = qs.filter(result__overall_score__gte=float(smin))
        smax = request.query_params.get("score_max")
        if smax: qs = qs.filter(result__overall_score__lte=float(smax))
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        total = qs.count()
        items = list(qs[(page-1)*page_size:page*page_size])
        # Enrich list items with result_detail and matched_rules
        enriched = []
        for fb in items:
            enriched.append({
                "id": str(fb.id),
                "result": str(fb.result.id),
                "dataset": str(fb.dataset.id),
                "status": fb.status,
                "reviewer": str(fb.reviewer_id) if fb.reviewer_id else None,
                "reviewer_name": fb.reviewer.username if fb.reviewer else "",
                "review_comment": fb.review_comment or "",
                "created_at": fb.created_at.isoformat() if fb.created_at else None,
                "resolved_at": fb.resolved_at.isoformat() if fb.resolved_at else None,
                "matched_rules": fb.matched_rules or [],
                "result_detail": {
                    "sample_id": fb.result.sample_id,
                    "overall_score": fb.result.overall_score,
                    "input": (fb.result.input or "")[:100],
                    "expected_output": (fb.result.expected_output or "")[:100],
                    "actual_output": (fb.result.actual_output or "")[:100],
                    "metric_results": fb.result.metric_results or {},
                    "latency_ms": fb.result.latency_ms,
                    "error": fb.result.error or "",
                },
            })
        return Response({"count": total, "page": page, "page_size": page_size, "results": enriched})

    @action(detail=True, methods=["get"], url_path="badcases/(?P<feedback_id>[^/.]+)")
    def get_badcase_detail(self, request, id=None, feedback_id=None):
        from django.shortcuts import get_object_or_404
        from evaluation.models import Trace
        from api.serializers import BadCaseFeedbackSerializer, TraceSerializer
        fb = get_object_or_404(BadCaseFeedback, id=feedback_id, result__task_id=id)
        fb_data = BadCaseFeedbackSerializer(fb).data
        if fb.result.trace_id:
            try:
                trace = Trace.objects.get(trace_id=fb.result.trace_id)
                fb_data["trace"] = TraceSerializer(trace).data
            except Trace.DoesNotExist:
                fb_data["trace"] = None
        fb_data["result_detail"] = {
            "sample_id": fb.result.sample_id,
            "overall_score": fb.result.overall_score,
            "input": fb.result.input,
            "expected_output": fb.result.expected_output,
            "actual_output": fb.result.actual_output,
            "metric_results": fb.result.metric_results,
            "latency_ms": fb.result.latency_ms,
            "error": fb.result.error,
        }
        return Response(fb_data)

    @action(detail=True, methods=["get"], url_path="badcases/stats")
    def badcase_stats(self, request, id=None):
        task = self.get_object()
        from django.db.models import Count
        qs = BadCaseFeedback.objects.filter(result__task=task)
        by_status = dict(qs.values_list("status").annotate(cnt=Count("id")).order_by("status"))
        by_rule = dict(qs.values("collection_rule__name").annotate(cnt=Count("id")).order_by("-cnt"))
        crs = BadCaseCollectionRecord.objects.filter(task=task).order_by("-started_at")[:5]
        return Response({
            "task_id": str(task.id), "task_name": task.name,
            "total_badcases": task.badcase_count, "total_feedbacks": qs.count(),
            "by_status": {k: v for k, v in by_status.items()},
            "by_rule": [{"rule_name": r["collection_rule__name"] or "default", "count": r["cnt"]} for r in by_rule],
            "recent_collections": [{"id": str(cr.id), "total_results": cr.total_results, "collected_count": cr.collected_count, "new_feedback_count": cr.new_feedback_count, "status": cr.status, "started_at": cr.started_at.isoformat() if cr.started_at else None, "completed_at": cr.completed_at.isoformat() if cr.completed_at else None} for cr in crs],
        })

    # ── BadCase Migration ────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="badcases/migrate")
    def migrate_badcases(self, request, id=None):
        task = self.get_object()
        feedback_ids = request.data.get("feedback_ids", [])
        target_dataset_id = request.data.get("target_dataset_id")
        new_dataset_name = request.data.get("new_dataset_name")
        merge_strategy = request.data.get("merge_strategy", "append")
        if not feedback_ids:
            return Response({"error": "feedback_ids is required"}, status=400)
        from evaluation.badcase.migrator import migrate_badcases_to_dataset
        try:
            result = migrate_badcases_to_dataset(
                feedback_ids=feedback_ids,
                target_dataset_id=target_dataset_id,
                new_dataset_name=new_dataset_name,
                merge_strategy=merge_strategy,
            )
            return Response(result)
        except Exception as e:
            logger.exception("Migration failed")
            return Response({"error": str(e)}, status=500)

    # ── Global BadCase Stats ─────────────────────────────────────

    @action(detail=False, methods=["get"], url_path="badcases/stats")
    def global_badcase_stats(self, request):
        from django.db.models import Count
        from django.db.models.functions import TruncDate

        agent_id = request.query_params.get("agent_id")
        all_fb = BadCaseFeedback.objects.all()
        if agent_id:
            all_fb = all_fb.filter(result__task__agent_id=agent_id)

        total = all_fb.count()
        by_status = dict(all_fb.values_list("status").annotate(cnt=Count("id")).order_by("status"))
        pending = all_fb.filter(status="pending").count()

        metric_failures = {}
        for fb in all_fb.select_related("result")[:500]:
            for mn, md in (fb.result.metric_results or {}).items():
                if isinstance(md, dict) and not md.get("passed", True):
                    metric_failures[mn] = metric_failures.get(mn, 0) + 1

        trend = all_fb.annotate(date=TruncDate("created_at")).values("date").annotate(cnt=Count("id")).order_by("-date")[:30]

        return Response({
            "total": total,
            "pending": pending,
            "by_status": {k: v for k, v in by_status.items()},
            "top_failed_metrics": sorted(metric_failures.items(), key=lambda x: x[1], reverse=True)[:10],
            "trend": [{"date": str(t["date"]), "count": t["cnt"]} for t in trend],
        })