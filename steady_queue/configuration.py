from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional

from crontab import CronTab
from django.core.exceptions import ValidationError
from django.utils.module_loading import import_string

from steady_queue.processes.base import Base


class Configuration:
    @dataclass
    class Worker:
        queues: list[str] = field(default_factory=lambda: ["*"])
        threads: int = 3
        processes: int = 1
        polling_interval: timedelta = timedelta(seconds=0.1)

    @dataclass
    class Dispatcher:
        polling_interval: timedelta = timedelta(seconds=1)
        batch_size: int = 500
        concurrency_maintenance: bool = True
        concurrency_maintenance_interval: timedelta = timedelta(minutes=5)

    @dataclass
    class RecurringTask:
        key: str
        class_name: Optional[str] = None
        command: Optional[str] = None
        arguments: Optional[dict] = None
        schedule: Optional[str] = None
        queue_name: Optional[str] = None
        priority: Optional[int] = None
        description: Optional[str] = None

        @classmethod
        def discover(cls) -> list["Configuration.RecurringTask"]:
            from steady_queue.recurring_task import configurations

            return configurations

        def clean(self) -> None:
            self.clean_schedule()
            self.clean_class_name()
            self.clean_command()

        def clean_schedule(self):
            try:
                CronTab(self.schedule)
            except ValueError as e:
                raise ValidationError(f'Invalid schedule "{self.schedule}": {str(e)}')

        def clean_class_name(self):
            try:
                import_string(self.class_name)
            except ImportError as e:
                raise ValidationError(
                    f'Invalid class name "{self.class_name}": {str(e)}'
                )

        def clean_command(self):
            if self.command is None:
                return

            raise ValidationError("Command is not yet supported for recurring tasks")

    @dataclass
    class Options:
        workers: list["Configuration.Worker"]
        dispatchers: list["Configuration.Dispatcher"]
        recurring_tasks: list["Configuration.RecurringTask"]
        only_work: bool = False
        skip_recurring: bool = False

        def __init__(
            self,
            workers: list["Configuration.Worker"] | None = None,
            dispatchers: list["Configuration.Dispatcher"] | None = None,
            recurring_tasks: list["Configuration.RecurringTask"] | None = None,
            only_work: bool = False,
            skip_recurring: bool = False,
        ):
            if workers is None:
                workers = [Configuration.Worker()]

            if dispatchers is None:
                dispatchers = [Configuration.Dispatcher()]

            if recurring_tasks is None:
                recurring_tasks = Configuration.RecurringTask.discover()

            self.workers = workers
            self.dispatchers = dispatchers
            self.recurring_tasks = recurring_tasks
            self.only_work = only_work
            self.skip_recurring = skip_recurring

    @dataclass
    class Process:
        kind: str
        attributes: dict

        def instantiate(self) -> Base:
            if self.kind == "worker":
                from steady_queue.processes.worker import Worker

                return Worker(options=self.attributes)
            elif self.kind == "dispatcher":
                from steady_queue.processes.dispatcher import Dispatcher

                return Dispatcher(options=self.attributes)
            elif self.kind == "scheduler":
                from steady_queue.processes.scheduler import Scheduler

                return Scheduler(**self.attributes)

            raise ValueError(f"Invalid process kind: {self.kind}")

    options: Options
    errors: list[ValidationError]

    def __init__(self, options: Optional[Options] = None):
        if options is None:
            options = self.Options()
        self.options = options
        self.errors = []

    @property
    def configured_processes(self) -> list["Configuration.Process"]:
        if self.options.only_work:
            return self.workers

        return self.workers + self.dispatchers + self.schedulers

    @property
    def workers(self) -> list["Configuration.Process"]:
        workers = []
        for worker_config in self.options.workers:
            workers += [
                self.Process(kind="worker", attributes=worker_config)
            ] * worker_config.processes

        return workers

    @property
    def dispatchers(self) -> list["Configuration.Process"]:
        return [
            self.Process(kind="dispatcher", attributes=dispatcher_config)
            for dispatcher_config in self.options.dispatchers
        ]

    @property
    def schedulers(self) -> list["Configuration.Process"]:
        return [
            self.Process(
                kind="scheduler",
                attributes={"recurring_tasks": self.options.recurring_tasks},
            )
        ]

    @property
    def is_valid(self):
        self.errors = []
        self.errors.extend(self.validate_configured_processes())
        self.errors.extend(self.validate_recurring_tasks())

        return len(self.errors) == 0

    def validate_configured_processes(self) -> list[ValidationError]:
        if len(self.configured_processes) == 0:
            return [ValidationError("No processes configured")]

        return []

    def validate_recurring_tasks(self) -> list[ValidationError]:
        if self.skip_recurring:
            return []

        if len(self.options.recurring_tasks) == 0:
            return []

        errors = []
        for task in self.options.recurring_tasks:
            try:
                task.clean()
            except ValidationError as e:
                errors.append(
                    ValidationError(f'Invalid recurring task "{task.key}": {e.message}')
                )

        return errors

    @property
    def skip_recurring(self) -> bool:
        return self.options.skip_recurring or self.options.only_work
