"""Full selected app and original PageComponent getter execution."""
import hashlib,json,pathlib,struct,subprocess
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4];BASE=pathlib.Path(__file__).parent;TASK=BASE.name
SNAP=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/prepared-main/snapshot')
PACKET=ROOT/'temp/recovery-work/reconstruction10x10-20261116/prepared-main/packets'/TASK
EXP=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/expansions/bound-20261116T055348/g03-page-tag/native-context.json')
START=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/expansions/root-followon01/main-screen-start-tag/native-context.json')
EXP=START
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def generate(exe):
 target=json.loads((PACKET/'request.json').read_text())['targets'][0];ev=SNAP/('temp/recovery-work/reconstruction10x10-20261116/native/'+TASK+'.json');body=json.loads(ev.read_text())['body'];helper=None
 elf=SNAP/'rootfs/CS18_v13840/home/root/surface';assert sha(elf)==target['original_elf_sha256'];raw=elf.read_bytes();startbody=next(iter(json.loads(START.read_text())['bodies'].values()));ranges=[body,startbody]
 assert struct.unpack_from('<I',raw,0x1983ac)[0]==startbody['address']
 with elf.open('rb') as f:
  e=ELFFile(f)
  for b in ranges:
   sec=e.get_section(b['section_index']);assert sec.name==b['section'];assert sec['sh_offset']+b['address']-sec['sh_addr']==b['file_offset'];assert hashlib.sha256(raw[b['file_offset']:b['file_offset']+b['size']]).hexdigest()==b['bytes_sha256']
 tags=[-2147483648,-1000,-1,0,3,7,14,20,29,30,2147483647];inputs=[[a,b,h] for a in tags for b in tags for h in [0,1]];payload=''.join(' '.join(map(str,x))+'\n' for x in inputs);provider=subprocess.check_output([str(exe),'provider'],input=payload.encode()).decode().splitlines();assert len(provider)==len(inputs);cases=[]
 for inp,line in zip(inputs,provider):
  observed,start=map(int,line.split())
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for addr in {body['address']&~4095,0x73000,0x1000000,0x1100000,0x1200000,0x1300000}:u.mem_map(addr,4096)
  
  for b in ranges:u.mem_write(b['address'],raw[b['file_offset']:b['file_offset']+b['size']])
  obj=0x1000000;stop=0x1200000;sites=[];writes=[];calls=[];u.mem_write(obj,struct.pack('<I',obj+0x100));u.mem_write(obj+0x12c,struct.pack('<I',startbody['address']));before=bytes(u.mem_read(obj,4096))
  def hook(uc,a,size,user):
   if a==0x738b0:
    assert uc.reg_read(UC_ARM_REG_R0)==obj;v=observed if a==0x738b0 else start;calls.append(['canonical-current-page-tag' if a==0x738b0 else 'virtual-start-tag',v]);uc.reg_write(UC_ARM_REG_R0,v&0xffffffff);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   assert any(b['address']<=a<a+size<=b['address']+b['size'] for b in ranges),hex(a);sites.append(a)
  def write(uc,access,a,size,v,user):
   if obj<=a<a+size<=obj+4096:writes.append([a-obj,size,v])
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for r,v in [(UC_ARM_REG_SP,0x1100800),(UC_ARM_REG_LR,stop),(UC_ARM_REG_R0,obj)]:u.reg_write(r,v)
  u.emu_start(body['address'],stop,count=100);assert u.reg_read(UC_ARM_REG_PC)==stop;assert not writes and before==bytes(u.mem_read(obj,4096))
  cases.append(dict(input=inp,expected=str(u.reg_read(UC_ARM_REG_R0)),provider=line,native_calls=calls,native_instructions=sites,object_writes=writes))
 return dict(producer={'path':str(BASE.relative_to(ROOT)/'native.py'),'sha256':sha(__file__),'unicorn_version':__import__('unicorn').__version__,'method':'independent original ARM instruction execution and separately observed source providers'},case_count=len(cases),elf_sha256=target['original_elf_sha256'],target_range={k:body[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},helper_ranges=[{k:startbody[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}],cases=cases,scope='242 concrete-default cases: signed current-page extremes and null/current-page state, while independent legacy Application start-tag values vary and are ignored by the concrete return-zero getter. Original comparison and virtual dispatch instructions execute; current-tag is an explicit bridge to independently observed canonical getter; concrete MainScreen getStartPageTag executes actual original return-zero body and verified primary table slot. Valid receiver/vtable, no writes; no original default-override implementation, return declaration/layout/ARM ABI or hardware claim.')
