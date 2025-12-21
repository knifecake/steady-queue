from django.db import models, transaction

from .execution import Execution, ExecutionQuerySet


class FailedExecutionQuerySet(ExecutionQuerySet, models.QuerySet):
    def retry(self):
        # TODO: optimize
        with transaction.atomic(using=self.db):
            count = self.count()
            for failed_execution in self.all():
                failed_execution.retry()
            return count


class FailedExecution(Execution):
    class Meta:
        verbose_name = "failed task"
        verbose_name_plural = "failed tasks"

    objects = FailedExecutionQuerySet.as_manager()

    job = models.OneToOneField(
        "Job",
        verbose_name="job",
        on_delete=models.CASCADE,
        related_name="failed_execution",
    )
    error = models.TextField(verbose_name="error", null=True, blank=True)

    @property
    def type(self):
        return "failed"

    def retry(self):
        with self.lock():
            self.job.reset_execution_counters()
            self.job.prepare_for_execution()
            self.delete()
