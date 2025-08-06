import uuid
from typing import Any

from django.utils import timezone, translation
from django.utils.module_loading import import_string

from robust_queue.arguments import Arguments
from robust_queue.job.errors import UnknownJobClassError


class Core:
    arguments: dict[str, Any]
    scheduled_at: timezone.datetime
    job_id: str
    # queue_name: str
    # priority: int
    executions: int
    exception_executions: dict[str, int]
    locale: str
    timezone: str
    enqueued_at: timezone.datetime
    successfully_enqueued: bool
    enqueue_error: Exception

    @classmethod
    def deserialize(cls, job_data: dict[str, Any]):
        try:
            job_class = import_string(job_data["job_class"])
        except ImportError as e:
            raise UnknownJobClassError(job_data["job_class"]) from e

        job = job_class()
        job.parse_data(job_data)
        return job

    @classmethod
    def configured_with(cls, /, **kwargs):
        raise NotImplementedError

    def __init__(self, **arguments):
        self.arguments = arguments
        self.job_id = uuid.uuid4()
        # self.queue_name = self.get_queue_name()
        self.scheduled_at = None
        # self.priority = self.get_priority()
        self.executions = 0
        self.exception_executions = {}
        self.timezone = timezone.get_current_timezone_name()

    def serialize(self) -> dict[str, Any]:
        return {
            "class_name": f"{self.__class__.__module__}.{self.__class__.__name__}",
            "job_id": self.job_id,
            "queue_name": self.queue_name,
            "priority": self.priority,
            "arguments": self._serialize_arguments_if_needed(self.arguments),
            "executions": self.executions,
            "exception_executions": self.exception_executions,
            "locale": translation.get_language(),
            "timezone": self.timezone,
            "enqueued_at": timezone.now().isoformat(),
            "scheduled_at": self.scheduled_at.isoformat()
            if self.scheduled_at
            else None,
        }

    def parse_data(self, data: dict[str, Any]) -> None:
        self.job_id = data["job_id"]
        self.queue_name = data["queue_name"]
        self.priority = data["priority"]
        self.serialized_arguments = data["arguments"]
        self.executions = data["executions"]
        self.exception_executions = data["exception_executions"]
        self.locale = data.get("locale", translation.get_language())
        self.timezone = data.get("timezone", timezone.get_current_timezone_name())
        if "enqueued_at" in data:
            self.enqueued_at = timezone.datetime.fromisoformat(data["enqueued_at"])
        if "scheduled_at" in data:
            self.scheduled_at = timezone.datetime.fromisoformat(data["scheduled_at"])

    def set(
        self,
        wait: timezone.timedelta = None,
        wait_until: timezone.datetime = None,
        queue_name: str = None,
        priority: int = None,
    ):
        if wait:
            self.scheduled_at = timezone.now() + wait
        elif wait_until:
            self.scheduled_at = wait_until
        if queue_name:
            self.queue_name = queue_name
        if priority:
            self.priority = priority
        return self

    def _serialize_arguments_if_needed(self, arguments):
        if self.serialized_arguments:
            return self.serialized_arguments
        return Arguments.serialize(arguments)

    def _deserialize_arguments_if_needed(self) -> None:
        if self.serialized_arguments:
            self.arguments = Arguments.deserialize(self.serialized_arguments)
            self.serialized_arguments = None
