from django.db import models
from django.utils import timezone


class CreatedAtMixin(models.Model):
    created_at = models.DateTimeField(default=timezone.now, verbose_name="created at")

    class Meta:
        abstract = True


class UpdatedAtMixin(models.Model):
    updated_at = models.DateTimeField(auto_now=True, verbose_name="updated at")

    class Meta:
        abstract = True
