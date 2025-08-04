from .execution import Execution
from django.db import models


class RecurringExecution(Execution):
    class Meta:
        verbose_name = "recurring execution"
        verbose_name_plural = "recurring executions"
        constraints = (
            models.UniqueConstraint(
                fields=("task_key", "run_at"), name="uq_sq_recurring_task_run_at"
            ),
        )

    job = models.OneToOneField(
        "Job",
        verbose_name="job",
        on_delete=models.CASCADE,
        related_name="recurring_execution",
    )
    task_key = models.CharField(max_length=255, verbose_name="task key")
    run_at = models.DateTimeField(verbose_name="run at")
