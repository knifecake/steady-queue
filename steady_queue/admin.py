from typing import Optional

from django.contrib import admin
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.db.models import Count

from .models import (
    BlockedExecution,
    ClaimedExecution,
    FailedExecution,
    Job,
    Process,
    Queue,
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


@admin.register(Job)
class JobAdmin(ReadOnlyAdminMixin, BaseAdmin):
    list_display = ("id", "class_name", "queue_name", "created_at")

    fields = (
        ("class_name", "status"),
        ("queue_name", "priority"),
        ("created_at", "scheduled_at", "finished_at"),
        ("django_task_id", "concurrency_key"),
        ("arguments",),
    )


class ExecutionAdmin(ReadOnlyAdminMixin, BaseAdmin):
    pass


@admin.register(FailedExecution)
class FailedExecutionAdmin(ExecutionAdmin):
    list_display = ("job__class_name", "error")
    actions = ("retry", "discard")

    @admin.action(description="Retry")
    def retry(self, request, queryset):
        count = queryset.retry()
        self.message_user(request, f"Retried {count} failed executions")

    @admin.action(description="Discard")
    def discard(self, request, queryset):
        count = queryset.discard_in_batches()
        self.message_user(request, f"Discarded {count} failed executions")


@admin.register(ScheduledExecution)
class ScheduledExecutionAdmin(ExecutionAdmin):
    list_display = ("job__class_name", "queue_name", "priority", "scheduled_at")


@admin.register(ClaimedExecution)
class ClaimedExecutionAdmin(ExecutionAdmin):
    list_display = ("job__class_name", "job__queue_name", "process", "running_since")

    @admin.display(description="Running since")
    def running_since(self, obj: ClaimedExecution) -> str:
        return naturaltime(obj.created_at)


@admin.register(BlockedExecution)
class BlockedExecutionAdmin(ExecutionAdmin):
    list_display = (
        "job__class_name",
        "queue_name",
        "priority",
        "concurrency_key",
        "expires_at",
    )


@admin.register(RecurringTask)
class RecurringTaskAdmin(ReadOnlyAdminMixin, BaseAdmin):
    list_display = ("key", "schedule", "class_name", "queue_name", "priority")


@admin.register(Process)
class ProcessAdmin(ReadOnlyAdminMixin, BaseAdmin):
    date_hierarchy = None
    list_display = ("name", "pid", "hostname", "job_count", "heartbeat_age")
    readonly_fields = ("job_count",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(job_count=Count("claimed_executions"))
        )

    @admin.display(description="Last heartbeat", ordering="last_heartbeat_at")
    def heartbeat_age(self, obj: Process) -> str:
        return naturaltime(obj.last_heartbeat_at)

    @admin.display(description="Running tasks", ordering="job_count")
    def job_count(self, obj: Process) -> Optional[int]:
        if obj.kind != "worker":
            return None

        return obj.job_count


@admin.register(Queue)
class QueueAdmin(ReadOnlyAdminMixin, BaseAdmin):
    ordering = ("queue_name",)
    date_hierarchy = None
    list_display = (
        "queue_name",
        "is_running",
        "pending_jobs",
    )
    readonly_fields = ("pending_jobs", "is_running")
    actions = ("pause", "resume")
    search_fields = ("queue_name",)

    @admin.action(description="Pause")
    def pause(self, request, queryset):
        count = queryset.pause()
        self.message_user(request, f"Paused {count} queues")

    @admin.action(description="Resume")
    def resume(self, request, queryset):
        count = queryset.resume()
        self.message_user(request, f"Resumed {count} queues")

    @admin.display(description="Running", boolean=True)
    def is_running(self, obj: Queue) -> bool:
        return obj.is_running
