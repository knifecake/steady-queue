# Robust Queue

Robust Queue is a port to Django of the excellent [Solid
Queue][solid-queue-github] DB-based queueing backend for Ruby on Rails. The goal
of this port has been to keep the internals as close as possible to a direct
translation from Ruby to Python, while adapting the external interfaces to be
idiomatic in Django and Python. Read more on the differences between Robust
Queue and Solid Queue below.

Robust queue exposes a task backend that is compatible with the background worker specification outlined in [DEP 0014][DEP0014]. In addition to task enqueueing and processing, it supports delayed tasks, concurrency controls, recurring tasks, pausing queues, numeric priorities per task, priorities by queue order and bulk enqueueing.

Robust Queue can be used with SQL databases such as MySQL, PostgreSQL or SQLite, and it leverages the `FOR UPDATE SKIP LOCKED` clause, if available, to avoid blocking and waiting on locks when polling tasks.

## Installation

1. **Install the `robust_queue` package.** Since Robust Queue depends on interfaces defined by DEP 0014 which has not become part of Django yet, it will add django-tasks (the reference implementation) as a dependency.
2. **Add `robust_queue` and `django_tasks` to your `INSTALLED_APPS`** in `settings.py`.
3. **Configure Robust Queue as a task backend.** In `settings.py`, add the Robust Queue backend:
   ```python
   TASKS = {
       "default": {
           "BACKEND": "robust_queue.backend.RobustQueueBackend",
           "QUEUES": ["default"],
           "OPTIONS": {},
       }
   }
   ```
4. **Migrate your database** with `python3 manage.py migrate`.


Now you're ready to start processing tasks by running `python manage.py robust_queue` on the server that's doing the work. This will start processing tasks in all queues using the default configuration. See below to learn more about configuring Robust Queue.

For small projects, you can run Robust Queue on the same machine as your webserver. When you're ready to scale, Robust Queue supports horizontal scaling out-of-the-box. You can run Robust Queue on a separate server from your webserver, or even run `python manage.py robust_queue` on multiple machines at the same time. Depending on the configuration, you can designate some machines to run only dispatchers or only workers. See the configuration section for more details on this.

## Usage

Robust Queue works like any other DEP 0014-compatible task backend.

Tasks are functions decorated with the `@task` decorator from `django_tasks`
(which will become `django.tasks` once integrated into Django):

```python
from django_tasks import task

@task()
def greet(name: str, times: int = 1):
    for _ in range(times):
        print(f"Hello, {name}")
```

To enqueue the task, call the `.enqueue()` method on it passing any arguments:

```python
greet.enqueue('World', 4)
```

### Configuring how tasks are run

The task decorator accepts these arguments to customize the task:

```python
@task(priority=10, queue_name='real_time', backend='robust_queue')
def tralalero():
    print('tralala')
```

- `priority` is a non-negative integer determining the importance of tasks within the same queue. The smaller the value, the higher the priority. The default value is `0`.
- `queue_name` is the name of the queue where instances of this task will run.
  If not specified, it defaults to the `default` queue.
- `backend` is the key of the backend that will be used in the `TASKS` configuration in `settings.py`. If not specified, the `default` backend is selected.

These attributes can also be modified at runtime with `.using()`:

```python
tralalero.using(priority=9, queue_name='low_importance').enqueue()
```

### Running tasks in the future

Robust Queue supports enqueueing tasks to be run at a later time via the
`run_after` parameter to `.using()`:

```python
greet.using(run_after=timezone.datetime(2030, 01, 01)).enqueue('World')
```

You can also pass a timedelta to be applied to the current time:

```python
greet.using(run_after=timezone.timedelta(minutes=1)).enqueue('hello')
```

### Argument serialization

Task functions can take almost any argument as either positional or keyword
arguments. Robust Queue improves on the serialization specified by DEP 0014 by
supporting timestamps, timedeltas and Django models. Django models are
serialized by storing the content type and object ID. If the model does not
exist on the database when the task is executed, a
`robust_queue.arguments.DeserializationError` is raised.

### Incremental adoption

If you're planning to adopt Robust Queue incrementally by switching one task at
a time, you can do so by setting the `backend` attribute on the `@task()`
decorator.

### High performance requirements

Robust Queue was designed for the highest throughput when used with MySQL 8+ or PostgreSQL 9.5+, as they support `FOR UPDATE SKIP LOCKED`. You can use it with older versions, but in that case, you might run into lock waits if you run multiple workers for the same queue. You can also use it with SQLite on smaller applications.

## Configuration

### Workers, dispatchers and scheduler

We have several types of actors in Robust Queue:

- _Workers_ are in charge of picking tasks ready to run from queues and processing them. They work off the `robust_queue_ready_executions` table.
- _Dispatchers_ are in charge of selecting tasks scheduled to run in the future that are due and _dispatching_ them, which is simply moving them from the `robust_queue_scheduled_executions` table over to the `robust_queue_ready_executions` table so that workers can pick them up. On top of that, they do some maintenance work related to [concurrency controls](#concurrency-controls).
- The _scheduler_ manages [recurring tasks](#recurring-tasks), enqueuing tasks for them when they're due.
- The _supervisor_ runs workers and dispatchers according to the configuration, controls their heartbeats, and stops and starts them when needed.

Robust Queue's supervisor will fork a separate process for each supervised worker/dispatcher/scheduler.

Robust Queue will try to find our configuration under the `ROBUST_QUEUE` variable in `settings.py`. Everything is optional. If no configuration is provided, Robust Queue will run with one dispatcher and one worker per the default settings:

```python
# settings.py
from robust_queue.configuration import Configuration
from datetime import timedelta

ROBUST_QUEUE = Configuration.ConfigurationOptions(
    dispatchers=[
        Configuration.DispatcherConfiguration(
            polling_interval=timedelta(seconds=1),
            batch_size=500
        )
    ],
    workers=[
        Configuration.WorkerConfiguration(
            queues=["*"],
            threads=3,
            polling_interval=timedelta(seconds=0.1)
        )
    ]
)
```

Everything is optional. If no configuration is provided at all, or no configuration is given for workers or dispatchers, Robust Queue will run with the defaults above.

Here's an overview of the different options:

- `polling_interval`: the time interval in seconds that workers and dispatchers will wait before checking for more tasks. This time defaults to `1` second for dispatchers and `0.1` seconds for workers.

- `batch_size`: the dispatcher will dispatch tasks in batches of this size. The default is 500.

- `concurrency_maintenance_interval`: the time interval in seconds that the
  dispatcher will wait before checking for blocked jobs that can be unblocked.
  Read more about [concurrency controls](#concurrency-controls) to learn more
  about this setting. It defaults to `600` seconds.

- `queues`: the list of queues that workers will pick tasks from. You can use
  `*` to indicate all queues (which is also the default and the behavior you'll
  get if you omit this). Tasks will be polled from those queues in order, so for
  example, with `['real_time', 'background']`, no jobs will be taken from
  `background` unless there aren't any more jobs waiting in `real_time`.

  You can also provide a prefix with a wildcard to match queues starting with a
  prefix. For example adding `staging*` to the queues list will create a worker
  fetching jobs from all queues starting with `staging`. The wildcard `*` is
  only allowed on it's own or at the end of a queue name; you can't specify
  queue names such as `*_some_queue`. These will be ignored.

  Finally you can combine prefixes with exact names, like `['staging*',
  'background']`, and the behavior with respect to order will be the same as
  with only exact names.

  Check the sections below on [how queue order behaves combined with priorities](#queue-order-and-priorities), and [how the way you specify the queues per worker might affect performance](#queues-specification-and-performance).

- `threads`: this is the max size of the thread pool that each worker will have
  to run tasks. Each worker will fetch this number of tasks from their queue(s),
  at most and will post them to the thread pool to be run. By default, this is
  `3`. Only workers have this setting.

  It is recommended to set this value less than or equal to the queue database's
  connection pool size minus 2, as each worker thread uses one connection, and
  two additional connections are reserved for polling and heartbeat.

- `processes`: this is the number of worker processes that will be forked by the
  supervisor with the settings given. By default, this is `1`, just a single
  process. This setting is useful if you want to dedicate more than one CPU core
  to a queue or queues with the same configuration. Only workers have this
  setting.

- `concurrency_maintenance`: whether the dispatcher will perform the concurrency
  maintenance work. This is `true` by default, and it's useful if you don't use
  any [concurrency controls](#concurrency-controls) and want to disable it or if
  you run multiple dispatchers and want some of them to just dispatch tasks
  without doing anything else.

### Queue order and priorities

As mentioned above, if you specify a list of queues for a worker, these will be
polled in the order given, such as for the list `'real_time', 'background'`, no
tasks will be taken from `background` unless there aren't any more tasks waiting
in `real_time`.

Robust Queue also supports positive integer priorities when enqueuing tasks. In
Robust Queue, the smaller the value, the higher the priority. The default is
`0`.

This is useful when you run tasks with different importance or urgency in the
same queue. Within the same queue, tasks will be picked in order of priority, but
in a list of queues, the queue order takes precedence, so in the previous
example with `real_time,background`, tasks in the `real_time` queue will be
picked before tasks in the `background` queue, even if those in the `background`
queue have a higher priority (smaller value) set.

We recommend not mixing queue order with priorities but either choosing one or
the other, as that will make task execution order more straightforward for you.

### Queues specification and performance

To keep polling performant and ensure a covering index is always used, Robust
Queue only does two types of polling queries:

```sql
-- No filtering by queue
SELECT job_id
FROM robust_queue_ready_executions
ORDER BY priority ASC, job_id ASC
LIMIT ?
FOR UPDATE SKIP LOCKED;

-- Filtering by a single queue
SELECT job_id
FROM robust_queue_ready_executions
WHERE queue_name = ?
ORDER BY priority ASC, job_id ASC
LIMIT ?
FOR UPDATE SKIP LOCKED;
```

The first one (no filtering by queue) is used when you specify

```python
queues=['*']
```
and there aren't any queues paused, as we want to target all queues.

In other cases, we need to have a list of queues to filter by, in order, because
we can only filter by a single queue at a time to ensure we use an index to
sort. This means that if you specify your queues as:

```python
queues=['beta*']
```

we'll need to get a list of all existing queues matching that prefix first, with a query that would look like this:

```sql
SELECT DISTINCT(queue_name)
FROM robust_queue_ready_execution
WHERE queue_name LIKE 'beta%';
```

This type of `DISTINCT` query on a column that's the leftmost column in an index
can be performed very fast in MySQL thanks to a technique called [Loose Index
Scan](https://dev.mysql.com/doc/refman/8.0/en/group-by-optimization.html#loose-index-scan).

PostgreSQL and SQLite, however, don't implement this technique, which means that
if your `robust_queue_ready_executions` table is very big because your queues
get very deep, this query will get slow. Normally your
`robust_queue_ready_executions` table will be small, but it can happen.

Similarly to using prefixes, the same will happen if you have paused queues,
because we need to get a list of all queues with a query like

```sql
SELECT DISTINCT(queue_name)
FROM solid_queue_ready_execution
```

and then remove the paused ones. Pausing in general should be something rare,
used in special circumstances, and for a short period of time. If you don't want
to process tasks from a queue anymore, the best way to do that is to remove it
from your list of queues.

💡 To sum up, **if you want to ensure optimal performance on polling**, the best
way to do that is to always specify exact names for them, and not have any
queues paused.

Do this:

```python
queues=['background', 'backend']
```

instead of this:

```python
queues=['back*']
```

### Threads, processes and signals

Workers in Robust Queue use a thread pool to run work in multiple threads,
configurable via the `threads` parameter above. Besides this, parallelism can be
achieved via multiple processes on one machine (configurable via different
workers or the `processes` parameter above) or by horizontal scaling.

The supervisor is in charge of managing these processes, and it responds to the
following signals:

- `TERM`, `INT`: starts graceful termination. The supervisor will send a `TERM`
  signal to its supervised processes, and it'll wait up to
  `robust_queue.shutdown_timeout` time until they're done. If any supervised
  processes are still around by then, it'll send a `QUIT` signal to them to
  indicate they must exit.
- `QUIT`: starts immediate termination. The supervisor will send a `QUIT` signal
  to its supervised processes, causing them to exit immediately.

When receiving a `QUIT` signal, if workers still have tasks in-flight, these
will be returned to the queue when the processes are deregistered.

If processes have no chance of cleaning up before exiting (e.g. if someone pulls
a cable somewhere), in-flight tasks might remain claimed by the processes
executing them. Processes send heartbeats, and the supervisor checks and prunes
processes with expired heartbeats. Tasks that were claimed by processes with an
expired heartbeat will be marked as failed with a
`robust_queue.processes.ProcessPrunedError` exception. You can configure both
the frequency of heartbeats and the threshold to consider a process dead. See
the section below for this.

In a similar way, if a worker is terminated in any other way not initiated by
the above signals (e.g. a worker is sent a `KILL` signal), tasks in progress
will be marked as failed so that they can be inspected, with a
`robust_queue.processes.ProcessExitError` exception. Sometimes a task in
particular is responsible for this, for example, if it has a memory leak and you
have a mechanism to kill processes over a certain memory threshold, so this will
help identifying this kind of situation.

### Database configuration

TODO

### Other configuration settings

*Note*: The settings in this section should be set directly on the `robust_queue` module. You can do this on `settings.py` as well:

```python
import robust_queue

robust_queue.process_heartbeat_interval = timedelta(minutes=5)
```

There are several settings that control how RObust Queue works that you can set as well:

- `process_heartbeat_interval`:  the heartbeat interval that all processes will
  follow—defaults to 60 seconds.
- `process_alive_threshold`: how long to wait until a process is considered dead
  after its last heartbeat—defaults to 5 minutes.
- `shutdown_timeout`: time the supervisor will wait since it sent the `TERM`
  signal to its supervised processes before sending a `QUIT` version to them
  requesting immediate termination—defaults to 5 seconds.
- `supervisor_pidfile`: path to a pidfile that the supervisor will create when
  booting to prevent running more than one supervisor in the same host, or in
  case you want to use it for a health check. It's set to
  `tmp/pids/robust_queue_supervisor.pid` by default.
- `preserve_finished_jobs`: whether to keep finished jobs in the
  `robust_queue_jobs` table—defaults to `True`.
- `clear_finished_jobs_after`: period to keep finished jobs around, in case
  `preserve_finished_jobs` is true—defaults to 1 day. **Note:** Right now,
  there's no automatic cleanup of finished jobs. You'd need to do this by
  periodically invoking `Job.objects.clear_finished_in_batches()`, which can be
  configured as [a recurring task](#recurring-tasks).
- `default_concurrency_control_period`: the value to be used as the default for
  the `duration` parameter in [concurrency controls](#concurrency-controls). It
  defaults to 3 minutes.

## Lifecycle hooks

TODO

## Errors when enqueueing

TODO

## Concurrency controls

TODO

## Failed jobs and retries

TODO

### Error reporting on tasks

TODO

# Logging

TODO

## Tasks and transactional integrity

:warning: Having your tasks in the same ACID-compliant database as your
application data enables a powerful yet sharp tool: taking advantage of
transactional integrity to ensure some action in your app is not committed
unless your task is also committed and vice versa, and ensuring that your task
won't be enqueued until the transaction within which you're enqueuing it is
committed. This can be very powerful and useful, but it can also backfire if you
base some of your logic on this behavior, and in the future, you move to another
active task backend, or if you simply move Robust Queue to its own database, and
suddenly the behavior changes under you. Because this can be quite tricky and
many people shouldn't need to worry about it, by default Robust Queue is
configured in a different database as the main app.

By default, the `@task` decorator sets the `enqueue_on_commit` flag to `True`,
deferring the enqueueing of the task inside a database transaction until that
transaction successfully commits. You can set this option via the
`enqueue_on_commit` parameter to the `@task` decorator or to the `.using()`
method of a task:

```python
# Sets the default enqueueing behavior for all task instances
@task(enqueue_on_commit=False)
def my_task():
    pass

# Enables enqueue_on_commit for a specific instance of the task
my_task.using(enqueue_on_commit=True).enqueue()
```

Using this option, you can also use Robust Queue in the same database as your app but not rely on transactional integrity.

## Recurring tasks

Robust Queue supports defining recurring tasks that run at specific times in the
future, on a regular basis like cron jobs. These are managed by the scheduler
process and are defined using the `@recurring` decorator:

```python
from robust_queue import recurring

@recurring(schedule="0 12 * * *", key="rot the brains at noon")
@task()
def ballerina():
    print('capuccina')
```

- The `schedule` parameter is a crontab string. Anything that is understood by
  the [crontab][contrab] library can be passed in here.
- The `key` parameter must be a unique identifier for this recurring
  configuration.
- Recurring tasks can also take arguments which can be configured together with
  the schedule via the `args` and `kwargs` parameters to `recurring`:

```python
@recurring(
    schedule="0 12 * * *",
    args=(10, 5),
    kwargs={'name': 'Sahur'},
    key="rot the brains at noon"
)
@task()
def countdown_greeting(from, to, name='Michael'):
    for i in range(from, to):
        print(i)

    print(f"Hello, {name}!")
```

This allows for running the same task on different schedules with different arguments:

```python
@recurring(schedule='0 10 * * *', args=('Alice',), key='greet_alice')
@recurring(schedule='0 12 * * *', args=('Bob',), key='greet_bob')
@task()
def greet(name):
    print(f"Hello, {name}!")
```

- `queue_name` allows specifying a different queue to be used when enqueueing the task. Otherwise, the queue passed to `@task()` or the default queue is used.
- `priority` is a numeric priority value used when enqueueing the task. If no
  priority is set on the recurring schedule, the priority passed to `@task()` or
  `0` is used instead.

Tasks are enqueued at their corresponding times by the scheduler, and each task schedules the next one.

It is possible to run multiple schedulers, for example, if you have multiple
servers for redundancy and your run the `scheduler` in more than one of them. To
avoid enqueueing duplicate tasks at the same time, an entry in the
`robust_queue_recurringexecution` table is added in the same transaction as the
job is enqueued. This table has a unique index on `task_key` and `run_at`,
ensuring only one entry per task per time will be created. This only works if
you have `preserve_finished_tasks` set to `True` (the default), and the
guarantee applies as long as you keep tasks around.


## Deviations from Solid Queue

The implementation of the task backend is largely a direct translation from Ruby on Rails to Django. Code organization in classes and mixins, method names, database field names and naming conventions are mostly untouched, but there are a few differences which we outline below.

- The ORM is of course changed from Active Record to the Django ORM.
  - Class methods in Rails models generally become model manager methods under Django. Similarly, Active Record scopes are translated as queryset methods.
- ActiveJobs (the interface for background tasks in Ruby on Rails) are called
  tasks.
  - Since Robust Queue follows [DEP 0014][DEP0014] for its public API, tasks are
    decorated functions instead of classes.
  - Some features of ActiveJob, like dynamically setting queue names,
    priorities, concurrency keys, retry policies or exceptions to be caught are
    not available in SolidQueue due to the nature of the decorator-based
    approach to tasks. Users are encouraged to write their own decorators or
    otherwise make use of the `.using()` method of classes to configure these
    parameters dynamically where needed.
- Robust Queue provides dashboards that integrate with the Django admin site and
  are roughly equivalent to [mission_control-jobs][mission_control-jobs], but
  without requiring an external dependency.
- Command-based recurring tasks (ie, those defined by passing code directly to
  the task schedule) are not supported in Robust Queue. Considering the ease
  with which a function can be scheduled as a periodic task, it is unlikely this
  will ever be supported, but we've kept the database column for compatibility.
- Robust Queue worker processes do not set the process name (or procline)
  because doing so requires introducing an external dependency.
- Robust Queue does not expose rich instrumentation like Solid Queue does due to
  the lack of a framework-native equivalent to `ActiveSupport::Notifications`.


## License

The package is available as open source under the terms of the [MIT License][MIT].


[solid-queue-github]: https://github.com/rails/solid_queue
[DEP0014]: https://github.com/django/deps/blob/main/accepted/0014-background-workers.rst#specification
[mission_control-jobs]: https://github.com/rails/mission_control-jobs
[MIT]: https://opensource.org/licenses/MIT
