from django.db import models
from django.tasks import TaskResult

from .execution import Execution, ExecutionQuerySet


class RecurringExecutionQuerySet(ExecutionQuerySet):
    def clearable(self):
        return self.filter(job__isnull=True)

    def record(self, task_result: TaskResult, task, run_at):
        self.update_or_create(
            task=task, run_at=run_at, defaults={"job_id": task_result.id}
        )

    def clear_in_batches(self, batch_size=500):
        while True:
            deleted, _ = self.clearable()[:batch_size].delete()
            if deleted == 0:
                break


class RecurringExecution(Execution):
    class Meta:
        verbose_name = "recurring execution"
        verbose_name_plural = "recurring executions"
        constraints = (
            models.UniqueConstraint(
                fields=("task", "run_at"), name="uq_sq_recurring_task_run_at"
            ),
        )

    objects = RecurringExecutionQuerySet.as_manager()

    job = models.OneToOneField(
        "Job",
        verbose_name="job",
        on_delete=models.CASCADE,
        related_name="recurring_execution",
    )
    task = models.ForeignKey(
        "RecurringTask",
        on_delete=models.CASCADE,
        db_column="task_key",
        to_field="key",
        verbose_name="recurring task",
    )
    run_at = models.DateTimeField(verbose_name="run at")
