from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from steady_queue.configuration import Configuration


class DefaultConfigurationTestCase(SimpleTestCase):
    """Tests for default configuration values."""

    def test_default_configuration_includes_all_queues(self):
        """Default worker configuration includes wildcard '*' for all queues."""
        config = Configuration()

        self.assertEqual(len(config.options.workers), 1)
        self.assertEqual(config.options.workers[0].queues, ["*"])

    def test_default_configuration_has_single_worker_process(self):
        """Default configuration includes one worker process."""
        config = Configuration()

        workers = config.workers
        self.assertEqual(len(workers), 1)
        self.assertEqual(workers[0].kind, "worker")

    def test_default_configuration_has_single_dispatcher(self):
        """Default configuration includes one dispatcher process."""
        config = Configuration()

        dispatchers = config.dispatchers
        self.assertEqual(len(dispatchers), 1)
        self.assertEqual(dispatchers[0].kind, "dispatcher")

    def test_default_configuration_has_single_scheduler(self):
        """Default configuration includes one scheduler process."""
        config = Configuration()

        schedulers = config.schedulers
        self.assertEqual(len(schedulers), 1)
        self.assertEqual(schedulers[0].kind, "scheduler")

    def test_default_worker_has_three_threads(self):
        """Default worker configuration has 3 threads."""
        config = Configuration()

        self.assertEqual(config.options.workers[0].threads, 3)

    def test_default_worker_polling_interval(self):
        """Default worker polling interval is 0.1 seconds."""
        config = Configuration()

        self.assertEqual(
            config.options.workers[0].polling_interval, timedelta(seconds=0.1)
        )

    def test_default_dispatcher_polling_interval(self):
        """Default dispatcher polling interval is 1 second."""
        config = Configuration()

        self.assertEqual(
            config.options.dispatchers[0].polling_interval, timedelta(seconds=1)
        )

    def test_default_dispatcher_batch_size(self):
        """Default dispatcher batch size is 500."""
        config = Configuration()

        self.assertEqual(config.options.dispatchers[0].batch_size, 500)


class ConfigurationProcessesTestCase(SimpleTestCase):
    """Tests for configuration process management."""

    def test_multiple_worker_processes_multiplied_correctly(self):
        """Worker processes configuration respects process count."""
        options = Configuration.Options(workers=[Configuration.Worker(processes=3)])
        config = Configuration(options)

        workers = config.workers
        self.assertEqual(len(workers), 3)

    def test_configured_processes_includes_all_by_default(self):
        """configured_processes includes workers, dispatchers, and schedulers."""
        config = Configuration()

        processes = config.configured_processes
        self.assertGreater(len(processes), 0)

        # Should have at least one of each
        kinds = [p.kind for p in processes]
        self.assertIn("worker", kinds)
        self.assertIn("dispatcher", kinds)
        self.assertIn("scheduler", kinds)

    def test_only_work_option_excludes_dispatchers_and_schedulers(self):
        """only_work option limits to worker processes only."""
        options = Configuration.Options(
            workers=[Configuration.Worker()], only_work=True
        )
        config = Configuration(options)

        processes = config.configured_processes
        kinds = [p.kind for p in processes]

        self.assertIn("worker", kinds)
        self.assertNotIn("dispatcher", kinds)
        self.assertNotIn("scheduler", kinds)

    def test_multiple_dispatchers_configuration(self):
        """Multiple dispatcher configurations are supported."""
        options = Configuration.Options(
            dispatchers=[
                Configuration.Dispatcher(),
                Configuration.Dispatcher(batch_size=1000),
            ]
        )
        config = Configuration(options)

        dispatchers = config.dispatchers
        self.assertEqual(len(dispatchers), 2)

    def test_worker_with_specific_queues(self):
        """Worker can be configured with specific queue names."""
        options = Configuration.Options(
            workers=[Configuration.Worker(queues=["high", "low"])]
        )
        config = Configuration(options)

        self.assertEqual(config.options.workers[0].queues, ["high", "low"])


class ConfigurationValidationTestCase(SimpleTestCase):
    """Tests for configuration validation."""

    def test_valid_configuration_passes_validation(self):
        """Valid default configuration passes validation."""
        config = Configuration()

        self.assertTrue(config.is_valid)
        self.assertEqual(len(config.errors), 0)

    def test_configuration_with_no_processes_fails_validation(self):
        """Configuration with no processes fails validation."""
        options = Configuration.Options(
            workers=[],
            dispatchers=[],
            only_work=True,  # Exclude schedulers
        )
        config = Configuration(options)

        self.assertFalse(config.is_valid)
        self.assertGreater(len(config.errors), 0)
        self.assertIn("No processes configured", str(config.errors[0]))

    def test_invalid_recurring_task_schedule_fails_validation(self):
        """Invalid cron schedule in recurring task fails validation."""
        invalid_task = Configuration.RecurringTask(
            key="invalid_schedule",
            class_name="tests.dummy.tasks.dummy_task",
            schedule="invalid cron expression",
        )
        options = Configuration.Options(recurring_tasks=[invalid_task])
        config = Configuration(options)

        self.assertFalse(config.is_valid)
        self.assertGreater(len(config.errors), 0)

    def test_invalid_recurring_task_class_name_fails_validation(self):
        """Invalid class name in recurring task fails validation."""
        invalid_task = Configuration.RecurringTask(
            key="invalid_class",
            class_name="nonexistent.module.task",
            schedule="0 0 * * *",
        )
        options = Configuration.Options(recurring_tasks=[invalid_task])
        config = Configuration(options)

        self.assertFalse(config.is_valid)
        self.assertGreater(len(config.errors), 0)

    def test_recurring_task_with_command_fails_validation(self):
        """Recurring task with command option fails validation."""
        task = Configuration.RecurringTask(
            key="command_task",
            class_name="tests.dummy.tasks.dummy_task",
            schedule="0 0 * * *",
            command="some_command",
        )

        with self.assertRaises(ValidationError) as context:
            task.clean()

        self.assertIn("Command is not yet supported", str(context.exception))

    def test_valid_recurring_task_passes_validation(self):
        """Valid recurring task passes validation."""
        valid_task = Configuration.RecurringTask(
            key="valid_task",
            class_name="tests.dummy.tasks.dummy_task",
            schedule="0 0 * * *",
        )

        # Should not raise
        valid_task.clean()

    def test_skip_recurring_bypasses_recurring_task_validation(self):
        """skip_recurring option bypasses recurring task validation."""
        invalid_task = Configuration.RecurringTask(
            key="invalid_schedule",
            class_name="tests.dummy.tasks.dummy_task",
            schedule="invalid",
        )
        options = Configuration.Options(
            recurring_tasks=[invalid_task], skip_recurring=True
        )
        config = Configuration(options)

        # Should still be valid since recurring tasks are skipped
        errors = config.validate_recurring_tasks()
        self.assertEqual(len(errors), 0)

    def test_skip_recurring_excludes_schedulers_from_configured_processes(self):
        """skip_recurring option excludes scheduler processes."""
        options = Configuration.Options(skip_recurring=True)
        config = Configuration(options)

        process_kinds = [p.kind for p in config.configured_processes]
        self.assertNotIn("scheduler", process_kinds)
        self.assertIn("worker", process_kinds)
        self.assertIn("dispatcher", process_kinds)


class RecurringTaskConfigurationTestCase(SimpleTestCase):
    """Tests for recurring task configuration."""

    def test_recurring_task_with_all_options(self):
        """Recurring task supports all configuration options."""
        task = Configuration.RecurringTask(
            key="full_task",
            class_name="tests.dummy.tasks.dummy_task",
            schedule="0 0 * * *",
            queue_name="default",
            priority=10,
            description="A test task",
            arguments={"arg1": "value1"},
        )

        self.assertEqual(task.key, "full_task")
        self.assertEqual(task.class_name, "tests.dummy.tasks.dummy_task")
        self.assertEqual(task.schedule, "0 0 * * *")
        self.assertEqual(task.queue_name, "default")
        self.assertEqual(task.priority, 10)
        self.assertEqual(task.description, "A test task")
        self.assertEqual(task.arguments, {"arg1": "value1"})

    def test_skip_recurring_property_with_only_work(self):
        """skip_recurring property returns True when only_work is True."""
        options = Configuration.Options(only_work=True)
        config = Configuration(options)

        self.assertTrue(config.skip_recurring)

    def test_skip_recurring_property_with_skip_recurring(self):
        """skip_recurring property returns True when skip_recurring is True."""
        options = Configuration.Options(skip_recurring=True)
        config = Configuration(options)

        self.assertTrue(config.skip_recurring)

    def test_skip_recurring_property_default(self):
        """skip_recurring property returns False by default."""
        config = Configuration()

        self.assertFalse(config.skip_recurring)


class ProcessInstantiationTestCase(SimpleTestCase):
    """Tests for process instantiation."""

    def test_worker_process_instantiation(self):
        """Worker process can be instantiated."""
        from steady_queue.processes.worker import Worker

        process = Configuration.Process(
            kind="worker", attributes=Configuration.Worker()
        )

        instance = process.instantiate()
        self.assertIsInstance(instance, Worker)

    def test_dispatcher_process_instantiation(self):
        """Dispatcher process can be instantiated."""
        from steady_queue.processes.dispatcher import Dispatcher

        process = Configuration.Process(
            kind="dispatcher", attributes=Configuration.Dispatcher()
        )

        instance = process.instantiate()
        self.assertIsInstance(instance, Dispatcher)

    def test_scheduler_process_instantiation(self):
        """Scheduler process can be instantiated."""
        from steady_queue.processes.scheduler import Scheduler

        process = Configuration.Process(
            kind="scheduler", attributes={"recurring_tasks": []}
        )

        instance = process.instantiate()
        self.assertIsInstance(instance, Scheduler)

    def test_invalid_process_kind_raises_error(self):
        """Invalid process kind raises ValueError."""
        process = Configuration.Process(kind="invalid_kind", attributes={})

        with self.assertRaises(ValueError) as context:
            process.instantiate()

        self.assertIn("Invalid process kind", str(context.exception))


class WorkerConfigurationTestCase(SimpleTestCase):
    """Tests for worker-specific configuration."""

    def test_worker_configuration_defaults(self):
        """Worker configuration has correct default values."""
        worker = Configuration.Worker()

        self.assertEqual(worker.queues, ["*"])
        self.assertEqual(worker.threads, 3)
        self.assertEqual(worker.processes, 1)
        self.assertEqual(worker.polling_interval, timedelta(seconds=0.1))

    def test_worker_configuration_custom_values(self):
        """Worker configuration accepts custom values."""
        worker = Configuration.Worker(
            queues=["high", "medium", "low"],
            threads=5,
            processes=2,
            polling_interval=timedelta(seconds=0.5),
        )

        self.assertEqual(worker.queues, ["high", "medium", "low"])
        self.assertEqual(worker.threads, 5)
        self.assertEqual(worker.processes, 2)
        self.assertEqual(worker.polling_interval, timedelta(seconds=0.5))


class DispatcherConfigurationTestCase(SimpleTestCase):
    """Tests for dispatcher-specific configuration."""

    def test_dispatcher_configuration_defaults(self):
        """Dispatcher configuration has correct default values."""
        dispatcher = Configuration.Dispatcher()

        self.assertEqual(dispatcher.polling_interval, timedelta(seconds=1))
        self.assertEqual(dispatcher.batch_size, 500)
        self.assertTrue(dispatcher.concurrency_maintenance)
        self.assertEqual(
            dispatcher.concurrency_maintenance_interval, timedelta(minutes=5)
        )

    def test_dispatcher_configuration_custom_values(self):
        """Dispatcher configuration accepts custom values."""
        dispatcher = Configuration.Dispatcher(
            polling_interval=timedelta(seconds=2),
            batch_size=1000,
            concurrency_maintenance=False,
            concurrency_maintenance_interval=timedelta(minutes=10),
        )

        self.assertEqual(dispatcher.polling_interval, timedelta(seconds=2))
        self.assertEqual(dispatcher.batch_size, 1000)
        self.assertFalse(dispatcher.concurrency_maintenance)
        self.assertEqual(
            dispatcher.concurrency_maintenance_interval, timedelta(minutes=10)
        )
