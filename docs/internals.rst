==================
Design & Internals
==================

This page describes how Steady Queue works internally. You don't need to
understand any of this to use it, but it may help when tuning performance,
debugging issues or contributing to the project.

Steady Queue is a port of `Solid Queue <https://github.com/rails/solid_queue>`_
from Ruby on Rails. The architecture maps closely to the original; the main
differences are in the external interface (Django's ``@task`` decorator instead
of ActiveJob classes) and the ORM (Django ORM instead of Active Record).

.. contents:: On this page
   :local:
   :depth: 2

Actors
------

When you run ``python manage.py steady_queue``, a **supervisor** process is
started. The supervisor forks and monitors the following types of child
processes:

**Workers**
    Workers poll the ``steady_queue_ready_executions`` table for tasks ready
    to run. Each worker maintains a thread pool (configurable via ``threads``)
    and fetches that many tasks at a time, posting them to threads for
    execution.

**Dispatchers**
    Dispatchers poll the ``steady_queue_scheduled_executions`` table for tasks
    whose scheduled run time has passed and moves them to
    ``steady_queue_ready_executions`` so workers can pick them up. Dispatchers
    also perform concurrency-control maintenance (releasing expired semaphores
    and unblocking waiting tasks).

**Scheduler**
    A single scheduler process manages recurring tasks. It reads the list of
    ``@recurring`` configurations registered in the codebase and enqueues them
    when their schedule is due.

The supervisor monitors child processes via heartbeats, restarts them if they
die unexpectedly, and coordinates graceful shutdown.

Database tables
---------------

``steady_queue_jobs``
    The primary record for each task invocation. Holds the task module path,
    serialized arguments, queue name, priority and status. Rows are kept after
    completion if ``preserve_finished_jobs`` is ``True``.

``steady_queue_ready_executions``
    Pointers to jobs that are ready to be picked up by a worker. Workers poll
    this table with ``SELECT FOR UPDATE SKIP LOCKED``.

``steady_queue_scheduled_executions``
    Pointers to jobs that should run in the future. Dispatchers move rows from
    here to ``steady_queue_ready_executions`` when the ``scheduled_at`` time
    is reached.

``steady_queue_blocked_executions``
    Jobs that are waiting for a concurrency semaphore. Dispatchers unblock them
    during maintenance runs.

``steady_queue_semaphores``
    Tracks active concurrency limits. Each row corresponds to one open
    concurrency slot.

``steady_queue_recurringexecution``
    Records of scheduled recurring task runs. A unique index on
    ``(task_key, run_at)`` prevents duplicate enqueues when multiple
    schedulers run concurrently.

``steady_queue_processes``
    Heartbeat records for all supervised processes. The supervisor prunes
    processes with expired heartbeats and marks their in-flight tasks as
    failed.

``steady_queue_pauses``
    Records of paused queues. Workers check this table to skip paused queues.

Polling strategy
----------------

To keep polling efficient, Steady Queue issues only two forms of polling
query:

.. code-block:: sql

    -- All queues (used when queues=['*'] and nothing is paused)
    SELECT job_id
    FROM steady_queue_ready_executions
    ORDER BY priority DESC, job_id ASC
    LIMIT ?
    FOR UPDATE SKIP LOCKED;

    -- Single queue (used for exact queue names)
    SELECT job_id
    FROM steady_queue_ready_executions
    WHERE queue_name = ?
    ORDER BY priority DESC, job_id ASC
    LIMIT ?
    FOR UPDATE SKIP LOCKED;

Both queries use a covering index on ``(queue_name, priority, job_id)`` and
avoid full table scans. When wildcards or paused queues are involved, an
additional ``DISTINCT`` query is required to enumerate matching queue names —
this is fast on MySQL (Loose Index Scan) but may be slower on PostgreSQL or
SQLite with large tables.

For optimal polling performance, specify exact queue names and avoid pausing
queues.

``FOR UPDATE SKIP LOCKED``
--------------------------

The key to Steady Queue's concurrency safety is the ``FOR UPDATE SKIP LOCKED``
SQL clause, available in MySQL 8+, PostgreSQL 9.5+ and SQLite 3.25+. This
allows multiple worker threads or processes to poll the same table
simultaneously without blocking each other: each worker locks the rows it is
about to process, and other workers transparently skip those rows.

On databases that don't support ``SKIP LOCKED``, workers may block waiting for
row locks from other workers. The system remains correct but throughput will be
lower.

Concurrency controls
--------------------

The ``@limits_concurrency`` decorator uses a semaphore table to enforce
concurrency limits. The flow is:

1. **Enqueue time:** Steady Queue computes the concurrency key and checks the
   semaphore table. If the semaphore count is below the limit, the count is
   incremented and the task is inserted as ``ready``. If the limit is reached,
   the task is inserted as ``blocked``.

2. **After task completion:** the semaphore count is decremented and the next
   blocked task with the same key (highest priority first) is moved to
   ``ready``.

3. **Dispatcher maintenance:** If a semaphore is held for longer than
   ``duration`` (e.g. the worker holding it was killed), the dispatcher's
   maintenance pass releases it and unblocks the next waiting task. The
   ``concurrency_maintenance_interval`` on the dispatcher controls how often
   this check runs.

Process lifecycle and signals
-----------------------------

The supervisor handles the following signals:

``TERM``, ``INT``
    Graceful shutdown. The supervisor forwards ``TERM`` to all child processes
    and waits up to ``shutdown_timeout`` for them to finish. Any processes
    still running after the timeout receive ``QUIT``.

``QUIT``
    Immediate shutdown. Child processes exit immediately. In-flight tasks are
    returned to the queue when processes deregister.

If a process exits unexpectedly (e.g. via ``SIGKILL``) its in-flight tasks
are marked as failed with a ``ProcessExitError`` exception. If the supervisor
detects a process with an expired heartbeat, it prunes the process record and
marks those tasks as failed with a ``ProcessPrunedError``.

Argument serialization
----------------------

Steady Queue extends the serialization format defined by DEP 0014 to support
additional Python types:

- ``datetime`` / ``date`` — serialized as ISO 8601 strings.
- ``timedelta`` — serialized as total seconds.
- Django model instances — serialized as ``{"content_type": ..., "pk": ...}``.
  At execution time, the model is re-fetched from the database. If the row no
  longer exists, ``DeserializationError`` is raised.

Transactional integrity
-----------------------

When Steady Queue shares a database with your application, enqueueing a task
inside a transaction makes the task visible to workers only after the
transaction commits. This can be useful (the task is guaranteed to see
consistent data) but also surprising if you're not aware of it.

When Steady Queue uses a separate database, this transactional coupling is
absent. To safely enqueue tasks after a transaction commits regardless of
database configuration, use Django's ``transaction.on_commit``:

.. code-block:: python

    from django.db import transaction
    from functools import partial

    def create_user(data):
        user = User.objects.create(**data)
        transaction.on_commit(partial(send_welcome_email.enqueue, user.pk))
