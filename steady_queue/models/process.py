from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone

from steady_queue.models.base import BaseModel
from steady_queue.models.executor import Executor
from steady_queue.models.prunable import Prunable, PrunableQuerySet


class ProcessQuerySet(PrunableQuerySet, models.QuerySet):
    pass


class Process(Executor, Prunable, BaseModel):
    class Meta:
        verbose_name = "process"
        verbose_name_plural = "processes"
        indexes = (
            models.Index(fields=("last_heartbeat_at",), name="ix_sq_process_heartbeat"),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("name", "supervisor"),
                name="uq_sq_process_name_supervisor",
            ),
        )

    objects = ProcessQuerySet.as_manager()

    kind = models.CharField(max_length=255, verbose_name="kind")
    last_heartbeat_at = models.DateTimeField(verbose_name="last heartbeat at")
    supervisor = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervisees",
    )

    pid = models.PositiveSmallIntegerField(verbose_name="pid")
    hostname = models.CharField(
        max_length=1024, null=True, blank=True, verbose_name="hostname"
    )
    metadata = models.JSONField(
        null=True, blank=True, verbose_name="metadata", encoder=DjangoJSONEncoder
    )
    name = models.CharField(max_length=255, verbose_name="name")

    @classmethod
    def register(cls, **kwargs):
        process = cls(**kwargs, last_heartbeat_at=timezone.now())
        process.save()
        return process

    def heartbeat(self):
        self.refresh_from_db()

        with self.lock():
            self.last_heartbeat_at = timezone.now()
            self.save()

    def deregister(self, pruned=False):
        if not (pruned or self.is_supervised):
            for sup in self.supervisees.all():
                sup.deregister()

        self.delete()

    @property
    def is_supervised(self):
        return self.supervisor_id is not None

    def __str__(self):
        return self.name
