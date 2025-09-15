import logging

from steady_queue.processes.supervised import Supervised

logger = logging.getLogger("steady_queue")


class Runnable(Supervised):
    mode: str = "async"

    def start(self):
        self.boot()

        if self.is_running_async:
            raise NotImplementedError
        else:
            self.run()

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
        return self.is_running_inline and self.is_all_work_completed

    @property
    def is_all_work_completed(self) -> bool:
        return False

    def set_procline(self):
        pass

    @property
    def is_running_inline(self) -> bool:
        return self.mode == "inline"

    @property
    def is_running_async(self) -> bool:
        return self.mode == "async"

    @property
    def is_running_as_fork(self) -> bool:
        return self.mode == "fork"
