from datetime import datetime
from typing import Optional

from django.db import models
from django.utils import timezone

from steady_queue.models.base import BaseModel, UpdatedAtMixin
from steady_queue.models.executable import Executable, ExecutableQuerySet
from steady_queue.task import SteadyQueueTask


class JobQuerySet(ExecutableQuerySet, models.QuerySet):
    def enqueue(self, task: SteadyQueueTask, scheduled_at: Optional[datetime] = None):
        try:
            enqueued_job = self.create(**self.model.attributes_from_django_task(task))
            task.provider_task_id = enqueued_job.id
            return enqueued_job
        except Exception as e:
            # TODO: enqueue error
            raise e


class Job(Executable, UpdatedAtMixin, BaseModel):
    class Meta:
        verbose_name = "task"
        verbose_name_plural = "tasks"
        indexes = (
            models.Index(
                fields=("django_task_id",),
                name="ix_sq_jobs_on_django_task_id",
            ),
            models.Index(fields=("class_name",), name="ix_sq_jobs_on_class_name"),
            models.Index(fields=("finished_at",), name="ix_sq_jobs_on_finished_at"),
            models.Index(
                fields=("queue_name", "finished_at"),
                name="ix_sq_jobs_for_filtering",
            ),
            models.Index(
                fields=("scheduled_at", "finished_at"),
                name="ix_sq_jobs_for_alerting",
            ),
        )

    objects = JobQuerySet.as_manager()

    queue_name = models.CharField(max_length=255, verbose_name="queue name")
    class_name = models.CharField(max_length=255, verbose_name="class name")
    arguments = models.JSONField(verbose_name="arguments")
    priority = models.IntegerField(default=0, verbose_name="priority")
    django_task_id: Optional[str] = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Django task ID"
    )
    scheduled_at = models.DateTimeField(
        blank=True, null=True, verbose_name="scheduled at"
    )
    finished_at = models.DateTimeField(
        blank=True, null=True, verbose_name="finished at"
    )
    concurrency_key = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="concurrency key"
    )

    DEFAULT_QUEUE_NAME = "default"
    DEFAULT_PRIORITY = 0

    @classmethod
    def attributes_from_django_task(cls, task: SteadyQueueTask):
        return {
            "queue_name": task.queue_name or cls.DEFAULT_QUEUE_NAME,
            "django_task_id": task.id,
            "priority": task.priority or cls.DEFAULT_PRIORITY,
            "scheduled_at": task.run_after or timezone.now(),
            "class_name": task.module_path,
            "arguments": task.serialize(),
            "concurrency_key": task.concurrency_key,
        }

    def __str__(self):
        if isinstance(self.pk, int):
            return f"#{self.pk}"

        return self.pk
