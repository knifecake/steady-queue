==============
Configuration
==============

.. contents:: On this page
   :local:
   :depth: 2

TASKS setting
-------------

Steady Queue is configured as a Django task backend under the ``TASKS``
setting:

.. code-block:: python

    # settings.py
    TASKS = {
        "default": {
            "BACKEND": "steady_queue.backend.SteadyQueueBackend",
            "QUEUES": ["default"],
            "OPTIONS": {},
        }
    }

You can add multiple backends (e.g. for incremental adoption):

.. code-block:: python

    TASKS = {
        "default": {
            "BACKEND": "steady_queue.backend.SteadyQueueBackend",
            "QUEUES": ["default"],
        },
        "legacy": {
            "BACKEND": "...",
        },
    }


STEADY_QUEUE setting
--------------------

The ``STEADY_QUEUE`` setting configures the workers, dispatchers and scheduler
that run when you execute ``python manage.py steady_queue``. All options are
optional and will fall back to sensible defaults.

.. code-block:: python

    # settings.py
    from steady_queue.configuration import Configuration
    from datetime import timedelta

    STEADY_QUEUE = Configuration.Options(
        dispatchers=[
            Configuration.Dispatcher(
                polling_interval=timedelta(seconds=1),
                batch_size=500,
            )
        ],
        workers=[
            Configuration.Worker(
                queues=["default"],
                threads=3,
                polling_interval=timedelta(seconds=0.1),
            )
        ],
    )

Workers
~~~~~~~

Each ``Configuration.Worker`` entry spawns one or more processes that poll
queues and execute tasks.

- ``queues`` — list of queue names to process. Use ``"*"`` (or omit) to
  process all queues. Prefix wildcards are supported (e.g. ``"staging*"``).
  Queue names are checked in order: tasks in the first queue are processed
  before tasks in the second queue, regardless of priority.
- ``threads`` — size of the thread pool used to run tasks concurrently within
  a single worker process. Defaults to ``3``. Recommended to be ≤ the
  database connection pool size minus 2.
- ``processes`` — number of worker processes to fork with this configuration.
  Defaults to ``1``.
- ``polling_interval`` — time between polls when there are no tasks waiting.
  Defaults to ``0.1`` seconds.

Dispatchers
~~~~~~~~~~~

Each ``Configuration.Dispatcher`` entry spawns a process that moves scheduled
tasks to the ready queue and performs concurrency-control maintenance.

- ``polling_interval`` — time between dispatcher polls. Defaults to ``1``
  second.
- ``batch_size`` — number of scheduled tasks dispatched per cycle. Defaults
  to ``500``.
- ``concurrency_maintenance_interval`` — time between concurrency control
  maintenance runs. Defaults to ``600`` seconds.
- ``concurrency_maintenance`` — whether this dispatcher performs concurrency
  maintenance at all. Defaults to ``True``. Set to ``False`` if you run
  multiple dispatchers and want some dedicated to dispatching only.

Queue order and priorities
~~~~~~~~~~~~~~~~~~~~~~~~~~

Within a single queue, tasks are ordered by numeric priority (higher numbers
run first; default ``0``). Across multiple queues specified for a worker, the
order of the list takes precedence: a task in the first queue will always be
picked before a task in the second queue, even if the second has a higher
priority.

Avoid mixing queue order with task priorities — choose one or the other to
keep execution order predictable.

.. _database-configuration:

Database configuration
----------------------

By default, Steady Queue stores its tables in the ``default`` database. For
production we recommend using a dedicated database to avoid accidentally
relying on transactional integrity between your application data and your job
queue.

1. Add a ``queue`` entry to ``DATABASES``:

   .. code-block:: python

       DATABASES = {
           "default": {...},
           "queue": {
               "ENGINE": "django.db.backends.postgresql",
               "NAME": "queue",
               "USER": "queue",
               "PASSWORD": "queue",
               "HOST": "localhost",
               "PORT": 5432,
               "TEST": {"NAME": "test_queue"},
           },
       }

2. Point Steady Queue at that alias and register the database router:

   .. code-block:: python

       import steady_queue

       steady_queue.database = "queue"
       DATABASE_ROUTERS = ["steady_queue.db_router.SteadyQueueRouter"]

3. Run migrations against the dedicated database:

   .. code-block:: bash

       python manage.py migrate --database queue steady_queue

Module-level settings
---------------------

These settings are set directly on the ``steady_queue`` module, typically in
``settings.py``:

.. code-block:: python

    import steady_queue
    from datetime import timedelta

    steady_queue.database = "queue"
    steady_queue.process_heartbeat_interval = timedelta(minutes=2)

Available settings:

``steady_queue.database``
    The database alias used for all Steady Queue tables. Defaults to
    ``"default"``. See :ref:`database-configuration`.

``steady_queue.process_heartbeat_interval``
    How often supervised processes send a heartbeat. Defaults to 1 minute.

``steady_queue.process_alive_threshold``
    How long after the last heartbeat a process is considered dead. Defaults
    to 5 minutes.

``steady_queue.shutdown_timeout``
    How long the supervisor waits after sending ``TERM`` before sending
    ``QUIT`` to force-stop supervised processes. Defaults to 5 seconds.

``steady_queue.supervisor_pidfile``
    Path to a PID file created by the supervisor. Used to prevent multiple
    supervisors on the same host and as a health check target. Defaults to
    ``tmp/pids/steady_queue_supervisor.pid``.

``steady_queue.preserve_finished_jobs``
    Whether to keep finished jobs in the ``steady_queue_jobs`` table. Defaults
    to ``True``. When ``False``, completed jobs are deleted immediately.

``steady_queue.clear_finished_jobs_after``
    How long to retain finished jobs when ``preserve_finished_jobs`` is
    ``True``. Defaults to 1 day. Note: there is no automatic cleanup — call
    ``Job.objects.clear_finished_in_batches()`` periodically (e.g. as a
    recurring task).

``steady_queue.default_concurrency_control_period``
    Default value for the ``duration`` parameter in
    :ref:`concurrency controls <api-limits-concurrency>`. Defaults to 3
    minutes.

Signals
-------

Steady Queue emits the standard `django.tasks signals
<https://docs.djangoproject.com/en/stable/ref/tasks/#signals>`_:

- ``django.tasks.signals.task_enqueued`` — fired when a task is inserted into
  the database.
- ``django.tasks.signals.task_started`` — fired when a worker begins executing
  a task.
- ``django.tasks.signals.task_finished`` — fired when a task finishes
  (successfully or with an error).

All signals include ``sender`` (the ``SteadyQueueBackend`` instance) and
``task_result`` (a ``django.tasks.TaskResult``).

Logging
-------

Steady Queue logs to the ``steady_queue`` logger using the standard Python
``logging`` module. Add it to ``LOGGING`` in ``settings.py`` to control
verbosity:

.. code-block:: python

    LOGGING = {
        "loggers": {
            "steady_queue": {
                "handlers": ["console"],
                "level": "INFO",
            },
        },
        # ...
    }
