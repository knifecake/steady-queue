from django.db import models, transaction

from .execution import Execution


class ClaimedExecutionQuerySet(models.QuerySet):
    def fail_all_with(self, error: str):
        executions = self.select_related("job").all()
        for execution in executions:
            execution.failed_with(error)
            execution.unblock_next_job()

    def release_all(self):
        for execution in self.all():
            execution.release()


class ClaimedExecution(Execution):
    class Meta:
        verbose_name = "claimed execution"
        verbose_name_plural = "claimed executions"
        indexes = (
            models.Index(
                fields=("process_id", "job_id"), name="ix_rq_claimed_process_job"
            ),
        )

    objects = ClaimedExecutionQuerySet.as_manager()

    job = models.OneToOneField(
        "Job",
        verbose_name="job",
        on_delete=models.CASCADE,
        related_name="claimed_execution",
    )
    process = models.ForeignKey(
        "Process",
        verbose_name="process",
        on_delete=models.CASCADE,
        related_name="claimed_executions",
    )

    @property
    def type(self):
        return "claimed"

    def failed_with(self, error: str):
        with transaction.atomic():
            self.job.failed_with(error)
            self.delete()

    def unblock_next_job(self):
        self.job.unblock_next_job()
