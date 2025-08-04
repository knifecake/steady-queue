import logging

from django.core.management.base import BaseCommand

from robust_queue.supervisor import Supervisor

logger = logging.getLogger("robust_queue.supervisor")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


class Command(BaseCommand):
    help = "Run the robust queue supervisor"

    def handle(self, *args, **options):
        Supervisor.launch()
