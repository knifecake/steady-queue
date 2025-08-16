import os
import secrets
import socket
from typing import Any


class Base:
    name: str
    stopped: bool = False
    pid: int

    def __init__(self):
        self.name = self.generate_name()
        self.stopped = False

    def boot(self):
        pass

    def shutdown(self):
        pass

    def stop(self):
        self.stopped = True

    @property
    def kind(self) -> str:
        return self.__class__.__name__.lower()

    @property
    def pid(self) -> int:
        return os.getpid()

    @property
    def hostname(self) -> str:
        return socket.gethostname()

    @property
    def metadata(self) -> dict[str, Any]:
        return {}

    @property
    def is_stopped(self) -> bool:
        return self.stopped

    def generate_name(self) -> str:
        return "-".join((self.kind, secrets.token_hex(10)))
