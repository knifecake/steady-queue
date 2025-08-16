from django.db import models
from steady_queue.models.failed_execution import FailedExecution


class RetryableQuerySet(models.QuerySet):
    def failed(self):
        return self.filter(failed_execution__isnull=False)


class Retryable:
    def retry(self):
        if not self.failed_execution:
            return

        self.failed_execution.retry()

    def failed_with(self, error: Exception | str) -> None:
        if isinstance(error, Exception):
            error = f"{error.__class__.__name__}: {error}"

        FailedExecution.objects.get_or_create(
            job=self,
            error=str(error),
        )

    def reset_execution_counters(self):
        self.executions = 0
        self.error_executions = {}
        self.save()
