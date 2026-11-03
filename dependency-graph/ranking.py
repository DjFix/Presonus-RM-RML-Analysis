"""Conservative derived work ranking; never writes canonical registry or claims.

Static facts and scoped requirements are separate from dispatch state. Every
event has an idempotency receipt. Updates visit only affected reverse consumers;
requirements are explicit attestations, so cycles cannot satisfy themselves.
"""
import argparse
import bisect
import collections
import hashlib
import json
import pathlib
import sqlite3
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = pathlib.Path(__file__).with_name('ranking_policy.json')


def packed(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def ro(path):
    c = sqlite3.connect(pathlib.Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    c.row_factory = sqlite3.Row
    return c


def feature(value, state='known', scope='static observation'):
    return {'value': value, 'state': state, 'scope': scope}


def canonical_observation(explicit_db=None):
    """Use the shared schema-checked snapshot without expanding proof documents."""
    sys.path.insert(0, str(ROOT / 'uc-library/tools/registry'))
    from adapter import snapshot
    with snapshot(ROOT / 'uc-library', db=explicit_db) as observed:
        records = [tuple(row) for row in observed.c.execute('SELECT elf,mangled,status,proof,metadata FROM records ORDER BY elf,mangled')]
        states = {(row[0], row[1]): row[2] for row in records}
        return states, hashlib.sha256(packed(records).encode()).hexdigest(), observed.provenance()


def scc(graph):
    """Iterative Kosaraju, including isolated vertices and self cycles."""
    reverse = {v: set() for v in graph}
    for v, children in graph.items():
        for w in children:
            reverse.setdefault(w, set()).add(v)
    visited, order = set(), []
    for v in sorted(reverse):
        stack = [(v, False)]
        while stack:
            w, done = stack.pop()
            if done:
                order.append(w)
            elif w not in visited:
                visited.add(w)
                stack.append((w, True))
                stack.extend((x, False) for x in sorted(graph.get(w, ()), reverse=True) if x not in visited)
    visited, groups = set(), []
    for v in reversed(order):
        if v in visited:
            continue
        group, stack = [], [v]
        visited.add(v)
        while stack:
            w = stack.pop()
            group.append(w)
            for x in reverse[w]:
                if x not in visited:
                    visited.add(x)
                    stack.append(x)
        groups.append(sorted(group))
    return groups


def cfg(body):
    """Decode retained, hash-bound instruction bytes, never literal-pool bytes.

    This is a bounded static CFG. Unhandled PC writes/indirect sites make it
    partial. Conditional ARM non-branch instructions are separately counted.
    """
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB, CS_GRP_JUMP, CS_GRP_CALL
    from capstone.arm import ARM_OP_IMM, ARM_OP_MEM, ARM_REG_PC, ARM_REG_LR, ARM_CC_AL, ARM_CC_INVALID
    decoders = {n: Cs(CS_ARCH_ARM, m) for n, m in [(4, CS_MODE_ARM), (2, CS_MODE_THUMB)]}
    for d in decoders.values():
        d.detail = True
    instructions = body.get('instructions', [])
    decoded = []
    graph, leaders, unresolved, conditional, back = {}, set(), [], 0, 0
    reads, writes = [], []
    addresses = {r['address'] for r in instructions}
    if instructions:
        leaders.add(instructions[0]['address'])
    for index, row in enumerate(instructions):
        raw = bytes.fromhex(row['bytes'])
        # A four-byte Thumb-2 instruction is explicitly unknown without mode.
        # Native producer currently emits ARM for these firmware ranges; verify
        # decoded text against retained mnemonic before accepting the observation.
        candidates = []
        for d in decoders.values():
            ins = next(d.disasm(raw, row['address'], count=1), None)
            if ins and ins.size == len(raw) and ins.mnemonic == row['mnemonic'] and ins.op_str == row['operands']:
                candidates.append(ins)
        if len(candidates) != 1:
            unresolved.append({'site': row['address'], 'reason': 'ambiguous decode mode'})
            continue
        ins = candidates[0]
        decoded.append(ins)
        address = ins.address
        next_address = instructions[index + 1]['address'] if index + 1 < len(instructions) else None
        contiguous = next_address == address + ins.size
        cond = ins.cc not in (ARM_CC_AL, ARM_CC_INVALID)
        jump, call = ins.group(CS_GRP_JUMP), ins.group(CS_GRP_CALL)
        _, changed = ins.regs_access()
        pc_write = ARM_REG_PC in changed
        ret = (ins.mnemonic.split('.')[0] in ('bx', 'bxeq', 'bxne') and ins.operands and ins.operands[0].reg == ARM_REG_LR)
        ret = ret or (ins.mnemonic.startswith(('pop', 'ldm')) and 'pc' in ins.op_str)
        target = ins.operands[0].imm & ~1 if jump and not call and ins.operands and ins.operands[0].type == ARM_OP_IMM else None
        edges = set()
        if jump and not call:
            if target in addresses:
                edges.add(target)
                leaders.add(target)
                back += target <= address
            elif target is not None:
                unresolved.append({'site': address, 'reason': 'external branch candidate', 'target': target})
            elif not ret:
                unresolved.append({'site': address, 'reason': 'indirect jump'})
            if cond and contiguous:
                edges.add(next_address)
            conditional += int(cond)
            if next_address is not None:
                leaders.add(next_address)
        elif pc_write and not call:
            if not ret:
                unresolved.append({'site': address, 'reason': 'unresolved PC write'})
            if cond and contiguous:
                edges.add(next_address)
            if next_address is not None:
                leaders.add(next_address)
        elif contiguous:
            edges.add(next_address)
        elif next_address is not None:
            unresolved.append({'site': address, 'reason': 'fallthrough into undecoded region'})
        elif not ret and not (jump and not call) and not pc_write:
            unresolved.append({'site': address, 'reason': 'fallthrough beyond bounded body'})
        if call and not (ins.operands and ins.operands[0].type == ARM_OP_IMM):
            unresolved.append({'site': address, 'reason': 'indirect call'})
        graph[address] = edges
        for operand in ins.operands:
            if operand.type == ARM_OP_MEM and operand.mem.base != ARM_REG_PC:
                obs = {'site': address, 'base': ins.reg_name(operand.mem.base),
                       'index': ins.reg_name(operand.mem.index), 'offset': operand.mem.disp,
                       'instruction': ins.mnemonic, 'width': 1 if ins.mnemonic.startswith(('ldrb', 'strb', 'ldrsb')) else 2 if ins.mnemonic.startswith(('ldrh', 'strh', 'ldrsh')) else 8 if ins.mnemonic.startswith(('ldrd', 'strd')) else 4 if ins.mnemonic.startswith(('ldr', 'str')) else None}
                (writes if ins.mnemonic.startswith(('str', 'stm')) else reads).append(obs)
    cycles = [g for g in scc(graph) if len(g) > 1 or (g and g[0] in graph.get(g[0], ()))]
    # Deliberately local provenance: do not merge paths or preserve values across
    # calls. r0 origin means only entry-register identity, never a class field.
    origins = {'r0': {'kind': 'entry_r0', 'offset': 0}}
    literal_values = body.get('literal_values', {})
    provenance, absolute_accesses = [], []
    by_site = collections.defaultdict(list)
    for obs in reads+writes:
        by_site[obs['site']].append(obs)
    from capstone.arm import ARM_OP_REG
    for index, ins in enumerate(decoded):
        if index and (ins.address in leaders or ins.address != decoded[index-1].address+decoded[index-1].size):
            origins = {}
        for obs in by_site[ins.address]:
            origin = origins.get(obs['base'])
            obs['base_origin'] = origin
            provenance.append({'site': ins.address, 'base': obs['base'], 'origin': origin, 'scope': 'within bounded basic block only'})
            if origin and origin['kind'] == 'constant' and not obs['index'] and obs['width']:
                absolute_accesses.append({'site': ins.address, 'address': (origin['value']+obs['offset']) & 0xffffffff,
                                          'width': obs['width'], 'instruction': ins.mnemonic,
                                          'origin_evidence': origin, 'scope': 'static instruction-derived address; execution not observed'})
        _, changed = ins.regs_access()
        previous = dict(origins)
        for reg in changed:
            origins.pop(ins.reg_name(reg), None)
        if ins.group(CS_GRP_CALL):
            origins = {}
            continue
        ops = ins.operands
        if ins.cc not in (ARM_CC_AL, ARM_CC_INVALID) or not ops or ops[0].type != ARM_OP_REG:
            continue
        destination = ins.reg_name(ops[0].reg)
        literal = literal_values.get(str(ins.address))
        if literal and ins.mnemonic == 'ldr':
            origins[destination] = {'kind': 'constant', 'value': literal['value'], 'literal_cell': literal['cell_address'], 'load_site': ins.address}
        elif ins.mnemonic in ('mov', 'movs') and len(ops) == 2:
            if ops[1].type == ARM_OP_REG and not ops[1].shift.type:
                value = previous.get(ins.reg_name(ops[1].reg))
                if value:
                    origins[destination] = dict(value)
            elif ops[1].type == ARM_OP_IMM:
                origins[destination] = {'kind': 'constant', 'value': ops[1].imm & 0xffffffff, 'immediate_site': ins.address}
        elif ins.mnemonic in ('add', 'sub') and len(ops) == 3 and ops[1].type == ARM_OP_REG and ops[2].type == ARM_OP_IMM:
            value = previous.get(ins.reg_name(ops[1].reg))
            if value and not ops[2].shift.type:
                updated = dict(value); delta = ops[2].imm * (1 if ins.mnemonic == 'add' else -1)
                key = 'value' if value['kind'] == 'constant' else 'offset'
                updated[key] = (updated[key]+delta) & 0xffffffff
                origins[destination] = updated
    return {'instruction_count': feature(len(instructions)), 'basic_blocks': feature(len(leaders), 'partial' if unresolved else 'known'),
            'conditional_branches': feature(conditional), 'back_edges': feature(back), 'cyclic_scc': feature(len(cycles), 'partial' if unresolved else 'known'),
            'unresolved_sites': feature(unresolved), 'cfg_complete': feature(bool(instructions) and not unresolved),
            'memory_reads': feature(reads, scope='explicit memory operands; no class-field identity'),
            'memory_writes': feature(writes, scope='explicit memory operands; no class-field identity'),
            'register_provenance': feature(provenance, 'partial' if any(x['origin'] is None for x in provenance) else 'known', 'bounded block-local origins only'),
            'proven_data_accesses': feature(absolute_accesses, scope='known constant base consumed by a memory instruction; no inferred C++ representation'),
            'relocations': feature(None, 'unknown')}


SCHEMA = '''
CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE original_catalog(id TEXT PRIMARY KEY,identity TEXT NOT NULL,work_memberships TEXT NOT NULL,exclusion TEXT);
CREATE TABLE native_features(native_id TEXT PRIMARY KEY,features TEXT NOT NULL,body_hash TEXT);
CREATE TABLE items(id TEXT PRIMARY KEY,kind TEXT NOT NULL,original_kind TEXT NOT NULL,namespace TEXT NOT NULL,identities TEXT NOT NULL,features TEXT NOT NULL,feature_hash TEXT NOT NULL);
CREATE TABLE states(id TEXT PRIMARY KEY REFERENCES items,canonical TEXT NOT NULL,claimed INTEGER NOT NULL,revision TEXT NOT NULL);
CREATE TABLE requirements(id TEXT PRIMARY KEY,consumer TEXT NOT NULL REFERENCES items,target TEXT NOT NULL,scope TEXT NOT NULL,evidence TEXT NOT NULL,satisfied INTEGER NOT NULL DEFAULT 0);
CREATE INDEX reverse_requirements ON requirements(target,consumer);
CREATE INDEX consumer_requirements ON requirements(consumer,satisfied);
CREATE TABLE requirement_origins(id TEXT PRIMARY KEY,evidence TEXT NOT NULL);
CREATE TABLE evaluations(id TEXT PRIMARY KEY REFERENCES items,queue TEXT NOT NULL,rank TEXT NOT NULL,reasons TEXT NOT NULL,potential INTEGER NOT NULL,sufficient INTEGER NOT NULL,binding TEXT NOT NULL);
CREATE TABLE events(id TEXT PRIMARY KEY,payload TEXT NOT NULL,receipt TEXT NOT NULL);
CREATE TRIGGER event_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'append only'); END;
CREATE TRIGGER event_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'append only'); END;
'''


def grade(f, thresholds):
    if f['state'] != 'known' or f['value'] is None:
        return 4
    return next((i for i, n in enumerate(thresholds) if f['value'] <= n), 3)


def evaluate(c, work_id, policy):
    item = c.execute('SELECT * FROM items WHERE id=?', (work_id,)).fetchone()
    state = c.execute('SELECT * FROM states WHERE id=?', (work_id,)).fetchone()
    f = json.loads(item['features'])
    reqs = list(c.execute('SELECT * FROM requirements WHERE consumer=? ORDER BY id', (work_id,)))
    essential = {'native_body', 'callee_context', 'data_context', 'extent', 'representation', 'consumer_binding', 'initialization_effects'}
    unmet = sum(not r['satisfied'] for r in reqs if r['scope'] in essential)
    reasons = []
    if state['claimed']:
        queue = 'claimed'
    elif state['canonical'] != 'remaining':
        queue = 'completed' if state['canonical'] in ('completed', 'ready', 'pending') else 'research_required'
        reasons.append('Existing result/status is routing only; no dependency satisfaction inferred: ' + state['canonical'])
    elif item['original_kind'].startswith('provider'):
        queue = 'provider_work'
    elif item['original_kind'] != 'reconstruct' or unmet:
        queue = 'research_required'
    elif item['kind'] == 'data_interpretation' or not f['cfg_complete']['value']:
        queue = 'research_required'
    else:
        queue = 'reconstruction_eligible'
    if unmet:
        reasons.append(f'{unmet} essential scoped requirements unresolved')
    uncertainty = 4 if (item['kind'] == 'data_interpretation' or not f.get('cfg_complete', {}).get('value')
                        or f.get('original_declaration', {}).get('state') == 'unknown') else 1
    reasons.append('Original declaration/layout unresolved; bounded source port only')
    if item['kind'] == 'data_interpretation':
        semantic = 4
    else:
        semantic = max(grade(f.get(name, feature(None, 'unknown')), policy['grades'][name]) for name in ('instruction_count', 'conditional_branches', 'basic_blocks'))
        if f.get('cyclic_scc', {}).get('value'):
            semantic = max(semantic, 2)
    dependencies = len({r['target'] for r in reqs if r['scope'] not in ('native_body', 'extent')})
    context = grade(feature(dependencies), policy['grades']['required_dependencies'])
    affected = {}
    for r in c.execute('SELECT * FROM requirements WHERE target=? AND satisfied=0', (work_id,)):
        other = c.execute('SELECT * FROM states WHERE id=?', (r['consumer'],)).fetchone()
        if r['consumer'] != work_id and other and other['canonical'] == 'remaining' and not other['claimed']:
            affected.setdefault(r['consumer'], []).append(r)
    # Potential help counts exact remaining consumer work, not aliases/sites.
    # Sufficiency is computed only if *all* unmet scopes are provided by this item.
    sufficient = sum(all(r['target'] == work_id for r in c.execute('SELECT target FROM requirements WHERE consumer=? AND satisfied=0', (v,))) for v in affected)
    helped = 0
    for consumer in affected:
        other = c.execute('SELECT features,original_kind FROM items WHERE id=?', (consumer,)).fetchone()
        of = json.loads(other['features'])
        if (consumer != work_id and other['original_kind'] == 'reconstruct' and of.get('cfg_complete', {}).get('value')
                and all(r['target'] == work_id for r in c.execute('SELECT target FROM requirements WHERE consumer=? AND satisfied=0', (consumer,)))):
            helped += 1
    rank = [unmet, uncertainty, semantic, context, dependencies, -helped, work_id]
    binding = {'feature_hash': item['feature_hash'], 'state_revision': state['revision'], 'policy': policy['version'],
               'requirements_hash': hashlib.sha256(packed([dict(r) for r in reqs]).encode()).hexdigest()}
    provenance = c.execute("SELECT value FROM meta WHERE key='provenance'").fetchone()
    binding['provenance_hash'] = hashlib.sha256(provenance[0].encode()).hexdigest() if provenance else None
    return (work_id, queue, packed(rank), packed(reasons), len(affected), sufficient, packed(binding))


def reevaluate(c, seeds=None):
    policy = json.loads(c.execute("SELECT value FROM meta WHERE key='policy'").fetchone()[0])
    if seeds is None:
        ids = {r[0] for r in c.execute('SELECT id FROM items')}
    else:
        ids = set(seeds)
        # Only a scoped requirement event can propagate. Re-evaluation is pure:
        # it never marks another requirement satisfied, including inside SCCs.
        ids.update(r[0] for v in seeds for r in c.execute('SELECT consumer FROM requirements WHERE target=?', (v,)))
        # A consumer claim/completion changes the help count of its suppliers.
        ids.update(r[0] for v in seeds for r in c.execute('SELECT target FROM requirements WHERE consumer=? AND target IN (SELECT id FROM items)', (v,)))
    changed = []
    for v in sorted(ids):
        value = evaluate(c, v, policy)
        old = c.execute('SELECT * FROM evaluations WHERE id=?', (v,)).fetchone()
        if old is None or tuple(old) != value:
            c.execute('INSERT OR REPLACE INTO evaluations VALUES(?,?,?,?,?,?,?)', value)
            changed.append(v)
    return {'visited': len(ids), 'changed': changed}


def event(c, payload):
    encoded = packed(payload)
    previous = c.execute('SELECT payload,receipt FROM events WHERE id=?', (payload['id'],)).fetchone()
    if previous:
        if previous['payload'] != encoded:
            raise ValueError('event id reused with changed payload')
        return json.loads(previous['receipt'])
    with c:
        seeds = set()
        for change in payload['changes']:
            v = change['item']
            row = c.execute('SELECT * FROM states WHERE id=?', (v,)).fetchone()
            if not row or row['revision'] != change['expected_revision']:
                raise ValueError('stale item/revision')
            if change.get('canonical', row['canonical']) not in ('remaining', 'completed', 'ready', 'pending', 'existing_result'):
                raise ValueError('unsupported canonical routing state')
            if change.get('claimed', row['claimed']) not in (0, 1):
                raise ValueError('claim observation must be boolean')
            c.execute('UPDATE states SET canonical=?,claimed=?,revision=? WHERE id=?',
                      (change.get('canonical', row['canonical']), change.get('claimed', row['claimed']), payload['id'], v))
            seeds.add(v)
            for attestation in change.get('requirements', []):
                req = c.execute('SELECT * FROM requirements WHERE id=?', (attestation['id'],)).fetchone()
                if not req or req['target'] != v:
                    raise ValueError('scope attestation must name exact target and requirement')
                if not isinstance(attestation['satisfied'], bool):
                    raise ValueError('satisfaction must be a boolean')
                evidence = attestation['evidence']
                path = ROOT / evidence['path']
                if not path.resolve().is_relative_to(ROOT) or digest(path) != evidence['sha256']:
                    raise ValueError('scope evidence changed or outside checkout')
                if not evidence.get('domain'):
                    raise ValueError('nonempty scope domain required')
                c.execute('UPDATE requirements SET satisfied=?,evidence=? WHERE id=?',
                          (bool(attestation['satisfied']), packed(evidence), req['id']))
                seeds.add(req['consumer'])
        receipt = reevaluate(c, seeds)
        c.execute('INSERT INTO events VALUES(?,?,?)', (payload['id'], encoded, packed(receipt)))
    return receipt


def build(out, reuse_db=None, registry_db=None):
    start = time.monotonic()
    ccl = ROOT / 'third_party/ccl-framework'
    pin = 'e8cbdea4a4a20e15111f5a690798a259c0374b31'
    if subprocess.check_output(['git', '-C', str(ccl), 'rev-parse', 'HEAD'], text=True).strip() != pin:
        raise ValueError('pinned CCL checkout changed')
    if subprocess.check_output(['git', '-C', str(ccl), 'rev-list', '--max-parents=0', 'HEAD'], text=True).strip() != pin:
        raise ValueError('CCL earliest fetched root differs')
    pointers = {name: json.loads((ROOT / 'dependency-graph' / (name + '_ACTIVE.json')).read_text()) for name in ('NATIVE', 'DEDUP')}
    native_path = ROOT / pointers['NATIVE']['database']
    if digest(native_path) != pointers['NATIVE']['sha256']:
        raise ValueError('native index corruption')
    d = ro(ROOT / pointers['DEDUP']['database'])
    n = ro(native_path)
    d.execute('BEGIN'); n.execute('BEGIN')
    meta = {r['key']: json.loads(r['value']) for r in d.execute('SELECT * FROM index_meta')}
    if not meta['complete'] or meta['generation'] != pointers['DEDUP']['generation'] or meta['native_generation'] != pointers['NATIVE']['sha256']:
        raise ValueError('mixed or incomplete generations')
    # Verify all retained immutable inputs, including original ELF and provider.
    for r in n.execute('SELECT * FROM inputs'):
        if digest(ROOT / r['path']) != r['sha256']:
            raise ValueError('native input changed: ' + r['path'])
    for r in d.execute('SELECT * FROM payload_contents'):
        path = ROOT / r['object_path']
        if path.stat().st_size != r['size'] or digest(path) != r['content_sha256']:
            raise ValueError('payload corruption: ' + r['id'])
    canonical, registry_observation, registry_snapshot = canonical_observation(registry_db)
    out.mkdir(parents=True, exist_ok=False)
    c = sqlite3.connect(out / 'ranking.sqlite'); c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    policy = json.loads(POLICY.read_text())
    provenance = {'native': pointers['NATIVE'], 'dedup': pointers['DEDUP'], 'source': json.loads((ROOT / 'dependency-graph/ACTIVE.json').read_text()),
                  'registry_observation': registry_observation, 'registry_snapshot': registry_snapshot,
                  'explicit_registry_database': bool(registry_db), 'producer': digest(__file__), 'policy_sha256': digest(POLICY)}
    for key, val in {'policy': policy, 'provenance': provenance}.items():
        c.execute('INSERT INTO meta VALUES(?,?)', (key, packed(val)))
    occurrences = {r['id']: dict(r) for r in d.execute('SELECT * FROM symbol_occurrences')}
    ranges = {r['id']: dict(r) for r in d.execute('SELECT * FROM binary_ranges')}
    releases = collections.defaultdict(list)
    for r in d.execute('SELECT * FROM binary_releases'):
        releases[r['elf_sha256']].append(dict(r))
    bodies = {r['id']: json.loads(r['payload']) for r in n.execute('SELECT * FROM bodies')}
    for edge in n.execute("SELECT src,site,metadata FROM edges WHERE kind='ELF_LITERAL_CELL'"):
        if edge['src'] in bodies:
            bodies[edge['src']].setdefault('literal_values', {})[str(edge['site'])] = json.loads(edge['metadata'])
    memberships = collections.defaultdict(list)
    original_memberships = collections.defaultdict(list)
    for r in d.execute('SELECT * FROM work_item_members'):
        memberships[r['work_item_id']].append(r['occurrence_id'])
        original_memberships[r['occurrence_id']].append(r['work_item_id'])
    def identity_for(oid):
        identity = dict(occurrences[oid]); identity['releases'] = releases[identity['elf_sha256']]
        identity.pop('provider_binding', None)
        identity['provider_binding_ref'] = {'database': pointers['DEDUP']['database'], 'occurrence': oid}
        identity['range'] = ranges.get(identity['range_id'])
        return identity
    for oid, original in occurrences.items():
        exclusion = None if original_memberships[oid] else ('catalog metadata/mapping symbol; not a reconstruction function' if original['symbol_kind'] in ('STT_FILE', 'STT_NOTYPE') else 'No current unique-work job; extent/interpretation/binding remains separately unresolved, not completed')
        c.execute('INSERT INTO original_catalog VALUES(?,?,?,?)', (oid, packed(identity_for(oid)), packed(sorted(original_memberships[oid])), exclusion))
    native_to_work = collections.defaultdict(set)
    active = {r[0] for r in d.execute("SELECT work_item_id FROM work_claims WHERE state='active'")}
    works = list(d.execute('SELECT * FROM reconstruction_work_items ORDER BY id'))
    for w in works:
        for oid in memberships[w['id']]:
            native_to_work[occurrences[oid]['native_id']].add(w['id'])
    cfg_cache, distributions = {}, collections.defaultdict(list)
    reuse_observation = None
    if reuse_db:
        previous = ro(reuse_db)
        prior = json.loads(previous.execute("SELECT value FROM meta WHERE key='provenance'").fetchone()[0])
        if (prior['native'] != provenance['native'] or prior['producer'] != provenance['producer']
                or static_digest(previous) != previous.execute("SELECT value FROM meta WHERE key='static_digest'").fetchone()[0]):
            raise ValueError('static reuse input/producer mismatch or corruption')
        marker = previous.execute("SELECT value FROM meta WHERE key='complete'").fetchone()
        if not marker or marker[0] != 'true':
            raise ValueError('cannot reuse incomplete index')
        for row in previous.execute('SELECT * FROM native_features'):
            if bodies.get(row['native_id'], {}).get('bytes_sha256') != row['body_hash']:
                raise ValueError('static native body changed')
            cfg_cache[row['native_id']] = json.loads(row['features'])
        reuse_observation = {'database': str(reuse_db), 'native_features_reused': len(cfg_cache), 'producer': prior['producer'],
                            'scope': 'static native observations only; no readiness, record, source, rank or scope-proof reuse'}
    for w in works:
        ids = []
        for oid in sorted(memberships[w['id']]):
            identity = identity_for(oid)
            ids.append(identity)
        if not ids:
            raise ValueError('work without original members: ' + w['id'])
        rep = occurrences[w['representative']] if w['representative'] else ids[0]
        body = bodies.get(rep['native_id'], {})
        data = rep['symbol_kind'] != 'STT_FUNC'
        initializer = rep['original_mangled'].startswith(('_GLOBAL__I_', '_GLOBAL__sub_I_', '__static_initialization_and_destruction_')) or body.get('section') == '.init'
        subject_kind = 'data' if data else 'initializer' if initializer else 'function'
        kind = {'extract_payload': 'payload_extraction', 'establish_extent': 'extent_research',
                'resolve_equivalence': 'equivalence_research', 'review_existing_result': 'review_existing_result',
                'provider_adapter': 'provider_binding', 'provider_binding': 'provider_binding'}.get(w['work_kind'],
                'data_interpretation' if data else 'initializer_reconstruction' if initializer else 'function_reconstruction')
        f = {'byte_count': feature(body.get('size'), 'known' if body.get('size') else 'unknown'),
             'subject_kind': feature(subject_kind),
             'representation': feature(None, 'unknown'), 'original_declaration': feature(None, 'unknown'),
             'body_hash': feature(body.get('bytes_sha256'), 'known' if body.get('bytes_sha256') else 'unknown'),
             'storage': feature(body.get('storage'), 'known' if body else 'unknown'),
             'width': feature(None, 'unknown'), 'count': feature(None, 'unknown'),
             'encoding': feature(None, 'unknown'), 'alignment': feature(None, 'unknown'),
             'initialization_order': feature(None, 'unknown'), 'lifetime': feature(None, 'unknown'),
             'state_provenance': feature(None, 'unknown')}
        if not data and rep['strategy'] != 'external_source' and body.get('instructions'):
            if rep['native_id'] not in cfg_cache:
                cfg_cache[rep['native_id']] = cfg(body)
            f.update(cfg_cache[rep['native_id']])
            member_features = []
            for identity in ids:
                native_id = identity['native_id']
                ib = bodies.get(native_id, {})
                if native_id not in cfg_cache:
                    cfg_cache[native_id] = cfg(ib)
                observation = cfg_cache[native_id]
                c.execute('INSERT OR IGNORE INTO native_features VALUES(?,?,?)', (native_id, packed(observation), ib.get('bytes_sha256')))
                member_features.append(observation)
            # Keep each original observation; never let the representative hide
            # a partial member or a worse range/CFG in reviewed shared work.
            f['cfg_complete'] = feature(all(x['cfg_complete']['value'] for x in member_features))
            for key in ('instruction_count', 'basic_blocks', 'conditional_branches', 'back_edges', 'cyclic_scc'):
                f[key] = feature(max(x[key]['value'] for x in member_features), 'partial' if any(x[key]['state'] != 'known' for x in member_features) else 'known', 'worst original member; individual native_features retained')
            for name in policy['grades']:
                if name in f and isinstance(f[name]['value'], int):
                    distributions[name].append(f[name]['value'])
        else:
            f['cfg_complete'] = feature(None, 'unknown')
        namespace = rep['demangled'].split('(')[0].rsplit('::', 1)[0] if '::' in rep['demangled'] else ''
        fh = hashlib.sha256(packed({'features': f, 'originals': ids, 'producer': provenance['producer']}).encode()).hexdigest()
        c.execute('INSERT INTO items VALUES(?,?,?,?,?,?,?)', (w['id'], kind, w['work_kind'], namespace, packed(ids), packed(f), fh))
        states = {canonical[(i['elf_sha256'], i['original_mangled'])] for i in ids if (i['elf_sha256'], i['original_mangled']) in canonical}
        state = 'existing_result' if states else 'completed' if w['status'] == 'completed' else 'remaining'
        if states and len(states) == 1:
            state = next(iter(states))
        c.execute('INSERT INTO states VALUES(?,?,?,?)', (w['id'], state, int(w['id'] in active), 'baseline'))
        scope = 'extent' if data else 'native_body'
        satisfied = all(bool(bodies.get(i['native_id'], {}).get('size') and (data or bodies.get(i['native_id'], {}).get('instructions'))) for i in ids)
        c.execute('INSERT INTO requirements VALUES(?,?,?,?,?,?)', (w['id'] + ':' + scope, w['id'], w['id'], scope, packed({'native': rep['native_id'], 'body_sha256': body.get('bytes_sha256'), 'storage': body.get('storage')}), satisfied))
        if data or initializer:
            for scope in (('representation', 'consumer_binding') if data else ('initialization_effects',)):
                c.execute('INSERT INTO requirements VALUES(?,?,?,?,?,0)', (w['id'] + ':' + scope, w['id'], w['id'], scope, '{}'))
    # Preserve actual direct-call requirements; candidates and name bridges are
    # retained as raw observations only, never promoted into execution edges.
    for edge in n.execute("SELECT * FROM edges WHERE kind='ELF_CALLS' ORDER BY src,dst,site"):
        for consumer in native_to_work.get(edge['src'], ()):
            targets = native_to_work.get(edge['dst'], ())
            for target in targets or {edge['dst']}:
                rid = hashlib.sha256(packed([consumer, target, 'callable_behavior']).encode()).hexdigest()
                c.execute('INSERT OR IGNORE INTO requirements VALUES(?,?,?,?,?,0)', (rid, consumer, target, 'callable_behavior', packed({'native_src': edge['src'], 'native_dst': edge['dst'], 'kind': edge['kind'], 'site': edge['site'], 'scope_note': 'direct call proven; callable declaration/behavior not inferred from status'})))
                target_body = bodies.get(edge['dst'], {})
                resolution = n.execute('SELECT * FROM symbol_resolution WHERE symbol_id=?', (edge['dst'],)).fetchone()
                provider_context = False
                if resolution and resolution['strategy'] == 'external_source':
                    binding = json.loads(resolution['evidence_json'])
                    definitions = [entry for entry in binding.get('upstream', []) if entry.get('definition') and entry.get('definition_extent_sha256')]
                    for definition in definitions:
                        raw = (ROOT / definition['repository_path']).read_bytes()
                        extent = raw[definition['definition_extent_start']:definition['definition_extent_end']]
                        if hashlib.sha256(extent).hexdigest() != definition['definition_extent_sha256']:
                            raise ValueError('provider definition extent changed')
                    provider_context = bool(definitions)
                context_available = bool(target_body.get('instructions')) or provider_context
                context_id = hashlib.sha256(packed([consumer, target, 'callee_context']).encode()).hexdigest()
                c.execute('INSERT OR IGNORE INTO requirements VALUES(?,?,?,?,?,?)', (context_id, consumer, target, 'callee_context', packed({'native_id': edge['dst'], 'body_hash': target_body.get('bytes_sha256'), 'provider_context': provider_context, 'scope': 'context availability only; no behavior/declaration/layout claim'}), int(context_available)))
    data_ranges = collections.defaultdict(list)
    for original in occurrences.values():
        if original['symbol_kind'] != 'STT_FUNC' and original['original_size']:
            data_ranges[original['elf_sha256']].append(original)
    interval_indexes = {}
    for elf, values in data_ranges.items():
        values.sort(key=lambda x: (x['original_address'], x['id']))
        maximum, ends = 0, []
        for value in values:
            maximum = max(maximum, value['original_address']+value['original_size']); ends.append(maximum)
        interval_indexes[elf] = ([v['original_address'] for v in values], ends, values)
    for original in occurrences.values():
        native_id = original['native_id']
        observations = cfg_cache.get(native_id, {}).get('proven_data_accesses', {}).get('value', [])
        starts, ends, values = interval_indexes.get(original['elf_sha256'], ([], [], []))
        for access in observations:
            address, width = access['address'], access['width']
            pos = bisect.bisect_right(starts, address)-1
            matched = []
            while pos >= 0 and ends[pos] >= address+width:
                value = values[pos]
                if value['original_address'] <= address and address+width <= value['original_address']+value['original_size']:
                    matched.append(value)
                pos -= 1
            for consumer in native_to_work.get(native_id, ()):
                targets = [(target, value) for value in matched for target in (native_to_work.get(value['native_id']) or {value['native_id']})]
                if not targets:
                    targets = [(f"native-address:{original['elf_sha256']}:{address:x}", None)]
                for target, value in targets:
                    evidence = packed({'native_src': native_id, 'native_data': value['native_id'] if value else None,
                                       'access': access, 'scope': 'constant-origin memory instruction within one basic block; not runtime execution or data representation'})
                    for scope, satisfied in [('data_context', bool(value and bodies.get(value['native_id'], {}).get('size'))), ('data_binding_behavior', False)]:
                        rid = hashlib.sha256(packed([consumer, target, scope, address, width]).encode()).hexdigest()
                        c.execute('INSERT OR IGNORE INTO requirements VALUES(?,?,?,?,?,?)', (rid, consumer, target, scope, evidence, int(satisfied)))
    c.execute('INSERT INTO requirement_origins SELECT id,evidence FROM requirements')
    c.execute('INSERT INTO meta VALUES(?,?)', ('static_digest', static_digest(c)))
    reevaluate(c)
    queues = dict(c.execute('SELECT queue,count(*) FROM evaluations GROUP BY queue').fetchall())
    stats = {}
    for name, values in distributions.items():
        values.sort()
        stats[name] = {'n': len(values), 'min': values[0], 'p25': values[len(values)//4], 'median': values[len(values)//2], 'p75': values[len(values)*3//4], 'max': values[-1]}
    inventory = {'work_items': len(works), 'occurrences': len(occurrences), 'queues': queues,
                 'physical_ranges': len(ranges), 'implementation_groups': d.execute('SELECT count(*) FROM implementation_groups').fetchone()[0],
                 'catalogued_without_work': sum(not original_memberships[oid] for oid in occurrences),
                 'unassigned_originals_by_kind': dict(collections.Counter(original['symbol_kind'] for oid, original in occurrences.items() if not original_memberships[oid])),
                 'kinds': [list(r) for r in c.execute('SELECT kind,count(*) FROM items GROUP BY kind')],
                 'distributions': stats, 'seconds': time.monotonic()-start,
                 'static_reuse': reuse_observation,
                 'limitations': ['No generic typed data interpretation inferred from extraction', 'No initializer effects/order inferred from symbol names', 'Direct callee requirements require explicit scope review; completed/pending not automatically sufficient'], 'provenance': provenance}
    c.execute('INSERT INTO meta VALUES(?,?)', ('inventory', packed(inventory)))
    c.execute('INSERT INTO meta VALUES(?,?)', ('complete', 'true'))
    c.commit(); c.close()
    (out / 'INVENTORY.json').write_text(json.dumps(inventory, indent=2) + '\n')
    export(out / 'ranking.sqlite', out / 'RANKED.json', out / 'RANKED.md')
    return inventory


def export(db, json_path, md_path):
    c = ro(db)
    rows = [dict(r) for r in c.execute('SELECT i.*,e.queue,e.rank,e.reasons,e.potential,e.sufficient,e.binding FROM items i JOIN evaluations e USING(id)')]
    for r in rows:
        for key in ('identities', 'features', 'rank', 'reasons', 'binding'):
            r[key] = json.loads(r[key])
    rows.sort(key=lambda r: (r['kind'], r['queue'], r['rank']))
    pathlib.Path(json_path).write_text(json.dumps(rows, indent=2) + '\n')
    lines = ['# Derived ranking', '', 'Within-kind lexicographic ranks; unknown≠0. No readiness/ABI claims.', '', '| Work | Kind | Queue | Rank | Original |', '|---|---|---|---|---|']
    for r in rows:
        lines.append('| ' + ' | '.join([r['id'], r['kind'], r['queue'], str(r['rank'][:-1]), r['identities'][0]['original_mangled'].replace('|', '\\|')]) + ' |')
    pathlib.Path(md_path).write_text('\n'.join(lines) + '\n')


def static_digest(c):
    h = hashlib.sha256()
    for query in ('SELECT * FROM original_catalog ORDER BY id', 'SELECT * FROM items ORDER BY id', 'SELECT * FROM native_features ORDER BY native_id',
                  'SELECT id,consumer,target,scope FROM requirements ORDER BY id', 'SELECT * FROM requirement_origins ORDER BY id'):
        for row in c.execute(query):
            h.update(packed(tuple(row)).encode())
            h.update(b'\n')
    return h.hexdigest()


def check_inputs(c, source_guard=False):
    marker = c.execute("SELECT value FROM meta WHERE key='complete'").fetchone()
    if not marker or marker[0] != 'true':
        raise ValueError('incomplete derived ranking')
    provenance = json.loads(c.execute("SELECT value FROM meta WHERE key='provenance'").fetchone()[0])
    if static_digest(c) != c.execute("SELECT value FROM meta WHERE key='static_digest'").fetchone()[0]:
        raise ValueError('ranking static content corruption')
    if digest(__file__) != provenance['producer'] or digest(POLICY) != provenance['policy_sha256']:
        raise ValueError('ranking producer/policy changed; new build required')
    for name in ('NATIVE', 'DEDUP'):
        live = json.loads((ROOT / 'dependency-graph' / (name + '_ACTIVE.json')).read_text())
        if live != provenance[name.lower()]:
            raise ValueError('stale ' + name + ' generation')
    native_path = ROOT / provenance['native']['database']
    if digest(native_path) != provenance['native']['sha256']:
        raise ValueError('native index corruption after ranking build')
    native = ro(native_path)
    for row in native.execute('SELECT * FROM inputs'):
        if digest(ROOT / row['path']) != row['sha256']:
            raise ValueError('changed native/provider input: ' + row['path'])
    dedup = ro(ROOT / provenance['dedup']['database'])
    for row in dedup.execute('SELECT * FROM payload_contents'):
        path = ROOT / row['object_path']
        if path.stat().st_size != row['size'] or digest(path) != row['content_sha256']:
            raise ValueError('changed shared payload: ' + row['id'])
    checked = set()
    for row in c.execute('SELECT evidence FROM requirements WHERE satisfied=1'):
        evidence = json.loads(row[0])
        if evidence.get('path'):
            key = (evidence['path'], evidence.get('sha256'))
            if key not in checked:
                path = (ROOT / key[0]).resolve()
                if not path.is_relative_to(ROOT) or digest(path) != key[1]:
                    raise ValueError('stale scoped requirement evidence')
                checked.add(key)
    live_source = json.loads((ROOT / 'dependency-graph/ACTIVE.json').read_text())
    if live_source != provenance['source']:
        raise ValueError('stale source generation')
    if source_guard:
        from context_runtime import guard
        guard(ROOT, live_source)
    return provenance


def reconcile(c):
    """Observe canonical routing/claims transactionally; do not infer scope proofs."""
    check_inputs(c)
    dp = json.loads((ROOT / 'dependency-graph/DEDUP_ACTIVE.json').read_text())
    d = ro(ROOT / dp['database']); d.execute('BEGIN')
    claims = {r[0] for r in d.execute("SELECT work_item_id FROM work_claims WHERE state='active'")}
    work_states = dict(d.execute('SELECT id,status FROM reconstruction_work_items'))
    provenance = json.loads(c.execute("SELECT value FROM meta WHERE key='provenance'").fetchone()[0])
    bound = provenance['registry_snapshot']['database'] if provenance['explicit_registry_database'] else None
    states, observed_digest, snapshot = canonical_observation(bound)
    if snapshot['database'] != provenance['registry_snapshot']['database']:
        raise ValueError('canonical registry database generation changed; new build required')
    changes = []
    for item in c.execute('SELECT i.id,i.identities,s.* FROM items i JOIN states s USING(id)'):
        originals = json.loads(item['identities'])
        found = {states[(i['elf_sha256'], i['original_mangled'])] for i in originals if (i['elf_sha256'], i['original_mangled']) in states}
        status = next(iter(found)) if len(found) == 1 else 'existing_result' if found else 'completed' if work_states[item['id']] == 'completed' else 'remaining'
        if status != item['canonical'] or int(item['id'] in claims) != item['claimed']:
            changes.append({'item': item['id'], 'expected_revision': item['revision'], 'canonical': status, 'claimed': int(item['id'] in claims)})
    if not changes:
        return {'visited': 0, 'changed': []}
    payload = {'id': 'reconcile:' + hashlib.sha256(packed(changes).encode()).hexdigest(), 'changes': changes}
    return event(c, payload)


def plan(c, packets_per_worker=10):
    """Read-only conservative exact ten-worker proposal; no claims or packet dispatch.

    Missing callable requirements are blockers, not permission to create stubs.
    The ordinary batch context gate is still required for any complete proposal.
    """
    if packets_per_worker not in (5, 10, 20):
        raise ValueError('Supported group sizes: five, ten or twenty')
    candidates, skipped = [], []
    for item in c.execute('SELECT i.*,e.queue,e.rank FROM items i JOIN evaluations e USING(id)'):
        r = dict(item); r['rank'] = json.loads(r['rank'])
        requirements = [dict(x) for x in c.execute('SELECT * FROM requirements WHERE consumer=?', (r['id'],))]
        calls = [x for x in requirements if x['scope'] in ('callable_behavior', 'data_binding_behavior')]
        if r['queue'] != 'reconstruction_eligible':
            skipped.append({'id': r['id'], 'reason': r['queue'], 'unmet': [x['id'] for x in requirements if not x['satisfied']]})
        elif not calls:
            skipped.append({'id': r['id'], 'reason': 'no proven substantive call/data/initialization dependency; leaves excluded from this trial'})
        else:
            r['requirements'] = requirements
            candidates.append(r)
    candidates.sort(key=lambda r: (r['kind'], r['rank']))
    groups = collections.defaultdict(list)
    for r in candidates:
        groups[r['namespace']].append(r)
    adequate = {name: values for name, values in groups.items() if name and len(values) >= packets_per_worker}
    # No claimed independence until exact source read/write sets are sealed.
    observation = hashlib.sha256(packed([tuple(x) for x in c.execute('SELECT * FROM evaluations ORDER BY id')]).encode()).hexdigest()
    return {'status': 'blocked' if len(adequate) < 10 else 'context_validation_required',
            'evaluation_digest': observation,
            'provenance': json.loads(c.execute("SELECT value FROM meta WHERE key='provenance'").fetchone()[0]),
            'eligible_with_proven_dependencies': len(candidates), 'namespace_groups_with_ten': sum(bool(n) and len(v)>=10 for n,v in groups.items()), 'namespace_groups_with_required_count': len(adequate), 'packets_per_worker': packets_per_worker, 'required_symbols': 10*packets_per_worker,
            'symbol_deficit': max(0, 10*packets_per_worker-len(candidates)), 'group_deficit': max(0, 10-len(adequate)),
            'policy': json.loads(c.execute("SELECT value FROM meta WHERE key='policy'").fetchone()[0]),
            'groups': {name: [r['id'] for r in values[:packets_per_worker]] for name, values in sorted(adequate.items())},
            'skipped': skipped,
            'limitations': ['Deficit is under this evidence-conservative policy, not a proof no future scoped research can unlock work.',
                            'Native index has no proven typed data reader/writer edges; address candidates not upgraded.',
                            'No safe inter-group independence asserted without complete context packets.'],
            'spawn_authorized': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build'); b.add_argument('--out', type=pathlib.Path, required=True); b.add_argument('--reuse-db'); b.add_argument('--registry-db')
    for name in ('explain', 'list', 'update', 'rebuild', 'reconcile', 'plan', 'validate-plan'):
        s = sub.add_parser(name); s.add_argument('--db', required=True)
        if name == 'explain': s.add_argument('--item', required=True)
        if name == 'update': s.add_argument('--event', required=True)
        if name in ('plan', 'validate-plan'):
            s.add_argument('--out', type=pathlib.Path, required=True)
            s.add_argument('--packets-per-worker', type=int, choices=(5, 10, 20), default=10)
        if name == 'validate-plan': s.add_argument('--plan', type=pathlib.Path, required=True)
    a = p.parse_args()
    if a.command == 'build':
        result = build(a.out, a.reuse_db, a.registry_db)
    elif a.command == 'list':
        c = ro(a.db)
        result = [dict(r) for r in c.execute('SELECT i.kind,e.id,e.queue,e.rank FROM evaluations e JOIN items i USING(id)')]
        result.sort(key=lambda r: (r['kind'], r['queue'], json.loads(r['rank'])))
    elif a.command == 'explain':
        c = ro(a.db)
        result = {'item': dict(c.execute('SELECT * FROM items WHERE id=?', (a.item,)).fetchone()),
                  'evaluation': dict(c.execute('SELECT * FROM evaluations WHERE id=?', (a.item,)).fetchone()),
                  'requirements': [dict(r) for r in c.execute('SELECT * FROM requirements WHERE consumer=?', (a.item,))]}
    elif a.command in ('plan', 'validate-plan'):
        c = sqlite3.connect(a.db); c.row_factory = sqlite3.Row
        check_inputs(c)
        reconcile(c)
        result = plan(c, a.packets_per_worker)
        if a.command == 'validate-plan':
            prior = json.loads(a.plan.read_text())
            for key in ('evaluation_digest', 'provenance', 'groups', 'policy', 'packets_per_worker', 'required_symbols'):
                if prior.get(key) != result[key]:
                    raise ValueError('stale or changed plan: ' + key)
        try:
            check_inputs(c, source_guard=True)
            result['source_fresh'] = True
        except (ValueError, RuntimeError) as error:
            result['status'] = 'blocked'; result['source_fresh'] = False
            result['source_blocker'] = str(error)
        a.out.mkdir(parents=True, exist_ok=False)
        (a.out / 'PLAN.json').write_text(json.dumps(result, indent=2) + '\n')
        (a.out / 'PLAN.md').write_text(f'# Exact 10×{a.packets_per_worker} planning gate\n\n' + packed({k: v for k, v in result.items() if k not in ('skipped', 'policy')}) + '\n')
        result = {k: v for k, v in result.items() if k not in ('skipped', 'policy')}
    else:
        c = sqlite3.connect(a.db); c.row_factory = sqlite3.Row
        check_inputs(c)
        if a.command == 'update': result = event(c, json.loads(pathlib.Path(a.event).read_text()))
        elif a.command == 'reconcile': result = reconcile(c)
        else:
            with c: result = reevaluate(c)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
