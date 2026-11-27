"""Operational consumers must use admitted SQLite state, never JSON overlays."""
import contextlib
import json
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent / 'registry'))
from adapter import catalog_roles
import uc_registration_map


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.c = sqlite3.connect(':memory:')
        self.addCleanup(self.c.close)
        self.c.executescript("""
            CREATE TABLE catalog_symbols(elf,role,firmware,mangled,demangled,address,
              size,section_json,kind,binding,policy,anchor);
            CREATE TABLE catalog_inputs(path,metadata);
        """)
        self.c.execute("INSERT INTO catalog_symbols VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            ('elf','client','13840','f','f()',16,0,'12','STT_FUNC','GLOBAL',
             'core-source-provided','a'))
        self.c.execute("INSERT INTO catalog_inputs VALUES(?,?)",
            ('recovered-all/client/manifest.json',json.dumps({'sha256':'elf','path':'original.elf'})))

    def test_catalog_retains_zero_size_identity_and_provider_policy(self):
        role = catalog_roles(self.c)['client']
        self.assertEqual(role['manifest']['path'], 'original.elf')
        symbol = role['symbols'][0]
        self.assertEqual(symbol['size'], 0)
        self.assertTrue(symbol['defined'])
        self.assertTrue(symbol['upstream_body_available'])
        self.assertNotIn('portable_ready', symbol)
        self.assertNotIn('bytes_verified', symbol)

    def test_manifest_mismatch_fails(self):
        self.c.execute("UPDATE catalog_inputs SET metadata=?", (json.dumps({'sha256':'wrong'}),))
        with self.assertRaises(ValueError):
            catalog_roles(self.c)

    def test_missing_manifest_fails(self):
        self.c.execute('DELETE FROM catalog_inputs')
        with self.assertRaises(ValueError):
            catalog_roles(self.c)

    def test_multiple_generations_fail(self):
        self.c.execute("INSERT INTO catalog_symbols SELECT 'other',role,firmware,mangled,"
                       "demangled,address,size,section_json,kind,binding,policy,'b' FROM catalog_symbols")
        with self.assertRaises(ValueError):
            catalog_roles(self.c)

    def test_current_consumers_do_not_reintroduce_legacy_registries(self):
        tools = Path(__file__).resolve().parent
        for name in ('uc_registration_map.py', 'audit_role_build.py',
                     'recovery/count_current_unique.py',
                     'recovery/generate_hal_symbol_tracking.py'):
            source = (tools / name).read_text()
            for retired in ('ready-functions.json', 'compiled-functions.json',
                            'tracking/coverage.json'):
                self.assertNotIn(retired, source, name)

    def test_registration_only_uses_admitted_snapshot(self):
        class Snapshot:
            c = self.c
            ready = {'functions':[{'mangled':'admitted','original_elf_sha256':'elf'}]}
            def provenance(self):
                return {'database':'fixture'}
        with patch.object(uc_registration_map, 'snapshot',
                          return_value=contextlib.nullcontext(Snapshot())):
            # No files exist here: no ledger, coverage JSON or pending fragments.
            roles, ready, provenance = uc_registration_map.registration_inputs(Path('absent'))
        self.assertEqual(ready, {('admitted','elf')})
        self.assertEqual(roles['client']['summary']['sha256'], 'elf')
        self.assertEqual(provenance['database'], 'fixture')


if __name__ == '__main__':
    unittest.main()
