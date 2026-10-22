"""Regression checks for discovery, session grouping, and the safe demo path."""
import time
import unittest
from unittest.mock import Mock, patch

import psutil

import hermes_monitor as monitor


def process(pid, name, parent, command):
    proc = Mock()
    proc.pid = pid
    proc.info = {"pid": pid, "name": name, "ppid": parent}
    proc.ppid.return_value = parent
    proc.cmdline.return_value = command
    return proc


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        monitor._cmdline_cache.clear()

    def test_launcher_and_workers_share_one_terminal(self):
        terminal = process(10, "cmd.exe", 0, ["cmd.exe"])
        launcher = process(20, "hermes.exe", 10, ["hermes.exe", "--profile", "work"])
        worker = process(30, "python.exe", 20, ["python.exe", "hermes_cli/main.py", "chat"])
        other_terminal = process(40, "cmd.exe", 0, ["cmd.exe"])
        other = process(50, "hermes.exe", 40, ["hermes.exe", "chat"])
        with patch.object(monitor, "enum_visible_windows", return_value=(
            {10: 100, 40: 200}, {100: "Work", 200: "Other"}
        )), patch.object(psutil, "process_iter", return_value=[
            terminal, launcher, worker, other_terminal, other
        ]):
            sessions = monitor.scan_sessions()
        self.assertEqual(set(sessions), {100, 200})
        self.assertEqual(sessions[100]["pids"], {20, 30})
        self.assertEqual(sessions[100]["profile"], "work")
        self.assertEqual(sessions[200]["profile"], "default")
        terminal.cmdline.assert_not_called()

    def test_gateway_self_and_orphan_are_excluded(self):
        terminal = process(10, "cmd.exe", 0, ["cmd.exe"])
        gateway = process(20, "hermes.exe", 10, ["hermes.exe", "gateway"])
        self_proc = process(30, "pythonw.exe", 10, ["pythonw.exe", "hermes_monitor.py"])
        orphan = process(40, "hermes.exe", 0, ["hermes.exe", "chat"])
        with patch.object(monitor, "enum_visible_windows", return_value=(
            {10: 100}, {100: "Terminal"}
        )), patch.object(psutil, "process_iter", return_value=[
            terminal, gateway, self_proc, orphan
        ]):
            self.assertEqual(monitor.scan_sessions(), {})

    def test_access_denied_does_not_break_discovery(self):
        proc = process(20, "python.exe", 0, [])
        proc.cmdline.side_effect = psutil.AccessDenied(20)
        with patch.object(monitor, "enum_visible_windows", return_value=({}, {})), \
             patch.object(psutil, "process_iter", return_value=[proc]):
            self.assertEqual(monitor.scan_sessions(), {})

    def test_dead_process_command_cache_is_pruned(self):
        monitor._cmdline_cache[999] = "old hermes.exe"
        with patch.object(monitor, "enum_visible_windows", return_value=({}, {})), \
             patch.object(psutil, "process_iter", return_value=[]):
            monitor.scan_sessions()
        self.assertNotIn(999, monitor._cmdline_cache)


class DemoTests(unittest.TestCase):
    def test_demo_never_scans_or_focuses_real_windows(self):
        with patch.object(monitor, "scan_sessions", side_effect=AssertionError("process scan")), \
             patch.object(monitor, "bring_to_front", side_effect=AssertionError("window focus")):
            app = monitor.MonitorApp(demo=True)
            try:
                app.root.update()
                self.assertEqual(len(app.lamps), 3)
                first = app.lamps[-1]
                self.assertEqual(first["state"], "green")
                self.assertIn("simulated", app._tooltip_text(-1))
                first["horse"].canvas.event_generate("<Button-1>", x=5, y=5)
                app.demo_started = time.monotonic() - 7
                app._refresh_demo()
                self.assertEqual(first["state"], "red")
                self.assertEqual(app.lamps[-2]["state"], "green")
            finally:
                app.root.destroy()


if __name__ == "__main__":
    unittest.main()
