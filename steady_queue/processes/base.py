import os
import secrets
import socket
from typing import Any

from django.db import connections


class Base:
    name: str
    stopped: bool = False

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

    def disable_connection_pooling(self):
        """
        Disable connection pooling for steady_queue processes.

        Connection pooling with psycopg doesn't work with forked processes.
        This method removes pool configuration from database settings to prevent
        pool-related errors in steady_queue workers.
        """
        import logging

        from django.conf import settings

        logger = logging.getLogger("steady_queue")

        # Disable pooling in database configuration
        if hasattr(settings, "DATABASES"):
            for alias, db_config in settings.DATABASES.items():
                if db_config.get("ENGINE") == "django.db.backends.postgresql":
                    # Remove pool configuration if it exists
                    options = db_config.setdefault("OPTIONS", {})
                    if "pool" in options:
                        logger.info(
                            "PID %d disabling connection pooling for database '%s'",
                            os.getpid(),
                            alias,
                        )
                        del options["pool"]

        # Also disable on any existing connections
        for alias in connections:
            connection = connections[alias]
            if hasattr(connection, "pool") and connection.pool is not None:
                try:
                    connection.pool.close()
                    connection.pool = None
                    logger.debug(
                        "PID %d removed existing pool for '%s'", os.getpid(), alias
                    )
                except Exception as e:
                    logger.debug(
                        "PID %d failed to close existing pool for '%s': %s",
                        os.getpid(),
                        alias,
                        e,
                    )

    def reset_database_connections(self):
        """
        Reset database connections for forked processes.

        This disables connection pooling and resets connection state to prevent
        issues with shared connections between parent and child processes.
        """
        # First disable connection pooling for steady_queue processes
        self.disable_connection_pooling()

        # Close all existing connections
        connections.close_all()
