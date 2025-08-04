import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":
    os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings"
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()

    test_labels = sys.argv[1:] or ["tests"]
    failures = test_runner.run_tests(test_labels)

    sys.exit(bool(failures))
