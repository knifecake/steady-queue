from django_tasks import ResultStatus, Task, TaskResult
from django_tasks.backends.base import BaseTaskBackend
from django_tasks.task import P, T

from steady_queue.models import Job
from steady_queue.task import SteadyQueueTask


class SteadyQueueBackend(BaseTaskBackend):
    task_class = SteadyQueueTask

    supports_defer = True

    supports_async_task = False

    supports_get_result = False

    def validate_task(self, task: Task) -> None:
        # TODO: do we need to do anything here?
        super().validate_task(task)

    def enqueue(
        self, task: Task[P, T], args: P.args, kwargs: P.kwargs
    ) -> TaskResult[T]:
        if not isinstance(task, SteadyQueueTask):
            raise ValueError("Steady Queue only supports SteadyQueueTasks")

        task.args = args
        task.kwargs = kwargs
        job = Job.objects.enqueue(task, scheduled_at=task.run_after)
        return self._to_task_result(task, job)

    def get_result(self, result_id: str) -> TaskResult:
        raise NotImplementedError(
            "This backend does not support retrieving or refreshing results."
        )

    def _to_task_result(self, task: SteadyQueueTask, job: Job) -> TaskResult:
        return TaskResult(
            task=task,
            id=str(job.id),
            status=ResultStatus("READY"),
            enqueued_at=job.created_at,
            started_at=None,
            finished_at=job.finished_at,
            last_attempted_at=None,
            args=[],
            kwargs=task.arguments,
            backend=task.backend,
            errors=[],
            worker_ids=[],
        )
