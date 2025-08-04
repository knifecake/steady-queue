import uuid
from typing import Any

from django.utils import timezone
from django.utils.module_loading import import_string
from django.utils.translation import get_language

from robust_queue.arguments import Arguments


class UnknownTaskError(Exception):
    def __init__(self, task_name: str):
        self.task_name = task_name

    def __str__(self):
        return f"Unknown task: {self.task_name}"


class BaseTask:
    priority: int = 0
    queue_name: str = "default"

    def __init__(self, /, **kwargs):
        self.arguments = kwargs
        self.job_id = uuid.uuid4()
        self.scheduled_at = None
        self.executions = 0
        self.exception_executions = {}

    def perform(self, **kwargs) -> Any:
        raise NotImplementedError

    def set(
        self,
        wait: timezone.timedelta = None,
        wait_until: timezone.datetime = None,
        queue_name: str = None,
        priority: int = None,
    ) -> "BaseTask":
        if wait:
            self.scheduled_at = timezone.now() + wait
        elif wait_until:
            self.scheduled_at = wait_until
        if queue_name:
            self.queue_name = queue_name
        if priority:
            self.priority = priority

        return self

    def enqueue(self) -> None:
        from robust_queue.models.job import Job

        Job.enqueue(self, scheduled_at=self.scheduled_at)

    def serialize(self) -> dict[str, Any]:
        return {
            "class_name": f"{self.__class__.__module__}.{self.__class__.__name__}",
            "job_id": self.job_id,
            "timezone": timezone.get_current_timezone_name(),
            "locale": get_language(),
            "enqueued_at": timezone.now().isoformat(),
            "priority": self.priority,
            "queue_name": self.queue_name,
            "arguments": self.arguments,
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "BaseTask":
        try:
            task_class = import_string(data["class_name"])
        except ImportError:
            raise UnknownTaskError(data["class_name"])

        task = task_class(**Arguments.deserialize(data["arguments"]))

        task.job_id = data["job_id"]
        task.timezone = data["timezone"]
        task.locale = data["locale"]
        task.enqueued_at = data["enqueued_at"]
        task.priority = data["priority"]
        task.queue_name = data["queue_name"]

        return task

    @classmethod
    def perform_now(cls, /, **kwargs):
        task = cls(**kwargs)
        return task.perform(**task.arguments)

    @classmethod
    def perform_later(cls, /, **kwargs) -> None:
        task = cls(**kwargs)
        task.enqueue()
