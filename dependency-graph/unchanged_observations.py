"""Retain exact old capture identities only after fresh semantic equivalence.

This is not a GCC serial-ID migration: changed observations always take the normal
facts path. Receipts bind both captures, and no historical file is rewritten.
"""
import hashlib
import json
from pathlib import Path
import shlex

from code_identity import VERSION, normalize_ast


class ObservationEquivalence:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.cache = {}
        self.receipt = {'version': 1, 'eligible': [], 'rejected': [],
                        'scope': 'fresh compiler equivalence retaining old immutable fact/capture identities'}

    def sha(self, path):
        path = Path(path)
        stat = path.stat()
        signature = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        previous = self.cache.get(str(path))
        if previous and previous[0] == signature:
            return previous[1]
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        after = path.stat()
        if signature != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('Input changed during equivalence verification: ' + str(path))
        self.cache[str(path)] = (signature, digest)
        return digest

    def pair(self, row, ast_path, gcc_path, expected=None):
        ast_path, gcc_path = Path(ast_path), Path(gcc_path)
        if any(not path.resolve().is_relative_to(self.root) for path in (ast_path, gcc_path)):
            raise ValueError('Capture path escapes project')
        bindings = {'ast': str(ast_path), 'gcc': str(gcc_path),
                    'ast_sha256': self.sha(ast_path), 'gcc_sha256': self.sha(gcc_path)}
        if expected:
            for key in ('ast_sha256', 'gcc_sha256'):
                if expected.get(key) != bindings[key]:
                    raise ValueError('Old capture binding mismatch: ' + key)
        ast, gcc = json.loads(ast_path.read_text()), json.loads(gcc_path.read_text())
        if ast.get('passed') is not True or gcc.get('returncode') != 0:
            raise ValueError('Failed compiler capture')
        inputs = ast.get('input_sha256')
        source = str(Path(row['file']).resolve())
        if not isinstance(inputs, dict) or not inputs or source not in inputs:
            raise ValueError('Source/input binding absent')
        if gcc.get('source') != row['file'] or gcc.get('source_sha256') != inputs[source]:
            raise ValueError('GCC source binding differs')
        for value, digest in inputs.items():
            path = Path(value)
            if not path.is_absolute() or not path.resolve().is_relative_to(self.root) or self.sha(path) != digest:
                raise ValueError('Current project input differs: ' + value)
        if ast.get('source') not in (source, str(Path(source).relative_to(self.root))):
            raise ValueError('AST source differs')
        # Both compiler runs must implement the same actual command. Only exact
        # extractor-controlled output/dump paths are excluded from comparison.
        scratch, dump = Path(gcc['scratch']), Path(gcc['dump'])
        if any(not path.resolve().is_relative_to(self.root) for path in (scratch, dump)):
            raise ValueError('GCC capture scratch/dump escapes project')
        argv = list(row.get('arguments') or shlex.split(row['command']))
        argv[argv.index('-o') + 1] = str(scratch / 'unit.o')
        argv.append('-fdump-ipa-cgraph=' + str(dump))
        if gcc.get('argv') != argv or dump != scratch / 'unit.cgraph':
            raise ValueError('GCC actual replay command differs')
        if self.sha(dump) != gcc.get('dump_sha256'):
            raise ValueError('GCC dump hash differs')
        bindings.update(dump=str(dump), dump_sha256=gcc['dump_sha256'])
        recovery = ast.get('recovery')
        if ast.get('parse_clean') is not True and not isinstance(recovery, dict):
            raise ValueError('Unclean AST lacks recovery binding')
        if recovery:
            if recovery.get('gcc_validation') != str(gcc_path) or recovery.get('sha256') != bindings['gcc_sha256']:
                raise ValueError('AST recovery pair binding differs')
        for container, field, expected_hash in ((ast, 'gcc_sha256', bindings['gcc_sha256']),
                                                (gcc, 'ast_sha256', bindings['ast_sha256'])):
            if field in container and container[field] != expected_hash:
                raise ValueError('Additional capture pair binding differs')
        normalized, _ = normalize_ast(self.root, row, ast)
        normalized.pop('seconds', None)
        normalized.pop('gcc_sha256', None)
        if recovery:
            normalized['recovery'] = {key: value for key, value in recovery.items()
                                      if key not in ('gcc_validation', 'sha256')}
        semantic_gcc = {key: value for key, value in gcc.items()
                        if key not in ('argv', 'seconds', 'dump', 'scratch', 'dump_sha256', 'ast_sha256')}
        if self.sha(ast_path) != bindings['ast_sha256'] or self.sha(gcc_path) != bindings['gcc_sha256']:
            raise ValueError('Capture changed during equivalence verification')
        return normalized, semantic_gcc, bindings

    def verify_retained(self):
        # Recheck every file used by successful equivalence immediately before
        # final publication sealing; stat-keyed cache rehashes changed files.
        for entry in self.receipt['eligible']:
            for capture in (entry['retained'], entry['fresh']):
                for key in ('ast', 'gcc', 'dump'):
                    if self.sha(capture[key]) != capture[key + '_sha256']:
                        raise ValueError('Equivalent capture changed before publication: ' + capture[key])

    def check(self, owner, row, previous, ast_path, gcc_path):
        try:
            if not previous or previous.get('command') != row:
                raise ValueError('New owner or changed compile command')
            old_ast, old_gcc, old_binding = self.pair(row, previous['ast'], previous['gcc'], previous)
            new_ast, new_gcc, new_binding = self.pair(row, ast_path, gcc_path)
            if previous.get('inputs') != old_ast.get('input_sha256') or old_ast.get('input_sha256') != new_ast.get('input_sha256'):
                raise ValueError('Full project input hashes differ')
            if previous.get('external_inputs') != old_ast.get('external_inputs') or old_ast.get('external_inputs') != new_ast.get('external_inputs'):
                raise ValueError('External input inventory differs')
            if old_ast != new_ast:
                raise ValueError('Normalized AST semantic fields differ')
            if old_gcc != new_gcc:
                raise ValueError('GCC semantic fields differ')
            self.receipt['eligible'].append({'owner': owner, 'retained': old_binding, 'fresh': new_binding,
                                              'identity_version': VERSION})
            return True
        except (KeyError, ValueError, TypeError, OSError) as exc:
            self.receipt['rejected'].append({'owner': owner, 'reason': str(exc)})
            return False
