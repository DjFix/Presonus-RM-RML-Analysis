"""Scope unchanged Preset native packet lookup to an explicitly hash-bound set."""
import argparse,hashlib,importlib.util,json,pathlib,runpy,sys
p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--checker',required=True);p.add_argument('args',nargs=argparse.REMAINDER);a=p.parse_args();m=json.loads(pathlib.Path(a.manifest).read_text());root=pathlib.Path.cwd();checker=pathlib.Path(a.checker).resolve();native=checker.with_name('native.py');sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
assert sha(native)==m['preset_native_sha256'];assert sha(checker)==m['preset_checker_sha256']
contexts=root/m['scoped_context_directory'];expected={}
for row in m['required_aliases']:
 q=root/row['alias'];assert sha(q)==row['sha256'];expected[q.resolve()]=row['sha256']
assert {q.resolve() for q in contexts.glob('*/CONTEXT.json')}==set(expected),'Unexpected or missing context in scoped runtime directory'
sys.path.insert(0,str(checker.parent));spec=importlib.util.spec_from_file_location('native',native);module=importlib.util.module_from_spec(spec);sys.modules['native']=module;spec.loader.exec_module(module);module.PACKETS=contexts
sys.argv=[str(checker),*(a.args[1:] if a.args[:1]==['--'] else a.args)];runpy.run_path(str(checker),run_name='__main__')
