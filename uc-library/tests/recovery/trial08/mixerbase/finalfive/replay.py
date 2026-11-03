"""Canonical replay: explicit built executables vs original/provider fixture observations."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--raw-executable',required=True);p.add_argument('--fixtures-dir',required=True);a=p.parse_args()
exe=Path(a.executable).resolve();raw=Path(a.raw_executable).resolve();fixtures=Path(a.fixtures_dir).resolve()
root=Path(__file__).resolve().parents[6]
scratch=root/'temp/test-work/trial08-mixerbase-finalfive';scratch.mkdir(parents=True,exist_ok=True)
run=Path(tempfile.mkdtemp(prefix='replay-',dir=scratch))
def execute(args,cwd=None):return json.loads(subprocess.check_output([str(exe),*map(str,args)],cwd=cwd,text=True,timeout=30))
count=0; observations=[]
for c in json.loads((fixtures/'naming-fixtures.json').read_text())['cases']:
 out=execute([8,c['cascade_bits'],c['count'],c['index'],c['missing'],c['custom']]);expected={k:c[k] for k in ('pending','states','trace')}
 assert out==expected,(c,out);count+=1
for n,c in enumerate(json.loads((fixtures/'permissions-fixtures.json').read_text())['cases']):
 directory=run/f'permissions-{n}';directory.mkdir()
 out=execute([7,c['present'],directory,c['current'],c['default']]);assert out['code']==c['code'],(c,out)
 if c['present']:
  path=Path(out['path']);assert path.is_relative_to(directory);assert str(path.relative_to(directory))==c['relative_path'];assert json.loads(path.read_text())==c['saved']
 else:assert out['path']==''
 count+=1
symbols=subprocess.check_output(['nm','--defined-only',str(exe)],text=True)
ends={9:'EN24StorageCompletionHandlerD0Ev',10:'EN17CompletionHandlerD0Ev'}
callbacks={c['method']:c for c in json.loads((fixtures/'callback-fixtures.json').read_text())['cases']}
for n,c in enumerate(json.loads((fixtures/'lifecycle-fixtures.json').read_text())['cases']):
 method=c['packet'];offset=int(next(line.split()[0] for line in symbols.splitlines() if line.endswith(ends[method])),16)
 directory=run/f'lifecycle-{n}';directory.mkdir();filename=callbacks[method]['filename']
 out=execute([method,filename,offset],directory)
 assert c['actual_host_free'] and c['allocator_reused_freed_storage'] and c['guest_object_unmapped_after_free']
 assert out['actual_frees']==int(c['actual_host_free']) and out['symbol_mapped']
 assert out['trace']==callbacks[method]['trace'],(c,out)
 assert json.loads((directory/filename).read_text())==json.loads((fixtures/'storage-fixture.json').read_text())
 observations.append(out);count+=1
directory=run/'scene-without-handler';directory.mkdir()
no_handler=execute([11,'result.scene',0],directory)
assert no_handler=={'queued':True} and json.loads((directory/'result.scene').read_text())==json.loads((fixtures/'storage-fixture.json').read_text())
subprocess.run([str(exe),'0'],check=True,stdout=subprocess.DEVNULL,timeout=30)
legacy=fixtures.parent/'fixtures.json'
for c in json.loads(legacy.read_text())['cases']:
 out=subprocess.check_output([str(raw),str(c['method']),str(c['value']),str(c['initial_flag'])],text=True).strip()
 expected=str(c['expected'])+'\n'+' '.join(map(str,c['observed_state']))
 assert out==expected,(c,out);count+=1
print(json.dumps({'result':'PASS','cases':count,'local_lifecycle_observations':observations,'scope':'original/native-provider fixture equality; raw getters and explicit binding guards; file writes limited to project temp'},indent=2))
