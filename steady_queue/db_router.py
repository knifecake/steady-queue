from __future__ import annotations

from django.conf import settings

from steady_queue.configuration import Configuration


def steady_queue_database_alias() -> str:
    """
    Resolve the database alias steady_queue should use.

    Priority:
    1. settings.STEADY_QUEUE when it is a Configuration.Options instance or has a
       ``database`` attribute
    2. Fallback to "default"
    """
    configured = getattr(settings, "STEADY_QUEUE", None)
    if isinstance(configured, Configuration.Options):
        return configured.database

    database_attr = getattr(configured, "database", None)
    if database_attr:
        return database_attr

    return "default"


class SteadyQueueRouter:
    """
    Route steady_queue models and migrations to a dedicated database alias.
    """

    app_label = "steady_queue"

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.app_label:
            return steady_queue_database_alias()
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.app_label:
            return steady_queue_database_alias()
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (
            obj1._meta.app_label == self.app_label
            or obj2._meta.app_label == self.app_label
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        alias = steady_queue_database_alias()
        if app_label == self.app_label:
            return db == alias

        # Prevent other apps from migrating into the steady_queue database.
        if db == alias:
            return False

        return None
