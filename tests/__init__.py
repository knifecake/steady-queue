from django.test import TestCase as DjangoTestCase

# Ensure Django test cases can access both default and queue databases
# Note: Must use "queue" explicitly since test settings set steady_queue.database = "queue"
DjangoTestCase.databases = {"default", "queue"}
