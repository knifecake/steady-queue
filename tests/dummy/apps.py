from django.apps import AppConfig


class RobustQueueConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tests.dummy"
    verbose_name = "Test Dummy"

    def ready(self):
        pass
