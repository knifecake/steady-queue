import logging
import os
import select
from datetime import timedelta
from functools import cached_property

logger = logging.getLogger("robust_queue")


class Interruptible:
    def wake_up(self):
        logger.debug("%s: wake_up", self.name)
        self.interrupt()

    def interruptible_sleep(self, duration: timedelta):
        """Sleep for the given duration, but can be interrupted by signals."""
        try:
            # Use select to wait on the read end of the pipe with a timeout
            ready, _, _ = select.select(
                [self.self_pipe[0]], [], [], duration.total_seconds()
            )
            if ready:
                logger.debug("%s: interruptible_sleep: interrupt received", self.name)
                # Signal received, drain the pipe to avoid accumulating data
                try:
                    os.read(self.self_pipe[0], 1024)
                except OSError:
                    # Pipe might be closed during shutdown, ignore
                    pass
        except OSError:
            # select() can be interrupted by signals on some systems, that's fine
            pass

    def interrupt(self):
        try:
            os.write(self.self_pipe[1], b"1")
        except OSError:
            # Pipe might be closed during shutdown, ignore
            pass

    @cached_property
    def self_pipe(self) -> tuple[int, int]:
        return os.pipe()

    def shutdown(self):
        """Clean up pipe file descriptors."""
        # Check if the cached_property has been accessed (pipe created)
        if "self_pipe" in self.__dict__:
            try:
                os.close(self.self_pipe[0])
                os.close(self.self_pipe[1])
            except OSError:
                pass
        logger.debug("%s: interruptible shutdown done", self.name)
        super().shutdown()
