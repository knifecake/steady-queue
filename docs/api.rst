=============
API Reference
=============

Steady Queue's public API is intentionally small. Most of the interface comes
from Django's ``django.tasks`` module (see the `Django tasks documentation
<https://docs.djangoproject.com/en/stable/ref/tasks/>`_). Steady Queue adds
two decorators and a handful of module-level settings.

.. contents:: On this page
   :local:
   :depth: 2


.. _api-recurring:

@recurring
----------

.. autofunction:: steady_queue.recurring_task.recurring

The ``@recurring`` decorator registers a task to be enqueued automatically on
a cron schedule. It must be applied *outside* the ``@task()`` decorator:

.. code-block:: python

    from django.tasks import task
    from steady_queue.recurring_task import recurring

    @recurring(schedule="0 9 * * 1-5", key="weekly_report")
    @task()
    def weekly_report():
        ...

The same task can have multiple recurring schedules:

.. code-block:: python

    @recurring(schedule="0 9 * * *", args=("Alice",), key="greet_alice")
    @recurring(schedule="0 12 * * *", args=("Bob",), key="greet_bob")
    @task()
    def greet(name: str):
        print(f"Hello, {name}!")

Parameters:

``schedule``
    A crontab expression (anything understood by the `crontab
    <https://pypi.org/project/crontab/>`_ library). For example:

    - ``"* * * * *"`` — every minute
    - ``"0 9 * * 1-5"`` — 9am on weekdays
    - ``"@daily"`` — once a day at midnight

``key``
    A unique string identifier for this recurring configuration. Must be
    unique across all ``@recurring`` decorators in your codebase. Used to
    prevent duplicate runs when multiple schedulers are active.

``args``
    Positional arguments to pass to the task when it is enqueued. Defaults to
    no arguments.

``kwargs``
    Keyword arguments to pass to the task when it is enqueued.

``queue_name``
    The queue to enqueue the task on. If omitted, uses the queue from the
    ``@task()`` decorator or the default queue.

``priority``
    Numeric priority for the enqueued task. If omitted, uses the priority from
    the ``@task()`` decorator or ``0``.

``description``
    Optional human-readable description. Currently unused but stored for
    future tooling.


.. _api-limits-concurrency:

@limits_concurrency
-------------------

.. autofunction:: steady_queue.concurrency.limits_concurrency

The ``@limits_concurrency`` decorator restricts how many instances of a task
can run at the same time. It must be applied *outside* the ``@task()``
decorator:

.. code-block:: python

    from django.tasks import task
    from steady_queue.concurrency import limits_concurrency

    @limits_concurrency(key=lambda user_id: str(user_id), to=1)
    @task()
    def generate_report(user_id: int):
        ...

Parameters:

``key``
    **Required.** A string or a callable that accepts the same arguments as
    the task and returns a string. Tasks with the same key value are counted
    together for the concurrency limit.

``to``
    Maximum number of tasks with the same key that may run simultaneously.
    Defaults to ``1``.

``duration``
    How long the concurrency guarantee is held. If a task holds a concurrency
    slot for longer than this, the slot may be released by the dispatcher's
    maintenance pass. Defaults to
    ``steady_queue.default_concurrency_control_period`` (3 minutes).

``group``
    A string used to apply a shared concurrency limit across different task
    types. Tasks from different functions that share the same ``group`` and
    ``key`` value count against the same limit. Defaults to the task's module
    path.


Argument serialization
----------------------

Task functions accept almost any argument type as positional or keyword
arguments. Beyond the standard DEP 0014 serializable types, Steady Queue adds
support for:

- ``datetime`` and ``date`` objects
- ``timedelta`` objects
- Django model instances (serialized as content type + primary key)

If a model instance cannot be found in the database when the task is executed,
a ``steady_queue.arguments.DeserializationError`` is raised.


Backend limitations
-------------------

The ``SteadyQueueBackend`` does not support the following features defined by
the Django task backend interface:

- **Async enqueueing** — tasks cannot be enqueued from async code.
- **Result fetching** — ``task_result.return_value`` is not supported. Store
  results directly in your database or file storage if they need to be
  persisted.

These limitations are advertised via the
`Django task feature flags
<https://docs.djangoproject.com/en/stable/ref/tasks/#feature-flags>`_.
