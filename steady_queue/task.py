import datetime
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from django.tasks import Task, TaskResult
from django.utils import timezone, translation
from django.utils.module_loading import import_string

from steady_queue.arguments import Arguments


class UnknownTaskClassError(Exception):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class SteadyQueueTask(Task):
    concurrency_key: Optional[str] = None
    concurrency_limit: Optional[int] = None
    concurrency_duration: Optional[timezone.timedelta] = None
    concurrency_group: Optional[str] = None

    def __post_init__(self):
        self.get_backend().validate_task(self)

    @property
    def id(self) -> str:
        return str(uuid.uuid4())

    def using(
        self,
        *,
        priority: Optional[int] = None,
        queue_name: Optional[str] = None,
        run_after: Optional[datetime.datetime | datetime.timedelta] = None,
        backend: Optional[str] = None,
    ):
        if isinstance(run_after, datetime.timedelta):
            run_after = timezone.now() + run_after

        return super(SteadyQueueTask, self).using(
            priority=priority,
            queue_name=queue_name,
            run_after=run_after,
            backend=backend,
        )

    def enqueue(self, *args: Any, **kwargs: Any) -> TaskResult:
        return self.get_backend().enqueue(self, args, kwargs)

    def serialize(self, args: list, kwargs: dict):
        return {
            "class_name": self.module_path,
            "job_id": self.id,  # TODO: make it stable
            "backend": self.backend,
            "queue_name": self.queue_name,
            "priority": self.priority,
            "arguments": Arguments.serialize_args_and_kwargs(args, kwargs),
            "locale": translation.get_language(),
            "timezone": timezone.get_current_timezone_name(),
            "enqueued_at": timezone.now().isoformat(),
            "scheduled_at": self.run_after.isoformat() if self.run_after else None,
        }

    @classmethod
    def execute(cls, job_data: dict[str, Any]):
        args, kwargs = Arguments.deserialize_args_and_kwargs(job_data["arguments"])
        task = cls.deserialize(job_data)
        task.func(*args, **kwargs)

    @classmethod
    def deserialize(cls, job_data: dict[str, Any]):
        try:
            task_class = import_string(job_data["class_name"])
        except ImportError as e:
            raise UnknownTaskClassError(job_data["class_name"]) from e

        return task_class.using(
            priority=job_data["priority"],
            queue_name=job_data["queue_name"],
            run_after=(
                timezone.datetime.fromisoformat(job_data["scheduled_at"])
                if job_data["scheduled_at"]
                else None
            ),
            backend=job_data["backend"],
        )
