import logging
import os

from django.db import connections

from robust_queue.processes.supervised import Supervised

logger = logging.getLogger("robust_queue")


class Runnable(Supervised):
    mode: str = "async"

    def start(self):
        logger.info("starting runnable %s (PID %d)", self.name, os.getpid())
        self.boot()
        logger.debug("booted runnable %s", self.name)

        if self.is_running_async:
            raise NotImplementedError
        else:
            logger.debug("running runnable %s", self.name)
            self.run()
            logger.info("runnable %s finished, exiting", self.name)

    def stop(self):
        super().stop()
        self.wake_up()
        # TODO: join thread

    def boot(self):
        self.reset_database_connections()
        super().boot()
        if self.is_running_as_fork:
            self.register_signal_handlers()
            self.set_procline()

    @property
    def is_shutting_down(self) -> bool:
        return (
            self.is_stopped
            or (self.is_running_as_fork and self.supervisor_went_away)
            or self.is_finished
            or not self.is_registered
        )

    def run(self):
        raise NotImplementedError

    @property
    def is_finished(self) -> bool:
        self.is_running_inline and self.is_all_work_completed

    @property
    def is_all_work_completed(self) -> bool:
        return False

    def set_procline(self):
        pass

    def reset_database_connections(self):
        connections.close_all()

    @property
    def is_running_inline(self) -> bool:
        return self.mode == "inline"

    @property
    def is_running_async(self) -> bool:
        return self.mode == "async"

    @property
    def is_running_as_fork(self) -> bool:
        return self.mode == "fork"
