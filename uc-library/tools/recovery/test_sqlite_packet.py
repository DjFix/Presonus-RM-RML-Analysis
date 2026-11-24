"""Standalone canonical SQLite packet tests with an isolated tiny ARM ELF."""
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


def tiny_elf(path):
    """Write a regular ELF32 symbol table and two file-backed code ranges."""
    code = bytes.fromhex('0dc0a0e100d82de904b04ce200a89de8')
    strings = b'\0' + b'\0'.join(n.encode() for n in NAMES) + b'\0'
    section_names = b'\0.text\0.symtab\0.strtab\0.shstrtab\0'
    syms = b'\0' * 16
    for index, name in enumerate(NAMES):
        syms += struct.pack('<IIIBBH', strings.index(name.encode()), 0x1000 + index * 16, 16, 0x12, 0, 1)
    start = struct.calcsize('<16sHHIIIIIHHHHHH')
    contents = (code * 2, syms, strings, section_names)
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


def fixture(root):
    """Build canonical registry data and authority input under project scratch."""
    lib = root / 'uc-library'
    lib.mkdir(parents=True)
    native = root / 'probe.elf'
    body = tiny_elf(native)
    elf = packet.digest(native)
    rows = [dict(mangled=name, demangled=f'Presonus::{scope}::{method}()',
                 address=0x1000+i*16, size=16, section=1, kind='STT_FUNC', binding='STB_GLOBAL')
            for i, (name, scope, method) in enumerate(zip(NAMES, ('Probe','Other'), ('one','two')))]
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
    scope_by_name = dict(zip(NAMES, ('Probe','Other')))
    code_hash = packet.hashlib.sha256(body).hexdigest()
    audit = root/'historical-receipts.json'
    packet.write(audit, {'crew':'fixture operator', 'exact_unassigned':[r['mangled'] for r in rows]})
    ref = {'path':audit.name, 'sha256':packet.digest(audit)}
    tasks, groups, custody_rows = [], [], []
    provider='third_party/ccl-framework/core/portable/fixture-provider.h'
    provider_path=root/provider
    provider_path.parent.mkdir(parents=True)
    provider_path.write_text('// fixture Core provider\n')
    provider_ref={'path':provider,'sha256':packet.digest(provider_path)}
    for row in sorted(catalog.query(db, role='client'), key=lambda r:r['mangled']):
        owner=scope_by_name[row['mangled']]; ident='task_'+owner.lower()
        workspace=root/f'temp/recovery-work/worktrees/{owner.lower()}'
        (workspace/'.git').mkdir(parents=True)
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
        groups.append({'owner':owner.lower(),'workspace':str(workspace.relative_to(root)),'tasks':[ident]})
    custody_file=root/'custody.json'
    packet.write(custody_file,{'version':1,'authority':'fixture operator','records':custody_rows})
    plan=root/'plan.json'
    packet.write(plan,{'version':1,'batch':'fixture_batch','elfs':{elf:native.name},
                       'custody':{'path':custody_file.name,'sha256':packet.digest(custody_file)},
                       'tasks':tasks,'groups':groups})
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


if __name__=='__main__':
    unittest.main()
