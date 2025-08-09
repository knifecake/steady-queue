from django.db import models

from robust_queue.models.base import BaseModel, UpdatedAtMixin


class Semaphore(UpdatedAtMixin, BaseModel):
    class Meta:
        verbose_name = "semaphore"
        verbose_name_plural = "semaphores"
        constraints = (
            models.UniqueConstraint(fields=("key",), name="uq_rq_semaphore_key"),
        )
        indexes = (
            models.Index(fields=("expires_at",), name="ix_rq_semaphore_expires_at"),
            models.Index(fields=("key", "value"), name="ix_rq_semaphores_key_value"),
        )

    key = models.CharField(max_length=255, verbose_name="key")
    value = models.IntegerField(default=1, verbose_name="value")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="expires at")
