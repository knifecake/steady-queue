from django.db import models

from .execution import Execution


class ReadyExecution(Execution):
    class Meta:
        verbose_name = "ready execution"
        verbose_name_plural = "ready executions"
        indexes = (
            models.Index(fields=("priority", "job"), name="ix_rq_poll_all"),
            models.Index(
                fields=("queue_name", "priority", "created_at"),
                name="ix_rq_poll_for_queue",
            ),
        )

    job = models.OneToOneField(
        "Job",
        verbose_name="job",
        on_delete=models.CASCADE,
        related_name="ready_execution",
    )

    queue_name = models.CharField(max_length=255, verbose_name="queue name")
    priority = models.IntegerField(default=0, verbose_name="priority")

    @property
    def type(self):
        return "ready"
