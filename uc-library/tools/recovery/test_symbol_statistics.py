import hashlib
import json
from pathlib import Path
import sys
import unittest

import symbol_statistics as stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'registry'))
import catalog_models
import orm
import test_workflow


def row(elf, name, status=None, policy='application-or-other', address=1):
    return (elf, elf, elf, name, address, 4, policy, status)


class Counts(unittest.TestCase):
    def test_symbols_update_is_bounded_and_idempotent(self):
        report=stats.aggregate([row('a','f','ready')],[])
        old='Intro\n## Coverage\nold table\n## Partial portable C++ evidence\nKeep this evidence.\n'
        new=stats.update_symbols_document(old,report)
        self.assertTrue(new.startswith('Intro\n'))
        self.assertTrue(new.endswith('## Partial portable C++ evidence\nKeep this evidence.\n'))
        self.assertNotIn('old table',new)
        self.assertEqual(stats.update_symbols_document(new,report),new)
        with self.assertRaises(ValueError):stats.update_symbols_document('No section',report)

    def test_exclusive_and_shared_groups_partition_every_column(self):
        rows = [row('a','only_a','ready'), row('b','only_b','pending'),
                row('a','shared','ready'), row('b','shared'),
                row('a','vendor'), row('b','vendor'),
                row('a','core',policy='core-deferred')]
        result = stats.aggregate(rows, [('a','vendor',1,'zlib'),('b','vendor',1,'zlib')])
        a,b,common,total = result['unique_names']
        self.assertEqual([a['total'],b['total'],common['total'],total['total']], [2,1,2,5])
        self.assertEqual([a['ready'],a['core'],b['pending'],common['zlib']], [1,1,1,1])
        self.assertEqual([common['reconstructed'],common['remaining'],common['partial']], [0,1,1])
        for key in ('total','ready','pending','reconstructed','core','libpng','zlib','remaining','partial'):
            self.assertEqual(a[key]+b[key]+common[key], total[key])

    def test_union_requires_all_roles_and_deduplicates_catalog_rows(self):
        rows = [row('a','f','ready'), row('a','f','ready'), row('b','f'),
                row('a','g','ready'), row('b','g','pending'),
                row('a','h','ready'), row('b','h','ready')]
        result = stats.aggregate(rows, [])
        self.assertEqual(result['elf_symbols'][-1]['total'], 6)
        union = result['unique_names'][-1]
        self.assertEqual([union[k] for k in ('total','ready','pending','remaining','partial')],
                         [3,1,1,1,1])

    def test_exact_provider_address_and_core_are_disjoint(self):
        rows = [row('a','png',address=8), row('b','png',address=9),
                row('a','core',policy='core-deferred')]
        # Same name, different ownership must not be silently merged.
        with self.assertRaisesRegex(ValueError, 'library conflicts'):
            stats.aggregate(rows, [('a','png',8,'libpng')])
        result = stats.aggregate(rows, [('a','png',8,'libpng'),('b','png',9,'libpng')])
        self.assertEqual(result['unique_names'][-1]['libpng'], 1)
        self.assertEqual(result['unique_names'][-1]['core'], 1)

    def test_provider_admission_overlap_rejected(self):
        with self.assertRaisesRegex(ValueError, 'overlap'):
            stats.aggregate([row('a','z','ready')], [('a','z',1,'zlib')])


class ImportTests(unittest.TestCase):
    setUp = test_workflow.WorkflowTests.setUp

    def test_orm_import_idempotence_atomic_rejection_and_sql_only_read(self):
        unit = orm.Unit(self.db, write=True)
        try:
            catalog_models.CatalogSymbol.__table__.create(unit.connection)
            for name in ('a','b','vendor'):
                unit.session.add(catalog_models.CatalogSymbol(anchor=name,elf='elf',
                    role='client',firmware='fixture',mangled=name,demangled=name,
                    address=1,size=4,section_json='1',kind='STT_FUNC',binding='global',
                    policy='application-or-other'))
            unit.commit()
        finally:
            unit.close()
        path = self.root/'providers.json'
        document = {'elfs':[{'sha256':'elf'}], 'definitions':[
            {'elf_sha256':'elf','original_mangled':'vendor',
             'original_address':1,'original_size':4,'section_index':'1','vendor':'zlib'}]}
        path.write_text(json.dumps(document))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        stats.import_providers(path,digest,self.db)
        self.assertTrue(stats.import_providers(path,digest,self.db)['already_imported'])
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            stats.import_providers(path,'wrong',self.db)
        document['definitions'].append(dict(document['definitions'][0], original_mangled='missing'))
        path.write_text(json.dumps(document))
        with self.assertRaisesRegex(ValueError, 'reconciliation|absent'):
            stats.import_providers(path,hashlib.sha256(path.read_bytes()).hexdigest(),self.db)
        path.unlink()  # Reports must not need the imported JSON anymore.
        rows,vendors,provenance = stats.load_facts(self.db)
        self.assertEqual(stats.aggregate(rows,vendors)['elf_symbols'][-1]['zlib'],1)
        self.assertEqual(len(provenance),1)
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(),before)


if __name__ == '__main__':
    unittest.main()
