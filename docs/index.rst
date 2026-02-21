============
Steady Queue
============

Steady Queue is a database-backed task backend for Django 6.0+. It is a port
to Python of the excellent `Solid Queue <https://github.com/rails/solid_queue>`_
backend for Ruby on Rails, and it is compatible with the
`django.tasks <https://docs.djangoproject.com/en/stable/ref/tasks/>`_ interface.

It lets you run background jobs using only your existing relational database.
By leveraging ``SELECT FOR UPDATE SKIP LOCKED``, Steady Queue provides a
high-performance, concurrency-safe queuing system without the operational
overhead of Redis or RabbitMQ.

Features
--------

- **Task enqueueing and processing.** Using the standard ``@task`` decorator
  introduced in `DEP 0014 <https://github.com/django/deps/blob/main/accepted/0014-background-workers.rst>`_,
  with support for queue selection, delayed tasks and numeric priorities.
- **No extra infrastructure.** Works with MySQL, PostgreSQL or SQLite.
- **Cron-style recurring tasks.** Define schedules directly in your code.
- **Concurrency controls.** Limit how many instances of a task run simultaneously.
- **Operational control.** Pause and resume queues, inspect and retry failed
  tasks via the Django admin.


.. toctree::
   :maxdepth: 2

   installation
   getting_started
   configuration
   api
   internals
   alternatives
