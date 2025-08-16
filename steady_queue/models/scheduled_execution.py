from django.db import models, transaction
from django.utils import timezone

from steady_queue.models.dispatching import Dispatching

from .execution import Execution


class ScheduledExecutionQuerySet(models.QuerySet):
    def due(self) -> models.QuerySet["ScheduledExecution"]:
        return self.filter(scheduled_at__lte=timezone.now())

    def ordered(self) -> models.QuerySet["ScheduledExecution"]:
        return self.order_by("scheduled_at", "priority", "job_id")

    def next_batch(self, batch_size: int) -> models.QuerySet["ScheduledExecution"]:
        return self.due().ordered()[:batch_size]


class ScheduledExecution(Dispatching, Execution):
    class Meta:
        verbose_name = "scheduled task"
        verbose_name_plural = "scheduled tasks"

        indexes = (
            models.Index(
                fields=("scheduled_at", "priority", "job"), name="ix_sq_dispatch_all"
            ),
        )

    objects = ScheduledExecutionQuerySet.as_manager()

    job = models.OneToOneField(
        "Job",
        verbose_name="job",
        on_delete=models.CASCADE,
        related_name="scheduled_execution",
    )
    queue_name = models.CharField(max_length=255, verbose_name="queue name")
    priority = models.IntegerField(default=0, verbose_name="priority")
    scheduled_at = models.DateTimeField(verbose_name="scheduled at")

    @property
    def type(self):
        return "scheduled"

    @classmethod
    def dispatch_next_batch(cls, batch_size: int) -> int:
        with transaction.atomic():
            job_ids = (
                cls.objects.next_batch(batch_size)
                .select_for_update(skip_locked=True)
                .values_list("job_id")
            )

            if len(job_ids) == 0:
                return 0
            else:
                return cls.dispatch_jobs(job_ids)

    @classmethod
    def attributes_from_job(cls, job):
        return {
            "queue_name": job.queue_name,
            "priority": job.priority,
            "scheduled_at": job.scheduled_at,
        }
