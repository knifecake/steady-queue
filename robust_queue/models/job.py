from django.db import models
from django.utils import timezone

from robust_queue.models.executable import Executable
from robust_queue.task import BaseTask

from .base import BaseModel
from .mixins import UpdatedAtMixin


class Job(Executable, UpdatedAtMixin, BaseModel):
    class Meta:
        verbose_name = "job"
        verbose_name_plural = "jobs"
        indexes = (
            models.Index(
                fields=("django_task_id",),
                name="ix_rq_jobs_on_django_task_id",
            ),
            models.Index(fields=("class_name",), name="ix_rq_jobs_on_class_name"),
            models.Index(fields=("finished_at",), name="ix_rq_jobs_on_finished_at"),
            models.Index(
                fields=("queue_name", "finished_at"),
                name="ix_rq_jobs_for_filtering",
            ),
            models.Index(
                fields=("scheduled_at", "finished_at"),
                name="ix_rq_jobs_for_alerting",
            ),
        )

    queue_name = models.CharField(max_length=255, verbose_name="queue name")
    class_name = models.CharField(max_length=255, verbose_name="class name")
    arguments = models.JSONField(verbose_name="arguments")
    priority = models.IntegerField(default=0, verbose_name="priority")
    django_task_id = models.CharField(
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

    @classmethod
    def enqueue(cls, task: BaseTask, scheduled_at: timezone.datetime = None) -> None:
        serialized_task = task.serialize()
        job = cls(
            queue_name=serialized_task["queue_name"],
            class_name=serialized_task["class_name"],
            arguments=serialized_task["arguments"],
            priority=serialized_task["priority"],
            scheduled_at=scheduled_at,
            django_task_id=serialized_task["job_id"],
        )
        job.save()
