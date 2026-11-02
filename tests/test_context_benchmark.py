"""Benchmark isolation/equivalence regression tests; no Docker or production writes."""
import pathlib
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'dependency-graph'))
from benchmark_context_batch import backup, normalize, run_one, BenchmarkEnvironment, canonical_packet, canonical_context_markdown
import benchmark_context_batch as benchmark


class BenchmarkTests(unittest.TestCase):
    def test_normalization_retains_scientific_identities_and_input_hashes(self):
        baseline = {'originals':[{'elf':'elf-one','mangled':'_ZN4Core1fEv','address':123,'size':12}],
                    'generation_sha256':'generation', 'tool_sha256':{'operator':'hash'},
                    'selected_file_sha256':{'source.cpp':'source-hash'},
                    'work_binding':{'claim_id':'one','database':'one.sqlite','work_item_id':'work'}}
        other = {'originals':baseline['originals'], 'generation_sha256':'generation',
                 'tool_sha256':baseline['tool_sha256'], 'selected_file_sha256':baseline['selected_file_sha256'],
                 'work_binding':{'claim_id':'two','database':'two.sqlite','work_item_id':'work'}}
        self.assertEqual(normalize(baseline, []), normalize(other, []))
        other['originals'] = [{'elf':'elf-two','mangled':'_ZN4Core1fEv','address':123,'size':12}]
        self.assertNotEqual(normalize(baseline, []), normalize(other, []))
        other['originals'] = baseline['originals']
        other['selected_file_sha256'] = {'source.cpp':'changed'}
        self.assertNotEqual(normalize(baseline, []), normalize(other, []))

    def test_normalization_does_not_hide_unrelated_database_or_claim_fields(self):
        self.assertNotEqual(normalize({'metadata':{'database':'one'}}, []),
                            normalize({'metadata':{'database':'two'}}, []))
        self.assertNotEqual(normalize({'metadata':{'claim_id':'one'}}, []),
                            normalize({'metadata':{'claim_id':'two'}}, []))

    def test_run_paths_normalized_in_keys_and_values(self):
        self.assertEqual(normalize({'run-a/file': ['run-a/file']}, ['run-a']),
                         normalize({'run-b/file': ['run-b/file']}, ['run-b']))

    def test_sqlite_backup_captures_committed_wal_and_preserves_source(self):
        scratch = ROOT/'temp/test-work'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            source = pathlib.Path(directory)/'source.sqlite'
            destination = pathlib.Path(directory)/'copy.sqlite'
            connection = sqlite3.connect(source)
            try:
                connection.execute('PRAGMA journal_mode=WAL')
                connection.execute('CREATE TABLE claims(id,state)')
                connection.execute('INSERT INTO claims VALUES(1,"completed")')
                connection.commit()
                backup(source, destination)
                with sqlite3.connect(destination) as copied:
                    self.assertEqual(copied.execute('SELECT * FROM claims').fetchall(), [(1,'completed')])
                    copied.execute('UPDATE claims SET state="active"')
                    copied.commit()
                self.assertEqual(connection.execute('SELECT * FROM claims').fetchall(), [(1,'completed')])
            finally:
                connection.close()

    def test_unordered_context_fields_preserve_content_and_multiplicity(self):
        a = {'unknowns':[{'from':'a','target':'x'},{'from':'b','target':'y'},{'from':'b','target':'y'}],
             'inclusion_reasons':{'f':['a','b','b']}, 'source_files':['first','second'], 'slice_translation_units':['a.cpp','b.cpp','b.cpp']}
        b = {'unknowns':list(reversed(a['unknowns'])), 'inclusion_reasons':{'f':['b','a','b']},
             'source_files':['first','second'], 'slice_translation_units':['b.cpp','a.cpp','b.cpp']}
        self.assertEqual(canonical_packet(a,[]),canonical_packet(b,[]))
        b['slice_translation_units'] = ['a.cpp','b.cpp']
        self.assertNotEqual(canonical_packet(a,[]),canonical_packet(b,[]))
        b['slice_translation_units'] = ['a.cpp','b.cpp','CHANGED.cpp']
        self.assertNotEqual(canonical_packet(a,[]),canonical_packet(b,[]))
        b['slice_translation_units'] = a['slice_translation_units']
        b['unknowns'] = b['unknowns'][1:]
        self.assertNotEqual(canonical_packet(a,[]),canonical_packet(b,[]))
        b['unknowns'] = a['unknowns']
        b['inclusion_reasons'] = {'f':['a','b']}
        self.assertNotEqual(canonical_packet(a,[]),canonical_packet(b,[]))
        b['inclusion_reasons'] = a['inclusion_reasons']
        b['source_files'] = ['second','first']
        self.assertNotEqual(canonical_packet(a,[]),canonical_packet(b,[]))
        b['source_files'] = a['source_files']
        b['unknowns'] = [{'from':'a','target':'CHANGED'},*a['unknowns'][1:]]
        self.assertNotEqual(canonical_packet(a,[]),canonical_packet(b,[]))

    def test_markdown_normalization_retains_body_order_and_unknown_duplicates(self):
        def doc(head, values):
            import json
            return head+'\n## Unknowns\n\n'+json.dumps(values)+'\n\nNo validation gate is waived.\n'
        a = doc('source body line1\nsource body line2',[{'target':'x'},{'target':'y'},{'target':'y'}])
        b = doc('source body line1\nsource body line2',[{'target':'y'},{'target':'x'},{'target':'y'}])
        self.assertEqual(canonical_context_markdown(a),canonical_context_markdown(b))
        dropped = doc('source body line1\nsource body line2',[{'target':'x'},{'target':'y'}])
        changed = doc('source body line1\nsource body line2',[{'target':'CHANGED'},{'target':'y'},{'target':'y'}])
        reordered = doc('source body line2\nsource body line1',[{'target':'x'},{'target':'y'},{'target':'y'}])
        for other in (dropped,changed,reordered):
            self.assertNotEqual(canonical_context_markdown(a),canonical_context_markdown(other))

    def test_isolation_replaces_frozen_pointer_without_duplicate_docker_mount(self):
        class CaptureHarness:
            def __init__(self):
                self.active_containers, self.argv = [], None
            def docker(self, argv, phase):
                self.argv = argv
        scratch = ROOT/'temp/test-work'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            output = pathlib.Path(directory)
            harness = CaptureHarness()
            environment = BenchmarkEnvironment(ROOT, output, harness)
            target = str(ROOT/'dependency-graph/DEDUP_ACTIVE.json')
            frozen = str(output/'snapshot/dependency-graph/DEDUP_ACTIVE.json')
            environment.command(['docker','run','-d','--name','fixture',
                                 '-v',frozen+':'+target+':ro','--user','1000:1000','image'], 'environment')
            volumes = [harness.argv[i+1] for i, x in enumerate(harness.argv[:-1]) if x == '-v']
            destinations = [v.split(':')[1] for v in volumes]
            self.assertEqual(len(destinations), len(set(destinations)))
            self.assertIn(str(output/'DEDUP_ACTIVE.json')+':'+target+':ro', volumes)
            self.assertFalse(any(v.startswith(frozen+':') for v in volumes))

    def test_pipeline_counts_shutdown_and_excludes_optional_observation(self):
        clock = [0.0]
        def advance(seconds):
            clock[0] += seconds
        class FakeHarness:
            def __init__(self, output):
                self.receipts, self.active_containers = [], []
            def observe_storage(self, container=None):
                advance(100)
                return {'available':True,'seconds':100}
            def execute(self, args, phase, *unused):
                advance(1)
                self.receipts.append({'phase':phase,'seconds':1})
            def stop(self):
                advance(7)
        def isolated(output, *unused):
            output.mkdir()
            advance(3)
            return ['unused-test-packet']
        scratch = ROOT/'temp/test-work'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            output = pathlib.Path(directory)/'result'
            with patch.object(benchmark,'Harness',FakeHarness), \
                 patch.object(benchmark,'create_run',isolated), \
                 patch.object(benchmark,'choose_limits',return_value={'selection_jobs':1,'slicing_jobs':1,'builder_jobs':1}), \
                 patch.object(benchmark.time,'perf_counter',side_effect=lambda:clock[0]):
                result = run_one(output, [], 'legacy', '1', None, None)
            self.assertEqual(result['errors'], [])
            self.assertEqual(result['isolation_seconds'], 3)
            self.assertEqual(result['builder_validation_wall_seconds'], 4)
            self.assertEqual(result['shutdown_seconds'], 7)
            self.assertEqual(result['pipeline_wall_seconds'], 11)
            self.assertEqual(result['observation_overhead_seconds'], 200)

    def test_missing_backup_source_does_not_create_database(self):
        scratch = ROOT/'temp/test-work'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            source = pathlib.Path(directory)/'absent.sqlite'
            with self.assertRaises(sqlite3.OperationalError):
                backup(source, pathlib.Path(directory)/'copy.sqlite')
            self.assertFalse(source.exists())


if __name__ == '__main__':
    unittest.main()
