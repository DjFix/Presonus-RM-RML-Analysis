"""Exact ARM caller oracle with independent real CCL/model RPC observations."""
import hashlib,json,pathlib,struct,subprocess,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3
ROOT=pathlib.Path(__file__).resolve().parents[4];BASE=pathlib.Path(__file__).parent;TASK=BASE.name;NAME=TASK.rsplit('_',1)[1];KIND={'fader':0,'meter':1,'paramchanged':2,'valuebar':3}[NAME]
PACKET=ROOT/'temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/packets'/TASK
SNAP=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/snapshot')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def evidence():
 req=json.loads((PACKET/'request.json').read_text());c=req['reconstruction_contract'];p=SNAP/c['path'];assert sha(p)==c['sha256'];contract=json.loads(p.read_text());ev=next(e for e in contract['requirements']['providers']['evidence'] if e['kind']=='native_observation');p=SNAP/ev['path'];assert sha(p)==ev['sha256'];return req,json.loads(p.read_text())
def specs():
 values=[0xbf000000,0,0x3e800000,0x3f800000,0x3fc00000]
 if KIND<2:
  tags=[0x1fff,0x2000,0x2001,0x2002,0x2007,0x2008,0x9000] if KIND==0 else [-1,0,1,2,7,8]
  for scenario in range(7):
   for tag in tags:
    for bits in values:
     seq=[dict(call=[tag,0,bits,0,0]),dict(call=[tag,0,bits,0,0])]
     if scenario==1:seq.insert(1,dict(mutate='APPEND'))
     if scenario==6:seq.insert(1,dict(mutate='NULL'))
     yield scenario,seq
 elif KIND==2:
  for tag in [0x1fff,*range(0x2000,0x2008),0x2008,0x9000,-1,-2147483648,2147483647]:
   for msg in [0,1,2,3,-1]:
    for bits in [0,0x3e800000,0x3f800000]:
     for scenario in [0,1]:yield scenario,[dict(call=[tag,0,bits,0,msg]),dict(call=[tag,0,bits,0,msg])]
 else:
  for scenario in range(11):
   for tag in [0x42ff,0x4300,0x4301,0x4307]:
    for mode in [-1,0,2,16777217]:
     bits=values[(scenario+mode)%len(values)];seq=[dict(call=[tag,mode,bits,scenario%2,0]),dict(call=[tag,mode,bits,1-scenario%2,0])]
     if scenario<8:seq.insert(1,dict(mutate='ADDBARS'))
     if scenario==8:seq.insert(1,dict(mutate='ALIAS'))
     yield scenario,seq

def generate(exe):
 req,ev=evidence();target=req['targets'][0];elf=SNAP/'rootfs/CS18_v13840/home/root/surface';raw=elf.read_bytes();assert sha(elf)==target['original_elf_sha256']
 app=ev['verified_body'];helpers={k:v for k,v in ev.get('original_nonCore_i2f_helpers',{}).items() if 'body' in v};ranges=[app]+[v['body'] for v in helpers.values()]
 with elf.open('rb') as f:
  e=ELFFile(f)
  def original(a,n):
   sec=next(s for s in e.iter_sections() if s['sh_type']!='SHT_NOBITS' and s['sh_addr']<=a<a+n<=s['sh_addr']+s['sh_size']);off=sec['sh_offset']+a-sec['sh_addr'];return raw[off:off+n],sec.name,off
  for b in ranges:
   sec=e.get_section(b['section_index']);off=sec['sh_offset']+b['address']-sec['sh_addr'];assert off==b['file_offset'] and sec.name==b['section'];assert hashlib.sha256(raw[off:off+b['size']]).hexdigest()==b['bytes_sha256']
  # Constructor peer ranges are evidence only; every alias separately verified.
  peers=[]
  for v in ev['existing_constructor_initialization_peers']:
   b=v['verified_body'];blob,sec,off=original(b['address'],b['size']);assert off==b['file_offset'] and hashlib.sha256(blob).hexdigest()==b['bytes_sha256'];peers.append(dict(mangled=v['identity']['mangled'],**{k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}))
  vt=ev['numeric_setNormalized_vtable'];blob,sec,off=original(vt['address'],vt['size']);assert hashlib.sha256(blob).hexdigest()==vt['sha256'];assert struct.unpack_from('<I',blob,8+4*vt['slot'])[0]==vt['entry'];tablewords=struct.unpack('<32I',blob)
 cases=[]
 for scenario,sequence in specs():
  proc=subprocess.Popen([str(exe),'provider'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,cwd=ROOT);proc.stdin.write(f'{KIND} {scenario}\n');proc.stdin.flush();rpc_trace=[]
  def rpc(command):
   proc.stdin.write(command+'\n');proc.stdin.flush();line=proc.stdout.readline().strip();assert line,('provider ended',command,proc.poll());rpc_trace.append([command,line]);return line
  assert rpc('ERROR')=='-1'
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
  def put(a,data):
   for page in range(a&~4095,(a+len(data)+4095)&~4095,4096):
    if page not in pages:u.mem_map(page,4096);pages.add(page)
   u.mem_write(a,data)
  for b in ranges:put(b['address'],raw[b['file_offset']:b['file_offset']+b['size']])
  obj=0x1000000;array=obj+0x4000;param=obj+0x5000;vtable=obj+0x8000;metadata=obj+0x9000;sp=0x1108000;stop=0x1200000
  for a in range(obj,obj+0x10000,4096):put(a,bytes(4096))
  put(sp-4096,bytes(8192));put(stop,bytes(4096))
  index_entry=0x11f194;setnorm=tablewords[2+25];setvalue=tablewords[2+22];getnorm=tablewords[2+24];touch=0xc0624;move=0xc058c
  for a in [index_entry,setnorm,setvalue,getnorm,touch,move]:put(a,bytes(4))
  put(vtable,blob[8:]);
  def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
  def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
  cache={0:(0xc58,0x2000),1:(0xc68,0),2:(0xc80,0x4400),3:(0xc74,0x4500),4:(0xc8c,0x4600)}
  for offset,base in cache.values():w(obj+offset,base);w(obj+offset+4,0xffffffff);u.mem_write(obj+offset+8,b'\0')
  # Default original ConstVector<Parameter*>::error storage is a distinct null
  # boundary cell. Original SHT_NOBITS identity is preserved, not file bytes.
  for v in ev['parameter_vector_error_item_identities']:
   put(v['address'],bytes(4))
  def sync():
   observed=list(map(int,rpc('LIST').split()));count=observed[0];ids=observed[1:];assert count==len(ids);w(obj+0x34,array);w(obj+0x38,count)
   for i,id in enumerate(ids):w(array+i*4,0 if id<0 else param+id*0x100)
   for id in set(ids):
    if id<0:continue
    tag=int(rpc('TAG '+str(id)));w(param+id*0x100,vtable);w(param+id*0x100+0xc,metadata+id*0x10);w(metadata+id*0x10+4,tag)
   w(obj+0xc64,param+(count-1)*0x100 if KIND==0 and scenario==5 else 0)
  sync();results=[];allpcs=[];writes=[];calls=[];probes={};current=None
  def ret(value):u.reg_write(UC_ARM_REG_R0,value&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  def boundary(uc,pc,size,user):
   if pc==index_entry:
    assert uc.reg_read(UC_ARM_REG_R0)==obj+0x28;tag=uc.reg_read(UC_ARM_REG_R1);assert tag in [b for o,b in cache.values()];index=int(rpc('INDEX '+str(tag)));calls.append(['actual-ParamList-index',tag,index]);ret(index);return
   if pc in [setnorm,setvalue]:
    receiver=uc.reg_read(UC_ARM_REG_R0);assert (receiver-param)%0x100==0;id=(receiver-param)//0x100;bits=uc.reg_read(UC_ARM_REG_R1);assert uc.reg_read(UC_ARM_REG_R2)==0
    assert id in probes.values(),(id,probes);rpc(f'SET {id} {bits} {int(pc==setnorm)}');calls.append(['actual-Numeric-set',id,bits,pc==setnorm,False]);ret(0);return
   if pc==getnorm:
    assert uc.reg_read(UC_ARM_REG_R0)==param;bits=int(rpc('NORMAL 0'));calls.append(['actual-Numeric-normalized',bits]);ret(bits);return
   if pc in [touch,move]:
    assert uc.reg_read(UC_ARM_REG_R0)==obj+0x88;tag=uc.reg_read(UC_ARM_REG_R1);signed=struct.unpack('<i',struct.pack('<I',tag))[0];value=uc.reg_read(UC_ARM_REG_R2);rpc(('TOUCH' if pc==touch else 'MOVE')+f' {signed} {value}');calls.append(['actual-existing-model',pc,tag,value]);ret(0);return
   assert any(b['address']<=pc<pc+size<=b['address']+b['size'] for b in ranges),hex(pc);allpcs.append(pc)
  def write(uc,access,a,n,value,user):
   allowed=[(obj+o+4,4) for o,b in cache.values()]+[(obj+o+8,1) for o,b in cache.values()]
   assert sp-1024<=a<a+n<=sp or (a,n) in allowed,(hex(a),n)
   if obj<=a<obj+0x10000:writes.append([a-obj,n,value])
  u.hook_add(UC_HOOK_CODE,boundary);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for action in sequence:
   if 'mutate' in action:rpc(action['mutate']);sync();continue
   tag,mode,bits,boolean,msg=action['call'];current=action['call'];probes={}
   if KIND<2:
    if not(KIND==0 and tag==0x9000):probes[KIND]=int(rpc(f'GET {KIND} {tag-(0x2000 if KIND==0 else 0)}'))
    elif scenario==5:probes[99]=r(obj+0x38)-1
   elif KIND==3:
    for stage in [2,3,4]:probes[stage]=int(rpc(f'GET {stage} {tag-0x4300}'))
   else:
    rpc(f'INPUT {tag} {bits}');w(metadata+4,tag)
   for reg,v in [(UC_ARM_REG_SP,sp),(UC_ARM_REG_LR,stop),(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,param if KIND==2 else tag),(UC_ARM_REG_R2,msg if KIND==2 else mode if KIND==3 else bits),(UC_ARM_REG_R3,bits)]:u.reg_write(reg,v&0xffffffff)
   w(sp,boolean)
   u.emu_start(app['address'],stop,count=500);assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==sp
   results.append(rpc('REPORT'))
  proc.stdin.close();assert proc.wait(timeout=10)==0
  cases.append(dict(scenario=scenario,sequence=sequence,expected=results,provider_trace=rpc_trace,native_calls=calls,instructions=allpcs,cache_writes=writes,cache_after={str(stage):[r(obj+o+4),int(u.mem_read(obj+o+8,1)[0])] for stage,(o,b) in cache.items()}))
 return dict(error_sentinel_identities=ev['parameter_vector_error_item_identities'],elf_sha256=target['original_elf_sha256'],target_range={k:app[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},helper_ranges=[dict(mangled=v['identity']['mangled'],**{k:v['body'][k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}) for v in helpers.values()],constructor_peers_static_only=peers,numeric_vtable=vt,cases=cases,scope=f'{NAME}: {len(cases)} sequences with two calls each. '+ 'Exact original application instructions, original i2f helper closure where used, independently executed actual CCL ParamArrayAccessor/ParamList/Numeric providers and existing canonical model.touchFader/moveFader/MIDI boundary. Normalized finite source-port domain, safe signed accessor index sums, stable owned metadata/parameters, default null vector error. Initial/cached/missing caches, positional sparse/reordered lists and bounded post-cache mutation; observer snapshots and actual MIDI bytes. Original returns/layout/ARM ABI and original constructors remain unresolved; no Core firmware execution.')
if __name__=='__main__':
 j=generate(pathlib.Path(sys.argv[1]));p=BASE/'fixtures.json'
 if '--generate' in sys.argv:p.write_text(json.dumps(j,indent=2)+'\n')
 else:assert json.loads(p.read_text())==j
 print(len(j['cases']),'native/provider sequences')
