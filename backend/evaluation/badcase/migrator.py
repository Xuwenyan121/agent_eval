"""
BadCase Migrator
================
Migrate BadCase feedbacks back into datasets for iterative evaluation.
"""
import logging
from typing import Optional
from django.utils import timezone

from evaluation.models import (
    Dataset, DatasetSample, BadCaseFeedback, EvaluationTask,
)

logger = logging.getLogger(__name__)


class BadCaseMigrator:
    """Migrate BadCase feedbacks to dataset samples for the evaluation feedback loop."""

    def __init__(self, feedbacks: list[BadCaseFeedback]):
        self.feedbacks = feedbacks

    def migrate_to_dataset(
        self,
        target_dataset: Dataset,
        merge_strategy: str = "append",
        include_original_score: bool = True,
        include_trace_summary: bool = True,
    ) -> list[DatasetSample]:
        """
        Migrate feedbacks into an existing dataset as new samples.

        Args:
            target_dataset: The dataset to add samples to.
            merge_strategy: 'append' (always append) or 'skip_duplicate' (skip if same input exists).
            include_original_score: Write original score into notes.
            include_trace_summary: Include trace summary in notes.

        Returns:
            List of created DatasetSample instances.
        """
        created = []
        for fb in self.feedbacks:
            # Skip if already migrated
            if fb.migrated_to_sample:
                logger.info("Feedback %s already migrated, skipping", fb.id)
                continue

            # Skip duplicate inputs if requested
            if merge_strategy == "skip_duplicate":
                exists = DatasetSample.objects.filter(
                    dataset=target_dataset,
                    input=fb.result.input,
                ).exists()
                if exists:
                    logger.info("Duplicate input in dataset %s, skipping feedback %s", target_dataset.id, fb.id)
                    continue

            # Build notes
            notes_parts = [f"[BadCase回流] 原始任务: {fb.result.task.name}"]
            if include_original_score:
                notes_parts.append(f"原始分数: {fb.result.overall_score:.3f}")
            if fb.matched_rules:
                rules = ", ".join(mr.get("rule_name", "unknown") for mr in fb.matched_rules)
                notes_parts.append(f"命中规则: {rules}")
            if fb.review_comment:
                notes_parts.append(f"审核备注: {fb.review_comment}")

            sample = DatasetSample.objects.create(
                dataset=target_dataset,
                sample_id=self._next_sample_id(target_dataset),
                input=fb.result.input,
                expected_output=fb.result.expected_output or "",
                context=fb.result.context or [],
                retrieval_context=fb.result.retrieval_context or [],
                tags=["badcase", "migrated"],
                notes="\n".join(notes_parts),
            )

            # Link feedback to sample
            fb.migrated_to_sample = sample
            fb.migrated_at = timezone.now()
            fb.status = "resolved"
            fb.save(update_fields=["migrated_to_sample", "migrated_at", "status"])

            created.append(sample)
            logger.info("Migrated feedback %s → sample %s in dataset %s", fb.id, sample.sample_id, target_dataset.id)

        # Update dataset metadata
        target_dataset.update_sample_count()
        if not target_dataset.tags:
            target_dataset.tags = []
        if "badcase" not in target_dataset.tags:
            target_dataset.tags = list(target_dataset.tags) + ["badcase"]
        target_dataset.save(update_fields=["tags", "sample_count"])

        logger.info("Migration complete: %d samples created in dataset %s", len(created), target_dataset.id)
        return created

    def create_badcase_dataset(self, name: str, description: str = "") -> Dataset:
        """
        Create a new dataset specifically for BadCase samples and migrate to it.

        Args:
            name: Name for the new dataset.
            description: Description text.

        Returns:
            The created Dataset with samples.
        """
        # Generate unique name
        base_name = name
        counter = 1
        while Dataset.objects.filter(name=base_name, version="v1.0").exists():
            counter += 1
            base_name = f"{name} ({counter})"

        dataset = Dataset.objects.create(
            name=base_name,
            version="v1.0",
            data_type="regression",
            description=description or f"BadCase 回流数据集 - 从评测任务中收集",
            tags=["badcase", "migrated"],
            status="published",
        )

        self.migrate_to_dataset(dataset)
        return dataset

    @staticmethod
    def _next_sample_id(dataset: Dataset) -> str:
        """Generate the next sample_id for a dataset."""
        existing = DatasetSample.objects.filter(dataset=dataset)
        if not existing.exists():
            return "BC-001"
        ids = []
        for s in existing:
            try:
                num = int(s.sample_id.replace("BC-", "").replace("S-", "").lstrip("0") or "0")
                ids.append(num)
            except (ValueError, AttributeError):
                pass
        next_num = max(ids) + 1 if ids else 1
        return f"BC-{next_num:03d}"


# ─── Convenience functions ──────────────────────────────────────────

def migrate_badcases_to_dataset(
    feedback_ids: list[str],
    target_dataset_id: str = None,
    new_dataset_name: str = None,
    merge_strategy: str = "append",
) -> dict:
    """
    Migrate BadCase feedbacks to a dataset.

    Args:
        feedback_ids: List of BadCaseFeedback UUIDs.
        target_dataset_id: UUID of existing dataset (takes priority over new_dataset_name).
        new_dataset_name: Name for a new dataset if target_dataset_id is None.
        merge_strategy: 'append' or 'skip_duplicate'.

    Returns:
        Summary dict.
    """
    feedbacks = list(BadCaseFeedback.objects.filter(id__in=feedback_ids).select_related("result", "result__task"))
    if not feedbacks:
        return {"error": "No feedbacks found", "migrated_count": 0}

    migrator = BadCaseMigrator(feedbacks)

    if target_dataset_id:
        try:
            dataset = Dataset.objects.get(id=target_dataset_id)
        except Dataset.DoesNotExist:
            return {"error": "Target dataset not found", "migrated_count": 0}
        samples = migrator.migrate_to_dataset(dataset, merge_strategy=merge_strategy)
        return {
            "target_dataset_id": str(dataset.id),
            "target_dataset_name": dataset.name,
            "migrated_count": len(samples),
            "sample_ids": [s.sample_id for s in samples],
        }

    if new_dataset_name:
        dataset = migrator.create_badcase_dataset(new_dataset_name)
        return {
            "target_dataset_id": str(dataset.id),
            "target_dataset_name": dataset.name,
            "migrated_count": dataset.sample_count,
        }

    return {"error": "Either target_dataset_id or new_dataset_name is required", "migrated_count": 0}