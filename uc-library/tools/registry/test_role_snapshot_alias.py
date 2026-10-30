"""Execute the actual role reader AST stage with its existing snapshot dict."""
import ast
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
import adapter
import registry as reg
import test_workflow as fixtures

ROOT=Path(__file__).resolve().parents[3]
ROLE=ROOT/'uc-library/tools/recovery/audit_role_build_basic_activity.py'

def actual_and_preimage():
    current=ROLE.read_text()
    assert current.count('from adapter import snapshot as registry_snapshot\n')==1
    assert current.count('with registry_snapshot(lib,args.registry_db) as registry:')==1
    preimage=current.replace('from adapter import snapshot as registry_snapshot\n','from adapter import snapshot\n').replace('with registry_snapshot(lib,args.registry_db) as registry:','with snapshot(lib,args.registry_db) as registry:')
    return current,preimage

class RoleSnapshotAliasTests(unittest.TestCase):
    setUp=fixtures.WorkflowTests.setUp
    def stage(self,text):
        tree=ast.parse(text);main=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='main')
        source_hashes=next(x for x in main.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='snapshot' for t in x.targets))
        reader=next(x for x in main.body if isinstance(x,ast.With) and isinstance(x.items[0].context_expr,ast.Call) and isinstance(x.items[0].context_expr.func,ast.Name) and x.items[0].context_expr.func.id in ('snapshot','registry_snapshot'))
        required=next(x for x in main.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='required' for t in x.targets))
        per_role=next(x for x in main.body if isinstance(x,ast.For) and isinstance(x.target,ast.Tuple) and any(isinstance(v,ast.Name) and v.id=='role' for v in x.target.elts))
        for value in ast.walk(source_hashes):
            if isinstance(value,ast.Constant) and isinstance(value.value,str):
                path=self.lib/value.value;path.parent.mkdir(parents=True,exist_ok=True)
                if not path.exists():path.write_text('synthetic context fixture\n')
        body=copy.deepcopy([source_hashes,reader,required,per_role])
        body.append(ast.parse('return snapshot,ready,registry_source,required').body[0])
        fn=ast.FunctionDef(name='actual_role_reader_stage',args=ast.arguments(posonlyargs=[],args=[ast.arg(arg='lib'),ast.arg(arg='args'),ast.arg(arg='all_sources')],kwonlyargs=[],kw_defaults=[],defaults=[]),body=body,decorator_list=[])
        module=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]));namespace={'snapshot':adapter.snapshot,'registry_snapshot':adapter.snapshot,'sha':reg.digest,'json':json}
        exec(compile(module,'<actual-role-reader-stage>','exec'),namespace)
        return namespace['actual_role_reader_stage'](self.lib,SimpleNamespace(registry_db=self.db),set())
    def test_actual_preimage_reproduces_shadowing_and_alias_executes_stage(self):
        new,old=actual_and_preimage()
        with self.assertRaises(TypeError):self.stage(old)
        source_hashes,ready,provenance,required=self.stage(new)
        self.assertIsInstance(source_hashes,dict);self.assertEqual([r['mangled'] for r in ready],['a']);self.assertIn('guard',provenance)
        self.assertEqual(required['presonus_uc'],{'a'});self.assertEqual(required['presonus_cs18_components'],{'a'})
    def test_patch_changes_only_two_names_preserving_every_policy_assertion(self):
        new,old=actual_and_preimage()
        expected=old.replace('from adapter import snapshot\n','from adapter import snapshot as registry_snapshot\n').replace('with snapshot(lib,args.registry_db) as registry:','with registry_snapshot(lib,args.registry_db) as registry:')
        self.assertEqual(new,expected)
        assertions=lambda s:[ast.dump(x,include_attributes=False) for x in ast.walk(ast.parse(s)) if isinstance(x,ast.Assert)]
        self.assertEqual(assertions(old),assertions(new));self.assertEqual(len(assertions(new)),42)

if __name__=='__main__':unittest.main()
