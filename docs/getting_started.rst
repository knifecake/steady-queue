===============
Getting Started
===============

Steady Queue implements the `django.tasks
<https://docs.djangoproject.com/en/stable/ref/tasks/>`_ interface (DEP 0014),
so most of what you need to know is already covered in the Django documentation.
This guide focuses on what's specific to Steady Queue and how to get up and
running quickly.

Defining tasks
--------------

Tasks are plain Python functions decorated with ``@task`` from ``django.tasks``:

.. code-block:: python

    from django.tasks import task

    @task()
    def send_welcome_email(user_id: int):
        user = User.objects.get(pk=user_id)
        # ... send the email

Enqueueing tasks
----------------

Call ``.enqueue()`` on the decorated function to run it in the background:

.. code-block:: python

    send_welcome_email.enqueue(user.pk)

You can customise how a task is enqueued using ``.using()``:

.. code-block:: python

    # Run with a higher priority
    send_welcome_email.using(priority=10).enqueue(user.pk)

    # Run on a specific queue
    send_welcome_email.using(queue_name="email").enqueue(user.pk)

    # Run after a delay
    from django.utils import timezone
    from datetime import timedelta

    send_welcome_email.using(run_after=timedelta(minutes=5)).enqueue(user.pk)

Task decorator options
----------------------

These options can be set on the ``@task`` decorator as defaults:

.. code-block:: python

    @task(priority=10, queue_name="email", backend="default")
    def send_welcome_email(user_id: int):
        ...

- ``priority`` — integer between -100 and 100; higher numbers run first.
  Defaults to ``0``.
- ``queue_name`` — the queue where this task will be enqueued. Defaults to
  ``"default"``.
- ``backend`` — the key in ``TASKS`` settings to use. Defaults to
  ``"default"``.

Enqueueing after a transaction commits
---------------------------------------

When you enqueue a task inside a database transaction, it's possible that the
task is picked up by a worker before the transaction commits, or that the
transaction rolls back after the task has been enqueued. To avoid this, use
Django's ``transaction.on_commit``:

.. code-block:: python

    from django.db import transaction
    from functools import partial

    def sign_up(request):
        user = User.objects.create(...)
        transaction.on_commit(partial(send_welcome_email.enqueue, user.pk))

Running the worker
------------------

Start Steady Queue with Django's management command:

.. code-block:: bash

    python manage.py steady_queue

This will start one dispatcher and one worker with the default configuration.
See :doc:`configuration` for how to customise the number of workers, queues,
and polling intervals.

Recurring tasks
---------------

Steady Queue can enqueue tasks on a schedule, like a cron job:

.. code-block:: python

    from django.tasks import task
    from steady_queue.recurring_task import recurring

    @recurring(schedule="0 9 * * *", key="daily_digest")
    @task()
    def send_daily_digest():
        # runs every day at 9am
        ...

See :ref:`api-recurring` for the full ``@recurring`` API.

Concurrency controls
--------------------

Prevent too many instances of a task from running at the same time:

.. code-block:: python

    from django.tasks import task
    from steady_queue.concurrency import limits_concurrency

    @limits_concurrency(key=lambda user_id: str(user_id), to=1)
    @task()
    def process_user_export(user_id: int):
        ...

See :ref:`api-limits-concurrency` for the full ``@limits_concurrency`` API.
