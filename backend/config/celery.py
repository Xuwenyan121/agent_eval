"""
Celery application configuration for Agent Evaluation Platform.
Configures task routing, result backend, serialization, and monitoring.
"""

import os
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

_is_local = os.environ.get("USE_LOCAL_DB", "false").lower() in ("true", "1")

# Celery 5.6 doesn't allow changing broker/backend after creation via conf.update.
# Must pass them to the constructor. Skip config_from_object in local mode to avoid
# the Django->config->celery circular import issue.
app = Celery(
    "agent_eval",
    broker="memory://" if _is_local else os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend="cache+memory://" if _is_local else os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
)

if not _is_local:
    app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()


# ─── Task Routing ───────────────────────────────────────────────────

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=os.environ.get("USE_LOCAL_DB", "false").lower() not in ("true", "1"),
    worker_prefetch_multiplier=1,
    result_expires=604800,
    task_routes={
        "evaluation.tasks.run_evaluation_task": {"queue": "evaluation"},
        "evaluation.tasks.run_batch_evaluation": {"queue": "evaluation"},
        "evaluation.tasks.cleanup_expired_tasks": {"queue": "maintenance"},
    },
    broker_transport_options={
        "visibility_timeout": 3600,
    },
)


# ─── Task Signals (Monitoring) ──────────────────────────────────────

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kw):
    """Log task start."""
    import logging
    logger = logging.getLogger("celery.task.signals")
    logger.info("Task started: %s (id=%s)", task.name if task else "unknown", task_id)


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None,
                         retval=None, state=None, **kw):
    """Log task completion."""
    import logging
    logger = logging.getLogger("celery.task.signals")
    logger.info("Task completed: %s (id=%s, state=%s)", task.name if task else "unknown", task_id, state)


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None,
                         kwargs=None, traceback=None, einfo=None, **kw):
    """Log task failure."""
    import logging
    logger = logging.getLogger("celery.task.signals")
    logger.error("Task failed: %s (id=%s, error=%s)", sender.name if sender else "unknown", task_id, exception)


# ─── Health Check Task ──────────────────────────────────────────────

@app.task(bind=True)
def health_check(self):
    """Simple health check task for monitoring."""
    return {"status": "ok", "task_id": self.request.id}
