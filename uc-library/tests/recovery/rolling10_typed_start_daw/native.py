"""Typed real-provider bridge plus verified original app/non-Core helper execution."""
import hashlib,json,pathlib,struct,subprocess,sys
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
 req,ev=evidence();target=req['targets'][0];elf=SNAP/'rootfs/CS18_v13840/home/root/surface';raw=elf.read_bytes();assert sha(elf)==target['original_elf_sha256']
 app=ev['verified_original_body'];helpers=ev['original_nonCore_helper_closure'];ranges=[app]+[v['body'] for v in helpers.values()]
 with elf.open('rb') as f:
  e=ELFFile(f)
  for b in ranges:
   sec=e.get_section(b['section_index']);off=sec['sh_offset']+b['address']-sec['sh_addr'];assert off==b['file_offset'] and sec.name==b['section'];assert hashlib.sha256(raw[off:off+b['size']]).hexdigest()==b['bytes_sha256']
 vt=ev['numeric_interface_symbols']['_ZTVN4Core8Portable12NumericParamE'];assert hashlib.sha256(raw[vt['file_offset']:vt['file_offset']+vt['size']]).hexdigest()==vt['bytes_sha256'];getter=vt['slot17'];assert struct.unpack_from('<I',raw,vt['file_offset']+8+17*4)[0]==getter
 inputs=[[v,o] for v in [0xbf800000,0,0x80000000,0x3f000000,0x3f7fffff,0x3f800000,0x3f800001,0x40000000] for o in [0,0x3f800000]]
 lines=subprocess.check_output([str(exe),'provider'],input=''.join(f'{v} {o}\n' for v,o in inputs).encode()).decode().splitlines();assert len(lines)==len(inputs);cases=[];tag=1000 if TASK.endswith('daw') else 1001
 for inp,line in zip(inputs,lines):
  observed_tag,bits=map(int,line.split());assert observed_tag==tag and bits==inp[0]
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
  def mapbytes(a,data):
   for page in range(a&~4095,(a+len(data)+4095)&~4095,4096):
    if page not in pages:u.mem_map(page,4096);pages.add(page)
   u.mem_write(a,data)
  for b in ranges:mapbytes(b['address'],raw[b['file_offset']:b['file_offset']+b['size']])
  for a in [0x1000000,0x1100000,0x1200000,0x11acf0&~4095,getter&~4095]:mapbytes(a,bytes(4096))
  obj=0x1000000;param=obj+0x100;vtable=obj+0x200;sp=0x1100800;stop=0x1200000
  def w(a,v):u.mem_write(a,struct.pack('<I',v))
  w(param,vtable);w(vtable+0x44,getter);before=bytes(u.mem_read(obj,4096));trace=[];sites=[];writes=[]
  def ret(value):u.reg_write(UC_ARM_REG_R0,value);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  def hook(uc,a,size,user):
   if a==0x11acf0:
    assert uc.reg_read(UC_ARM_REG_R0)==obj and uc.reg_read(UC_ARM_REG_R1)==observed_tag;trace.append(['lookup',observed_tag]);ret(param);return
   if a==getter:
    assert uc.reg_read(UC_ARM_REG_R0)==param;trace.append(['actual-NumericParam-getValue',bits]);ret(bits);return
   assert any(b['address']<=a<a+size<=b['address']+b['size'] for b in ranges),hex(a);sites.append(a)
  def write(uc,access,a,size,value,user):
   if obj<=a<a+size<=obj+4096:writes.append([a-obj,size,value])
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for reg,v in [(UC_ARM_REG_SP,sp),(UC_ARM_REG_LR,stop),(UC_ARM_REG_R0,obj)]:u.reg_write(reg,v)
  u.emu_start(app['address'],stop,count=500);assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==sp
  assert not writes and before==bytes(u.mem_read(obj,4096))
  cases.append(dict(input=inp,provider=[observed_tag,bits],expected=u.reg_read(UC_ARM_REG_R0),trace=trace,instructions=sites,object_writes=writes))
 return dict(elf_sha256=target['original_elf_sha256'],target_range={k:app[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},helper_ranges=[dict(mangled=v['identity']['mangled'],**{k:v['body'][k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}) for v in helpers.values()],numeric_vtable=vt,cases=cases,scope='Original application and full non-Core equality helper closure execute. Real pinned provider mode independently observes actual collection lookup/getter; native typed bridge only returns those observations. No Core instructions execute. Valid NumericParam tag1000/1001; finite domain, no null parameter support or original ABI/declaration claim.')
if __name__=='__main__':
 j=generate(pathlib.Path(sys.argv[1]));p=BASE/'fixtures.json'
 if '--generate' in sys.argv:p.write_text(json.dumps(j,indent=2)+'\n')
 else:assert j==json.loads(p.read_text())
 print(len(j['cases']),'original app/helper cases')
