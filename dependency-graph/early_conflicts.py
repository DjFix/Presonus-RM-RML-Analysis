"""Pure pre-slice string-overlap guard; never grants dispatch or freshness.

Caller must validate each just-selected context and freeze all requests under the
ordinary input/content/freshness gates. No filesystem or graph access occurs here.
"""
import copy
import hashlib
import json
import re
import threading


class EarlyConflict(ValueError):
    def __init__(self, detail):
        self.detail = copy.deepcopy(detail)
        super().__init__(json.dumps(self.detail, sort_keys=True))


def _fail(reason, **fields):
    raise EarlyConflict(dict(reason=reason, dispatch_authorized=False,
                             independence_proven=False, **fields))


def _path(value):
    if (not isinstance(value, str) or not value or value.startswith('/') or '\\' in value
            or '\x00' in value or any(p in ('', '.', '..') for p in value.split('/'))):
        _fail('invalid_repository_relative_path', path=value)
    return value


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        _fail('invalid_sha256')
    return value


def _encoded(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    except (ValueError, TypeError):
        _fail('request_is_not_json')


class SelectedReadGuard:
    """Snapshot all planned writes, then check each selected packet before slice.

    Exact normalized string equality matches final check_groups/check_conflicts.
    This deliberately does not resolve aliases/hardlinks or translate canonical
    reads through source_proposal_map. The latter changes physical owned_files,
    not the selected canonical read paths. Final physical/freshness guards remain.

    request_sha256 binds actual request.json bytes, supplied by the caller, not a
    reserialization. A canonical JSON snapshot additionally rejects changed live
    request dictionaries supplied to check(). Other requests must stay frozen by
    the caller; an immutable copy prevents external mutation of this plan.
    """
    def __init__(self, requests, generation_sha256, request_sha256, groups=None):
        self._generation = _digest(generation_sha256)
        if not isinstance(requests, dict) or not requests:
            _fail('empty_or_invalid_requests')
        if not isinstance(request_sha256, dict) or set(request_sha256) != set(requests):
            _fail('request_hash_coverage_mismatch')
        self._owners, self._requests, self._hashes = {}, {}, {}
        self._tasks, self._works, self._writes = {}, {}, {}
        for packet, request in requests.items():
            _path(packet)
            if not isinstance(request, dict):
                _fail('invalid_request', packet=packet)
            task = request.get('task_id')
            if (not isinstance(task, str) or not task or packet.split('/')[-1] != task
                    or task in self._tasks.values()):
                _fail('foreign_or_duplicate_task', packet=packet)
            owned = request.get('owned_files')
            mode = request.get('mode')
            if mode not in ('audit', 'research', 'reconstruct'):
                _fail('invalid_request_mode', packet=packet)
            if not isinstance(owned, list) or (not owned and mode == 'reconstruct'):
                _fail('missing_owned_files', packet=packet)
            if owned and mode == 'audit':
                _fail('audit_must_be_read_only', packet=packet)
            writes = [_path(path) for path in owned]
            binding = request.get('work_binding')
            if not isinstance(binding, dict):
                _fail('missing_or_invalid_work_binding', packet=packet)
            work = binding.get('work_item_id')
            if not isinstance(work, str) or not work or work in self._works.values():
                _fail('missing_or_duplicate_unique_work', packet=packet)
            self._requests[packet] = hashlib.sha256(_encoded(request)).hexdigest()
            self._hashes[packet] = _digest(request_sha256[packet])
            self._tasks[packet], self._works[packet] = task, work
            self._writes[packet] = frozenset(writes)
        if groups is not None:
            if not isinstance(groups, list) or not groups:
                _fail('invalid_groups')
            names = set()
            for group in groups:
                if not isinstance(group, dict):
                    _fail('invalid_group')
                name = group.get('task_name')
                if not isinstance(name, str) or not re.fullmatch('[a-z][a-z0-9_]{0,63}', name) or name in names:
                    _fail('invalid_or_duplicate_owner')
                names.add(name)
                packets = group.get('packets')
                if not isinstance(packets, list) or not packets:
                    _fail('invalid_group_packets')
                for packet in packets:
                    _path(packet)
                    if packet not in requests or packet in self._owners:
                        _fail('foreign_or_duplicate_group_packet', packet=packet)
                    self._owners[packet] = name
            if set(self._owners) != set(requests):
                _fail('group_request_coverage_mismatch')
        else:
            self._owners = {packet: self._tasks[packet] for packet in requests}
        self._writers = {}
        for packet, writes in self._writes.items():
            for path in writes:
                self._writers.setdefault(path, []).append(packet)
        for path, packets in sorted(self._writers.items()):
            if len({self._owners[p] for p in packets}) > 1:
                _fail('planned_write_write_overlap', path=path, writer_packets=sorted(packets))
        # Only these result/duplicate controls mutate after setup; all access is locked.
        self._lock = threading.Lock()
        self._checked = set()
        self._failure = None

    @property
    def first_failure(self):
        with self._lock:
            return copy.deepcopy(self._failure)

    def check(self, packet, context, request):
        """Call immediately after current selection validation, before AST slice.

        Malformed data or overlap latches first failure. All later calls reject;
        the caller must stop/cancel queued builders, retain evidence and claims,
        and preserve the final unchanged dispatch checks. Already running work may
        overlap detection; this guard does not add a select-all barrier.
        """
        with self._lock:
            if self._failure is not None:
                raise EarlyConflict(self._failure)
            try:
                return self._check(packet, context, request)
            except EarlyConflict as error:
                self._failure = copy.deepcopy(error.detail)
                raise

    def _check(self, packet, context, request):
        _path(packet)
        if packet not in self._requests:
            _fail('unknown_packet', packet=packet)
        if packet in self._checked:
            _fail('duplicate_selected_packet', packet=packet)
        if hashlib.sha256(_encoded(request)).hexdigest() != self._requests[packet]:
            _fail('request_changed_after_planning', packet=packet)
        if not isinstance(context, dict):
            _fail('invalid_selected_context', packet=packet)
        if context.get('state') not in ('selected', 'dispatch_ready'):
            _fail('context_not_selected', packet=packet)
        if context.get('task_id') != self._tasks[packet]:
            _fail('foreign_context_task', packet=packet)
        if context.get('generation_sha256') != self._generation:
            _fail('mixed_or_unknown_generation', packet=packet)
        if context.get('task_sha256') != self._hashes[packet]:
            _fail('context_request_hash_mismatch', packet=packet)
        binding = context.get('work_binding')
        if not isinstance(binding, dict) or binding.get('work_item_id') != self._works[packet]:
            _fail('context_unique_work_mismatch', packet=packet)
        reads = context.get('selected_file_sha256')
        if not isinstance(reads, dict) or not reads:
            _fail('missing_selected_read_coverage', packet=packet)
        for path in reads:
            _path(path)
        for path, digest in sorted(reads.items()):
            _digest(digest)
            for writer in sorted(self._writers.get(path, [])):
                if self._owners[writer] != self._owners[packet]:
                    _fail('selected_read_planned_write_overlap', packet=packet,
                          reader_owner=self._owners[packet], writer_packet=writer,
                          writer_owner=self._owners[writer], read_path=path,
                          writer_path=path, generation_sha256=self._generation,
                          path_semantics='exact_normalized_strings_same_as_final_gate')
        self._checked.add(packet)
        return {'outcome': 'no_known_selected_overlap', 'packet': packet,
                'dispatch_authorized': False, 'independence_proven': False,
                'generation_sha256': self._generation,
                'scope': 'Supplied selected-read keys vs all frozen planned write strings only; caller freshness/content validation and final gate remain mandatory.'}
