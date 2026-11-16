"""Full selected app and original PageComponent getter execution."""
import hashlib,json,pathlib,struct,subprocess
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4];BASE=pathlib.Path(__file__).parent;TASK=BASE.name
SNAP=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/prepared-main/snapshot')
PACKET=ROOT/'temp/recovery-work/reconstruction10x10-20261116/prepared-main/packets'/TASK
EXP=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/expansions/bound-20261116T055348/g03-show-start/native-context.json')
START=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/expansions/root-followon01/main-screen-start-tag/native-context.json')
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def generate(exe):
 target=json.loads((PACKET/'request.json').read_text())['targets'][0];ev=SNAP/('temp/recovery-work/reconstruction10x10-20261116/native/'+TASK+'.json');body=json.loads(ev.read_text())['body'];helper=next(v for v in json.loads(EXP.read_text())['bodies'].values() if v['address']==0x73c24)
 elf=SNAP/'rootfs/CS18_v13840/home/root/surface';assert sha(elf)==target['original_elf_sha256'];raw=elf.read_bytes();startbody=next(iter(json.loads(START.read_text())['bodies'].values()));ranges=[body,helper,startbody]
 assert struct.unpack_from('<I',raw,0x1983ac)[0]==startbody['address']
 with elf.open('rb') as f:
  e=ELFFile(f)
  for b in ranges:
   sec=e.get_section(b['section_index']);assert sec.name==b['section'];assert sec['sh_offset']+b['address']-sec['sh_addr']==b['file_offset'];assert hashlib.sha256(raw[b['file_offset']:b['file_offset']+b['size']]).hexdigest()==b['bytes_sha256']
 tags=[-2147483648,-1000,-1,*range(0,34),2147483647];inputs=[[a,h] for a in tags for h in [0,1]];payload=''.join(f'{a} {h}\n' for a,h in inputs);provider=subprocess.check_output([str(exe),'provider'],input=payload.encode()).decode().splitlines();assert len(provider)==len(inputs);cases=[]
 for inp,line in zip(inputs,provider):
  observed=int(line)
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for addr in {body['address']&~4095,helper['address']&~4095,startbody['address']&~4095,0x1000000,0x1100000,0x1200000,0x1300000}:u.mem_map(addr,4096)
  for b in ranges:u.mem_write(b['address'],raw[b['file_offset']:b['file_offset']+b['size']])
  obj=0x1000000;stop=0x1200000;sites=[];writes=[];calls=[]
  u.mem_write(obj,struct.pack('<I',obj+0x100));u.mem_write(obj+0x100+0x2c,struct.pack('<I',startbody['address']))
  before=bytes(u.mem_read(obj,4096))
  def ret(v):u.reg_write(UC_ARM_REG_R0,v&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  def hook(uc,a,size,user):
   if a==0x738b0:
    assert uc.reg_read(UC_ARM_REG_R0)==obj;calls.append(['canonical-current-page-tag',observed]);ret(observed);return
   if a==0x73bf8:
    assert uc.reg_read(UC_ARM_REG_R0)==obj and uc.reg_read(UC_ARM_REG_R1)==0;calls.append(['show-page-boundary',0]);ret(0);return
   assert any(b['address']<=a<a+size<=b['address']+b['size'] for b in ranges),hex(a);sites.append(a)
  def write(uc,access,a,size,v,user):
   if obj<=a<a+size<=obj+4096:writes.append([a-obj,size,v])
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for r,v in [(UC_ARM_REG_SP,0x1100800),(UC_ARM_REG_LR,stop),(UC_ARM_REG_R0,obj)]:u.reg_write(r,v)
  u.emu_start(body['address'],stop,count=150);assert u.reg_read(UC_ARM_REG_PC)==stop;assert not writes and before==bytes(u.mem_read(obj,4096))
  cases.append(dict(input=inp,expected=str(sum(c[0]=='show-page-boundary' for c in calls)),provider=line,native_calls=calls,native_instructions=sites,object_writes=writes))
 return dict(producer={'path':str(BASE.relative_to(ROOT)/'native.py'),'sha256':sha(__file__),'unicorn_version':__import__('unicorn').__version__,'method':'independent original ARM instruction execution and separately observed source providers'},case_count=len(cases),elf_sha256=target['original_elf_sha256'],target_range={k:body[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},helper_ranges=[{k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']} for b in [helper,startbody]],cases=cases,scope='Signed page-tag extremes, all 0..33 and absent current page. Original application plus expanded showStartPage instructions execute. getCurrentPageTag bridge uses separately observed actual canonical provider result; concrete getStartPageTag executes original return-zero body with verified table slot; showPage is an explicit trace boundary. Actual product executes real canonical providers and requestPage test boundary. No original return/layout/ARM ABI or hardware claim.')
