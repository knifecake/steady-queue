============
Installation
============

Requirements
------------

- Python 3.12+
- Django 6.0+
- A supported SQL database: MySQL 8+, PostgreSQL 9.5+, or SQLite

Steps
-----

1. **Install the package:**

   .. code-block:: bash

       pip install steady-queue

2. **Add the app** to ``INSTALLED_APPS`` in ``settings.py``:

   .. code-block:: python

       INSTALLED_APPS = [
           # ...
           "steady_queue",
       ]

3. **Configure a task backend** in ``settings.py``:

   .. code-block:: python

       TASKS = {
           "default": {
               "BACKEND": "steady_queue.backend.SteadyQueueBackend",
               "QUEUES": ["default"],
               "OPTIONS": {},
           }
       }

4. **Run migrations:**

   .. code-block:: bash

       python manage.py migrate

5. **Start the worker** on your server:

   .. code-block:: bash

       python manage.py steady_queue


That's it! Tasks decorated with ``@task()`` will now be processed by Steady
Queue.

For larger projects you may want to configure a dedicated database for Steady
Queue. See :ref:`database-configuration` in the configuration guide.
