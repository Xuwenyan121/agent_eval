"""
BadCase Collector
=================
Multi-rule collection engine that evaluates EvaluationResults against
a set of BadCaseCollectionRules and produces BadCaseFeedback records.
"""
import logging
from collections import defaultdict
from typing import Optional

from django.utils import timezone
from django.db import transaction

from evaluation.models import (
    EvaluationTask,
    EvaluationResult,
    EvaluationTask as Task,
    BadCaseCollectionRule,
    BadCaseCollectionRecord,
    BadCaseFeedback,
)
from .matchers import get_matcher

logger = logging.getLogger(__name__)


class BadCaseCollector:
    """
    Collects BadCase samples from a completed EvaluationTask using
    configured collection rules.

    Usage::

        task = EvaluationTask.objects.get(id=task_id)
        rules = BadCaseCollectionRule.objects.filter(enabled=True)
        collector = BadCaseCollector(task, rules)
        collected = collector.collect()
        collector.save_feedbacks(collected)
    """

    def __init__(self, task, rules=None):
        """
        Args:
            task: EvaluationTask instance.
            rules: iterable of BadCaseCollectionRule (or dict) objects.
                   If None, uses default rules from evaluator_config.
        """
        self.task = task
        self.rules = list(rules or [])
        self._results_cache = None

    @property
    def results(self):
        """Lazy-load all evaluation results for this task."""
        if self._results_cache is None:
            self._results_cache = list(
                EvaluationResult.objects.filter(task=self.task).order_by("sample_id")
            )
        return self._results_cache

    def collect(self) -> dict:
        """
        Run all rules against the task's results.

        Returns:
            dict of {rule_id_or_name: [matched_results]}
        """
        if not self.rules:
            logger.info("No collection rules configured for task %s, using defaults", self.task.id)
            self.rules = self._build_default_rules()

        collected = {}
        for rule in self.rules:
            # Skip disabled rules
            if hasattr(rule, "enabled") and not rule.enabled:
                continue
            try:
                matcher = get_matcher(rule)
            except ValueError as e:
                logger.warning("Skipping rule %s: %s", self._rule_name(rule), e)
                continue

            matched = []
            max_count = self._rule_max_count(rule)
            for result in self.results:
                try:
                    if matcher.matches(result):
                        matched.append(result)
                        if max_count and len(matched) >= max_count:
                            break
                except Exception:
                    logger.exception("Matcher error for rule %s on result %s",
                                     self._rule_name(rule), result.sample_id)

            if matched:
                key = self._rule_id(rule)
                collected[key] = matched
                logger.info("Rule '%s' matched %d results", self._rule_name(rule), len(matched))

        return collected

    def save_feedbacks(self, collected: dict,
                       collection_record: Optional[BadCaseCollectionRecord] = None
                       ) -> tuple[int, BadCaseCollectionRecord]:
        """
        Persist collected results as BadCaseFeedback records.

        Deduplicates by (result, collection_rule) to avoid duplicates
        within the same collection run.

        Args:
            collected: dict from self.collect().
            collection_record: existing record to link feedbacks to.

        Returns:
            (new_count, collection_record)
        """
        if collection_record is None:
            collection_record = BadCaseCollectionRecord.objects.create(
                task=self.task,
                rules_snapshot=self._rules_snapshot(),
                total_results=len(self.results),
                collected_count=sum(len(v) for v in collected.values()),
                status="running",
            )

        rule_map = self._build_rule_map()
        new_count = 0
        seen = set()  # (result_id, rule_id) dedup key

        for rule_key, results in collected.items():
            rule = rule_map.get(rule_key)
            for result in results:
                dedup_key = (str(result.id), rule_key)
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                # Build matched_rules list
                matched_rules = []
                if rule:
                    matcher = get_matcher(rule)
                    reason = matcher.reason(result)
                    matched_rules.append({
                        "rule_id": self._rule_id(rule),
                        "rule_name": self._rule_name(rule),
                        "reason": reason,
                    })
                else:
                    matched_rules.append({
                        "rule_id": rule_key,
                        "rule_name": rule_key,
                        "reason": "default rule match",
                    })

                try:
                    BadCaseFeedback.objects.create(
                        result=result,
                        dataset=self.task.dataset,
                        collection_rule=rule if isinstance(rule, BadCaseCollectionRule) else None,
                        collection_record=collection_record,
                        matched_rules=matched_rules,
                        status="pending",
                    )
                    new_count += 1
                except Exception:
                    logger.exception("Failed to create BadCaseFeedback for result %s", result.id)

        # Update collection record
        collection_record.new_feedback_count = new_count
        collection_record.collected_count = sum(len(v) for v in collected.values())
        collection_record.status = "completed"
        collection_record.completed_at = timezone.now()
        collection_record.save(update_fields=["new_feedback_count", "collected_count", "status", "completed_at"])

        logger.info("Collection complete: %d new feedbacks from %d matches",
                     new_count, sum(len(v) for v in collected.values()))

        return new_count, collection_record

    # ─── Default rules ───────────────────────────────────────────────────

    def _build_default_rules(self) -> list:
        """Build default rules from task.evaluator_config or sensible defaults."""
        badcase_config = self.task.evaluator_config.get("badcase_collection", {}) if self.task.evaluator_config else {}
        default_rules = badcase_config.get("default_rules", [])
        if default_rules:
            return default_rules

        # Fallback: use badcase_threshold from evaluator_config
        threshold = self.task.evaluator_config.get("badcase_threshold", 0.6) if self.task.evaluator_config else 0.6
        return [
            {"rule_type": "score_below", "parameters": {"threshold": float(threshold)}, "name": "默认低分收集"},
            {"rule_type": "random", "parameters": {"sample_rate": 0.05}, "name": "随机质量抽查"},
        ]

    # ─── Helpers ─────────────────────────────────────────────────────────

    def _build_rule_map(self) -> dict:
        """Map rule identifiers to rule objects."""
        return {self._rule_id(r): r for r in self.rules}

    def _rules_snapshot(self) -> list:
        """Return a JSON-serializable snapshot of the rules."""
        snapshot = []
        for r in self.rules:
            if hasattr(r, "rule_type"):
                snapshot.append({
                    "id": str(r.id) if hasattr(r, "id") else None,
                    "name": self._rule_name(r),
                    "rule_type": r.rule_type,
                    "parameters": r.parameters or {},
                    "priority": r.priority if hasattr(r, "priority") else 0,
                })
            else:
                snapshot.append(dict(r))
        return snapshot

    @staticmethod
    def _rule_id(rule) -> str:
        if hasattr(rule, "id") and rule.id:
            return str(rule.id)
        return rule.get("name", rule.get("rule_type", "unknown"))

    @staticmethod
    def _rule_name(rule) -> str:
        if hasattr(rule, "name"):
            return rule.name
        return rule.get("name", rule.get("rule_type", "Unknown Rule"))

    @staticmethod
    def _rule_max_count(rule) -> Optional[int]:
        if hasattr(rule, "max_count"):
            return rule.max_count
        return rule.get("max_count")


def collect_badcases_for_task(task_id: str, rule_ids: list = None) -> dict:
    """
    Convenience function: collect BadCases for a task.

    Args:
        task_id: UUID of the EvaluationTask.
        rule_ids: optional list of BadCaseCollectionRule UUIDs to use.
                  If None, loads all enabled rules.

    Returns:
        dict with summary of collection results.
    """
    from evaluation.models import EvaluationTask as TaskModel

    try:
        task = TaskModel.objects.get(id=task_id)
    except TaskModel.DoesNotExist:
        return {"error": "Task not found", "task_id": task_id}

    if rule_ids:
        rules = BadCaseCollectionRule.objects.filter(id__in=rule_ids, enabled=True)
    else:
        rules = BadCaseCollectionRule.objects.filter(enabled=True)

    collector = BadCaseCollector(task, rules)
    collected = collector.collect()

    if not collected:
        return {
            "task_id": str(task.id),
            "task_name": task.name,
            "total_results": len(collector.results),
            "rules_applied": len(collector.rules),
            "collected_count": 0,
            "new_feedback_count": 0,
            "message": "No results matched any rule",
        }

    new_count, record = collector.save_feedbacks(collected)
    return {
        "task_id": str(task.id),
        "task_name": task.name,
        "total_results": len(collector.results),
        "rules_applied": len(collector.rules),
        "collected_count": sum(len(v) for v in collected.values()),
        "new_feedback_count": new_count,
        "collection_record_id": str(record.id),
        "breakdown": {
            collector._rule_name(rule): len(results)
            for rule_key, results in collected.items()
            for rule in collector.rules
            if collector._rule_id(rule) == rule_key
        },
    }