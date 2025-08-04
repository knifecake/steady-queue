import logging
import threading
import time
from datetime import timedelta
from typing import Callable

logger = logging.getLogger("robust_queue")


def wait_until(timeout: timedelta, condition: Callable):
    timeout = timeout.total_seconds()
    if timeout > 0:
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline and not condition():
            time.sleep(0.1)
            yield
    else:
        while not condition():
            yield


class TimerTask:
    """
    A task that runs periodically in a separate thread to provide as much
    isolation as possible, inspired by Ruby's Concurrent::TimerTask.

    It supports adding observers that are called when an error is found.
    """

    def __init__(self, interval: timedelta, callable: Callable):
        self.interval = interval
        self.callable = callable
        self.is_stopped = False
        self.observers = []

    def add_observer(self, observer: Callable):
        self.observers.append(observer)

    def remove_observer(self, observer: Callable):
        self.observers.remove(observer)

    def start(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def stop(self):
        self.is_stopped = True

        self.thread.join()

    def run(self):
        while not self.is_stopped:
            time.sleep(self.interval.total_seconds())

            # Run the callable in a separate thread to isolate crashes
            work_thread = threading.Thread(target=self.wrapped_callable)
            work_thread.start()
            work_thread.join()

    def wrapped_callable(self):
        try:
            self.callable()
        except Exception as e:
            logger.exception(
                "unhandled exception in timer task: %s", str(e), exc_info=False
            )
