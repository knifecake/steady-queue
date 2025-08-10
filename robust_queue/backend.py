from django_tasks import ResultStatus, Task, TaskResult
from django_tasks.backends.base import BaseTaskBackend
from django_tasks.task import P, T

from robust_queue.models import Job
from robust_queue.task import RobustQueueTask


class RobustQueueBackend(BaseTaskBackend):
    task_class = RobustQueueTask

    supports_defer = True

    supports_async_task = False

    supports_get_result = False

    def validate_task(self, task: Task) -> None:
        # TODO: do we need to do anything here?
        super().validate_task(task)

    def enqueue(
        self, task: Task[P, T], args: P.args, kwargs: P.kwargs
    ) -> TaskResult[T]:
        if not isinstance(task, RobustQueueTask):
            raise ValueError("robust queue only supports RobustQueueTasks")

        task.args = args
        task.kwargs = kwargs
        job = Job.enqueue(task, scheduled_at=task.run_after)
        return self._to_task_result(task, job)

    def get_result(self, result_id: str) -> TaskResult:
        raise NotImplementedError(
            "This backend does not support retrieving or refreshing results."
        )

    def _to_task_result(self, task: RobustQueueTask, job: Job):
        return TaskResult(
            task=task,
            id=job.id,
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
