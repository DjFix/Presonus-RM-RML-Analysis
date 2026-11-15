SOURCES=['uc-library/include/presonus/panel/StormPanelRegistrar.hpp', 'uc-library/src/Presonus/Panel/StormPanelRegistrar.cpp', 'uc-library/tests/recovery/compact20_panel_registrars_02/Replay.cpp']
import argparse,json,hashlib,subprocess,sys,datetime
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--fixtures',required=True);p.add_argument('--proof');a=p.parse_args();f=json.loads(Path(a.fixtures).read_text());exe=Path(a.exe).resolve();commands=[]
for c in f['cases']:
 argv=[str(exe),str(c['group'])];r=subprocess.run(argv,text=True,capture_output=True,check=True);assert list(map(int,r.stdout.split()))==c['expected'],(c,r.stdout);commands.append({'argv':argv,'returncode':r.returncode})
names=subprocess.check_output(['nm','--defined-only',str(exe)],text=True);assert f['target']['mangled'] in {line.split()[-1] for line in names.splitlines() if line.split()}
proof={'version':1,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cpp_differential_passed':True,'compiled_mangled_names_matched':True,'functions':[dict(f['target'],original_elf_sha256=f['target']['original_elf_sha256'],cases=len(f['cases']),domain=f['domain'])],'commands':commands,'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'fixtures_sha256':hashlib.sha256(Path(a.fixtures).read_bytes()).hexdigest(),'producer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'native_producer_sha256':f['native_producer_sha256'],'native_range':f['range'],'portable_ready':False,'declaration_uncertainties':['Original return declaration is unencoded and unresolved; source port return spelling is provisional.'],'source_bindings':{}}
for path in SOURCES:
 q=Path(path);proof['source_bindings'][path]=hashlib.sha256(q.read_bytes()).hexdigest()
if a.proof:
 dest=Path(a.proof);assert not dest.exists(),'Proof output must be new';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps({'passed':True,'cases':len(f['cases']),'mangled':f['target']['mangled']}))
