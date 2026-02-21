============
Alternatives
============

.. contents:: On this page
   :local:
   :depth: 2

vs django-tasks
---------------

`django-tasks <https://github.com/RealOrangeOne/django-tasks>`_ is the
third-party package that defined the ``django.tasks`` interface (DEP 0014) and
served as its reference implementation. It ships a ``DatabaseBackend`` that
stores and executes tasks using your application's database.

The ``django-tasks`` ``DatabaseBackend`` is intentionally minimal. Steady
Queue is also a database-backed implementation of the same interface, but adds:

- **Cron-style recurring tasks** via the ``@recurring`` decorator.
- **Concurrency controls** via ``@limits_concurrency``.
- **Operational visibility**: inspect, retry and discard failed tasks from the
  Django admin.
- **Queue pausing**: pause and resume individual queues from the admin.
- **Horizontal scaling**: run multiple worker or dispatcher processes across
  machines.
- **Configurable process topology**: control the number of workers, threads per
  worker, polling intervals and which queues each worker handles.
- **Heartbeat-based liveness checks** with automatic task recovery when a
  worker process dies.

If you just need simple background task execution and none of the above
features matter to you, ``django-tasks`` is a fine choice. Steady Queue is
the better fit when you need more operational control or advanced features.

Because both implement the same ``django.tasks`` interface, you can switch
between them by changing a single line in ``settings.py``.

vs Celery
---------

Celery is the most widely used task queue library in the Python ecosystem. It
is mature, has a huge community and supports a wide range of brokers (Redis,
RabbitMQ, Amazon SQS, etc.).

The main trade-off is operational complexity: Celery requires a separate broker
process (typically Redis or RabbitMQ) that must be deployed, monitored and
maintained. Steady Queue uses your existing database, so there's nothing new to
operate.

Celery also has its own task definition interface (``@app.task`` / ``@shared_task``),
whereas Steady Queue follows the standard ``django.tasks`` interface (DEP 0014),
which keeps your task code portable across compliant backends.

Consider Celery if you need features like task routing to heterogeneous worker
pools, support for non-relational brokers, or the rich ecosystem of
third-party Celery extensions. Consider Steady Queue if you'd rather not
introduce a broker dependency and your workloads fit comfortably within a
relational database.

vs django-rq
------------

`django-rq <https://github.com/rq/django-rq>`_ integrates the `RQ
<https://python-rq.org/>`_ task queue (which uses Redis as a broker) with
Django. Like Celery, it requires Redis to be running. It is simpler than
Celery and easier to set up, but still adds operational overhead compared to a
pure database solution.

vs Solid Queue
--------------

`Solid Queue <https://github.com/rails/solid_queue>`_ is the Ruby on Rails
library that Steady Queue is ported from. If you're coming from a Rails
background, the concepts and configuration will look familiar. The main
differences in the external interface are:

- **Task definition.** Solid Queue works with Active Job classes; Steady Queue
  uses the ``@task`` decorator from DEP 0014.
- **Priority ordering.** Steady Queue follows Django's convention where *larger*
  numbers mean *higher* priority (e.g. priority 10 runs before priority 0).
  Solid Queue uses the inverse.
- **Recurring tasks.** Solid Queue supports command-based recurring tasks
  (arbitrary shell commands on a schedule). Steady Queue only supports
  recurring Python task functions.
- **Instrumentation.** Solid Queue emits rich ``ActiveSupport::Notifications``
  events. Steady Queue uses standard Python logging and the ``django.tasks``
  signals instead.
