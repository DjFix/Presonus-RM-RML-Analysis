"""Full selected app and original PageComponent getter execution."""
import hashlib,json,pathlib,struct,subprocess
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4];BASE=pathlib.Path(__file__).parent;TASK=BASE.name
SNAP=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/prepared-main/snapshot')
PACKET=ROOT/'temp/recovery-work/reconstruction10x10-20261116/prepared-main/packets'/TASK
EXP=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/expansions/bound-20261116T055348/g03-page-tag/native-context.json')
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def generate(exe):
 target=json.loads((PACKET/'request.json').read_text())['targets'][0];ev=SNAP/('temp/recovery-work/reconstruction10x10-20261116/native/'+TASK+'.json');body=json.loads(ev.read_text())['body'];helper=next(v for v in json.loads(EXP.read_text())['bodies'].values() if v['address']==0x64660)
 elf=SNAP/'rootfs/CS18_v13840/home/root/surface';assert sha(elf)==target['original_elf_sha256'];raw=elf.read_bytes();ranges=[body,helper]
 with elf.open('rb') as f:
  e=ELFFile(f)
  for b in ranges:
   sec=e.get_section(b['section_index']);assert sec.name==b['section'];assert sec['sh_offset']+b['address']-sec['sh_addr']==b['file_offset'];assert hashlib.sha256(raw[b['file_offset']:b['file_offset']+b['size']]).hexdigest()==b['bytes_sha256']
 inputs=[[a,b,p,m] for a in [-1000,0,3,7,29,30] for b in [-1000,0,3,7,29,30] for p in [0,1] for m in [0,1]]
 provider_inputs=[[mode,enabled,0,0] for mode in [0,1,2] for enabled in [0,1]]
 provider=subprocess.check_output([str(exe),'provider'],input=''.join(' '.join(map(str,x))+'\n' for x in provider_inputs).encode()).decode().splitlines();assert len(provider)==len(provider_inputs);lookup={(x[0],x[1]):line for x,line in zip(provider_inputs,provider)};cases=[]
 for inp in inputs:
  a,b,previous,bound=inp
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for addr in {body['address']&~4095,helper['address']&~4095,0x7f000,0x1000000,0x1100000,0x1200000}:u.mem_map(addr,4096)
  for r in ranges:u.mem_write(r['address'],raw[r['file_offset']:r['file_offset']+r['size']])
  obj=0x1000000;page=obj+0x200;old=obj+0x400;mapping=obj+0x600;stop=0x1200000;sites=[];writes=[];calls=[]
  for p,v in [(page+0x8c,a),(old+0x8c,b),(obj+0xf8,mapping if bound else 0)]:u.mem_write(p,struct.pack('<I',v&0xffffffff))
  before=bytes(u.mem_read(obj,4096))
  def hook(uc,addr,size,user):
   if addr in [0x7f314,0x7f24c]:
    assert uc.reg_read(UC_ARM_REG_R0)==mapping;mode=1 if addr==0x7f314 else 2;enabled=uc.reg_read(UC_ARM_REG_R1);assert enabled in [0,1];calls.append([mode,enabled]);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   assert any(r['address']<=addr<addr+size<=r['address']+r['size'] for r in ranges),hex(addr);sites.append(addr)
  def write(uc,access,p,size,v,user):
   if obj<=p<p+size<=obj+4096:writes.append([p-obj,size,v])
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for r,v in [(UC_ARM_REG_SP,0x1100800),(UC_ARM_REG_LR,stop),(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,page),(UC_ARM_REG_R2,old if previous else 0)]:u.reg_write(r,v)
  u.emu_start(body['address'],stop,count=200);assert u.reg_read(UC_ARM_REG_PC)==stop;assert not writes and before==bytes(u.mem_read(obj,4096));assert len(calls)<=1
  expected=lookup[tuple(calls[0])] if calls else lookup[(0,0)]
  cases.append(dict(input=inp,expected=expected,native_calls=calls,native_instructions=sites,object_writes=writes))
 return dict(producer={'path':str(BASE.relative_to(ROOT)/'native.py'),'sha256':sha(__file__),'unicorn_version':__import__('unicorn').__version__,'method':'independent original ARM instruction execution and separately observed source providers'},case_count=len(cases),elf_sha256=target['original_elf_sha256'],target_range={k:body[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},helper_ranges=[{k:helper[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}],cases=cases,provider_observations=[dict(input=x,expected=line) for x,line in zip(provider_inputs,provider)],scope='Page transitions across tag3/tag29 precedence, equal tags, unrelated tags and null previous/mapping. Full original app and getter instructions run. Native Mapping calls are explicit argument trace boundaries; expected parameter observations come separately from actual canonical Mapping methods on real CCL numeric parameters. Product wraps and executes those real providers; null encoder handler domain. No hardware/layout/return declaration/ARM ABI claim.')
