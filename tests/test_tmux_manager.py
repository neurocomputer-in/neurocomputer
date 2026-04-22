"""Tests for core.tmux_manager. Uses unittest (no pytest dep).

Requires `tmux` on PATH. Each test that creates a tmux session is
careful to kill it in tearDown.
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import tmux_manager as tm


def _cleanup(name):
    subprocess.run(
        ["tmux", "kill-session", "-t", name],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


class TmuxManagerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._created = []

    def tearDown(self):
        for name in self._created:
            _cleanup(name)

    def test_tmux_available(self):
        self.assertTrue(tm.tmux_available())

    def test_make_session_name_pattern(self):
        n1 = tm.make_session_name("default", "main-default")
        n2 = tm.make_session_name("default", "main-default")
        self.assertRegex(n1, r"^neuro-default-main-default-[0-9a-f]{8}$")
        self.assertNotEqual(n1, n2)

    def test_slug_unsafe_chars(self):
        name = tm.make_session_name("My Space", "Proj/X!")
        self.assertRegex(name, r"^neuro-my-space-proj-x-[0-9a-f]{8}$")

    def test_new_session_is_idempotent(self):
        name = tm.make_session_name("t", "p")
        self._created.append(name)
        tm.new_session(name, self._tmp)
        self.assertTrue(tm.session_exists(name))
        # second call must not raise or create a dupe
        tm.new_session(name, self._tmp)
        self.assertTrue(tm.session_exists(name))

    def test_list_sessions_filter(self):
        a = tm.make_session_name("workA", "projA")
        b = tm.make_session_name("workA", "projB")
        self._created.extend([a, b])
        tm.new_session(a, self._tmp)
        tm.new_session(b, self._tmp)
        rows = tm.list_sessions(prefix="neuro-worka-proja-")
        names = [r["name"] for r in rows]
        self.assertIn(a, names)
        self.assertNotIn(b, names)

    def test_kill_session(self):
        name = tm.make_session_name("t", "p")
        tm.new_session(name, self._tmp)
        self.assertTrue(tm.session_exists(name))
        self.assertTrue(tm.kill_session(name))
        self.assertFalse(tm.session_exists(name))


if __name__ == "__main__":
    unittest.main()
