from django.test import TestCase as DjangoTestCase

from steady_queue.db_router import steady_queue_database_alias

# Ensure Django test cases can access both default and queue databases
DjangoTestCase.databases = {"default", steady_queue_database_alias()}
