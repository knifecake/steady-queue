import logging
from typing import Optional

import steady_queue
from steady_queue.app_executor import AppExecutor
from steady_queue.models import Process
from steady_queue.processes.base import Base
from steady_queue.processes.timer import TimerTask

logger = logging.getLogger("steady_queue")


class Registrable(Base):
    supervisor: Optional[Process] = None
    process: Optional[Process] = None

    def boot(self):
        super().boot()
        self.register()
        self.launch_heartbeat()

    def shutdown(self):
        self.stop_heartbeat()
        super().shutdown()
        self.deregister()

    def register(self):
        self.process = Process.register(
            kind=self.kind,
            name=self.name,
            pid=self.pid,
            hostname=self.hostname,
            supervisor=self.supervisor,
            metadata=self.metadata,
        )
        logger.debug(
            "Registered PID %s (%s) as %s", self.pid, self.kind, self.process.id
        )

    def deregister(self):
        if self.process is None:
            return

        logger.debug(
            "De-registering PID %s (%s) as %s", self.pid, self.kind, self.process.id
        )

        self.process.deregister()
        logger.debug(
            "de-registered PID %s (%s) as %s", self.pid, self.kind, self.process.id
        )

    @property
    def is_registered(self):
        return self.process is not None

    def launch_heartbeat(self):
        self.heartbeat_task = TimerTask(
            interval=steady_queue.process_heartbeat_interval,
            callable=lambda: self.heartbeat(),
        )

        self.heartbeat_task.start()

    def stop_heartbeat(self):
        logger.debug("stopping heartbeat for %s", self.name)
        self.heartbeat_task.stop()
        logger.debug("stopped heartbeat for %s", self.name)

    def heartbeat(self):
        with AppExecutor.wrap_in_app_executor():
            try:
                logger.debug("heartbeat from %s", self.name)
                self.process.heartbeat()
            except Process.DoesNotExist:
                self.process = None
                self.wake_up()

    @property
    def process_id(self):
        if not self.is_registered:
            return None

        return self.process.id
