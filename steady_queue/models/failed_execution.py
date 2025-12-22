from django.db import models, transaction

from steady_queue.models.dispatching import Dispatching

from .execution import Execution, ExecutionQuerySet


class FailedExecutionQuerySet(ExecutionQuerySet, models.QuerySet):
    def retry(self) -> int:
        return self.model.retry_all(
            [
                failed_execution.job
                for failed_execution in self.select_related("job").all()
            ]
        )


class FailedExecution(Dispatching, Execution):
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

    @classmethod
    def retry_all(cls, jobs: list) -> int:
        with transaction.atomic(using=cls.objects.db):
            job_ids = cls.objects.lock_all_from_jobs(jobs)
            return cls.dispatch_jobs(job_ids)
