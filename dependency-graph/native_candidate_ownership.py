"""Exact provenance for links created by the source/native lifecycle only."""
import base64
import zlib
import hashlib
import json
from context_runtime import ContextError

OWNER = 'source-native-lifecycle:v1'
BASIS = 'encoded name only; not ABI proof'
FIELDS = {'basis', 'candidate_owner', 'candidate_token', 'candidate_created_by'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(value):
    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    result = hashlib.sha256()
    for chunk in encoder.iterencode(value):
        result.update(chunk.encode())
    return result.hexdigest()


def canonical_matches(text, value):
    """Exact canonical byte spelling without materializing a second huge string."""
    if '"guard_codec"' in text:
        try:
            envelope = json.loads(text)
            if type(envelope) is dict and envelope.get('guard_codec') in ('owner-lists-zlib-base64-v1', 'owner-atoms-zlib-base64-v2'):
                from itertools import zip_longest
                encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=False)
                sentinel = object()
                return all(a == b for a, b in zip_longest(encoder.iterencode(unpack_guard(envelope)), encoder.iterencode(value), fillvalue=sentinel))
        except (ValueError, TypeError, KeyError, ContextError, zlib.error):
            return False
    offset = 0
    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    for chunk in encoder.iterencode(value):
        if not text.startswith(chunk, offset):
            return False
        offset += len(chunk)
    return offset == len(text)


def checkpoint_id(delta_sha, seal_sha, native_generation):
    return 'native-candidates:' + digest([delta_sha, seal_sha, native_generation])


def owned_properties(src, dst, native_generation, checkpoint):
    return {'basis': BASIS, 'candidate_owner': OWNER, 'candidate_created_by': checkpoint,
            'candidate_token': digest([src, dst, native_generation, checkpoint])}


def claims_ownership(props):
    return any(key.startswith('candidate_') for key in props)


def read_checkpoint(session, identity, include_seal=False):
    rows = list(session.run('MATCH(p:NativeCandidateCheckpoint {id:$id}) RETURN properties(p) AS p', id=identity))
    if len(rows) != 1:
        raise ContextError('Missing/duplicate native candidate ownership checkpoint')
    p = rows[0]['p']
    try:
        before, after = json.loads(p['before_json']), json.loads(p['after_json'])
        orphan_before, orphan_after = json.loads(p['orphan_before_json']), json.loads(p['orphan_after_json'])
        seal = unpack_guard(json.loads(p['seal_json']))
        seal_body = dict(seal); seal_hash = seal_body.pop('seal_sha256')
        valid = (p['contract_version'] == 1 and p['owner'] == OWNER and p['state'] in ('committed', 'verified') and
                 p['id'] == checkpoint_id(p['source_delta_sha256'], p['seal_sha256'], p['native_generation']) and
                 p['journal_sha256'] == digest({'before': before, 'after': after, 'orphan_before': orphan_before, 'orphan_after': orphan_after}) and
                 seal_hash == p['seal_sha256'] == digest(seal_body) and seal['native']['sha256'] == p['native_generation'] and
                 isinstance(before, list) and isinstance(after, list))
    except (KeyError, TypeError, ValueError) as error:
        raise ContextError('Invalid native candidate ownership journal') from error
    if not valid:
        raise ContextError('Invalid native candidate ownership journal')
    return (p, before, after, seal) if include_seal else (p, before, after)


class OwnershipVerification:
    """One session/transaction only. Never reuse across verification boundaries."""
    def __init__(self, session):
        self.session = session
        self.checkpoints = {}

    def add(self, identity, p, before, after, seal):
        # Only call with the result of read_checkpoint in this same operation.
        from collections import Counter
        compact = {key: value for key, value in p.items() if not key.endswith('_json')}
        self.checkpoints[identity] = (compact, seal['native_nodes'],
            Counter(canonical(row) for row in after),
            set(canonical(row) for row in before),
            {(row['src'], row['dst']) for row in seal['expected']})

    def read(self, identity):
        if identity not in self.checkpoints:
            self.add(identity, *read_checkpoint(self.session, identity, include_seal=True))
        return self.checkpoints[identity]


def validate_owned_edge(session, src, dst, props, native_generation, allow_committed=None, verification=None):
    """Reject invented/foreign ownership; only a certified creation is mutable."""
    if set(props) != FIELDS or props.get('candidate_owner') != OWNER:
        raise ContextError('Foreign or changed native candidate ownership properties')
    creator = props['candidate_created_by']
    if props != owned_properties(src, dst, native_generation, creator):
        raise ContextError('Invalid native candidate ownership token')
    verification = verification or OwnershipVerification(session)
    if verification.session is not session:
        raise ContextError('Ownership cache crossed session boundary')
    p, seal, after_counts, before_records, expected_pairs = verification.read(creator)
    if p['native_generation'] != native_generation:
        raise ContextError('Native candidate ownership generation requires migration')
    if p['state'] != 'verified' and creator != allow_committed:
        raise ContextError('Native candidate creation checkpoint remains unverified')
    record = {'src': src, 'dst': dst, 'properties': props}
    key = canonical(record)
    if after_counts[key] != 1 or key in before_records or (src, dst) not in expected_pairs:
        raise ContextError('Native candidate ownership certificate does not prove creation')


def _guard_bytes(value):
    return canonical(value).encode()


def pack_guard(seal):
    if type(seal) is not dict or seal.get('version') != 1:
        raise ContextError('Invalid logical guard')
    body = dict(seal)
    pool, indexes, sources = [], {}, []
    atoms, atom_indexes = [], {}
    for source in body['sources']:
        if type(source) is not dict or set(source) != {'owners', 'properties'}:
            raise ContextError('Unsupported guard source')
        owners = source['owners']
        if type(owners) is not list or any(type(v) is not str for v in owners):
            raise ContextError('Invalid guard owner list')
        key = tuple(owners)
        if key not in indexes:
            indexes[key] = len(pool)
            references = []
            for owner in owners:
                if owner not in atom_indexes:
                    atom_indexes[owner] = len(atoms)
                    atoms.append(owner)
                references.append(atom_indexes[owner])
            pool.append(references)
        sources.append({'properties': source['properties'], 'owners_ref': indexes[key]})
    body['sources'] = sources
    payload = _guard_bytes({'seal': body, 'owner_lists': pool, 'owner_atoms': atoms})
    logical = _guard_bytes(seal)
    return {'guard_codec': 'owner-atoms-zlib-base64-v2', 'logical_sha256': hashlib.sha256(logical).hexdigest(),
            'logical_bytes': len(logical), 'payload_bytes': len(payload),
            'payload_sha256': hashlib.sha256(payload).hexdigest(),
            'data': base64.b64encode(zlib.compress(payload, 6)).decode('ascii')}


def _unpack_guard(value):
    if type(value) is dict and value.get('version') == 1 and 'guard_codec' not in value:
        return value  # Legacy logical validation remains the caller's responsibility.
    fields = {'guard_codec', 'logical_sha256', 'logical_bytes', 'payload_bytes', 'payload_sha256', 'data'}
    if type(value) is not dict or set(value) != fields or value['guard_codec'] not in ('owner-lists-zlib-base64-v1', 'owner-atoms-zlib-base64-v2'):
        raise ContextError('Invalid guard codec envelope')
    for name in ('logical_bytes', 'payload_bytes'):
        if type(value[name]) is not int or not 0 <= value[name] <= 256 * 1024 * 1024:
            raise ContextError('Invalid guard size')
    for name in ('logical_sha256', 'payload_sha256'):
        if type(value[name]) is not str or len(value[name]) != 64 or any(c not in '0123456789abcdef' for c in value[name]):
            raise ContextError('Invalid guard digest')
    if type(value['data']) is not str:
        raise ContextError('Invalid guard bytes')
    compressed = base64.b64decode(value['data'], validate=True)
    decoder = zlib.decompressobj()
    payload = decoder.decompress(compressed, value['payload_bytes'] + 1)
    if len(payload) != value['payload_bytes'] or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ContextError('Truncated/oversized/trailing guard')
    if hashlib.sha256(payload).hexdigest() != value['payload_sha256']:
        raise ContextError('Guard payload digest mismatch')
    packed = json.loads(payload)
    atom_codec = value['guard_codec'] == 'owner-atoms-zlib-base64-v2'
    expected_fields = {'seal', 'owner_lists', 'owner_atoms'} if atom_codec else {'seal', 'owner_lists'}
    if type(packed) is not dict or set(packed) != expected_fields:
        raise ContextError('Invalid guard payload')
    pool, seal = packed['owner_lists'], packed['seal']
    atoms = packed.get('owner_atoms')
    if atom_codec:
        if (type(atoms) is not list or any(type(atom) is not str for atom in atoms) or
                type(pool) is not list or any(type(row) is not list or any(
                    type(ref) is not int or not 0 <= ref < len(atoms) for ref in row) for row in pool)):
            raise ContextError('Invalid guard owner atoms/references')
        atom_sizes = [len(_guard_bytes(atom)) for atom in atoms]
        owner_sizes = [2 + sum(atom_sizes[ref] for ref in row) + max(0, len(row) - 1) for row in pool]
    else:
        if type(pool) is not list or any(type(owners) is not list or any(type(v) is not str for v in owners) for owners in pool):
            raise ContextError('Invalid guard owner pool')
        owner_sizes = [len(_guard_bytes(owners)) for owners in pool]
    if type(seal) is not dict or seal.get('version') != 1 or type(seal.get('sources')) is not list:
        raise ContextError('Invalid logical guard')
    # Calculate exact expanded canonical length BEFORE copying shared lists.
    empty_sources = dict(seal); empty_sources['sources'] = []
    expanded_bytes = len(_guard_bytes(empty_sources))
    for index, source in enumerate(seal['sources']):
        if type(source) is not dict or set(source) != {'properties', 'owners_ref'}:
            raise ContextError('Invalid packed source')
        ref = source['owners_ref']
        if type(ref) is not int or not 0 <= ref < len(pool):
            raise ContextError('Invalid guard owner reference')
        expanded_bytes += len(_guard_bytes({'properties': source['properties'], 'owners': []})) - 2 + owner_sizes[ref] + bool(index)
        if expanded_bytes > value['logical_bytes']:
            raise ContextError('Guard expansion exceeds declared logical size')
    if expanded_bytes != value['logical_bytes']:
        raise ContextError('Guard expanded logical size mismatch')
    sources = []
    for source in seal['sources']:
        if type(source) is not dict or set(source) != {'properties', 'owners_ref'}:
            raise ContextError('Invalid packed source')
        ref = source['owners_ref']
        if type(ref) is not int or not 0 <= ref < len(pool):
            raise ContextError('Invalid guard owner reference')
        sources.append({'properties': source['properties'], 'owners': [atoms[index] for index in pool[ref]] if atom_codec else list(pool[ref])})
    seal['sources'] = sources
    logical = _guard_bytes(seal)
    if len(logical) != value['logical_bytes'] or hashlib.sha256(logical).hexdigest() != value['logical_sha256']:
        raise ContextError('Guard logical digest mismatch')
    return seal


def unpack_guard(value):
    try:
        return _unpack_guard(value)
    except (ValueError, TypeError, KeyError, zlib.error) as error:
        raise ContextError('Invalid compressed native candidate guard') from error
