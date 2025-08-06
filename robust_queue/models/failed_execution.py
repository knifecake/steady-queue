from django.db import models

from .execution import Execution, ExecutionQuerySet


class FailedExecutionQuerySet(ExecutionQuerySet, models.QuerySet):
    pass


class FailedExecution(Execution):
    class Meta:
        verbose_name = "failed execution"
        verbose_name_plural = "failed executions"

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
