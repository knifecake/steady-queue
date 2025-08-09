from django_tasks import ResultStatus, Task, TaskResult
from django_tasks.backends.base import BaseTaskBackend
from django_tasks.exceptions import ResultDoesNotExist

from robust_queue.models import Job
from robust_queue.task import RobustQueueTask


class RobustQueueBackend(BaseTaskBackend):
    task_class = RobustQueueTask

    supports_defer = True

    supports_async_task = False

    supports_get_result = False

    def enqueue(self, task: Task, args, kwargs) -> TaskResult:
        if not isinstance(task, RobustQueueTask):
            raise ValueError("robust queue only supports RobustQueueTasks")

        if args:
            raise ValueError("robust queue does not support positional arguments yet")

        task.set_arguments(kwargs)
        job = Job.enqueue(task, scheduled_at=task.run_after)
        return self.to_task_result(task, job)

    def get_result(self, result_id: str) -> TaskResult:
        raise ResultDoesNotExist

    def to_task_result(self, task: RobustQueueTask, job: Job):
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
