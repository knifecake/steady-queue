from __future__ import annotations

import steady_queue


def steady_queue_database_alias() -> str:
    """
    Resolve the database alias steady_queue should use.

    Returns the value of steady_queue.database (defaults to "default").
    """
    return steady_queue.database


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
