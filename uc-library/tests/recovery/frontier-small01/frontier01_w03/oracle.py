"""Execute exact original application ranges, never Core instructions.

Provider calls are bounded interceptions with explicit supplied outputs. Complete
application branches, writes and call order are retained. Compare real provider
observations separately; this is not original provider or ARM ABI validation.
"""
from pathlib import Path
import hashlib,itertools,json,struct,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
PACKETS=Path('temp/recovery-work/frontier-small01/batch01/packets')
OBJ,ARENA,STACK,STOP=0x1000000,0x1001000,0x1100000,0x1200000
REGS=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
P={}
def load():
 for i in range(1,8):
  p=PACKETS/f'frontier01_w03_{i:02d}';c=json.loads((p/'context.json').read_text());nc=c['native_context'];nid=c['native_roots'][0];body=nc['bodies'][nid];md=nc['nodes'][nid]['metadata'];ep=Path(nc['binaries'][md['elf']]['path']);raw=ep.read_bytes()
  assert hashlib.sha256(raw).hexdigest()==md['elf']
  with ep.open('rb') as f:
   e=ELFFile(f);section=e.get_section(body['section_index']);assert section.name==body['section'];assert int(section['sh_offset'])+body['address']-int(section['sh_addr'])==body['file_offset']
   segments=[(int(s['p_vaddr']),int(s['p_memsz']),s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
  assert hashlib.sha256(raw[body['file_offset']:body['file_offset']+body['size']]).hexdigest()==body['bytes_sha256']
  calls={x['metadata']['target_address']:nc['nodes'][x['dst']]['label'] for x in nc['edges'] if x['src']==nid and x['kind']=='ELF_CALLS'}
  P[i]=(body,segments,calls,md)
def execute(i,inputs):
 b,segs,callmap,md=P[i];u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
 for addr,size,data in segs:
  for page in range(addr&~4095,(addr+size+4095)&~4095,4096):
   if page not in pages:u.mem_map(page,4096);pages.add(page)
  u.mem_write(addr,data)
 u.mem_map(OBJ,0x10000);u.mem_map(STACK,0x10000);u.mem_map(STOP,4096)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def string(a):
  if not a:return None
  out=bytearray()
  while len(out)<256:
   x=u.mem_read(a+len(out),1)[0]
   if not x:break
   out.append(x)
  return out.decode()
 u.mem_write(OBJ,b'\xa5'*512)
 u.mem_write(ARENA,b'nested\0wanted\0target-name\0')
 bitmaps=[0,ARENA+0x100,ARENA+0x200]
 for ix in [1,2]:w(bitmaps[ix]+8,[0,7,13][ix]);w(bitmaps[ix]+0x34,0)
 trace=[];writes=[];executed=[];nodes={}
 for reg,val in zip(REGS,[OBJ,ARENA+0x800,ARENA+0x900,17]):u.reg_write(reg,val)
 if i==1:
  flags,opt,oi,os,ol,ni,ns,nl,previous=inputs
  w(OBJ+0x40,flags);w(OBJ+0x58,bitmaps[oi]);w(OBJ+0x5c,bitmaps[os]);w(OBJ+0x60,bitmaps[ol]);w(OBJ+0x64,9);w(OBJ+0x68,-1);w(OBJ+0x6c,previous)
  for v in [oi,os,ol]:
   if v:w(bitmaps[v]+0x34,r(bitmaps[v]+0x34)+1)
 elif i==2:
  kind,value=inputs;u.mem_write(OBJ+0xe8,b'\0')
 elif i==3:
  depth,leaf,wrong,present=inputs
  for n in range(depth+1):
   ptr=ARENA+0x1000+n*0x100
   nodes[ptr]={'nested':(ARENA+0x1000+(n+1)*0x100) if n<depth else (1 if wrong else 0),'wanted':bool(present and n==depth)}
  u.reg_write(UC_ARM_REG_R1,0 if leaf==2 else ARENA+0x1000+(depth*0x100 if leaf else 0));u.reg_write(UC_ARM_REG_R2,ARENA);u.reg_write(UC_ARM_REG_R3,ARENA+7)
 else:
  value=inputs[0];u.reg_write(UC_ARM_REG_R3,value&0xffffffff);u.reg_write(UC_ARM_REG_R2,0);u.mem_write(ARENA+0x800,struct.pack('<4i',1,2,30,40))
 def code(uc,addr,size,_):
  if addr in callmap:
   label=callmap[addr];args=[uc.reg_read(x) for x in REGS];entry={'address':addr,'identity':label,'arguments':args};trace.append(entry)
   result=0
   if i in [4,5,6,7]:
    # Source providers observed separately. Prefix memory supplied explicitly;
    # arbitrary synthetic vptrs are replaced by actual original app vptr writes.
    uc.mem_write(OBJ,bytes(0x58 if i in [5,7] else 0xe8));w(OBJ+0x40,18 if i==7 else 0);entry['supplied_base_options']=18 if i==7 else 0;entry['supplied_prefix_zero_bytes']=0x58 if i in [5,7] else 0xe8
   elif i==1:
    if addr==0x1147a4:pass # bounded View call: no supplied style/disabled changes
    elif addr==0x10f83c:
     entry['option_table']=[[string(r(args[1]+8*n)),r(args[1]+8*n+4)] for n in range(3)];entry['key']=string(args[2]);result=[0,0x200000,0x400000,0x600000,0][opt]
    elif addr==0xf940c:
     key=string(args[2]);entry['key']=key;v={'image':ni,'focusStrip':ns,'focusSlice':nl}[key];ptr=bitmaps[v]
     entry['supplied_bitmap_pointer']=ptr
     if ptr:
      entry['reference_count_before']=r(ptr+0x34);w(ptr+0x34,r(ptr+0x34)+1);entry['reference_count_after']=r(ptr+0x34)
     w(args[0],ptr);result=args[0]
    else:raise AssertionError(label)
   elif i==2:
    if addr==0x124200:
     entry['key']=string(args[1]);result=ARENA+14 if kind in [1,2] else 0
     if kind==2:uc.mem_write(ARENA+14,b'\0')
   elif i==3:
    entry['key']=string(args[1]);node=nodes[args[0]]
    if addr==0x121d4c:result=int(bool(node['nested']) if entry['key']=='nested' else node['wanted'])
    elif addr==0x122198:result=node['nested'] if node['nested']!=1 else 0
    else:raise AssertionError(label)
   uc.reg_write(UC_ARM_REG_R0,result);entry['supplied_return']=result;uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
  assert b['address']<=addr<b['address']+b['size'],hex(addr)
  executed.append(addr)
 def write(uc,access,addr,size,value,_):
  if OBJ<=addr<OBJ+0x10000:writes.append({'address':addr,'size':size,'value':value})
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP)
 u.emu_start(b['address'],STOP,count=4000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 if i==1:
  output=[r(OBJ+0x40),bitmaps.index(r(OBJ+0x58)),bitmaps.index(r(OBJ+0x5c)),bitmaps.index(r(OBJ+0x60)),r(OBJ+0x64),r(OBJ+0x6c),struct.unpack('<i',u.mem_read(OBJ+0x68,4))[0],r(bitmaps[1]+0x34),r(bitmaps[2]+0x34)]
 elif i==2:output=[int(r(OBJ+0xec)==trace[-1]['supplied_return'] or (trace[-1]['supplied_return']==0 and string(r(OBJ+0xec))=='')),u.mem_read(OBJ+0xe8,1)[0],int(bool(string(r(OBJ+0xec))))]
 elif i==3:output=[u.reg_read(UC_ARM_REG_R0)]
 elif i in [4,6]:output=[u.mem_read(OBJ+0xe8,1)[0],string(r(OBJ+0xec))]
 elif i==5:output=[r(OBJ+0x40),r(OBJ+0x64),struct.unpack('<i',u.mem_read(OBJ+0x68,4))[0],r(OBJ+0x6c),int(not any(r(OBJ+k) for k in [0x58,0x5c,0x60]))]
 else:output=[r(OBJ+0x64),int(not any(r(OBJ+k) for k in [0x58,0x5c,0x60]))]
 return {'packet':i,'inputs':inputs,'output':output,'calls':trace,'writes':writes,'executed_addresses':executed,'return_word':u.reg_read(UC_ARM_REG_R0)}
def generate(selected):
 load();cases=[]
 for i in [4,5,6,7]:
  if i not in selected:continue
  for v in [-2147483648,-1,0,1,17,2147483647]:cases.append(execute(i,[v]))
 for kind in (range(4) if 2 in selected else []):
  for v in [-1,0,17,2147483647]:cases.append(execute(2,[kind,v]))
 for depth,leaf,wrong,present in (itertools.product([0,1,2,7],[0,1,2],[0,1],[0,1]) if 3 in selected else []):cases.append(execute(3,[depth,leaf,wrong,present]))
 triples=list(itertools.product(range(3),repeat=3))
 for j,(old,new) in enumerate(itertools.product(triples,repeat=2) if 1 in selected else []):
  inputs=[ [0,4,20,0x400004,0x200014][j%5],j%5,*old,*new,[0,99,-17][j%3] ];cases.append(execute(1,inputs))
 ranges={str(i):{k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}|{'elf_sha256':m['elf'],'mangled':m['mangled']} for i,(b,_,_,m) in P.items() if i in selected}
 return {'version':1,'oracle':'Unicorn original ARM application instructions; intercepted actual provider boundaries','ranges':ranges,'cases':cases,'limitations':'Core instructions excluded; deterministic boundary outputs supplied, not firmware Core behavior. Constructors are observed after supplied base-state initialization; native vptr values retained without claiming portable layout. View/RadioButton effects are independently exercised on pinned CCL. No ARM ABI/hardware claim.'}
if __name__=='__main__':
 selected={int(sys.argv[sys.argv.index('--packet')+1])} if '--packet' in sys.argv else set(range(1,8))
 result=generate(selected)
 if sys.argv[1]=='--verify':
  expected=json.loads(Path(sys.argv[2]).read_text());expected['cases']=[x for x in expected['cases'] if x['packet'] in selected];expected['ranges']={k:v for k,v in expected['ranges'].items() if int(k) in selected};assert result==expected
 else:Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
 print('original executions',len(result['cases']),'independent ranges',len(result['ranges']))
