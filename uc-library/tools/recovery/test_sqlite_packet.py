"""Standalone canonical SQLite packet tests with an isolated tiny ARM ELF."""
from contextlib import ExitStack
import json
from pathlib import Path
import shutil
import sqlite3
import struct
import tempfile
import unittest

import sqlite_packet as packet
import catalog
import registry
import schema
import workflow

ROOT = Path(__file__).resolve().parents[3]
NAMES = ('_ZN8Presonus5Probe3oneEv', '_ZN8Presonus5Other3twoEv')


def tiny_elf(path, names):
    """Write a regular ELF32 symbol table and file-backed code ranges."""
    code = bytes.fromhex('0dc0a0e100d82de904b04ce200a89de8')
    strings = b'\0' + b'\0'.join(n.encode() for n in names) + b'\0'
    section_names = b'\0.text\0.symtab\0.strtab\0.shstrtab\0'
    syms = b'\0' * 16
    for index, name in enumerate(names):
        syms += struct.pack('<IIIBBH', strings.index(name.encode()), 0x1000 + index * 16, 16, 0x12, 0, 1)
    start = struct.calcsize('<16sHHIIIIIHHHHHH')
    contents = (code * len(names), syms, strings, section_names)
    offsets = []
    for item in contents:
        offsets.append(start)
        start += len(item)
    padding = (-start) % 4
    ident = b'\x7fELF\x01\x01\x01' + b'\0' * 9
    head = struct.pack('<16sHHIIIIIHHHHHH', ident, 2, 40, 1, 0, 0, start+padding,
                       0x5000000, 52, 0, 0, 40, 5, 4)
    sections = b'\0' * 40
    attrs = ((1, 6, 0x1000, 0, 0, 4, 0), (2, 0, 0, 3, 1, 4, 16),
             (3, 0, 0, 0, 0, 1, 0), (3, 0, 0, 0, 0, 1, 0))
    for name, offset, data, values in zip((b'.text', b'.symtab', b'.strtab', b'.shstrtab'), offsets, contents, attrs):
        kind, flags, address, link, info, align, entry = values
        sections += struct.pack('<IIIIIIIIII', section_names.index(name), kind, flags, address,
                                offset, len(data), link, info, align, entry)
    path.write_bytes(head + b''.join(contents) + b'\0' * padding + sections)
    return code


def fixture(root, interfaces=None):
    """Build canonical registry data and authority input under project scratch."""
    lib = root / 'uc-library'
    lib.mkdir(parents=True)
    native = root / 'probe.elf'
    if interfaces is None:
        interfaces = list(zip(NAMES, ('Probe', 'Other'), ('one', 'two')))
    body = tiny_elf(native, [name for name, _, _ in interfaces])
    elf = packet.digest(native)
    rows = [dict(mangled=name, demangled=f'Presonus::{scope}::{method}()',
                 address=0x1000+i*16, size=16, section=1, kind='STT_FUNC', binding='STB_GLOBAL')
            for i, (name, scope, method) in enumerate(interfaces)]
    roles = {'client': {'summary': {'sha256': elf, 'label': 'test ARM client'}, 'symbols': rows}}
    roles['server']={'summary': {'sha256': 'b'*64, 'label': 'test ARM server'}, 'symbols': []}
    tracking = lib / 'tracking'
    tracking.mkdir()
    packet.write(tracking/'coverage.json', {'roles':roles})
    for role, inputs in roles.items():
        recovered=lib/'recovered-all'/role
        recovered.mkdir(parents=True)
        for name, value in [('manifest.json', {'sha256':inputs['summary']['sha256']}),
                            ('all-symbols.json', inputs['symbols']), ('symbols.json', inputs['symbols'])]:
            packet.write(recovered/name, value)
    fragments = {}
    for status in ('ready', 'pending'):
        path = root / (status+'.json')
        packet.write(path, {'functions':[]})
        fragments[status] = path
    registry.capture(fragments, root/'baseline-snapshot')
    baseline, db = root/'baseline.sqlite', root/'working.sqlite'
    registry.import_snapshots(root/'baseline-snapshot', baseline)
    workflow.working_copy(baseline, db)
    schema.upgrade(db, root/'schema-before.sqlite', apply=True)
    catalog.import_catalog(db, lib, False)
    scope_by_name = {name: (scope, method) for name, scope, method in interfaces}
    code_hash = packet.hashlib.sha256(body).hexdigest()
    audit = root/'temp/recovery-work/history/historical-receipts.json'
    audit.parent.mkdir(parents=True)
    packet.write(audit, {'crew':'fixture operator', 'exact_unassigned':[r['mangled'] for r in rows]})
    ref = {'path':str(audit.relative_to(root)), 'sha256':packet.digest(audit)}
    tasks, owner_groups, custody_rows = [], {}, []
    provider='third_party/ccl-framework/core/portable/fixture-provider.h'
    provider_path=root/provider
    provider_path.parent.mkdir(parents=True)
    provider_path.write_text('// fixture Core provider\n')
    provider_ref={'path':provider,'sha256':packet.digest(provider_path)}
    for row in sorted(catalog.query(db, role='client'), key=lambda r:r['mangled']):
        owner, method = scope_by_name[row['mangled']]
        ident = 'task_' + owner.lower() + '_' + method
        workspace=root/f'temp/recovery-work/worktrees/{owner.lower()}'
        (workspace/'.git').mkdir(parents=True, exist_ok=True)
        source=f'uc-library/src/{owner}.cpp'
        (root/source).parent.mkdir(parents=True, exist_ok=True)
        (root/source).write_text(f'// canonical {owner}\n')
        for relative in (source, provider):
            (workspace/relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root/relative, workspace/relative)
        keys=('anchor','elf','mangled','role','firmware','address','size','section')
        original={key:row[key] for key in keys}
        custody_rows.append({**{key:row[key] for key in ('anchor','elf','mangled')},
                             'disposition':'available','evidence':[ref]})
        task={'id':ident,'namespace':'Presonus::'+owner,'objective':'Implement bounded fixture method.',
              'mode':'reconstruct','owned_files':[source,f'uc-library/tests/recovery/{ident}/Replay.cpp'],
              'sources':{source:packet.digest(root/source),provider:provider_ref['sha256']},
              'review':{'reviewer':'fixture operator','domain':'Exact local native and host replay.',
                        'oracle_plan':'Replay both approved native and host checks.',
                        'limitations':['No original ABI.'],'evidence':[ref],
                        'providers':[provider_ref],'required_provider_paths':[provider]},
              'originals':[{**original,'range_sha256':code_hash}]}
        tasks.append(task)
        group = owner_groups.setdefault(owner, {'owner': owner.lower(),
            'workspace': str(workspace.relative_to(root)), 'tasks': []})
        group['tasks'].append(ident)
    custody_file=root/'custody.json'
    packet.write(custody_file,{'version':1,'authority':'fixture operator','records':custody_rows})
    plan=root/'plan.json'
    packet.write(plan,{'version':1,'batch':'fixture_batch','elfs':{elf:native.name},
                       'custody':{'path':custody_file.name,'sha256':packet.digest(custody_file)},
                       'tasks':tasks,'groups':list(owner_groups.values())})
    return root, db, plan


class PacketTests(unittest.TestCase):
    def setUp(self):
        scratch=ROOT/'temp/recovery-work/sqlite-packet-tests'
        scratch.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=scratch)
        self.root,self.db,self.plan=fixture(Path(self.temp.name))
        self.out=self.root/'temp/recovery-work/prepared'

    def tearDown(self):
        self.temp.cleanup()

    def rewrite(self, data):
        self.plan.write_text(json.dumps(data))

    def state(self):
        with sqlite3.connect(self.db) as db:
            return db.execute('SELECT state,revision FROM catalog_tasks ORDER BY anchor').fetchall()

    def test_native_elf_cache_rejects_replacement_and_in_place_edits(self):
        plan = packet.load(self.plan)
        targets = [task['originals'][0] for task in plan['tasks']]
        source, = plan['elfs'].values()
        path = self.root / source
        before = path.read_bytes()
        with ExitStack() as stack:
            reader = packet.NativeELF(self.root, source, plan['tasks'][0]['originals'][0]['elf'], stack)
            self.assertEqual(reader.range_for(targets[0]),
                             packet.native_range(self.root, targets[0], source, {}))
            self.assertEqual(reader.range_for(targets[1]),
                             packet.native_range(self.root, targets[1], source, {}))
            wrong = dict(targets[1], range_sha256='0'*64)
            with self.assertRaisesRegex(ValueError, 'range hash mismatch'):
                reader.range_for(wrong)
            replacement = path.with_name('replacement.elf')
            replacement.write_bytes(before)
            replacement.replace(path)
            with self.assertRaisesRegex(ValueError, 'changed during scoped prepare'):
                reader.verify_unchanged()
        with ExitStack() as stack:
            reader = packet.NativeELF(self.root, source, plan['tasks'][0]['originals'][0]['elf'], stack)
            with path.open('ab') as file:
                file.write(b'changed after hash')
            with self.assertRaisesRegex(ValueError, 'changed during scoped prepare'):
                reader.range_for(targets[0])

    def test_original_sha_and_symbol_membership_unchanged_with_cache(self):
        plan = packet.load(self.plan)
        source, = plan['elfs'].values()
        target = plan['tasks'][0]['originals'][0]
        with ExitStack() as stack:
            reader = packet.NativeELF(self.root, source, plan['tasks'][0]['originals'][0]['elf'], stack)
            wrong = dict(target, elf='1'*64)
            with self.assertRaisesRegex(ValueError, 'ELF SHA-256 mismatch'):
                reader.range_for(wrong)
            wrong = dict(target, address=target['address']+16)
            with self.assertRaisesRegex(ValueError, 'does not identify one row'):
                reader.range_for(wrong)
            wrong = dict(target, section=3)
            with self.assertRaisesRegex(ValueError, 'executable and file-backed'):
                reader.range_for(wrong)

    def test_original_thunk_keeps_identity_and_rejects_other_scope(self):
        symbol = '_ZThn1040_N8Presonus5Panel15SPIControlGroup4openEPKc'
        row = {'mangled': symbol, 'demangled':
               'non-virtual thunk to Presonus::Panel::SPIControlGroup::open(char const*)'}
        before = dict(row)
        packet.validate_callable_namespace(row, 'Presonus::Panel::SPIControlGroup')
        self.assertEqual(row, before)
        with self.assertRaisesRegex(ValueError, 'namespace differs'):
            packet.validate_callable_namespace(row, 'Presonus::Panel::SPIControl')
        with self.assertRaisesRegex(ValueError, 'namespace differs'):
            packet.validate_callable_namespace(
                {'mangled':'_ZThnot_valid', 'demangled':row['demangled']},
                'Presonus::Panel::SPIControlGroup')

    def test_template_namespace_uses_callable_name_without_encoded_return(self):
        mangled = '_ZN8Presonus5Probe6createIiEEPT_v'
        foreign = '_ZN8Presonus5Other6createINS_5ProbeEEEPT_RKS2_'
        self.assertIsNone(packet.validate_callable_namespace(
            {'demangled':'Presonus::Probe* Presonus::Other::create<Presonus::Probe>(Presonus::Probe const&)',
             'mangled':foreign}, 'Presonus::Other'))
        with self.assertRaisesRegex(ValueError, 'namespace differs'):
            packet.validate_callable_namespace(
                {'demangled':'Presonus::Probe* Presonus::Other::create<Presonus::Probe>(Presonus::Probe const&)',
                 'mangled':foreign}, 'Presonus::Probe')
        with tempfile.TemporaryDirectory(dir=self.root) as folder:
            root, db, plan = fixture(Path(folder), [(mangled, 'Probe', 'create')])
            full_name = 'int* Presonus::Probe::create<int>()'
            with sqlite3.connect(db) as draft:
                draft.execute('UPDATE catalog_symbols SET demangled=? WHERE mangled=?',
                              (full_name, mangled))
            wrong = packet.load(plan)
            wrong['tasks'][0]['namespace'] = 'Presonus::Other'
            wrong_plan = root / 'wrong-namespace.json'
            packet.write(wrong_plan, wrong)
            with self.assertRaisesRegex(ValueError, 'namespace differs'):
                packet.prepare(root, wrong_plan, root / 'wrong-out', db)
            out = root / 'temp/recovery-work/template-prepare'
            packet.prepare(root, plan, out, db)
            self.assertEqual(packet.dispatch(root, out, db)['assigned_originals'], 1)
            with sqlite3.connect(db) as check:
                self.assertEqual(check.execute('SELECT demangled FROM catalog_symbols WHERE mangled=?',
                                               (mangled,)).fetchone()[0], full_name)

    def test_prepare_dispatch_idempotence(self):
        index=packet.prepare(self.root,self.plan,self.out,self.db)
        self.assertEqual(self.state(),[('todo',0)]*2)
        self.assertEqual(index['mode'],'canonical_sqlite_only')
        seal=packet.dispatch(self.root,self.out,self.db)
        self.assertEqual(seal['assigned_originals'],2)
        self.assertEqual(seal,packet.dispatch(self.root,self.out,self.db))
        self.assertEqual(self.state(),[('assigned',1)]*2)
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM catalog_journal').fetchone()[0],2)

    def test_complete_class_may_exceed_ten_tasks(self):
        methods = [f'entry_{index}' for index in range(12)]
        interfaces = [(f'_ZN8Presonus5Probe{len(method)}{method}Ev', 'Probe', method)
                      for method in methods]
        root, db, plan = fixture(self.root / 'same-owner', interfaces)
        out = root / 'temp/recovery-work/prepared'
        prepared = packet.prepare(root, plan, out, db)
        self.assertEqual(len(prepared['groups']), 1)
        self.assertEqual(len(prepared['groups'][0]['tasks']), 12)
        published = packet.dispatch(root, out, db)
        self.assertEqual(published['assigned_originals'], 12)
        self.assertEqual(len(published['workers']), 1)
        self.assertEqual(len(published['workers'][0]['packets']), 12)
        self.assertEqual(published, packet.dispatch(root, out, db))

    def test_reject_missing_provider_binding(self):
        plan=packet.load(self.plan)
        plan['tasks'][0]['review']['providers']=[]
        self.rewrite(plan)
        with self.assertRaisesRegex(ValueError,'provider binding'):
            packet.prepare(self.root,self.plan,self.out,self.db)

    def test_reject_mismatched_exact_elf_range(self):
        plan=packet.load(self.plan)
        plan['tasks'][0]['originals'][0]['range_sha256']='1'*64
        self.rewrite(plan)
        with self.assertRaisesRegex(ValueError,'native range hash mismatch'):
            packet.prepare(self.root,self.plan,self.out,self.db)

    def test_reject_two_independent_owners_sharing_a_read_write_path(self):
        plan=packet.load(self.plan)
        path=plan['tasks'][0]['owned_files'][0]
        plan['tasks'][1]['sources'][path]=packet.digest(self.root/path)
        self.rewrite(plan)
        with self.assertRaisesRegex(ValueError,'overlap'):
            packet.prepare(self.root,self.plan,self.out,self.db)

    def test_declared_source_drift_prevents_assignment(self):
        packet.prepare(self.root,self.plan,self.out,self.db)
        source=packet.load(self.plan)['tasks'][0]['owned_files'][0]
        (self.root/source).write_text('// changed\n')
        with self.assertRaisesRegex(ValueError,'Current source'):
            packet.dispatch(self.root,self.out,self.db)
        self.assertEqual(self.state(),[('todo',0)]*2)

    def test_physical_drift_prevents_assignment(self):
        packet.prepare(self.root,self.plan,self.out,self.db)
        plan=packet.load(self.plan)
        task=next(t for t in plan['tasks'] if t['id']==plan['groups'][0]['tasks'][0])
        source=task['owned_files'][0]
        (self.root/plan['groups'][0]['workspace']/source).write_text('// stale physical source\n')
        with self.assertRaisesRegex(ValueError,'Physical checkout input differs'):
            packet.dispatch(self.root,self.out,self.db)
        self.assertEqual(self.state(),[('todo',0)]*2)

    def test_physical_review_evidence_is_hydrated_and_hash_verified(self):
        packet.prepare(self.root,self.plan,self.out,self.db)
        plan=packet.load(self.plan)
        group=plan['groups'][0]
        task=next(t for t in plan['tasks'] if t['id']==group['tasks'][0])
        evidence=task['review']['evidence'][0]
        physical=self.root/group['workspace']/evidence['path']
        self.assertFalse(physical.exists())
        packet.dispatch(self.root,self.out,self.db)
        self.assertEqual(packet.digest(physical),evidence['sha256'])

    def test_stale_physical_evidence_stops_assignment(self):
        packet.prepare(self.root,self.plan,self.out,self.db)
        plan=packet.load(self.plan)
        group=plan['groups'][0]
        task=next(t for t in plan['tasks'] if t['id']==group['tasks'][0])
        physical=self.root/group['workspace']/task['review']['evidence'][0]['path']
        physical.parent.mkdir(parents=True)
        physical.write_text('different earlier evidence')
        with self.assertRaisesRegex(ValueError,'Physical checkout input differs'):
            packet.dispatch(self.root,self.out,self.db)
        self.assertEqual(self.state(),[('todo',0)]*2)
        self.assertEqual(physical.read_text(),'different earlier evidence')


if __name__=='__main__':
    unittest.main()
