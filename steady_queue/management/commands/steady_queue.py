import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.module_loading import autodiscover_modules

from steady_queue.processes.supervisor import Supervisor

logger = logging.getLogger("steady_queue")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


class Command(BaseCommand):
    help = "Run the steady queue supervisor"

    def add_arguments(self, parser):
        parser.add_argument(
            "--disable-autoload",
            action="store_true",
            help="Disable automatic loading of tasks modules to automatically register recurring tasks",
        )

    def handle(self, *args, **options):
        if not options.get("disable_autoload"):
            autodiscover_modules("tasks")

        Supervisor.launch(getattr(settings, "STEADY_QUEUE", None))
