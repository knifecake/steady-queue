from .base import BaseModel
from django.db import models

from .mixins import UpdatedAtMixin


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

    key = models.CharField(max_length=255, verbose_name="key")
    schedule = models.CharField(max_length=255, verbose_name="schedule")
    command = models.CharField(
        max_length=2048, verbose_name="command", blank=True, null=True
    )
    class_name = models.CharField(max_length=255, verbose_name="class name")
    arguments = models.JSONField(verbose_name="arguments")
    queue_name = models.CharField(max_length=255, verbose_name="queue name")
    priority = models.PositiveSmallIntegerField(verbose_name="priority", default=0)
    static = models.BooleanField(verbose_name="static", default=False)
    description = models.TextField(verbose_name="description", blank=True, null=True)
