import collections,csv,json,sqlite3,subprocess,argparse,sys,os
from pathlib import Path
def load(p):return json.loads(Path(p).read_text())
def db(p):return sqlite3.connect('file:'+p+'?mode=ro',uri=True)
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'uc-library/tools/registry'))
from providers import definitions
VENDOR_IMPORT_SHA256 = 'aa7481c4c75678654e73de1262d5c36070cbad3026cefcaf46350d9cc0ae412e'

def main():
 parser=argparse.ArgumentParser(description='Inspect admitted callers of pinned library implementations')
 parser.add_argument('--out',type=Path,required=True)
 args=parser.parse_args()
 args.out=args.out.resolve()
 os.chdir(ROOT)
 vendor=definitions(VENDOR_IMPORT_SHA256)
 reg=db(load('uc-library/validation/registry-sqlite/ACTIVE.json')['database']['path'])
 admit={(e,n):s for e,n,s in reg.execute('select elf,mangled,status from records')}
 c=db(load('dependency-graph/NATIVE_ACTIVE.json')['database'])
 nodes={i:json.loads(m) for i,m in c.execute("select id,metadata from nodes where kind='NativeFunction'")}
 rev=collections.defaultdict(set)
 for a,b in c.execute("select src,dst from edges where kind in ('ELF_CALLS','ELF_TAIL_BRANCH')"):
  if a in nodes and b in nodes and nodes[a]['elf']==nodes[b]['elf']:rev[b].add(a)
 result={}
 for lib in ('libpng','zlib'):
  keys={(r['elf_sha256'],r['original_mangled'],r['original_address']) for r in vendor if r['vendor']==lib}
  src={i for i,m in nodes.items() if (m['elf'],m['mangled'],m['address']) in keys}
  q=collections.deque(sorted(src)); nxt=dict.fromkeys(q)
  while q:
   b=q.popleft()
   for a in sorted(rev[b]):
    if a not in nxt:nxt[a]=b;q.append(a)
  rows=[]
  for i in nxt:
   m=nodes[i];key=m['elf'],m['mangled']
   if key not in admit or i in src:continue
   path=[i]
   while nxt[path[-1]]:path.append(nxt[path[-1]])
   rows.append(dict(role=m['role'],status=admit[key],mangled=m['mangled'],steps=len(path)-1,path=[nodes[a]['demangled'] for a in path]))
  result[lib]=rows
  print(lib,len(rows),collections.Counter((r['role'],r['steps']==1) for r in rows))
  for r in sorted(rows,key=lambda r:r['steps'])[:12]: print(r['role'],r['status'],r['steps'],r['path'][:5])
  names={n for _,n,_ in keys}
  for f in Path('temp/core-upstream/root-integration-01').glob('libpresonus*_components.a'):
   out=subprocess.check_output(['nm','-A','-u',str(f)],text=True,stderr=subprocess.DEVNULL)
   print(f.name,sorted({l.split(':')[-2]+': '+l.split()[-1] for l in out.splitlines() if l.split() and l.split()[-1] in names})[:25])
 args.out.parent.mkdir(parents=True,exist_ok=True)
 with args.out.open('x') as output:output.write(json.dumps(result,indent=2)+'\n')

if __name__ == "__main__":
 main()
