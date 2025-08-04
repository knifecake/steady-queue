from django.contrib import admin

from .models import Job, Process


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


@admin.register(Job)
class JobAdmin(BaseAdmin):
    pass


@admin.register(Process)
class ProcessAdmin(ReadOnlyAdminMixin, BaseAdmin):
    date_hierarchy = None
    list_display = ("pid", "hostname", "kind", "name", "last_heartbeat_at")
