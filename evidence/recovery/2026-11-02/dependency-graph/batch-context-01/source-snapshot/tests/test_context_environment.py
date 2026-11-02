"""Real snapshot and Docker environment regressions, entirely in project scratch."""
import fcntl
import json
import pathlib
import shlex
import sqlite3
import subprocess
import sys
import time
import unittest
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'dependency-graph'))
from context_batch import Environment, capture_inputs, check_inputs, freeze_snapshot
from context_runtime import ContextError, fingerprint, inventory, sha


def docker(*args):
    return subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', *args])],
                          capture_output=True, text=True)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / 'temp/test-work/context-environment' / uuid.uuid4().hex
        self.output = self.root / 'temp/recovery-work/batch'
        for relative in ['dependency-graph/state', 'uc-library/src', 'uc-library/include',
                         'uc-library/tools/recovery', 'uc-library/validation/registry-sqlite', 'docs']:
            (self.root / relative).mkdir(parents=True)
        self.output.mkdir(parents=True)
        self.source = self.root / 'uc-library/src/input.cpp'
        self.source.write_text('frozen original bytes\n')
        (self.root / 'uc-library/include/input.hpp').write_text('frozen header\n')
        for name in ['AGENTS.md', 'dependency-graph/producer.py', 'dependency-graph/DEDUP_ACTIVE.json',
                     'uc-library/tools/recovery/select_context.py',
                     'uc-library/validation/registry-sqlite/ACTIVE.json', 'docs/worker-handoff.md',
                     'dependency-graph/CONTEXT_SELECTION.md', 'dependency-graph/BATCH_CONTEXT.md', 'dependency-graph/DEDUPLICATION.md']:
            (self.root / name).write_text('{}')
        (self.root / 'dependency-graph/context_runtime.py').write_bytes(
            (ROOT / 'dependency-graph/context_runtime.py').read_bytes())
        state = {'files': {'uc-library/src/input.cpp': {'sha256': sha(self.source),
                  'fingerprint': fingerprint(self.source)}}, 'source_inventory': inventory(self.root)}
        path = self.root / 'dependency-graph/state/generation.json'
        path.write_text(json.dumps(state))
        (path.parent / 'context.lock').touch()
        active = {'state': str(path.relative_to(self.root)), 'state_sha256': sha(path)}
        (self.root / 'dependency-graph/ACTIVE.json').write_text(json.dumps(active))
        native = self.root / 'native.sqlite'
        with sqlite3.connect(native) as connection:
            connection.executescript('CREATE TABLE inputs(path TEXT,sha256 TEXT); CREATE TABLE binaries(id TEXT,path TEXT);')
        report = self.root / 'native-report.json'
        report.write_text('{}')
        (self.root / 'dependency-graph/NATIVE_ACTIVE.json').write_text(json.dumps({
            'database': 'native.sqlite', 'sha256': sha(native),
            'report': 'native-report.json', 'report_sha256': sha(report)}))
        self.frozen = capture_inputs(self.root, None, [])
        self.prepare_images()
        self.snapshot = freeze_snapshot(self.root, self.output, self.frozen, [])

    def prepare_images(self):
        (self.output / 'IMAGES.json').write_text(json.dumps({
            'runner': {'id': 'sha256:' + 'a' * 64},
            'analysis': {'id': 'sha256:' + 'b' * 64}}))

    def test_snapshot_is_independent_and_revalidation_rejects_tampering(self):
        copy = self.output / 'snapshot/uc-library/src/input.cpp'
        self.assertNotEqual(self.source.stat().st_ino, copy.stat().st_ino)
        self.source.write_text('workspace edit\n')
        self.assertEqual(copy.read_text(), 'frozen original bytes\n')
        self.source.write_text('frozen original bytes\n')
        check_inputs(self.root, None, self.frozen)
        copy.write_text('snapshot altered\n')
        with self.assertRaisesRegex(ContextError, 'snapshot modified'):
            freeze_snapshot(self.root, self.output, self.frozen, [])

    def test_source_addition_and_removal_change_inventory_and_not_snapshot(self):
        added = self.source.parent / 'new.cpp'
        added.write_text('new file')
        self.assertFalse((self.output / 'snapshot/uc-library/src/new.cpp').exists())
        with self.assertRaisesRegex(ContextError, 'stale'):
            check_inputs(self.root, None, self.frozen)
        added.rename(added.with_suffix('.retained'))
        self.source.rename(self.source.with_suffix('.retained'))
        self.assertTrue((self.output / 'snapshot/uc-library/src/input.cpp').is_file())
        with self.assertRaisesRegex(ContextError, 'stale'):
            check_inputs(self.root, None, self.frozen)

    def test_registry_adapter_inventory_and_bytes_are_frozen(self):
        path = self.root / 'uc-library/tools/registry/adapter.py'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('original adapter')
        with self.assertRaisesRegex(ContextError, 'registry adapter inventory changed'):
            check_inputs(self.root, None, self.frozen)
        frozen = capture_inputs(self.root, None, [])
        path.write_text('changed adapter')
        with self.assertRaisesRegex(ContextError, 'Frozen batch input changed'):
            check_inputs(self.root, None, frozen)

    def test_endpoint_addition_and_change_are_frozen(self):
        endpoint = self.root / 'dependency-graph/state/memgraph-endpoint.json'
        endpoint.write_text(json.dumps({'uri': 'bolt://other-server:7687'}))
        with self.assertRaisesRegex(ContextError, 'endpoint changed'):
            check_inputs(self.root, None, self.frozen)
        frozen = capture_inputs(self.root, None, [])
        endpoint.write_text(json.dumps({'uri': 'bolt://changed-server:7687'}))
        with self.assertRaisesRegex(ContextError, 'endpoint changed'):
            check_inputs(self.root, None, frozen)

    def test_migration_pending_rejects_input_capture(self):
        endpoint = self.root / 'dependency-graph/state/memgraph-endpoint.json'
        endpoint.write_text(json.dumps({'status': 'migration_pending'}))
        with self.assertRaisesRegex(ContextError, 'migration pending'):
            capture_inputs(self.root, None, [])

    def test_partial_snapshot_evidence_is_archived_without_overwrite(self):
        # The manifest is a completion marker. A tree without it is retained.
        other = self.root / 'temp/recovery-work/partial'
        partial = other / 'snapshot'
        partial.mkdir(parents=True)
        retained = partial / 'old.log'
        retained.write_text('partial evidence')
        (other / 'IMAGES.json').write_bytes((self.output / 'IMAGES.json').read_bytes())
        freeze_snapshot(self.root, other, self.frozen, [])
        archives = list(other.glob('snapshot-interrupted-*'))
        self.assertEqual(len(archives), 1)
        self.assertEqual((archives[0] / 'old.log').read_text(), 'partial evidence')


class DockerEnvironmentTests(SnapshotTests):
    # Keep snapshots tests in the parent only; these methods exercise actual
    # Docker mounts and independent in-container flock ownership.
    test_snapshot_is_independent_and_revalidation_rejects_tampering = None
    test_source_addition_and_removal_change_inventory_and_not_snapshot = None
    test_partial_snapshot_evidence_is_archived_without_overwrite = None
    test_registry_adapter_inventory_and_bytes_are_frozen = None
    test_endpoint_addition_and_change_are_frozen = None
    test_migration_pending_rejects_input_capture = None

    @classmethod
    def setUpClass(cls):
        for image in ['dependency-graph-runner:01', 'dependency-graph-analysis:01']:
            result = docker('image', 'inspect', image)
            if result.returncode:
                raise unittest.SkipTest('Required local Docker image unavailable: ' + image)

    def prepare_images(self):
        self.environment = Environment(self.root, self.output)
        self.environment.pin_images()

    def setUp(self):
        super().setUp()
        self.addCleanup(self.environment.close)
        self.environment.start()

    def test_pinned_image_and_directory_overlay_keep_frozen_bytes(self):
        runner = self.environment.names['runner']
        observed = docker('inspect', '--format', '{{.Image}}', runner)
        self.assertEqual(observed.returncode, 0, observed.stderr)
        self.assertEqual(observed.stdout.strip(), self.environment.images['runner']['id'])
        self.source.write_text('transient workspace change\n')
        added = self.source.parent / 'new.cpp'
        added.write_text('must remain invisible')
        result = docker('exec', runner, 'python', '-c',
                        'import pathlib; p=pathlib.Path(' + repr(str(self.source)) + '); '
                        'print(p.read_text(),end=""); print((p.parent/"new.cpp").exists())')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'frozen original bytes\nFalse\n')
        self.source.write_text('frozen original bytes\n')
        check = docker('exec', runner, 'cat', str(self.source))
        self.assertEqual(check.stdout, 'frozen original bytes\n')

    def test_real_guard_uses_only_bound_snapshot_copy_fingerprints(self):
        script = self.output / 'guard-copy.py'
        code = ('import json,pathlib,sys\n'
                f'sys.path.insert(0,{str(self.root / "dependency-graph")!r})\n'
                'import context_runtime as runtime\n'
                f'root=pathlib.Path({str(self.root)!r})\n'
                'original=runtime.sha\n'
                f'source=root/{str(self.source.relative_to(self.root))!r}\n'
                'def checked(path):\n'
                '    if pathlib.Path(path).resolve()==source.resolve():\n'
                '        raise AssertionError("verified source copy was rehashed")\n'
                '    return original(path)\n'
                'runtime.sha=checked\n'
                'runtime.guard(root,json.loads((root/"dependency-graph/ACTIVE.json").read_text()))\n')
        script.write_text(code)
        self.source.write_text('outside editor changed live source\n')
        result = subprocess.run(['sg', 'docker', '-c', shlex.join(
            self.environment.builder_argv('runner', script, []))], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with self.assertRaisesRegex(ContextError, 'stale'):
            check_inputs(self.root, None, self.frozen)
        copied = self.output / 'snapshot/uc-library/src/input.cpp'
        copied.write_text('snapshot corruption\n')
        recheck = code.replace('runtime.sha=checked', '# use ordinary fresh hash fallback')
        result = docker('exec', self.environment.names['runner'], 'python3', '-c', recheck)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('stale', result.stderr)

    def test_builder_adds_script_parent_for_sibling_imports(self):
        directory = self.output / 'isolated-scripts'
        directory.mkdir()
        (directory / 'local_sibling.py').write_text('VALUE = 42\n')
        marker = self.output / 'imported-sibling'
        script = directory / 'entry.py'
        script.write_text('import local_sibling, pathlib\n'
                          f'pathlib.Path({str(marker)!r}).write_text(str(local_sibling.VALUE))\n')
        result = subprocess.run(['sg', 'docker', '-c', shlex.join(
            self.environment.builder_argv('runner', script, []))], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(marker.read_text(), '42')

    def test_live_previous_environment_blocks_resume(self):
        next_environment = Environment(self.root, self.output)
        with self.assertRaisesRegex(ContextError, 'live or uninspectable'):
            next_environment.check_previous()
        self.environment.close()
        self.environment.started.clear()
        next_environment.check_previous()

    def test_orphan_builder_keeps_shared_lock_after_docker_client_dies(self):
        marker = self.output / 'entered'
        release = self.output / 'release'
        script = self.output / 'lock-child.py'
        script.write_text('import pathlib,time\n'
                          f'pathlib.Path({str(marker)!r}).write_text("entered")\n'
                          f'while not pathlib.Path({str(release)!r}).exists(): time.sleep(.02)\n')
        argv = self.environment.builder_argv('runner', script, [])
        client = subprocess.Popen(['sg', 'docker', '-c', shlex.join(argv)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 5
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(marker.exists(), 'builder did not enter SH region')
            client.terminate()
            client.wait(timeout=5)
            with (self.root / 'dependency-graph/state/context.lock').open('a') as stream:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                release.write_text('exit')
                deadline = time.monotonic() + 5
                acquired = False
                while time.monotonic() < deadline:
                    try:
                        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        acquired = True
                        break
                    except BlockingIOError:
                        time.sleep(.02)
                self.assertTrue(acquired, 'orphan SH did not release after builder exit')
        finally:
            release.write_text('exit')
            if client.poll() is None:
                client.terminate()
                client.wait(timeout=5)
            client.communicate(timeout=5)


if __name__ == '__main__':
    unittest.main()
