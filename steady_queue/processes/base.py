import logging
import os
import secrets
import socket
from typing import Any

from django.db import connections

logger = logging.getLogger("steady_queue")


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
        This method removes pool configuration from database settings and from
        already-instantiated Django connection wrappers.
        """
        from django.conf import settings

        if hasattr(settings, "DATABASES"):
            for alias, db_config in settings.DATABASES.items():
                if db_config.get("ENGINE") != "django.db.backends.postgresql":
                    continue

                options = db_config.setdefault("OPTIONS", {})
                if "pool" in options:
                    logger.info(
                        "%(name)s disabling connection pooling for database '%(alias)s'",
                        {"name": self.name, "alias": alias},
                    )
                    del options["pool"]

        for alias in connections:
            connection = connections[alias]
            if (
                connection.settings_dict.get("ENGINE")
                != "django.db.backends.postgresql"
            ):
                continue

            options = connection.settings_dict.setdefault("OPTIONS", {})
            if "pool" in options:
                logger.debug(
                    "%(name)s removing pool option from instantiated connection '%(alias)s'",
                    {"name": self.name, "alias": alias},
                )
                del options["pool"]

    def close_postgresql_connection_pools(self):
        """
        Close and clear Django's class-level psycopg pool cache.

        Django stores psycopg pools in DatabaseWrapper._connection_pools, so we
        must clear those references to avoid inheriting stale pools across fork.
        """
        closed_pool_maps: set[int] = set()

        for alias in connections:
            connection = connections[alias]
            if (
                connection.settings_dict.get("ENGINE")
                != "django.db.backends.postgresql"
            ):
                continue

            pool_map = getattr(connection.__class__, "_connection_pools", None)
            if not isinstance(pool_map, dict) or id(pool_map) in closed_pool_maps:
                continue

            for pool_alias, pool in list(pool_map.items()):
                try:
                    pool.close()
                    logger.debug(
                        "%(name)s closed psycopg pool for '%(alias)s'",
                        {"name": self.name, "alias": pool_alias},
                    )
                except Exception as e:
                    logger.debug(
                        "%(name)s failed to close pool for '%(alias)s': %(e)s",
                        {"name": self.name, "alias": pool_alias, "e": e},
                    )
                finally:
                    pool_map.pop(pool_alias, None)

            closed_pool_maps.add(id(pool_map))

    def reset_database_connections(self):
        """
        Reset database connections for forked processes.

        This disables connection pooling and resets connection state to prevent
        issues with shared connections between parent and child processes.
        """
        self.disable_connection_pooling()
        connections.close_all()
        self.close_postgresql_connection_pools()
