"""Prospective execution-boundary coverage, separate from readiness and ranking.

ARM indirect sites are review candidates, not inferred call targets. Root must
classify local control flow versus actual providers with bound evidence.
"""
import contextlib
import contextvars
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path


# This scope caches only verified immutable file bytes and native identity lookup,
# never contract dispositions, live registry records, claims or decisions.
_BATCH = contextvars.ContextVar('execution_review_batch', default=None)


class _BatchValidation:
    def __init__(self, root):
        tools = str(Path(__file__).resolve().parents[1] / 'uc-library/tools')
        if tools not in sys.path:
            sys.path.insert(0, tools)
        from merge_readiness import ValidationCache
        self.root = Path(root).resolve()
        self.cache = ValidationCache()
        self.native = None
        self.identities = None

    def check(self):
        try:
            self.cache.unchanged()
        except (AssertionError, OSError) as error:
            raise ValueError('Batch execution evidence changed: ' + str(error)) from error

    def digest(self, path):
        self.check()
        try:
            result = self.cache.sha(path)
        except (AssertionError, OSError) as error:
            raise ValueError('Batch execution evidence changed: ' + str(error)) from error
        self.check()
        return result


@contextlib.contextmanager
def batch_validation(root):
    """One preparation's byte checks, with path/stat guards on use and exit."""
    session = _BatchValidation(root)
    token = _BATCH.set(session)
    try:
        yield session
        session.check()
    finally:
        _BATCH.reset(token)


def checked_digest(root, path):
    session = _BATCH.get()
    if session is None:
        digest = hashlib.sha256()
        with Path(path).open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        return digest.hexdigest()
    if Path(root).resolve() != session.root:
        raise ValueError('Batch execution evidence repository changed')
    return session.digest(path)


def check_batch_validation():
    session = _BATCH.get()
    if session is not None:
        session.check()


def _node_identities(connection):
    resolved = {}
    for row in connection.execute("SELECT id,json_extract(metadata,'$.elf_sha256'),json_extract(metadata,'$.mangled'),json_extract(metadata,'$.address'),json_extract(metadata,'$.size') FROM nodes"):
        resolved.setdefault(tuple(row)[1:], []).append(row[0])
    return resolved


def indirect_candidate(instruction):
    mnemonic = instruction['mnemonic'].lower()
    operands = instruction.get('operands', '').lower().strip()
    # ARM32 register branches, including conditional forms. bx lr is a return;
    # blx lr is still a call. Immediate branches are covered by native edges.
    if re.fullmatch(r'(?:bx|blx)(?:eq|ne|cs|hs|cc|lo|mi|pl|vs|vc|hi|ls|ge|lt|gt|le|al)?', mnemonic):
        return not operands.startswith('#') and not (mnemonic.startswith('bx') and operands in ('lr', 'r14'))
    if operands.split(',')[0].strip() in ('pc', 'r15'):
        return not (mnemonic.startswith('mov') and operands in ('pc, lr', 'r15, r14'))
    # Stack restores are returns; other multiple-load PC destinations require review.
    return (mnemonic.startswith('ldm') and re.search(r'\b(?:pc|r15)\b', operands)
            and not operands.startswith(('sp', 'r13')))


def collect(connection, targets, identities=None):
    observations = {}
    resolved = _node_identities(connection) if identities is None else identities
    for target in targets:
        matches = resolved.get((target['original_elf_sha256'], target['mangled'], target['address'], target['size']), [])
        if len(matches) != 1:
            raise ValueError('Exact native target/range required for execution review')
        source = matches[0]
        for edge in connection.execute("SELECT * FROM edges WHERE src=? AND kind IN ('ELF_CALLS','ELF_TAIL_BRANCH')", (source,)):
            value = {'source': source, 'kind': edge['kind'], 'site': edge['site'], 'destination': edge['dst']}
            key = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
            observations[key] = value
        row = connection.execute('SELECT payload FROM bodies WHERE id=?', (source,)).fetchone()
        if not row:
            raise ValueError('Native body required for execution review')
        for instruction in json.loads(row[0]).get('instructions', []):
            if indirect_candidate(instruction):
                value = {'source': source, 'kind': 'ARM_INDIRECT_REVIEW_CANDIDATE', 'site': instruction['address'], 'instruction': instruction}
                key = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
                observations[key] = value
    return observations


def validate(root, task, review):
    from reconstruction_contract import evidence
    root = Path(root)
    binding = review.get('execution_boundary_review')
    if not binding:
        raise ValueError('Execution-boundary review required before reconstruction')
    active = json.loads((root / 'dependency-graph/NATIVE_ACTIVE.json').read_text())
    database = (root / active['database']).resolve()
    if not database.is_relative_to(root.resolve()):
        raise ValueError('Native database outside repository')
    if binding.get('native_sha256') != active['sha256'] or checked_digest(root, root / active['database']) != active['sha256']:
        raise ValueError('Execution review native generation changed')
    with sqlite3.connect('file:' + str(database) + '?mode=ro', uri=True) as connection:
        connection.row_factory = sqlite3.Row
        session = _BATCH.get()
        if session is not None:
            session.check()
            if session.native is not None and session.native != active:
                raise ValueError('Execution review native generation changed within batch')
            if session.identities is None:
                session.identities = _node_identities(connection)
                session.native = active
            observed = collect(connection, task['targets'], session.identities)
            session.check()
        else:
            observed = collect(connection, task['targets'])
    entries = binding.get('observations', [])
    indexed = {entry['key']: entry for entry in entries}
    if len(indexed) != len(entries) or set(indexed) != set(observed):
        raise ValueError('Execution review must cover exact direct/tail edges and indirect candidates')
    for key, entry in indexed.items():
        evidence(root, entry.get('evidence', []))
        if not entry.get('reason'):
            raise ValueError('Execution boundary needs an explicit reason')
        if entry.get('kind') == 'local_control_flow':
            if observed[key]['kind'] != 'ARM_INDIRECT_REVIEW_CANDIDATE':
                raise ValueError('Proven execution edge cannot be dismissed as local control flow')
        elif entry.get('kind') == 'dependency':
            index = entry.get('dependency_index')
            if type(index) is not int or not 0 <= index < len(review.get('dependencies', [])):
                raise ValueError('Execution boundary needs an actual reviewed dependency')
        else:
            raise ValueError('Unclassified execution boundary')
    return {'observations': len(observed), 'indirect_candidates': sum(x['kind'] == 'ARM_INDIRECT_REVIEW_CANDIDATE' for x in observed.values()), 'semantic_or_readiness_proof': False}
