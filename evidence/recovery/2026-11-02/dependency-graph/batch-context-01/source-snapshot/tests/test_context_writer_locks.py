"""Real advisory-lock contention plus supported mutation-entrypoint coverage."""
import ast
import fcntl
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / "dependency-graph"
sys.path.insert(0, str(BASE))
from context_writer_lock import exclusive_writer


class ContextWriterLockTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "temp/test-work/context-writer-locks"
        scratch.mkdir(parents=True, exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=scratch)
        self.root = pathlib.Path(self.directory.name)
        (self.root / "dependency-graph/state").mkdir(parents=True)
        self.processes = []

    def tearDown(self):
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)
        self.directory.cleanup()

    def writer(self, marker, hold=False):
        code = (
            "import pathlib,sys,time;sys.path.insert(0,sys.argv[1]);"
            "from context_writer_lock import exclusive_writer;"
            "\nwith exclusive_writer(pathlib.Path(sys.argv[2])):"
            "\n pathlib.Path(sys.argv[3]).write_text('entered')"
            + ("\n time.sleep(30)" if hold else "")
        )
        process = subprocess.Popen([sys.executable, "-c", code, str(BASE), str(self.root), str(marker)])
        self.processes.append(process)
        return process

    def wait_marker(self, marker):
        end = time.monotonic() + 10
        while not marker.exists() and time.monotonic() < end:
            time.sleep(0.02)
        self.assertTrue(marker.exists())

    def test_writer_waits_for_all_shared_builders(self):
        lock = self.root / "dependency-graph/state/context.lock"
        with lock.open("a") as first, lock.open("a") as second:
            fcntl.flock(first, fcntl.LOCK_SH)
            fcntl.flock(second, fcntl.LOCK_SH)
            marker = self.root / "writer"
            process = self.writer(marker)
            time.sleep(0.2)
            self.assertFalse(marker.exists())
            fcntl.flock(first, fcntl.LOCK_UN)
            time.sleep(0.1)
            self.assertFalse(marker.exists())
            fcntl.flock(second, fcntl.LOCK_UN)
            self.wait_marker(marker)
            self.assertEqual(process.wait(timeout=10), 0)

    def test_exclusive_writers_serialize_and_termination_releases_lock(self):
        first_marker, second_marker = self.root / "first", self.root / "second"
        first = self.writer(first_marker, hold=True)
        self.wait_marker(first_marker)
        second = self.writer(second_marker)
        time.sleep(0.2)
        self.assertFalse(second_marker.exists())
        first.terminate()
        first.wait(timeout=10)
        self.wait_marker(second_marker)
        self.assertEqual(second.wait(timeout=10), 0)

    def test_helper_creates_and_releases_lock(self):
        with exclusive_writer(self.root):
            with (self.root / "dependency-graph/state/context.lock").open("a") as other:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(other, fcntl.LOCK_SH | fcntl.LOCK_NB)
        with (self.root / "dependency-graph/state/context.lock").open("a") as other:
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_internal_publisher_matches_runner_python_entrypoint(self):
        from refresh_graph import publisher_script
        output = pathlib.Path('/bound/project/output')
        command = publisher_script(output)
        self.assertEqual(command[0], '-c')
        self.assertEqual(command[-1], str(output))
        self.assertIn('from refresh_publish import main', command[1])

    def test_supported_direct_mutation_entrypoints_take_exclusive_lock(self):
        for name in ("import_bolt.py", "load_full_graph.py", "case_last_cycle.py", "refresh_publish.py", "native_graph.py", "native_publish.py", "context_selector.py"):
            with self.subTest(name=name):
                tree = ast.parse((BASE / name).read_text())
                entry = tree.body[-1]
                self.assertIsInstance(entry, ast.If)
                scopes = [node for node in ast.walk(entry) if isinstance(node, ast.With)]
                self.assertTrue(any(isinstance(scope.items[0].context_expr, ast.Call)
                                    and isinstance(scope.items[0].context_expr.func, ast.Name)
                                    and scope.items[0].context_expr.func.id == "exclusive_writer"
                                    for scope in scopes))
        native = ast.parse((BASE / "locked_native_graph.py").read_text())
        self.assertTrue(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                            and node.func.id == "exclusive_writer" for node in ast.walk(native)))


if __name__ == "__main__":
    unittest.main()
