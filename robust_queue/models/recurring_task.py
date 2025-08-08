from datetime import datetime, timedelta
from functools import cached_property

from crontab import CronTab
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from robust_queue.configuration import Configuration
from robust_queue.models.recurring_execution import RecurringExecution

from .base import BaseModel
from .mixins import UpdatedAtMixin


class RecurringTaskQuerySet(models.QuerySet):
    def static(self):
        return self.filter(static=True)

    def create_or_update_all(self, tasks):
        self.bulk_create(
            tasks,
            update_conflicts=True,
            unique_fields=("key",),
            update_fields=[
                f.name
                for f in self.model._meta.fields
                if f.name not in ("id", "created_at", "updated_at")
            ],
        )


class RecurringTask(UpdatedAtMixin, BaseModel):
    class Meta:
        verbose_name = "recurring task"
        verbose_name_plural = "recurring tasks"
        indexes = (
            models.Index(fields=("static",), name="ix_rq_recurring_tasks_static"),
        )
        constraints = (
            models.UniqueConstraint(fields=("key",), name="uq_rq_recurring_tasks_key"),
        )

    objects = RecurringTaskQuerySet.as_manager()

    key = models.CharField(max_length=255, verbose_name="key")
    schedule = models.CharField(max_length=255, verbose_name="schedule")
    command = models.CharField(
        max_length=2048, verbose_name="command", blank=True, null=True
    )
    class_name = models.CharField(max_length=255, verbose_name="class name")
    arguments = models.JSONField(verbose_name="arguments", null=True, blank=True)
    queue_name = models.CharField(
        max_length=255, verbose_name="queue name", null=True, blank=True
    )
    priority = models.PositiveSmallIntegerField(verbose_name="priority", default=0)
    static = models.BooleanField(verbose_name="static", default=False)
    description = models.TextField(verbose_name="description", blank=True, null=True)

    @classmethod
    def wrap(cls, self_or_config):
        if isinstance(self_or_config, cls):
            return self_or_config
        return cls.from_configuration(self_or_config)

    @classmethod
    def from_configuration(cls, config: Configuration.RecurringTaskConfiguration):
        return cls(
            key=config.key,
            static=True,
            class_name=config.class_name,
            command=config.command,
            arguments=config.arguments,
            schedule=config.schedule,
            queue_name=config.queue_name,
            priority=config.priority,
            description=config.description,
        )

    @cached_property
    def parsed_schedule(self):
        return CronTab(self.schedule)

    @cached_property
    def job_class(self):
        return import_string(self.class_name)

    @property
    def delay_from_now(self) -> timedelta:
        return self.next_time - timezone.now()

    @property
    def next_time(self) -> datetime:
        return self.parsed_schedule.next(timezone.now(), return_datetime=True)

    @property
    def last_enqueued_time(self) -> datetime:
        return self.recurring_executions.max("run_at")

    def enqueue(self, run_at: datetime):
        if self.is_using_robust_queue_adapter:
            return self.enqueue_and_record(run_at)
        else:
            raise NotImplementedError

        # TODO: error handling

    @property
    def is_using_robust_queue_adapter(self) -> bool:
        return True  # TODO: implement

    def enqueue_and_record(self, run_at: datetime):
        with transaction.atomic():
            result = self.job_class.using(
                queue_name=self.queue_name, priority=self.priority
            ).enqueue()
            RecurringExecution.objects.record(result, self, run_at)

    @property
    def previous_time(self) -> datetime:
        return self.parsed_schedule.previous(timezone.now(), return_datetime=True)

    def clean_schedule(self):
        try:
            self.parsed_schedule
        except ValueError as e:
            raise ValidationError(f'Invalid schedule "{self.schedule}": {str(e)}')

    def clean_class_name(self):
        try:
            self.job_class
        except ImportError as e:
            raise ValidationError(f'Invalid class name "{self.class_name}": {str(e)}')

    def clean_command(self):
        if self.command is None:
            return

        raise ValidationError("Command is not yet supported for recurring tasks")
