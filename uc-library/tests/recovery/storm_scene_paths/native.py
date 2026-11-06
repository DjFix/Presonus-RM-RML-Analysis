"""Only sealed Storm app instructions execute; providers run from pinned sources.

No Core firmware instructions, hardware IO or host syscall passthrough. Provider
subprocess operations never call either reconstructed helper. Real mkdir is
Landlock-confined by the provider executable to assigned project-local scratch.
"""
import functools, hashlib, json, pathlib, struct, subprocess, sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT = pathlib.Path(__file__).resolve().parents[4]
BASE = pathlib.Path('uc-library/tests/recovery/storm_scene_paths')
PACKETS = pathlib.Path('temp/recovery-work/rolling200-03/storm_paths164/prepared164/packets')
ELF = 'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
WORK = pathlib.Path('temp/recovery-work/rolling200-03/storm-paths164')
OBJ=0x1000000;OTHER=OBJ+0x1000;MAN=OBJ+0x2000;CACHE=OBJ+0x3000;OUT=OBJ+0x4000
STACK=0x1100000;SP=STACK+0x8000;STOP=0x1200000

def verified():
 raw=(ROOT/ELF).read_bytes(); assert hashlib.sha256(raw).hexdigest()==SHA
 bodies=[];segments=[]
 with (ROOT/ELF).open('rb') as f:
  elf=ELFFile(f)
  for seg in elf.iter_segments():
   if seg['p_type']=='PT_LOAD':segments.append((int(seg['p_vaddr']),int(seg['p_memsz']),seg.data()))
  for i in range(1,3):
   j=json.loads((ROOT/PACKETS/f'rolling200_03_storm_paths164_{i:02d}/native-context.json').read_text())
   b=j['bodies'][j['roots'][0]];sec=elf.get_section(b['section_index'])
   off=int(sec['sh_offset'])+b['address']-int(sec['sh_addr'])
   assert off==b['file_offset'] and sec.name==b['section']
   assert hashlib.sha256(raw[off:off+b['size']]).hexdigest()==b['bytes_sha256']
   bodies.append({k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']})
  for a,text in [(0x16d554,b'mixscene\0'),(0x33934c,b'undo\0'),(0x339354,b'mixscene.undo\0'),(0x35b15c,b'\0')]:
   sec=next(s for s in elf.iter_sections() if int(s['sh_addr'])<=a<int(s['sh_addr'])+int(s['sh_size']))
   off=int(sec['sh_offset'])+a-int(sec['sh_addr']);assert raw[off:off+len(text)]==text
 return bodies,segments

def execute(bodies,segments,argv,provider):
 mode,binding,index,folder,kind,slots,fs=argv;binding=int(binding);index=int(index)
 provider('setup',folder,fs)
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
 for a,n,data in segments:
  for pg in range(a&~4095,(a+n+4095)&~4095,4096):
   if pg not in pages:u.mem_map(pg,4096);pages.add(pg)
  u.mem_write(a,data)
 for a,n in [(OBJ,0x10000),(STACK,0x10000),(STOP,4096)]:u.mem_map(a,n)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def s(a):
  if not a:return ''
  out=bytearray()
  while u.mem_read(a,1)!=b'\0':out+=u.mem_read(a,1);a+=1
  return out.decode()
 def put(a,t):u.mem_write(a,t.encode()+b'\0')
 def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 put(OBJ+8,'scene');put(OTHER+8,'different')
 manager_cell=r(0x734e0);w(manager_cell,0 if binding==-1 else MAN)
 trace=[];writes=[];mkdir_paths=[];provider_ops=[]
 def op(operation,*args):
  value=provider(operation,*args);provider_ops.append(dict(operation=operation,arguments=list(args),result=value));return value
 def hook(uc,a,size,user):
  R=[uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]];sp=uc.reg_read(UC_ARM_REG_SP)
  if a==STOP:return
  if a==0x84b08:
   assert R[0]==MAN;name=s(R[1]);trace.append('lookup:'+name)
   ret(CACHE if binding in [1,2] and name==kind else 0);return
  if a==0x85764:
   assert R[1]==CACHE and s(R[3])=='mixscene' and s(r(sp))=='' and r(sp+4)==0 and r(sp+8)==1
   trace.append('build:'+str(R[2]));put(R[0],op('build',folder,kind,str(R[2]),s(R[3])));ret(R[0]);return
  if a==0x129ba4:put(R[0],op('construct',s(R[1])));ret(R[0]);return
  if a==0xae68:uc.mem_write(R[0],bytes(uc.mem_read(R[1],R[2])));assert R[2]==256;ret(R[0]);return
  if a==0xb030:trace.append('guard-acquire');ret(1);return
  if a==0xaa3c:w(R[0],1);trace.append('guard-release');ret();return
  if a==0x127acc:put(R[1],op('name',s(R[0])));ret();return
  if a==0xad18:
   offset=s(R[0]).find(s(R[1]));ret(R[0]+offset if offset>=0 else 0);return
  if a==0xae98:ret(len(s(R[0])));return
  if a==0x1289f4:put(R[0],op('descend',s(R[0]),s(R[1])));ret(R[0]);return
  if a==0x1279b4:
   path=s(R[0]);mkdir_paths.append(path);trace.append('mkdir:'+path)
   # Actual source-provider result is intentionally unused by native app.
   ret(int(provider('mkdir',path)));return
  if a==0xa7e4:assert R[0]==24;trace.append('allocate-manager');ret(MAN);return
  if a==0x847b4:assert R[0]==MAN;trace.append('construct-manager');ret(MAN);return
  if a==0x126cfc:assert R[0]==MAN;trace.append('register-deletable');ret();return
  assert any(b['address']<=a<a+size<=b['address']+b['size'] for b in bodies),(hex(a),R)
 def write(uc,access,a,n,value,user):
  if not STACK<=a<a+n<=SP:writes.append([a,n,value])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 def call(obj,undo=False):
  start=bodies[1 if undo or mode=='undo' else 0]['address']
  for reg,value in [(UC_ARM_REG_SP,SP),(UC_ARM_REG_LR,STOP),(UC_ARM_REG_R0,OUT),(UC_ARM_REG_R1,obj),(UC_ARM_REG_R2,index)]:u.reg_write(reg,value)
  u.emu_start(start,STOP,count=20000);assert u.reg_read(UC_ARM_REG_PC)==STOP
  return s(OUT)
 first=call(OBJ);warm=call(OBJ);undo=mode=='undo' or bool(((index-1)&0xffffffff)&0x80000000)
 cross=call(OTHER,undo)
 assert first==warm
 if undo:assert first==cross and len(mkdir_paths)==1 and trace.count('lookup:scene')==1
 else:assert cross=='' and len(mkdir_paths)==0
 if binding==-1:assert trace.count('allocate-manager')==1 and trace.count('register-deletable')==1
 parent=first.rsplit('/',1)[0] if '/' in first else first
 made=provider('directory',parent) if undo else '0'
 return dict(argv=argv,expected=[first,warm,cross,made],trace=trace,application_writes=writes,provider_operations=provider_ops,mkdir_paths=mkdir_paths)

def cleanup_observations(bodies,segments):
 observations=[]
 for entry in [0x734cc,0x73608]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
  for a,n,data in segments:
   for pg in range(a&~4095,(a+n+4095)&~4095,4096):
    if pg not in pages:u.mem_map(pg,4096);pages.add(pg)
   u.mem_write(a,data)
  u.mem_map(OBJ,0x10000);u.mem_map(STACK,0x10000);u.mem_map(STOP,4096)
  trace=[]
  def hook(uc,a,size,user):
   if a in [0xac10,0xaa18]:
    value=uc.reg_read(UC_ARM_REG_R0);trace.append([hex(a),value]);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   if a==0xacd0:
    assert uc.reg_read(UC_ARM_REG_R0)==OBJ+0x800;trace.append(['rethrow',OBJ+0x800]);uc.reg_write(UC_ARM_REG_PC,STOP);return
   assert any(b['address']<=a<a+size<=b['address']+b['size'] for b in bodies)
  u.hook_add(UC_HOOK_CODE,hook)
  for reg,v in [(UC_ARM_REG_SP,SP),(UC_ARM_REG_R0,OBJ+0x800),(UC_ARM_REG_R6,MAN)]:u.reg_write(reg,v)
  u.emu_start(entry,STOP,count=100);observations.append(dict(entry=entry,trace=trace))
 return observations

def generate(executable=str(WORK/'replay')):
 @functools.lru_cache(maxsize=None)
 def pure(*args):
  return subprocess.check_output([executable,'provider',*args],cwd=ROOT,text=True).rstrip('\n')
 def provider(*args):
  if args[0] in ['mkdir','setup','directory']:
   return subprocess.check_output([executable,'provider',*args],cwd=ROOT,text=True).rstrip('\n')
  return pure(*args)
 bodies,segments=verified();cases=[];base=str(WORK/'files')
 variants=[(-1,'cold','scene',0,'none'),(0,'missing','scene',0,'none'),(1,'normal','scene',0,'directory'),(2,'singleton','scene',2,'directory'),(1,'01.mixscene.scene/sub','scene',2,'directory'),(1,'blocked','scene',0,'file'),(1,'absent/parent','scene',0,'none'),(1,'','scene',0,'none'),(1,'x'*230,'scene',0,'none'),(1,'a/b/'+'c'*235,'scene',0,'none'),(1,'wrong-type','other',0,'directory')]
 for binding,suffix,kind,slots,fs in variants:
  folder=(base+'/'+suffix) if suffix else ''
  for index in [0,1,2,0x80000000,0x80000001,0xffffffff]:
   cases.append(execute(bodies,segments,['filename',str(binding),str(index),folder,kind,str(slots),fs],provider))
  cases.append(execute(bodies,segments,['undo',str(binding),'1',folder,kind,str(slots),fs],provider))
 return dict(elf=ELF,elf_sha256=SHA,ranges=bodies,cases=cases,cleanup=cleanup_observations(bodies,segments),boundaries='Only two original app ranges execute. Source-built CCL FileName and accepted cache run independently via provider mode, never reconstructed helpers, at declared native call boundaries. Manager constructor, allocation, Deletable registration, cxa guards, memcpy/strlen/strstr are bounded observations. Directory calls run actual source provider confined by Landlock; ignored return not captured as deterministic fixture. No original unwinder, Core firmware, device IO, syscall passthrough or original ABI claim.')
if __name__=='__main__':
 j=generate();path=ROOT/BASE/'fixtures.json'
 if '--generate' in sys.argv:path.write_text(json.dumps(j,indent=2)+'\n')
 else:assert j==json.loads(path.read_text())
 print(len(j['cases']),'native/provider observations; cleanup landing pads',len(j['cleanup']))
