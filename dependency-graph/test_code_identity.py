import copy
import json
import pathlib
import unittest
from code_identity import CursorCache, context_id, indirect_id, normalize_ast, owner_id

ROOT = pathlib.Path('/project')


class IdentityTests(unittest.TestCase):
    def row(self):
        return {'directory': '/project/build', 'file': '/project/src/a.cpp',
                'command': 'c++ -DROLE=1 -I/project/include -c /project/src/a.cpp -o CMakeFiles/a.dir/a.o'}

    def test_capture_path_and_command_encoding_do_not_change_context(self):
        row = self.row(); other = dict(row, gcc_validation='/new/run/0000.json')
        self.assertEqual(context_id(ROOT, row), context_id(ROOT, other))
        import shlex
        other['arguments'] = shlex.split(other.pop('command'))
        self.assertEqual(context_id(ROOT, row), context_id(ROOT, other))

    def test_flags_and_target_variants_are_distinct(self):
        row = self.row()
        for before, after in [('ROLE=1', 'ROLE=2'), ('a.dir', 'b.dir'), ('include', 'other')]:
            other = dict(row, command=row['command'].replace(before, after))
            self.assertNotEqual(context_id(ROOT, row), context_id(ROOT, other))

    def test_reordering_and_inserting_commands_preserves_existing_owners(self):
        a=self.row(); b=dict(a, command=a['command'].replace('ROLE=1', 'ROLE=2'))
        before={r['command']:owner_id(ROOT, 'app', r) for r in [a,b]}
        after={r['command']:owner_id(ROOT, 'app', r) for r in [b,dict(a,command='c++ -c extra.cpp -o extra.o'),a]}
        self.assertTrue(all(after[k]==v for k,v in before.items()))

    def ast(self, tu):
        site=json.dumps({'path':'src/a.cpp','line':2,'column':3,'tu':tu},sort_keys=True)
        indirect=indirect_id('function:f',site)
        return {'nodes':{tu:{'kind':'TranslationUnit','label':'a','metadata':{'compile_command':self.row()}},indirect:{'kind':'UnresolvedCall','label':'fp','metadata':{'tu':tu}}},
                'edges':[['function:f',indirect,'INDIRECT_CALL',site]],'unresolved':[{'site':json.loads(site)}]}

    def test_legacy_opaque_indirect_id_is_recomputed_before_diff(self):
        a,am=normalize_ast(ROOT,self.row(),self.ast('tu:old'))
        b,bm=normalize_ast(ROOT,self.row(),self.ast('tu:new'))
        self.assertEqual(a,b)
        self.assertNotEqual(am['tu:old'],'tu:old')
        self.assertEqual(normalize_ast(ROOT,self.row(),a)[0],a)
        self.assertEqual(json.loads(a['edges'][0][3])['tu'], 'tu:'+context_id(ROOT,self.row()))

    def test_real_call_site_changes_are_not_ignored(self):
        a=self.ast('tu:old'); b=copy.deepcopy(a)
        site=json.loads(b['edges'][0][3]);site['line']=4;b['edges'][0][3]=json.dumps(site,sort_keys=True)
        self.assertNotEqual(normalize_ast(ROOT,self.row(),a)[0]['edges'],normalize_ast(ROOT,self.row(),b)[0]['edges'])

    def test_hash_collision_does_not_alias_clang_cursors(self):
        class Cursor:
            hash=7
            def __init__(self,name):self.name=name
            def __eq__(self,other):return self.name==other.name
        cache=CursorCache();a=Cursor('a');b=Cursor('b')
        cache.put(a,'function:a');cache.put(b,'data:b')
        self.assertEqual(cache.get(Cursor('a')),'function:a')
        self.assertEqual(cache.get(b),'data:b')
        self.assertIsNone(cache.get(Cursor('c')))




class ProvenanceTests(unittest.TestCase):
    def test_new_capture_does_not_rewrite_logical_edges_and_history_is_retained(self):
        import tempfile
        from unittest.mock import patch
        from refresh_facts import connect, facts, replace
        root=pathlib.Path(__file__).resolve().parents[1]
        base=root/'temp/test-work/identity';base.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as directory:
            folder=pathlib.Path(directory)
            row={'directory':str(folder),'file':str(folder/'a.cpp'),'arguments':['c++','-c',str(folder/'a.cpp'),'-o','a.o']}
            ast={'passed':True,'nodes':{'tu:legacy':{'kind':'TranslationUnit','label':'a','metadata':{}},'function:f':{'kind':'Function','label':'f','metadata':{'mangled':'f'}}},'edges':[]}
            record={'name':'f','number':'1','demangled':'f','calls':[['g','2']],'references':[], 'indirect':['function pointer'], 'definition':True,'type':'function'}
            gp={'returncode':0,'dump_sha256':'old','symbols':{'1':record}}
            first=folder/'first';second=folder/'second';first.mkdir();second.mkdir()
            for dest in (first,second):
                (dest/'ast.json').write_text(json.dumps(ast));(dest/'gcc.json').write_text(json.dumps(gp))
            gp['dump_sha256']='new';(second/'gcc.json').write_text(json.dumps(gp))
            with patch('refresh_facts.catalogs',return_value={}):
                a,ae=facts(root,'app:0001',row,first/'ast.json',first/'gcc.json')
                b,be=facts(root,'app:0999',row,second/'ast.json',second/'gcc.json')
            self.assertEqual(a,b);self.assertEqual(ae,be)
            c=connect(folder/'observations.sqlite')
            for dest,nodes,edges in [(first,a,ae),(second,b,be)]:
                replace(c,'app:stable',row,nodes,edges,{},dest/'ast.json',dest/'gcc.json')
            self.assertEqual(c.execute('SELECT count(*) FROM observations').fetchone()[0],2)
            self.assertEqual(c.execute('SELECT count(*) FROM current_observations').fetchone()[0],1)
            self.assertEqual(c.execute('SELECT count(*) FROM edge_facts').fetchone()[0],len(ae))
            c.close()


class MigrationGateTests(unittest.TestCase):
    def test_legacy_index_is_rejected_without_writing(self):
        import sqlite3
        import tempfile
        from context_runtime import ContextError,sha
        from refresh_graph import check_existing_identity
        from code_identity import VERSION
        root=pathlib.Path(__file__).resolve().parents[1]
        base=root/'temp/test-work/identity';base.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as directory:
            path=pathlib.Path(directory)/'legacy.sqlite'
            with sqlite3.connect(path) as c:c.execute('CREATE TABLE meta(key PRIMARY KEY,value)')
            before=sha(path)
            with self.assertRaises(ContextError):check_existing_identity(path)
            self.assertEqual(sha(path),before)
            with sqlite3.connect(path) as c:c.execute('INSERT INTO meta VALUES(?,?)',('identity_version',str(VERSION)))
            check_existing_identity(path)

if __name__=='__main__':
    unittest.main()
