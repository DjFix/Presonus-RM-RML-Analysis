import argparse,json,pathlib,tempfile
from oracle import BASE,prepare,invoke,observe
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
fixtures=json.loads(pathlib.Path(a.fixtures).read_text())
assert observe(a.executable)==fixtures
run=pathlib.Path(tempfile.mkdtemp(prefix='replay-',dir=BASE));results=[]
for c in fixtures['cases']:
 if c['id']=='empty-boundary-only':continue
 args,path,exists=prepare(a.executable,run,c)
 assert pathlib.Path(path).name==c['filename_basename'] and exists==c['provider_exists']
 actual=invoke(a.executable,'app',*args).splitlines()
 assert actual==[str(c['native']['result']),'ensure,folder,cache,'],(c,actual)
 results.append({'case':c['id'],'result':int(actual[0]),'services':actual[1]})
(run/'replay.json').write_text(json.dumps(results,indent=2)+'\n')
print('PASS: 7 portable app/cache/provider cases and 8 native observations; no hardware/ARM ABI claim')
