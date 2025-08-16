from django.apps import AppConfig


class SteadyQueueConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "steady_queue"
    verbose_name = "Steady Queue"

    def ready(self):
        pass
