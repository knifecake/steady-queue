from datetime import datetime
from typing import Optional


class ProcessPrunedError(RuntimeError):
    def __init__(self, last_heartbeat_at: Optional[datetime] = None):
        self.last_heartbeat_at = last_heartbeat_at


class ProcessMissingError(RuntimeError):
    pass
