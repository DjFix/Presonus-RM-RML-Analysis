import importlib.util,json,pathlib,sys
p=pathlib.Path(__file__).resolve();common=p.parent.parent/'compact20_surface_fx_pages_02/native.py';spec=importlib.util.spec_from_file_location('fx_native',common);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
task=p.parent.name;out=m.generate(task);f=p.parent/'fixtures.json'
if '--verify' in sys.argv:assert json.loads(f.read_text())==out
else:f.write_text(json.dumps(out,indent=2)+'\n')
print(task,len(out['cases']),'independent original executions')
