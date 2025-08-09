from typing import Optional

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
    list_display: tuple[str, ...] = ("id", "__str__", "created_at")
    date_hierarchy: Optional[str] = "created_at"
    search_fields: tuple[str, ...] = ("id",)
    ordering: tuple[str, ...] = ("-created_at",)


@admin.register(ReadyExecution)
class ReadyExecutionAdmin(ReadOnlyAdminMixin, BaseAdmin):
    list_display = ("job_id", "queue_name", "priority", "created_at")


@admin.register(FailedExecution)
class FailedExecutionAdmin(ReadOnlyAdminMixin, BaseAdmin):
    list_display = ("job", "error", "created_at")
    actions = ("retry",)

    @admin.action(description="Retry")
    def retry(self, request, queryset):
        count = queryset.retry()
        self.message_user(request, f"Retried {count} failed executions")


@admin.register(Job)
class JobAdmin(ReadOnlyAdminMixin, BaseAdmin):
    list_display = ("class_name", "status", "queue_name", "priority", "scheduled_at")
    readonly_fields = ("status",)


@admin.register(ScheduledExecution)
class ScheduledExecutionAdmin(ReadOnlyAdminMixin, BaseAdmin):
    pass


@admin.register(RecurringExecution)
class RecurringExecutionAdmin(ReadOnlyAdminMixin, BaseAdmin):
    list_display = ("task__key", "run_at")


@admin.register(RecurringTask)
class RecurringTaskAdmin(ReadOnlyAdminMixin, BaseAdmin):
    list_display = ("key", "schedule", "class_name", "queue_name", "priority")


@admin.register(Pause)
class PauseAdmin(ReadOnlyAdminMixin, BaseAdmin):
    pass


@admin.register(ClaimedExecution)
class ClaimedExecutionAdmin(ReadOnlyAdminMixin, BaseAdmin):
    list_display = ("job_id", "process__name", "created_at")


@admin.register(BlockedExecution)
class BlockedExecutionAdmin(ReadOnlyAdminMixin, BaseAdmin):
    pass


@admin.register(Process)
class ProcessAdmin(ReadOnlyAdminMixin, BaseAdmin):
    date_hierarchy = None
    list_display = ("pid", "hostname", "kind", "name", "last_heartbeat_at")
