"""Batch launch-barrier regressions using isolated, retained project fixtures.

Run: uc-library/.venv/bin/python -m unittest discover -s tests -p test_context_batch.py
No production graph, registry, or claim is used by these tests.
"""
import copy
import json
import pathlib
import sys
import unittest
import uuid
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'dependency-graph'))

from context_runtime import ContextError
import context_publication as publication


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / 'temp/test-work/context-batch' / uuid.uuid4().hex
        self.output = self.root / 'batch'
        self.output.mkdir(parents=True)
        self.packets = ['packets/first', 'packets/second']
        for name in self.packets:
            packet = self.root / name
            packet.mkdir(parents=True)
            (packet / 'context.json').write_text(json.dumps({'task_id': name, 'state': 'dispatch_ready'}))
        self.payload = {'workers': [{'arguments': {'task_name': 'worker', 'message': 'sealed'}}]}

    def publish(self):
        return publication.publish_batch(self.root, self.output, self.payload, self.packets)

    def test_completed_batch_authorizes_every_member_without_per_packet_dispatch(self):
        path = self.publish()
        expected = json.loads(path.read_text())
        for name in self.packets:
            self.assertEqual(publication.authorization(self.root, self.root / name), expected)
            self.assertFalse((self.root / name / 'DISPATCH.json').exists())

    def test_builder_output_has_no_permission(self):
        for name in self.packets:
            with self.assertRaisesRegex(ContextError, 'no completed'):
                publication.authorization(self.root, self.root / name)

    def test_interruption_after_members_does_not_authorize_any_packet(self):
        original = publication.atomic_json
        def fail_final(path, value):
            if path.name == 'BATCH_DISPATCH.json':
                raise OSError('simulated publication interruption')
            original(path, value)
        with mock.patch.object(publication, 'atomic_json', side_effect=fail_final):
            with self.assertRaisesRegex(OSError, 'interruption'):
                self.publish()
        for name in self.packets:
            with self.assertRaisesRegex(ContextError, 'incomplete'):
                publication.authorization(self.root, self.root / name)
        self.publish()  # Exact same output can resume its interrupted publication.
        for name in self.packets:
            publication.authorization(self.root, self.root / name)

    def test_interruption_during_members_never_exposes_arguments(self):
        original = publication.atomic_json
        calls = []
        def fail_second(path, value):
            calls.append(path)
            if len(calls) == 2:
                raise OSError('simulated member interruption')
            original(path, value)
        with mock.patch.object(publication, 'atomic_json', side_effect=fail_second):
            with self.assertRaises(OSError):
                self.publish()
        for name in self.packets:
            with self.assertRaises(ContextError):
                publication.authorization(self.root, self.root / name)
            member = self.root / name / 'BATCH_MEMBER.json'
            if member.exists():
                self.assertNotIn('arguments', json.loads(member.read_text()))

    def test_all_completion_bindings_are_verified(self):
        path = self.publish()
        original = json.loads(path.read_text())
        for field, value in [('publication_state', 'building'), ('publication_id', 'different'),
                             ('packet_manifests', {})]:
            with self.subTest(field=field):
                altered = dict(original, **{field: value})
                path.write_text(json.dumps(altered))
                with self.assertRaisesRegex(ContextError, 'binding mismatch'):
                    publication.authorization(self.root, self.root / self.packets[0])
        path.write_text(json.dumps(original))
        publication.authorization(self.root, self.root / self.packets[0])

    def test_current_packet_digest_is_checked(self):
        self.publish()
        packet = self.root / self.packets[0]
        (packet / 'context.json').write_text('{"changed":true}')
        with self.assertRaisesRegex(ContextError, 'binding mismatch'):
            publication.authorization(self.root, packet)

    def test_cross_batch_reuse_fails_and_existing_manifest_is_preserved(self):
        manifest = self.publish()
        before = manifest.read_bytes()
        other = self.root / 'other'
        other.mkdir()
        with self.assertRaisesRegex(ContextError, 'another batch'):
            publication.publish_batch(self.root, other, self.payload, self.packets)
        with self.assertRaisesRegex(ContextError, 'already published'):
            self.publish()
        self.assertEqual(before, manifest.read_bytes())

    def test_duplicates_and_empty_publication_are_rejected(self):
        for packets in [[], self.packets * 2]:
            with self.subTest(packets=packets):
                with self.assertRaisesRegex(ContextError, 'Empty or duplicate'):
                    publication.publish_batch(self.root, self.output, self.payload, packets)
        self.assertFalse((self.output / 'BATCH_DISPATCH.json').exists())

    def test_standalone_dispatch_compatibility_and_exclusion(self):
        packet = self.root / self.packets[0]
        single = {'task_name': 'single', 'fork_turns': 'none', 'message': 'authenticated'}
        (packet / 'DISPATCH.json').write_text(json.dumps(single))
        self.assertEqual(publication.authorization(self.root, packet), single)
        with self.assertRaisesRegex(ContextError, 'standalone'):
            self.publish()



# The graph/container boundary is replaced, while task parsing, generation/hash
# checks, file locks, threaded builders, resumable files and publication are real.
import fcntl
import os
import threading
import time
import types
import context_batch as batch
import context_work_batch
from context_runtime import fingerprint, inventory, sha


class FakeEnvironment:
    def __init__(self, root, output, hook=None, fail_task=None):
        self.root, self.output = root, output
        self.hook, self.fail_task = hook, fail_task
        self.lock = threading.Lock()
        self.concurrent = 0
        self.maximum = 0
        self.calls = []
        self.slicing_concurrent = 0
        self.slicing_maximum = 0

    def start(self):
        pass

    def close(self):
        pass

    def selector(self, action, packets, tag):
        with self.lock:
            self.concurrent += 1
            self.maximum = max(self.maximum, self.concurrent)
            self.calls.append((action, list(packets)))
        try:
            time.sleep(0.005)
            if self.hook:
                self.hook(action, packets)
            for name in packets:
                directory = self.root / name
                request = json.loads((directory / 'request.json').read_text())
                if action == 'prepare':
                    if request['task_id'] == self.fail_task:
                        raise ContextError('injected builder failure')
                    entry = {'task_id': request['task_id'], 'generation_sha256': self.active_digest,
                             'state': 'selected', 'selected_file_sha256': {},
                             'work_binding': request['work_binding'], 'originals': request['originals'],
                             'packet_sha256': {}, 'tool_sha256': {},
                             'agents_sha256': sha(self.root / 'AGENTS.md'),
                             'source_slices': {'functions': {item['original']['mangled']: {
                                 'mangled': item['original']['mangled'], 'excerpt': 'int fixture() {}',
                                 'source_sha256': 'a' * 64} for item in request['originals']}}}
                    (directory / 'context.json').write_text(json.dumps(entry))
                    (directory / 'SUBAGENT_PROMPT.md').write_text('Required authenticated prompt')
                elif action == 'finalize':
                    entry = json.loads((directory / 'context.json').read_text())
                    entry['state'] = 'dispatch_ready'
                    (directory / 'context.json').write_text(json.dumps(entry))
                elif action == 'validate':
                    entry = json.loads((directory / 'context.json').read_text())
                    if entry['state'] != 'dispatch_ready':
                        raise ContextError('not finalized')
        finally:
            with self.lock:
                self.concurrent -= 1

    def slice(self, packet, tag):
        with self.lock:
            self.slicing_concurrent += 1
            self.slicing_maximum = max(self.slicing_maximum, self.slicing_concurrent)
        try:
            time.sleep(0.005)
            (self.root / packet / 'source-slices.json').write_text('{"fixture":true}')
        finally:
            with self.lock:
                self.slicing_concurrent -= 1


class BatchOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / 'temp/test-work/context-batch' / uuid.uuid4().hex
        for name in ['dependency-graph/state', 'uc-library/src', 'uc-library/tools/recovery',
                     'uc-library/validation/registry-sqlite', 'tasks', 'docs']:
            (self.root / name).mkdir(parents=True)
        self.source = self.root / 'uc-library/src/input.cpp'
        self.source.write_text('int original = 1;\n')
        for name in ['docs/worker-handoff.md', 'dependency-graph/CONTEXT_SELECTION.md',
                     'dependency-graph/BATCH_CONTEXT.md', 'dependency-graph/DEDUPLICATION.md', 'AGENTS.md', 'dependency-graph/producer.py', 'dependency-graph/NATIVE_ACTIVE.json', 'dependency-graph/DEDUP_ACTIVE.json',
                     'uc-library/tools/recovery/select_context.py',
                     'uc-library/validation/registry-sqlite/ACTIVE.json']:
            (self.root / name).write_text('{}')
        state = {'files': {'uc-library/src/input.cpp': {'sha256': sha(self.source),
                                                      'fingerprint': fingerprint(self.source)}},
                 'source_inventory': inventory(self.root)}
        (self.root / 'dependency-graph/state/generation.json').write_text(json.dumps(state))
        active = {'state': 'dependency-graph/state/generation.json',
                  'state_sha256': sha(self.root / 'dependency-graph/state/generation.json')}
        (self.root / 'dependency-graph/ACTIVE.json').write_text(json.dumps(active))
        self.tasks = [self.task(i) for i in range(4)]
        for index, task in enumerate(self.tasks):
            (self.root / f'tasks/{index}.json').write_text(json.dumps(task))
        self.manifest = self.root / 'tasks/manifest.json'
        self.manifest.write_text(json.dumps({'tasks': [f'tasks/{i}.json' for i in range(4)]}))
        self.records_changed = False
        self.operator = types.SimpleNamespace(ROOT=self.root, ensure_fresh=lambda: None,
                                              memgraph_uri=lambda root: 'bolt://isolated', enrich=self.enrich)
        self.claims = {}
        self.validations = []
        self.envs = []
        self.hook = None
        self.fail_task = None
        connection = types.SimpleNamespace(close=lambda: None, execute=self.query_claim)
        self.dedup = types.SimpleNamespace(active_index=lambda root: (connection, {'database': 'test.sqlite'}),
            plan=lambda connection, task: self.plan(task), validate_claim=lambda c, b, p: None,
            claim_task=self.claim, validate_packet_work=self.validate_claim,
            validate_batch_work=self.validate_claims)
        self.patches = [mock.patch.dict(sys.modules, {'dedup_work': self.dedup}),
                        mock.patch('context_work_batch.BatchWorkValidator', side_effect=self.work_validator),
                        mock.patch.object(batch, 'choose_limits', return_value={
                            'limits': {'builders': 4, 'selection': 2, 'slicing': 1}})]
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.active_digest = active['state_sha256']

    def task(self, i):
        return {'task_id': f'work{i}', 'objective': 'test boundary', 'namespace': 'Presonus::Test',
                'mode': 'reconstruct', 'owned_files': [f'uc-library/src/out{i}.cpp'],
                'targets': [{'original_elf_sha256': 'a' * 64, 'mangled': f'_Ztest{i}'}]}

    def enrich(self, task):
        result = copy.deepcopy(task)
        result['originals'] = [{'original': dict(target, elf=target['original_elf_sha256'],
                                  address=4, size=4, section_json='{}', anchor='1'),
                                  'record': {'revision': int(self.records_changed)}}
                               for target in task['targets']]
        return result

    def claim(self, root, task, packet):
        identity = task['task_id']
        if identity in self.claims:
            raise ContextError('claim theft attempted')
        self.claims[identity] = dict(self.plan(task), claim_id='claim-' + identity,
                                     claim_owner=identity, claim_packet=packet, database='test.sqlite')
        return dict(task, work_binding=copy.deepcopy(self.claims[identity]))

    def plan(self, task):
        return {'work_item_id': task['task_id'], 'equivalence_decision_id': None,
                'covered_occurrences': [{'catalog_anchor': '1', 'elf_sha256': 'a' * 64,
                                         'original_mangled': task['targets'][0]['mangled']}]}

    def query_claim(self, sql, params):
        binding = self.claims.get(params[0])
        row = ({'owner': binding['claim_owner'], 'packet_path': binding['claim_packet'],
                'id': binding['claim_id']} if binding else None)
        return types.SimpleNamespace(fetchone=lambda: row)

    def validate_claim(self, root, request, packet):
        if request['work_binding'] != self.claims[request['task_id']]:
            raise ContextError('claim changed')

    def work_validator(self, root):
        remembered = []
        def validate(entry, packet):
            self.validate_claim(root, entry, packet)
            remembered.append((entry, packet))
        def finish():
            for entry, packet in remembered:
                self.validate_claim(root, entry, packet)
            self.validations.append([packet for _, packet in remembered])
        return types.SimpleNamespace(validate=validate, finish=finish, close=lambda: None)

    def validate_claims(self, root, entries, packets):
        for entry, packet in zip(entries, packets):
            self.validate_claim(root, entry, packet)
        self.validations.append(packets)

    def factory(self, root, output):
        environment = FakeEnvironment(root, output, self.hook, self.fail_task)
        environment.active_digest = self.active_digest
        self.envs.append(environment)
        return environment

    def run_batch(self, resume=False):
        return batch.run(self.operator, 'tasks/manifest.json', 'temp/recovery-work/batch',
                         jobs=4, resume=resume, runner_factory=self.factory)

    def assert_no_permission(self):
        output = self.root / 'temp/recovery-work/batch'
        self.assertFalse((output / 'BATCH_DISPATCH.json').exists())
        for packet in (output / 'packets').glob('*'):
            with self.assertRaises(ContextError):
                publication.authorization(self.root, packet)

    def grouped_batch(self, count, worker_count=10, flexible=False):
        tasks = [self.task(i) for i in range(worker_count * count)]
        groups = []
        for i, task in enumerate(tasks):
            task['owned_files'] = [f'uc-library/src/group{i // count}.cpp']
            (self.root / f'tasks/{i}.json').write_text(json.dumps(task))
        for i in range(worker_count):
            paths = [f'temp/recovery-work/batch/packets/work{j}'
                     for j in range(i * count, (i + 1) * count)]
            groups.append({'task_name': f'group{i}', 'packets': paths,
                           'execution_order': paths[::-1], 'scope_reason': 'shared class ownership'})
        self.manifest.write_text(json.dumps({'tasks': [f'tasks/{i}.json' for i in range(len(tasks))],
                                             'groups': groups, **({'flexible_total':200} if flexible else {})}))
        result = self.run_batch()
        payload = json.loads(result.read_text())
        self.assertEqual(len(payload['workers']), worker_count)
        self.assertEqual(len(payload['packet_manifests']), worker_count * count)
        for worker, expected in zip(payload['workers'], groups):
            self.assertEqual(worker['packets'], expected['packets'])
            self.assertEqual(worker['arguments']['task_name'], expected['task_name'])
            for packet in worker['packets']:
                self.assertFalse((self.root / packet / 'DISPATCH.json').exists())
                publication.authorization(self.root, self.root / packet)

    def test_flexible_eight_by25_same_atomic_barrier(self):
        self.grouped_batch(25, worker_count=8, flexible=True)

    def test_ten_by_five_shares_ownership_only_within_group(self):
        self.grouped_batch(5)

    def test_ten_by_ten_shares_ownership_only_within_group(self):
        self.grouped_batch(10)

    def test_ten_by_twenty_preserves_atomic200_publication(self):
        self.grouped_batch(20)

    def test_explicit_smaller_unequal_groups_publish_same_barrier(self):
        groups=[]
        for i in range(4):
            task=self.task(i)
            task['owned_files']=[f'uc-library/src/smallgroup{0 if i == 0 else 1}.cpp']
            (self.root/f'tasks/{i}.json').write_text(json.dumps(task))
        for index,ids in enumerate(([0],[1,2,3])):
            paths=[f'temp/recovery-work/batch/packets/work{i}' for i in ids]
            groups.append({'task_name':f'small{index}','packets':paths,
                           'execution_order':paths[:],'scope_reason':'explicit scoped small trial'})
        self.manifest.write_text(json.dumps({'tasks':[f'tasks/{i}.json' for i in range(4)],
            'groups':groups,'allow_smaller':True,'smaller_batch_authorization':'synthetic fixture authorization'}))
        payload=json.loads(self.run_batch().read_text())
        self.assertEqual(len(payload['workers']),2)
        self.assertEqual(len(payload['packet_manifests']),4)
        self.assertEqual(payload['publication_state'],'complete')
        for worker in payload['workers']:
            for packet in worker['packets']:
                publication.authorization(self.root,self.root/packet)

    def test_smaller_flag_requires_explicit_authorization_before_claim(self):
        manifest=json.loads(self.manifest.read_text());manifest['allow_smaller']=True
        self.manifest.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ContextError,'authorization'):self.run_batch()
        self.assertFalse(self.claims)

    def test_parallel_builders_obey_selection_limit_and_publish_after_validation(self):
        result = self.run_batch()
        self.assertEqual(self.envs[0].maximum, 2)
        self.assertEqual(self.envs[0].slicing_maximum, 1)
        payload = json.loads(result.read_text())
        self.assertEqual(len(payload['workers']), 4)
        self.assertEqual([action for action, _ in self.envs[0].calls].count('validate'), 1)
        self.assertEqual(len(self.claims), 4)
        self.assertTrue(self.validations)
        for worker in payload['workers']:
            publication.authorization(self.root, self.root / worker['packet'])

    def test_builder_failure_retains_claims_and_completed_evidence_then_resumes(self):
        self.fail_task = 'work1'
        with self.assertRaisesRegex(ContextError, 'builders failed'):
            self.run_batch()
        self.assert_no_permission()
        self.assertEqual(len(self.claims), 4)
        existing = self.root / 'temp/recovery-work/batch/packets/work0/context.json'
        original = existing.read_bytes()
        self.fail_task = None
        self.run_batch(resume=True)
        self.assertEqual(existing.read_bytes(), original)
        self.assertEqual(len(self.claims), 4)
        attempts = list((self.root / 'temp/recovery-work/batch').glob('attempt-*'))
        self.assertEqual(len(attempts), 2)
        self.assertEqual(sum((p / 'FAILED.json').exists() for p in attempts), 1)
        self.assertEqual(sum((p / 'COMPLETED.json').exists() for p in attempts), 1)

    def test_source_inventory_instructions_tools_generation_and_records_mutation_block(self):
        # Each mutation uses a fresh fixture to avoid admitting stale successes.
        for mutation in ['source', 'add', 'delete', 'instructions', 'tool', 'generation', 'record', 'claim']:
            with self.subTest(mutation=mutation):
                child = BatchOrchestrationTests('test_parallel_builders_obey_selection_limit_and_publish_after_validation')
                child.setUp()
                try:
                    changed = []
                    def alter(action, packets):
                        if action != 'validate' or changed:
                            return
                        changed.append(True)
                        if mutation == 'source':
                            child.source.write_text('int changed = 2;')
                        elif mutation == 'add':
                            (child.source.parent / 'added.cpp').write_text('int added;')
                        elif mutation == 'delete':
                            child.source.rename(child.source.with_suffix('.retained'))
                        elif mutation == 'instructions':
                            (child.root / 'AGENTS.md').write_text('changed instructions')
                        elif mutation == 'tool':
                            (child.root / 'dependency-graph/producer.py').write_text('changed producer')
                        elif mutation == 'generation':
                            (child.root / 'dependency-graph/ACTIVE.json').write_text('{}')
                        elif mutation == 'record':
                            child.records_changed = True
                        elif mutation == 'claim':
                            child.claims['work0']['claim_id'] = 'stolen'
                    child.hook = alter
                    with self.assertRaises(ContextError):
                        child.run_batch()
                    child.assert_no_permission()
                finally:
                    child.doCleanups()

    def test_builder_shared_lock_excludes_generation_publisher(self):
        observed = []
        def probe(action, packets):
            if action != 'prepare':
                return
            with (self.root / 'dependency-graph/state/context.lock').open('a') as stream:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                observed.append(True)
        self.hook = probe
        self.run_batch()
        self.assertEqual(len(observed), 4)

    def test_resume_after_atomic_publish_preserves_exact_manifest(self):
        path = self.run_batch()
        original = path.read_bytes()
        # Model interruption after atomic manifest publication but before the
        # coordinator records its terminal receipt by retaining publication.
        self.run_batch(resume=True)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(len(self.claims), 4)
        payload = json.loads(path.read_text())
        for worker in payload['workers']:
            publication.authorization(self.root, self.root / worker['packet'])

    def test_live_coordinator_cannot_be_resumed(self):
        output = self.root / 'temp/recovery-work/batch'
        output.mkdir(parents=True)
        with (output / 'coordinator.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            with self.assertRaisesRegex(ContextError, 'already running'):
                self.run_batch(resume=True)
        self.assertFalse(self.claims)

    def test_duplicate_identity_and_owner_rejected_before_claim(self):
        for field in ['task_id', 'targets', 'owned_files']:
            with self.subTest(field=field):
                tasks = copy.deepcopy(self.tasks)
                tasks[1][field] = tasks[0][field]
                with self.assertRaises(ContextError):
                    batch.validate_tasks(tasks)
        batch.validate_tasks(self.tasks)

    def test_final_conflicts_include_work_generation_and_read_write_edges(self):
        requests = [{'owned_files': ['uc-library/src/a.cpp']}, {'owned_files': ['uc-library/src/b.cpp']}]
        baseline = [{'task_id': f't{i}', 'generation_sha256': 'g',
                     'work_binding': {'work_item_id': f'w{i}'}, 'selected_file_sha256': {}}
                    for i in range(2)]
        batch.check_conflicts(baseline, requests)
        for mutation in ['task', 'work', 'generation', 'read']:
            with self.subTest(mutation=mutation):
                entries = copy.deepcopy(baseline)
                if mutation == 'task': entries[1]['task_id'] = 't0'
                if mutation == 'work': entries[1]['work_binding']['work_item_id'] = 'w0'
                if mutation == 'generation': entries[1]['generation_sha256'] = 'other'
                if mutation == 'read': entries[1]['selected_file_sha256']['uc-library/src/a.cpp'] = 'digest'
                with self.assertRaises(ContextError):
                    batch.check_conflicts(entries, requests)


class BatchCrashTests(unittest.TestCase):
    setUp = BatchOrchestrationTests.setUp
    task = BatchOrchestrationTests.task
    enrich = BatchOrchestrationTests.enrich
    claim = BatchOrchestrationTests.claim
    plan = BatchOrchestrationTests.plan
    query_claim = BatchOrchestrationTests.query_claim
    validate_claim = BatchOrchestrationTests.validate_claim
    work_validator = BatchOrchestrationTests.work_validator
    validate_claims = BatchOrchestrationTests.validate_claims
    factory = BatchOrchestrationTests.factory
    run_batch = BatchOrchestrationTests.run_batch
    assert_no_permission = BatchOrchestrationTests.assert_no_permission

    def test_killed_coordinator_leaves_no_permission_and_can_resume_same_claims(self):
        # Fork an isolated engine, block inside one graph-boundary call, then
        # terminate it. flock must release on process death; evidence stays.
        import multiprocessing
        context = multiprocessing.get_context('fork')
        entered = context.Event()
        def pause(action, packets):
            if action == 'prepare':
                entered.set()
                time.sleep(30)
        self.hook = pause
        process = context.Process(target=self.run_batch)
        process.start()
        try:
            self.assertTrue(entered.wait(5), 'child did not reach builder boundary')
            process.terminate()
            process.join(5)
            self.assertFalse(process.is_alive())
            self.assert_no_permission()
            output = self.root / 'temp/recovery-work/batch'
            with (output / 'coordinator.lock').open('a') as stream:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Child used fake in-memory claim records. Restore their exact
            # saved identities from durable request evidence, never reclaim.
            self.claims = {json.loads(p.read_text())['task_id']:
                           json.loads(p.read_text())['work_binding']
                           for p in (output / 'packets').glob('*/request.json')}
            self.assertEqual(len(self.claims), 4)
            self.hook = None
            self.run_batch(resume=True)
        finally:
            if process.is_alive():
                process.terminate()
                process.join(5)

    def test_final_packet_tampering_is_not_a_reused_validation_success(self):
        def corrupt(action, packets):
            if action == 'validate':
                path = self.root / packets[0] / 'context.json'
                entry = json.loads(path.read_text())
                entry['source_slices']['functions'] = {}
                path.write_text(json.dumps(entry))
        self.hook = corrupt
        with self.assertRaises(ContextError):
            self.run_batch()
        self.assert_no_permission()

    def test_mutation_during_builder_is_caught_before_publication(self):
        fired = threading.Event()
        def change(action, packets):
            if action == 'prepare' and not fired.is_set():
                fired.set()
                self.source.write_text('int changed_during_builder;')
        self.hook = change
        with self.assertRaises(ContextError):
            self.run_batch()
        self.assert_no_permission()
        self.assertFalse(any(action == 'validate' for action, _ in self.envs[0].calls))


    def test_unfinalized_and_empty_evidence_fail_fresh_file_barrier(self):
        # A successful container validation cannot bypass this final host gate.
        for mutation in ['selected', 'empty']:
            with self.subTest(mutation=mutation):
                child = BatchOrchestrationTests('test_parallel_builders_obey_selection_limit_and_publish_after_validation')
                child.setUp()
                try:
                    def break_packet(action, packets):
                        if action == 'validate':
                            path = child.root / packets[0] / 'context.json'
                            value = json.loads(path.read_text())
                            if mutation == 'selected': value['state'] = 'selected'
                            if mutation == 'empty': value['source_slices']['functions'] = {}
                            path.write_text(json.dumps(value))
                    child.hook = break_packet
                    with self.assertRaises(ContextError):
                        child.run_batch()
                    child.assert_no_permission()
                finally:
                    child.doCleanups()

    def test_setup_waits_for_real_exclusive_generation_operation(self):
        started = threading.Event()
        finished = threading.Event()
        errors = []
        def prepare():
            started.set()
            try:
                self.run_batch()
            except BaseException as error:
                errors.append(error)
            finally:
                finished.set()
        lock_path = self.root / 'dependency-graph/state/context.lock'
        with lock_path.open('a') as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            thread = threading.Thread(target=prepare)
            thread.start()
            self.assertTrue(started.wait(2))
            self.assertFalse(finished.wait(0.05))
            self.assertFalse(self.claims)
        self.assertTrue(finished.wait(5))
        thread.join(5)
        self.assertFalse(errors)

    def test_injected_resume_uncertainty_flag_is_rejected(self):
        self.fail_task = 'work1'
        with self.assertRaises(ContextError):
            self.run_batch()
        path = self.root / 'temp/recovery-work/batch/packets/work0/request.json'
        request = json.loads(path.read_text())
        request['uncertainty_work'] = True
        path.write_text(json.dumps(request))
        with self.assertRaisesRegex(ContextError, 'Resume request differs'):
            self.run_batch(resume=True)
        self.assert_no_permission()

    def test_changed_resume_task_never_reclaims_work(self):
        self.fail_task = 'work1'
        with self.assertRaises(ContextError):
            self.run_batch()
        before = copy.deepcopy(self.claims)
        task = self.root / 'tasks/0.json'
        value = json.loads(task.read_text())
        value['objective'] = 'edited after failure'
        task.write_text(json.dumps(value))
        with self.assertRaisesRegex(ContextError, 'Frozen batch input changed'):
            self.run_batch(resume=True)
        self.assertEqual(before, self.claims)
        self.assert_no_permission()


if __name__ == '__main__':
    unittest.main()
