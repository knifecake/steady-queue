import logging
import os
import signal
import sys
from typing import Optional

from steady_queue.models import Process

logger = logging.getLogger("steady_queue")


class Supervised:
    supervisor: Optional[Process] = None

    @property
    def is_supervised(self) -> bool:
        return self.supervisor is not None

    @property
    def supervisor_went_away(self) -> bool:
        return self.supervisor is not None and self.supervisor.pid != os.getppid()

    def set_procline(self):
        pass

    def register_signal_handlers(self):
        def h(signum, frame):
            logger.info(
                "%s supervised received signal %s", self.name, signal.strsignal(signum)
            )
            self.stop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, h)

        signal.signal(signal.SIGQUIT, lambda *args: sys.exit(1))
