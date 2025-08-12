from typing import Optional

from django.contrib import admin, messages
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.db.models import Count

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


class JobStatusFilter(admin.SimpleListFilter):
    title = "status"

    parameter_name = "status"

    def lookups(self, request, model_admin):
        return (
            ("scheduled", "Scheduled"),
            ("blocked", "Blocked"),
            ("ready", "Ready"),
            ("claimed", "Claimed"),
            ("finished", "Finished"),
            ("failed", "Failed"),
        )

    def queryset(self, request, queryset):
        if self.value() == "scheduled":
            return queryset.scheduled()
        elif self.value() == "ready":
            return queryset.ready()
        elif self.value() == "failed":
            return queryset.failed()
        elif self.value() == "claimed":
            return queryset.claimed()
        elif self.value() == "blocked":
            return queryset.blocked()
        elif self.value() == "finished":
            return queryset.finished()
        return queryset


class ExecutionInline(admin.StackedInline):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # These objects have one-to-one relationships, so we hack the plural
        # name to render the singular name
        self.verbose_name_plural = self.model._meta.verbose_name


class FailedExecutionInline(ExecutionInline):
    model = FailedExecution


class ClaimedExecutionInline(ExecutionInline):
    model = ClaimedExecution


class BlockedExecutionInline(ExecutionInline):
    model = BlockedExecution


class ReadyExecutionInline(ExecutionInline):
    model = ReadyExecution


@admin.register(Job)
class JobAdmin(ReadOnlyAdminMixin, BaseAdmin):
    list_display = ("class_name", "status", "queue_name", "priority", "scheduled_at")
    list_filter = ("queue_name", JobStatusFilter)
    readonly_fields = ("status",)
    actions = ("retry_failed_executions",)

    def get_inlines(
        self, request, obj: Optional[Job] = None
    ) -> list[type[admin.StackedInline]]:
        inlines = []
        if (executable_inline := self.get_executable_inlines(request, obj)) is not None:
            inlines.append(executable_inline)
        return inlines

    def get_executable_inlines(
        self, request, obj: Optional[Job] = None
    ) -> type[ExecutionInline]:
        if obj.status == "ready":
            return ReadyExecutionInline
        elif obj.status == "failed":
            return FailedExecutionInline
        elif obj.status == "claimed":
            return ClaimedExecutionInline
        elif obj.status == "blocked":
            return BlockedExecutionInline

        return None

    @admin.action(description="Retry failed executions")
    def retry_failed_executions(self, request, queryset):
        count = queryset.count()
        failed_executions = FailedExecution.objects.filter(job__in=queryset)
        retried_count = failed_executions.retry()

        self.message_user(request, f"Retried {retried_count} failed executions")

        if (not_failed_count := count - retried_count) > 0:
            self.message_user(
                request,
                f"{not_failed_count} jobs were not retried because they were not failed",
                level=messages.WARNING,
            )


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

    @admin.display(description="Tasks", ordering="job_count")
    def job_count(self, obj: Process) -> int:
        return obj.job_count
