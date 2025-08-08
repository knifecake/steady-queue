from django.utils import timezone


class ProcessPrunedError(RuntimeError):
    def __init__(self, last_heartbeat_at: timezone.datetime = None):
        self.last_heartbeat_at = last_heartbeat_at


class ProcessMissingError(RuntimeError):
    pass
