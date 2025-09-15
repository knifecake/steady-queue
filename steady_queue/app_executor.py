import logging
import threading
from contextlib import contextmanager

from django.db import connections

logger = logging.getLogger("steady_queue")


class AppExecutor:
    @staticmethod
    @contextmanager
    def wrap_in_app_executor():
        """
        Django equivalent of Rails' wrap_in_app_executor.
        Ensures proper database connection handling in background threads.
        """
        # Ensure we have a database connection for this thread
        connection = connections["default"]  # or your specific database alias

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
            # Django automatically manages connection lifecycle,
            # but we can explicitly close if needed for long-running processes
            if threading.current_thread() != threading.main_thread():
                # Only close connections in background threads
                # Main thread connections are handled by Django's request/response cycle
                connection.close()
