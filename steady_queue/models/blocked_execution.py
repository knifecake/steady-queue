from django.db import models

from steady_queue.models.execution import Execution, ExecutionQuerySet


class BlockedExecutionQuerySet(ExecutionQuerySet):
    pass


class BlockedExecution(Execution):
    class Meta:
        verbose_name = "blocked task"
        verbose_name_plural = "blocked tasks"
        indexes = (
            models.Index(
                fields=("concurrency_key", "priority", "job"),
                name="ix_sq_blocked_for_release",
            ),
            models.Index(
                fields=("expires_at", "concurrency_key"),
                name="ix_sq_blocked_for_maintenance",
            ),
        )

    objects = BlockedExecutionQuerySet.as_manager()

    job = models.OneToOneField(
        "Job",
        verbose_name="job",
        on_delete=models.CASCADE,
        related_name="blocked_execution",
    )
    queue_name = models.CharField(max_length=255, verbose_name="queue name")
    priority = models.IntegerField(default=0, verbose_name="priority")
    concurrency_key = models.CharField(max_length=255, verbose_name="concurrency key")
    expires_at = models.DateTimeField(verbose_name="expires at")

    @property
    def type(self):
        return "blocked"
