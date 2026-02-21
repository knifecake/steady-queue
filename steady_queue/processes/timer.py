import logging
import threading
import time
from datetime import timedelta
from typing import Callable

logger = logging.getLogger("steady_queue")


def wait_until(timeout: timedelta, condition: Callable):
    timeout_seconds: float = timeout.total_seconds()
    if timeout_seconds > 0:
        deadline = time.monotonic() + timeout_seconds

        while time.monotonic() < deadline and not condition():
            time.sleep(0.1)
            yield
    else:
        while not condition():
            time.sleep(0.5)
            yield


class TimerTask:
    """
    A task that runs periodically in a separate thread to provide as much
    isolation as possible, inspired by Ruby's Concurrent::TimerTask.
    """

    def __init__(
        self,
        interval: timedelta,
        callable: Callable,
        run_now: bool = False,
    ):
        self.interval = interval
        self.callable = callable
        self.run_now = run_now
        self._stop_event = threading.Event()

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        self._stop_event.set()  # Signal the thread to wake up

        time.sleep(0.1)
        if self.thread.is_alive():
            logger.warning(
                "timer task did not stop within timeout, may still be running"
            )

        self.thread.join(timeout=0.1)
        logger.debug("timer task stopped")

    def run(self):
        if self.run_now:
            self.perform_task()

        while not self._stop_event.is_set():
            # Use Event.wait() for efficient interruptible sleep
            logger.debug("timer task waiting for %s", self.interval)
            if self._stop_event.wait(timeout=self.interval.total_seconds()):
                # Event was set (stop was called), break out of loop
                break

            self.perform_task()

    def perform_task(self):
        # Run the callable in a separate thread to isolate crashes
        work_thread = threading.Thread(target=self.wrapped_callable, daemon=True)
        work_thread.start()
        work_thread.join()

    def wrapped_callable(self):
        try:
            self.callable()
        except Exception as e:
            logger.exception(
                "unhandled exception in timer task: %s", str(e), exc_info=True
            )
