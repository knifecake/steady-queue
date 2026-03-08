import os
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

import steady_queue
from steady_queue.processes.pidfile import Pidfile


class PidfileDefaultsTestCase(SimpleTestCase):
    def test_supervisor_pidfile_defaults_to_none(self):
        self.assertIsNone(steady_queue.supervisor_pidfile)


class PidfileLifecycleTestCase(SimpleTestCase):
    def test_setup_registers_atexit_cleanup_hook(self):
        with TemporaryDirectory() as temp_dir, patch("atexit.register") as register:
            path = os.path.join(temp_dir, "pids", "steady_queue_supervisor.pid")

            pidfile = Pidfile(path)
            pidfile.setup()

            register.assert_called_once()
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                self.assertEqual(str(os.getpid()), f.read().strip())

    def test_setup_replaces_stale_pidfile_for_dead_process(self):
        with TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "pids", "steady_queue_supervisor.pid")

            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write("999999")

            with patch("atexit.register"):
                pidfile = Pidfile(path)
                pidfile.setup()

            with open(path) as f:
                self.assertEqual(str(os.getpid()), f.read().strip())
