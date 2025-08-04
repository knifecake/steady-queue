from dataclasses import dataclass

from robust_queue.processes.runnable import Runnable


class Configuration:
    @dataclass
    class Process:
        kind: str
        attributes: dict

        def instantiate(self) -> Runnable:
            if self.kind == "worker":
                from robust_queue.worker import Worker

                return Worker(**self.attributes)
            elif self.kind == "dispatcher":
                from robust_queue.dispatcher import Dispatcher

                return Dispatcher(**self.attributes)
            elif self.kind == "scheduler":
                from robust_queue.scheduler import Scheduler

                return Scheduler(**self.attributes)

            raise ValueError(f"Invalid process kind: {self.kind}")

    def __init__(self, **kwargs):
        self.options = {**self.default_options, **kwargs}

    @property
    def default_options(self):
        return {
            "only_work": False,
            "config_file": None,
            "recurring_schedule_file": None,
        }

    @property
    def configured_processes(self):
        if self.options["only_work"]:
            return self.workers
        else:
            return self.workers + self.dispatchers + self.schedulers

    @property
    def workers(self):
        return [
            self.Process(kind="worker", attributes={}),
        ]

    @property
    def dispatchers(self):
        return [
            self.Process(kind="dispatcher", attributes={}),
        ]

    @property
    def schedulers(self):
        # TODO: implement
        return []

    @property
    def is_valid(self):
        # TODO: implement
        return True
