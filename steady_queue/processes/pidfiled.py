from typing import Optional

import steady_queue
from steady_queue.processes.pidfile import Pidfile


class Pidfiled:
    pidfile: Optional[Pidfile] = None

    def boot(self):
        self.setup_pidfile()
        super().boot()

    def shutdown(self):
        super().shutdown()
        self.delete_pidfile()

    def setup_pidfile(self):
        if steady_queue.supervisor_pidfile is not None:
            self.pidfile = Pidfile(steady_queue.supervisor_pidfile)
            self.pidfile.setup()

    def delete_pidfile(self):
        if self.pidfile is not None:
            self.pidfile.delete()
