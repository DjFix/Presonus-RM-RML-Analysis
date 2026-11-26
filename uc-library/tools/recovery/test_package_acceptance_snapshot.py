"""Finite offline fixtures only; never opens the operational database."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('package_snapshot', HERE / 'package_acceptance_snapshot.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
ELF_A, ELF_B = 'a' * 64, 'b' * 64


def fixture():
    rows = [{'elf': elf, 'mangled': name, 'role': role}
            for elf, role in [(ELF_A, 'client'), (ELF_B, 'server')]
            for name in ['_ZN1AC1Ev', '_ZN1AC2Ev']]
    package = {'user_denominator': {'components': {'cohort': 1}, 'unique_methods': 1,
                                    'minimum_canonical_accepted_methods': 1}}
    membership = {'scopes': {'cohort': [{'method': 'A::A()', 'originals': rows,
                                        'excluded_thunk_identities': [{'elf': ELF_A, 'mangled': '_ZThn4_N1A1fEv'}]}]},
                  'overlaps': {}, 'grouping_issues': []}
    return package, membership


def record(identity, status='ready'):
    return {'id': 1, 'status': status, 'elf': identity['elf'], 'mangled': identity['mangled'],
            'proof': None, 'metadata': json.dumps({'original_elf_sha256': identity['elf'],
                                                  'mangled': identity['mangled']})}


class PackageFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=HERE, prefix='offline-accounting-')
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_partial_variant_or_role_never_credits_method(self):
        p, membership = fixture()
        methods, excluded = m.validate_membership(p, membership)
        rows = methods[0]['ordinary_identities']
        records = {(r['elf'], r['mangled']): record(r) for r in rows[:-1]}
        counts, groups = m.tally(methods, records)
        self.assertEqual(counts['cohort']['canonical_admitted'], 0)
        self.assertEqual(counts['cohort']['missing_identities'], 1)
        self.assertFalse(groups[0]['canonical_admitted'])
        self.assertEqual(len(excluded), 1)

    def test_all_roles_and_variants_one_credit_mixed_classifications(self):
        p, membership = fixture()
        methods, _ = m.validate_membership(p, membership)
        rows = methods[0]['ordinary_identities']
        records = {(r['elf'], r['mangled']): record(r, 'ready' if n % 2 else 'pending')
                   for n, r in enumerate(rows)}
        counts, groups = m.tally(methods, records)
        self.assertEqual(counts['cohort']['canonical_admitted'], 1)
        self.assertEqual(counts['cohort']['mixed_ready_pending'], 1)
        self.assertEqual(counts['cohort']['ready_identities'], 2)
        self.assertEqual(counts['cohort']['pending_identities'], 2)
        self.assertEqual(groups[0]['classification'], 'mixed_ready_pending')

    def test_duplicate_method_across_groups_rejected(self):
        p, membership = fixture()
        p['user_denominator'].update(components={'cohort': 1, 'other': 1}, unique_methods=2,
                                     minimum_canonical_accepted_methods=2)
        membership['scopes']['other'] = membership['scopes']['cohort']
        with self.assertRaisesRegex(ValueError, 'Duplicate method'):
            m.validate_membership(p, membership)

    def test_identity_cannot_credit_two_methods(self):
        p, membership = fixture()
        p['user_denominator'].update(components={'cohort': 2}, unique_methods=2,
                                     minimum_canonical_accepted_methods=2)
        membership['scopes']['cohort'].append({'method': 'A::other()', 'originals': membership['scopes']['cohort'][0]['originals']})
        with self.assertRaisesRegex(ValueError, 'Duplicate ordinary identity'):
            m.validate_membership(p, membership)

    def test_existing_output_is_preserved(self):
        output = self.root / 'receipt'
        output.mkdir()
        marker = output / 'SNAPSHOT.json'
        marker.write_text('original evidence\n')
        with self.assertRaises(FileExistsError):
            m.reserve_output(output)
        self.assertEqual(marker.read_text(), 'original evidence\n')

    def test_exact_sql_reader_closes_and_excludes_thunk(self):
        p, membership = fixture()
        methods, _ = m.validate_membership(p, membership)
        db = self.root / 'fixture.sqlite'
        connection = sqlite3.connect(db)
        connection.execute('CREATE TABLE records(id INTEGER,status TEXT,elf TEXT,mangled TEXT,proof TEXT,metadata TEXT,UNIQUE(elf,mangled))')
        row = record(methods[0]['ordinary_identities'][0])
        connection.execute('INSERT INTO records VALUES(:id,:status,:elf,:mangled,:proof,:metadata)', row)
        connection.commit()
        connection.close()
        keys = {(v['elf'], v['mangled']) for g in methods for v in g['ordinary_identities']}
        records, reader = m.snapshot_records(db, keys)
        self.assertTrue(reader['connection_closed'])
        self.assertEqual(reader['exact_identity_queries'], 4)
        self.assertEqual(sum(v is not None for v in records.values()), 1)
        self.assertFalse(any(k[1].startswith('_ZTh') for k in records))
        # No lingering snapshot reader: a fixture exclusive write starts now.
        with sqlite3.connect(db, timeout=0) as check:
            check.execute('BEGIN EXCLUSIVE')

    def test_frozen_hashes_detect_membership_changes(self):
        p, membership = fixture()
        package = self.root / 'PACKAGE171.json'
        package.write_text(json.dumps(p))
        member = self.root / 'MEMBERSHIP.json'
        member.write_text(json.dumps(membership))
        inventory = self.root / 'INVENTORY.json'
        inventory.write_text(json.dumps({'files': {package.name: m.digest(package), member.name: m.digest(member)}}))
        m.load_package(package, m.digest(package), m.digest(inventory))
        member.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Membership differs'):
            m.load_package(package)

    def test_record_identity_mismatch_no_credit(self):
        p, membership = fixture()
        methods, _ = m.validate_membership(p, membership)
        records = {(r['elf'], r['mangled']): record(r) for r in methods[0]['ordinary_identities']}
        first = next(iter(records))
        records[first]['metadata'] = json.dumps({'mangled': '_Zwrong'})
        counts, _ = m.tally(methods, records)
        self.assertEqual(counts['cohort']['canonical_admitted'], 0)

    def test_proof_hash_observation_is_not_freshness(self):
        proof = self.root / 'proof.json'
        proof.write_text('{"passed": true}')
        row = {'proof': 'proof.json', 'metadata': json.dumps({'validation_sha256': m.digest(proof)})}
        observation = m.proof_observation(row, self.root, {})
        self.assertTrue(observation['matches_record_expected'])
        self.assertFalse(observation['freshness_checked'])


if __name__ == '__main__':
    unittest.main()
