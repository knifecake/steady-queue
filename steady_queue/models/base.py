from contextlib import contextmanager

from django.db import models, transaction
from django.utils import timezone


class CreatedAtMixin(models.Model):
    created_at = models.DateTimeField(default=timezone.now, verbose_name="created at")

    class Meta:
        abstract = True


class UpdatedAtMixin(models.Model):
    updated_at = models.DateTimeField(auto_now=True, verbose_name="updated at")

    class Meta:
        abstract = True


class BaseModel(CreatedAtMixin, models.Model):
    class Meta:
        abstract = True

    @contextmanager
    def lock(self):
        with transaction.atomic(using=self._state.db):
            self.refresh_from_db(from_queryset=type(self).objects.select_for_update())
            yield
