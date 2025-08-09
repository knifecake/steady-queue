import logging

from django.core.management.base import BaseCommand
from django.utils.module_loading import autodiscover_modules

from robust_queue.supervisor import Supervisor

logger = logging.getLogger("robust_queue.supervisor")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

from django.conf import settings


class Command(BaseCommand):
    help = "Run the robust queue supervisor"

    def add_arguments(self, parser):
        parser.add_argument(
            "--disable-autoload",
            action="store_true",
            help="Disable autoloading of tasks modules to automatically register recurring tasks",
        )

    def handle(self, *args, **options):
        if not options.get("disable_autoload"):
            autodiscover_modules("tasks")

        Supervisor.launch(getattr(settings, "ROBUST_QUEUE", None))
