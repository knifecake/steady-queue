from django.contrib import admin

from .models import (
    BlockedExecution,
    ClaimedExecution,
    FailedExecution,
    Job,
    Pause,
    Process,
    ReadyExecution,
    RecurringExecution,
    RecurringTask,
    ScheduledExecution,
)


class ReadOnlyAdminMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class BaseAdmin(admin.ModelAdmin):
    list_display = ("id", "__str__", "created_at")
    date_hierarchy = "created_at"
    search_fields = ("id",)
    ordering = ("-created_at",)


@admin.register(ReadyExecution)
class ReadyExecutionAdmin(ReadOnlyAdminMixin, BaseAdmin):
    list_display = ("job_id", "queue_name", "priority", "created_at")


@admin.register(FailedExecution)
class FailedExecutionAdmin(ReadOnlyAdminMixin, BaseAdmin):
    pass


@admin.register(Job)
class JobAdmin(ReadOnlyAdminMixin, BaseAdmin):
    pass


@admin.register(ScheduledExecution)
class ScheduledExecutionAdmin(ReadOnlyAdminMixin, BaseAdmin):
    pass


@admin.register(RecurringExecution)
class RecurringExecutionAdmin(ReadOnlyAdminMixin, BaseAdmin):
    pass


@admin.register(RecurringTask)
class RecurringTaskAdmin(ReadOnlyAdminMixin, BaseAdmin):
    pass


@admin.register(Pause)
class PauseAdmin(ReadOnlyAdminMixin, BaseAdmin):
    pass


@admin.register(ClaimedExecution)
class ClaimedExecutionAdmin(ReadOnlyAdminMixin, BaseAdmin):
    pass


@admin.register(BlockedExecution)
class BlockedExecutionAdmin(ReadOnlyAdminMixin, BaseAdmin):
    pass


@admin.register(Process)
class ProcessAdmin(ReadOnlyAdminMixin, BaseAdmin):
    date_hierarchy = None
    list_display = ("pid", "hostname", "kind", "name", "last_heartbeat_at")
