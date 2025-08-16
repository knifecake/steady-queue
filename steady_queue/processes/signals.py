import logging
import os
import signal
from typing import Iterable, Optional

logger = logging.getLogger("steady_queue")


class Signals:
    SIGNALS = (signal.SIGQUIT, signal.SIGINT, signal.SIGTERM)
    signal_queue: Optional[list] = None

    def boot(self):
        self.register_signal_handlers()
        super().boot()

    def shutdown(self):
        super().shutdown()
        self.restore_default_signal_handlers()

    def register_signal_handlers(self):
        self.signal_queue = []

        def trap(sig, frame):
            self.signal_queue.append(sig)
            self.interrupt()

        for sig in self.SIGNALS:
            signal.signal(sig, trap)

    def restore_default_signal_handlers(self):
        for sig in self.SIGNALS:
            signal.signal(sig, signal.SIG_DFL)

    def process_signal_queue(self):
        while self.signal_queue:
            sig = self.signal_queue.pop(0)
            self.handle_signal(sig)

    def handle_signal(self, sig):
        if sig in (signal.SIGTERM, signal.SIGINT):
            self.stop()
            self.terminate_gracefully()
        elif sig == self.SIGQUIT:
            self.stop()
            self.terminate_immediately()
        else:
            logger.warning("Received unexpected signal %s", sig)

    def signal_processes(self, pids: Iterable[int], signal: int) -> None:
        for pid in pids:
            self.signal_process(pid, signal)

    def signal_process(self, pid: int, signal: int) -> None:
        try:
            os.kill(pid, signal)
        except OSError:
            logger.warning("error killing process", pid, signal)
            pass
