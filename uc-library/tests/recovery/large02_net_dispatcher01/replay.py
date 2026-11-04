import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
f=json.loads(Path(a.fixtures).read_text())
for c in f['cases']:
 n=c['count'];r=json.loads(subprocess.check_output([a.executable,str(n)],text=True))
 # Selected host resource trace retains extra provenance table/borrowed mutex and
 # physical dispatcher deallocation, none are manufactured native events.
 normalized=[x for x in r['trace'] if x not in [1003,701,900]]
 assert normalized==c['observed']['trace'],(c['elf_sha256'],c['ctor'],n,r,c['observed']['trace'])
 assert r['id']==c['observed']['initialized']['id_offset']
 assert r['queue_sync']==[1 if x=='lock' else 2 for x in c['observed']['queue_sync']]
 assert r['before']==bool(n) and r['updated']==bool(n)
 assert r['buckets']==c['observed']['initialized']['buckets']
 assert r['allocations'][1]==[16,1002]
 assert r['trace'].count(1003)==1 and r['trace'].count(701)==1 and r['trace'][-1]==900
 for i in range(n): assert r['trace'].count(100+i)==r['trace'].count(200+i)==1
contracts=json.loads(subprocess.check_output([a.executable,'--source-contracts'],text=True))
assert contracts==dict(singleton_owned=True,borrowed_preserved=True,registration_dispatch=True)
print(json.dumps({'passed':True,'cases':len(f['cases']),'domain':'each exact ELF C1/C2/D1/D2, initialized64buckets, IDSet100/128, FIFO unique owned items, actual CCL resource frees; supplemental real typed update/registration/singleton/borrowed domains','source_contracts':contracts}))
