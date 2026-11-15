"""Invocation-local native byte reuse must detect external writes and replacement."""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import context_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]


class HashReuseTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / 'temp/test-work/input-hashes'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'dependency-graph').mkdir()
        self.source = self.root / 'input.elf'
        self.source.write_bytes(b'original')
        self.db = self.root / 'native.sqlite'
        with sqlite3.connect(self.db) as c:
            c.execute('CREATE TABLE inputs(path)')
            c.execute('INSERT INTO inputs VALUES(?)', ('input.elf',))
        (self.root / 'report.json').write_text('{}')
        (self.root / 'dependency-graph/NATIVE_ACTIVE.json').write_text(json.dumps(
            {'database': 'native.sqlite', 'report': 'report.json'}))

    def test_hash_once_per_scope_and_rehash_at_exit(self):
        original = runtime._digest
        with patch.object(runtime, '_digest', wraps=original) as digest:
            with runtime.input_hash_session(self.root) as cache:
                expected = runtime.sha(self.source)
                for _ in range(10):
                    self.assertEqual(runtime.sha(self.source), expected)
                self.assertEqual(cache['hits'], 10)
                self.assertEqual(digest.call_count, 1)
            self.assertEqual(digest.call_count, 2)

    def test_same_size_write_with_restored_mtime_is_rejected(self):
        with self.assertRaisesRegex(runtime.ContextError, 'changed'):
            with runtime.input_hash_session(self.root):
                runtime.sha(self.source)
                stamp = self.source.stat()
                self.source.write_bytes(b'modified')
                os.utime(self.source, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
                runtime.sha(self.source)

    def test_replacement_is_rejected_at_barrier_without_next_use(self):
        with self.assertRaisesRegex(runtime.ContextError, 'changed'):
            with runtime.input_hash_session(self.root):
                runtime.sha(self.source)
                replacement = self.root / 'replacement'
                replacement.write_bytes(b'original')
                replacement.replace(self.source)

    def test_mutable_non_native_files_are_never_cached(self):
        path = self.root / 'claims.sqlite'
        path.write_bytes(b'one')
        with runtime.input_hash_session(self.root) as cache:
            first = runtime.sha(path)
            path.write_bytes(b'two')
            self.assertNotEqual(runtime.sha(path), first)
            self.assertFalse(cache['verified'])

    def test_pointer_change_is_rejected(self):
        with self.assertRaisesRegex(runtime.ContextError, 'pointer changed'):
            with runtime.input_hash_session(self.root):
                (self.root / 'dependency-graph/NATIVE_ACTIVE.json').write_text('{}')

    def test_scope_never_leaks_after_exception(self):
        with self.assertRaises(RuntimeError):
            with runtime.input_hash_session(self.root):
                runtime.sha(self.source)
                raise RuntimeError('interrupted')
        self.assertIsNone(runtime._INPUT_HASHES.get())


if __name__ == '__main__':
    unittest.main()
