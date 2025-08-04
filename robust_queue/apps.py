from django.apps import AppConfig


class RobustQueueConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "robust_queue"
    verbose_name = "Robust Queue"

    def ready(self):
        pass
