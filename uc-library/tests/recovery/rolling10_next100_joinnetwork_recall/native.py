"""Typed real-provider bridge plus verified original app/non-Core helper execution."""
import hashlib,json,pathlib,struct,subprocess,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2
ROOT=pathlib.Path(__file__).resolve().parents[4];BASE=pathlib.Path(__file__).parent;TASK=BASE.name
PACKET=ROOT/'temp/recovery-work/rolling10x10-20261114/prepared06/packets'/TASK
SNAP=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared06/snapshot')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def evidence():
 req=json.loads((PACKET/'request.json').read_text());c=req['reconstruction_contract'];p=SNAP/c['path'];assert sha(p)==c['sha256'];contract=json.loads(p.read_text())
 e=next(e for e in contract['requirements']['providers']['evidence'] if e['kind']=='native_observation');p=SNAP/e['path'];assert sha(p)==e['sha256'];return req,json.loads(p.read_text())
def generate(exe):
 req,ev=evidence();target=req['targets'][0];elf=SNAP/'rootfs/RML16AI_Rack_13731/home/root/mixer';raw=elf.read_bytes();assert sha(elf)==target['original_elf_sha256']
 app=ev['verified_body'];b=app
 with elf.open('rb') as f:
  e=ELFFile(f);sec=e.get_section(b['section_index']);off=sec['sh_offset']+b['address']-sec['sh_addr'];assert off==b['file_offset'] and sec.name==b['section'];assert hashlib.sha256(raw[off:off+b['size']]).hexdigest()==b['bytes_sha256']
 vt=ev['verified_original_vtable'];assert hashlib.sha256(raw[vt['file_offset']:vt['file_offset']+vt['size']]).hexdigest()==vt['bytes_sha256'];setter=vt['slots']['29'];assert struct.unpack_from('<I',raw,vt['file_offset']+8+29*4)[0]==setter
 literal=ev['verified_literal_strings'][0];assert hashlib.sha256(raw[literal['file_offset']:literal['file_offset']+literal['size']]).hexdigest()==literal['sha256']
 inputs=[[i,n] for i in range(5) for n in [1,2]];lines=subprocess.check_output([str(exe),'provider'],input=''.join(f'{i} {n}\n' for i,n in inputs).encode()).decode().splitlines();assert len(lines)==len(inputs);cases=[]
 for inp,line in zip(inputs,lines):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
  def put(a,data):
   for page in range(a&~4095,(a+len(data)+4095)&~4095,4096):
    if page not in pages:u.mem_map(page,4096);pages.add(page)
   u.mem_write(a,data)
  put(app['address'],raw[app['file_offset']:app['file_offset']+app['size']]);put(literal['original_string_address'],raw[literal['file_offset']:literal['file_offset']+literal['size']])
  for a in [0x1000000,0x1100000,0x1200000,0x119c4c&~4095,setter&~4095]:put(a,bytes(4096))
  obj=0x1000000;tree=obj+0x400;param=obj+0x500;vtable=obj+0x600;sp=0x1100800;stop=0x1200000
  def w(a,v):u.mem_write(a,struct.pack('<I',v))
  w(obj+0x118,tree);w(param,vtable);w(vtable+0x74,setter);before=bytes(u.mem_read(obj,4096));trace=[];sites=[];writes=[]
  def ret(value):u.reg_write(UC_ARM_REG_R0,value);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  def hook(uc,a,size,user):
   if a==0x119c4c:
    assert uc.reg_read(UC_ARM_REG_R0)==tree and uc.reg_read(UC_ARM_REG_R1)==8;trace.append(['actual-Component-lookup',8]);ret(param);return
   if a==setter:
    assert uc.reg_read(UC_ARM_REG_R0)==param and uc.reg_read(UC_ARM_REG_R1)==literal['original_string_address'] and uc.reg_read(UC_ARM_REG_R2)==0
    trace.append(['actual-StringParam-fromString','',False]);ret(0xbad);return
   assert app['address']<=a<a+size<=app['address']+app['size'],hex(a);sites.append(a)
  def write(uc,access,a,size,value,user):
   if obj<=a<a+size<=obj+4096:writes.append([a-obj,size,value])
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for _ in range(inp[1]):
   for reg,v in [(UC_ARM_REG_SP,sp),(UC_ARM_REG_LR,stop),(UC_ARM_REG_R0,obj)]:u.reg_write(reg,v)
   u.emu_start(app['address'],stop,count=100);assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==sp
  assert not writes and before==bytes(u.mem_read(obj,4096)) and len(trace)==2*inp[1]
  cases.append(dict(input=inp,expected=line,provider_observation=line,trace=trace,instructions=sites,object_writes=writes))
 return dict(elf_sha256=target['original_elf_sha256'],target_range={k:app[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},string_vtable=vt,literal=literal,cases=cases,scope='10 exact original ARM executions with repeated calls: valid borrowed real Component tree and StringParam tag8; independent actual provider clears empty/ASCII/200-byte/UTF8 text using fromString(empty,false), records real observer notifications, unchanged tag9 and no editing. Native instruction trace verifies actual tag8 receiver and exact original empty literal/edit=false dispatch; Core instructions excluded. Original return/layout/ABI and invalid/null receivers excluded.')
if __name__=='__main__':
 j=generate(pathlib.Path(sys.argv[1]));p=BASE/'fixtures.json'
 if '--generate' in sys.argv:p.write_text(json.dumps(j,indent=2)+'\n')
 else:assert j==json.loads(p.read_text())
 print(len(j['cases']),'original app/provider cases')
