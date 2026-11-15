"""Typed real-provider bridge plus verified original app/non-Core helper execution."""
import ctypes,hashlib,json,pathlib,struct,subprocess,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_R0,UC_ARM_REG_R1
ROOT=pathlib.Path(__file__).resolve().parents[4];BASE=pathlib.Path(__file__).parent;TASK=BASE.name
PACKET=ROOT/'temp/recovery-work/rolling10x10-20261114/prepared06/packets'/TASK
SNAP=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared06/snapshot')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def evidence():
 req=json.loads((PACKET/'request.json').read_text());c=req['reconstruction_contract'];p=SNAP/c['path'];assert sha(p)==c['sha256'];contract=json.loads(p.read_text())
 e=next(e for e in contract['requirements']['providers']['evidence'] if e['kind']=='native_observation');p=SNAP/e['path'];assert sha(p)==e['sha256'];return req,json.loads(p.read_text())
def generate(exe):
 req,ev=evidence();target=req['targets'][0];elf=SNAP/'rootfs/RML16AI_Rack_13731/home/root/mixer';raw=elf.read_bytes();assert sha(elf)==target['original_elf_sha256']
 app=ev['verified_body'];helpers=ev['original_nonCore_helpers'];ranges=[app]+[v['body'] for v in helpers.values()]
 with elf.open('rb') as f:
  e=ELFFile(f)
  for b in ranges:
   sec=e.get_section(b['section_index']);off=sec['sh_offset']+b['address']-sec['sh_addr'];assert off==b['file_offset'] and sec.name==b['section'];assert hashlib.sha256(raw[off:off+b['size']]).hexdigest()==b['bytes_sha256']
 vt=ev['numeric_vtable'];assert hashlib.sha256(raw[vt['file_offset']:vt['file_offset']+vt['size']]).hexdigest()==vt['sha256'];getter=vt['slots']['17'];assert struct.unpack_from('<I',raw,vt['file_offset']+8+17*4)[0]==getter
 literal=ev['substring_literal'];needle=bytes.fromhex(literal['bytes_hex']);assert raw[literal['file_offset']:literal['file_offset']+len(needle)]==needle and hashlib.sha256(needle).hexdigest()==literal['sha256']
 runtime=json.loads((SNAP/'temp/recovery-work/rolling10x10-20261114/runtime-reserve.json').read_text())['providers']['host_libc'];libpath=pathlib.Path(runtime['path']);assert sha(libpath)==runtime['sha256'];libc=ctypes.CDLL(str(libpath));libc.strstr.argtypes=[ctypes.c_void_p,ctypes.c_void_p];libc.strstr.restype=ctypes.c_void_p
 names=['','H','D','hd','HD','HD-main','nameHD','nameHDtail','HDHD','x'*60+'HD'];values=[0xbf800000,0,0x80000000,0x3f000000,0x3f7fffff,0x3f800000,0x3f800001,0x40000000]
 inputs=[[p,m,v,n,initial] for p in [0,1] for m in [0,1,2,3,4,0xffffffff] for v in values for n in range(len(names)) for initial in [0,1,165]]
 lines=subprocess.check_output([str(exe),'provider'],input=''.join(' '.join(map(str,x))+'\n' for x in inputs).encode()).decode().splitlines();assert len(lines)==len(inputs);cases=[]
 for inp,line in zip(inputs,lines):
  present,mode,requested,index,initial=inp;assert len(names[index].encode())<=67;bits,provider_offset=map(int,line.split());assert bits==requested
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
  def put(a,data):
   for page in range(a&~4095,(a+len(data)+4095)&~4095,4096):
    if page not in pages:u.mem_map(page,4096);pages.add(page)
   u.mem_write(a,data)
  for b in ranges:put(b['address'],raw[b['file_offset']:b['file_offset']+b['size']])
  put(literal['address'],needle)
  for a in [0x1000000,0x1100000,0x1200000,0xad18&~4095,getter&~4095]:put(a,bytes(4096))
  obj=0x1000000;param=obj+0x400;vtable=obj+0x500;sp=0x1100800;stop=0x1200000
  def w(a,v):u.mem_write(a,struct.pack('<I',v))
  w(obj+0x120,param if present else 0);w(obj+0x118,mode);w(param,vtable);w(vtable+0x44,getter);u.mem_write(obj+5,bytes([initial]));u.mem_write(obj+0xd4,names[index].encode()+b'\0')
  before=bytes(u.mem_read(obj,4096));trace=[];sites=[];writes=[]
  def ret(value):u.reg_write(UC_ARM_REG_R0,value);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  def hook(uc,a,size,user):
   if a==getter:
    assert uc.reg_read(UC_ARM_REG_R0)==param;trace.append(['actual-NumericParam-getValue',bits]);ret(bits);return
   if a==0xad18:
    assert uc.reg_read(UC_ARM_REG_R0)==obj+0xd4 and uc.reg_read(UC_ARM_REG_R1)==literal['address']
    hay=ctypes.create_string_buffer(names[index].encode()+b'\0');need=ctypes.create_string_buffer(needle);match=libc.strstr(hay,need);offset=match-ctypes.addressof(hay) if match else -1;assert offset==provider_offset
    trace.append(['actual-host-libc-strstr',names[index],needle[:-1].decode(),offset]);ret(obj+0xd4+offset if match else 0);return
   assert any(b['address']<=a<a+size<=b['address']+b['size'] for b in ranges),hex(a);sites.append(a)
  def write(uc,access,a,size,value,user):
   if obj<=a<a+size<=obj+4096:writes.append([a-obj,size,value])
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for reg,v in [(UC_ARM_REG_SP,sp),(UC_ARM_REG_LR,stop),(UC_ARM_REG_R0,obj)]:u.reg_write(reg,v)
  u.emu_start(app['address'],stop,count=500);assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==sp
  after=bytes(u.mem_read(obj,4096));assert before[:5]==after[:5] and before[6:]==after[6:]
  if not present or mode not in [1,3]:assert not writes and not trace and after[5]==initial
  else:assert writes==[[5,1,after[5]]] and len(trace)==2
  cases.append(dict(input=inp,provider=[bits,provider_offset],expected=after[5],trace=trace,instructions=sites,object_writes=writes))
 return dict(elf_sha256=target['original_elf_sha256'],target_range={k:app[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},helper_ranges=[dict(mangled=v['identity']['mangled'],**{k:v['body'][k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}) for v in helpers.values()],numeric_vtable=vt,literal=literal,host_libc=runtime,cases=cases,scope='2880 exact original app cases: optional NumericParam, modes0/1/2/3/4/UINT32_MAX, 8 finite binary32 values around1 including signedzero, 10 NUL-terminated names of length0..62 with absent/leading/interior/trailing/repeated HD and 3 initial flag bytes. Actual pinned Numeric getter observations plus independently executed hash-bound host libc strstr; original complete non-Core greater-than closure executes. Early paths preserve flag/no calls; active paths write only flag0/1. Core excluded, no original ABI/layout/return claim.')
if __name__=='__main__':
 j=generate(pathlib.Path(sys.argv[1]));p=BASE/'fixtures.json'
 if '--generate' in sys.argv:p.write_text(json.dumps(j,indent=2)+'\n')
 else:assert j==json.loads(p.read_text())
 print(len(j['cases']),'original app/provider/helper cases')
