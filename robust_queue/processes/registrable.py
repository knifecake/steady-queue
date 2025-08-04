import logging
from datetime import timedelta
from typing import Optional

from robust_queue.models import Process
from robust_queue.processes.base import Base
from robust_queue.timer import TimerTask

logger = logging.getLogger("robust_queue")


class Registrable(Base):
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
            supervisor=getattr(self, "supervisor", None),
            # metadata=self.metadata, # TODO: custom serializer
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

    @property
    def is_registered(self):
        return self.process is not None

    def launch_heartbeat(self):
        self.maintenance_task = TimerTask(
            interval=timedelta(seconds=1),
            callable=lambda: self.heartbeat(),
        )

        self.maintenance_task.start()

    def stop_heartbeat(self):
        logger.debug("stopping heartbeat for %s", self.name)
        self.maintenance_task.stop()

    def heartbeat(self):
        try:
            logger.debug("heartbeat from %s", self.name)
            self.process.heartbeat()
        except Process.DoesNotExist:
            self.process = None
            self.wake_up()

    def process_id(self):
        if not self.is_registered:
            return None

        return self.process.id
