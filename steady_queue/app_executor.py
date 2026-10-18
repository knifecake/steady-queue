import logging
import threading
from contextlib import contextmanager

from django.db import connections

from steady_queue.db_router import steady_queue_database_alias

logger = logging.getLogger("steady_queue")


class AppExecutor:
    @staticmethod
    @contextmanager
    def wrap_in_app_executor():
        """
        Django equivalent of Rails' wrap_in_app_executor.
        Ensures proper database connection handling in background threads.
        """
        # Ensure we have a database connection for this thread on the steady_queue DB
        alias = steady_queue_database_alias()
        connection = connections[alias]

        try:
            # Ensure connection is established
            connection.ensure_connection()

            # Clear any existing queries from connection (equivalent to Rails query cache reset)
            # if hasattr(connection, "queries_logged"):
            #     connection.queries_logged = 0
            #     connection.queries = []

            yield

        except Exception as e:
            # Handle any database-related errors
            # Close connection on error to prevent connection leaks
            logger.exception("error in AppExecutor: %(e)s", {"e": e})
            if connection.connection:
                connection.close()
            raise
        finally:
            if threading.current_thread() != threading.main_thread():
                # Worker threads are reused without Django's request cleanup.
                # Return connections for every initialized alias, including the
                # application databases used by the task, to their pools.
                connections.close_all()
