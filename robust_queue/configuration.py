from dataclasses import dataclass
from datetime import timedelta

from django.db import connection

from robust_queue.processes.runnable import Runnable


class Configuration:
    @dataclass
    class WorkerConfiguration:
        queues: str | list[str] = "*"
        threads: int = 3
        processes: int = 1
        polling_interval: timedelta = timedelta(seconds=1)

    @dataclass
    class DispatcherConfiguration:
        polling_interval: timedelta = timedelta(seconds=0.1)
        batch_size: int = 500
        concurrency_maintenance: bool = True
        concurrency_maintenance_interval: timedelta = timedelta(minutes=5)

    @dataclass
    class ConfigurationOptions:
        workers: list["Configuration.WorkerConfiguration"]
        dispatchers: list["Configuration.DispatcherConfiguration"]
        only_work: bool = False
        skip_recurring: bool = False

        def __init__(
            self,
            workers: list["Configuration.WorkerConfiguration"] | None = None,
            dispatchers: list["Configuration.DispatcherConfiguration"] | None = None,
            only_work: bool = False,
            skip_recurring: bool = False,
        ):
            if workers is None:
                workers = [Configuration.WorkerConfiguration()]

            if dispatchers is None:
                dispatchers = [Configuration.DispatcherConfiguration()]

            self.workers = workers
            self.dispatchers = dispatchers
            self.only_work = only_work
            self.skip_recurring = skip_recurring

    @dataclass
    class Process:
        kind: str
        attributes: dict

        def instantiate(self) -> Runnable:
            if self.kind == "worker":
                from robust_queue.worker import Worker

                return Worker(options=self.attributes)
            elif self.kind == "dispatcher":
                from robust_queue.dispatcher import Dispatcher

                return Dispatcher(options=self.attributes)
            elif self.kind == "scheduler":
                from robust_queue.scheduler import Scheduler

                return Scheduler(options=self.attributes)

            raise ValueError(f"Invalid process kind: {self.kind}")

    def __init__(self, options: ConfigurationOptions = None):
        if options is None:
            options = self.ConfigurationOptions()
        self.options = options

    @property
    def configured_processes(self):
        if self.options.only_work:
            return self.workers

        return self.workers + self.dispatchers + self.schedulers

    @property
    def workers(self):
        workers = []
        for worker_config in self.options.workers:
            workers += [
                self.Process(kind="worker", attributes=worker_config)
            ] * worker_config.processes

        return workers

    @property
    def dispatchers(self):
        return [
            self.Process(kind="dispatcher", attributes=dispatcher_config)
            for dispatcher_config in self.options.dispatchers
        ]

    @property
    def schedulers(self):
        # TODO: implement
        return []

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
