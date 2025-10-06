from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional

from steady_queue.processes.base import Base


class Configuration:
    @dataclass
    class Worker:
        queues: list[str] = field(default_factory=lambda: ["*"])
        threads: int = 3
        processes: int = 1
        polling_interval: timedelta = timedelta(seconds=1)

    @dataclass
    class Dispatcher:
        polling_interval: timedelta = timedelta(seconds=0.1)
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

    def __init__(self, options: Optional[Options] = None):
        if options is None:
            options = self.Options()
        self.options = options

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
        ensure_configured_processes = len(self.configured_processes) > 0
        ensure_valid_recurring_tasks = True  # TODO
        ensure_correctly_sized_thread_pool = True  # TODO

        return (
            ensure_configured_processes
            and ensure_valid_recurring_tasks
            and ensure_correctly_sized_thread_pool
        )
