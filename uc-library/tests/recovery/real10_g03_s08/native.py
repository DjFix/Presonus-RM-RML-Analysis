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
 inputs=[]
 for n in [0,1,3]:
  for mask in sorted({0,1&((1<<n)-1),7&((1<<n)-1)}):
   for params in [0,1,5,7]:
    for current,nextp in [(-1,-1),(0,-1),(2,-1),(0,2),(2,0),(3,-1)]:
     for tags in [[-1000,0,7],[7,7,7],[-2147483648,2147483647,0]]:
      for sortedp in [0,1]:inputs.append([n,mask,params,current,nextp,*tags,sortedp])
 payload=''.join(' '.join(map(str,x))+'\n' for x in inputs);observations=subprocess.check_output([str(exe),'inspect'],input=payload.encode()).decode().splitlines();assert len(observations)==len(inputs);cases=[];provider_inputs=[]
 slot=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/VTABLE_FOLLOWON04.json');slotrow=json.loads(slot.read_text())[0];assert slotrow['elf_sha256']==target['original_elf_sha256'];slotentry=slotrow['slots'][0];assert struct.unpack_from('<I',raw,slotentry['file_offset'])[0]==0x121198
 for inp,line in zip(inputs,observations):
  n,mask,params,current,nextp,*rest=inp;tags=rest[:3];observed=list(map(int,line.split()));assert len(observed)==3*n
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for addr in {body['address']&~4095,helper['address']&~4095,0x11f000,0x121000,0x1000000,0x1100000,0x1200000,0x1300000}:u.mem_map(addr,4096)
  for b in ranges:u.mem_write(b['address'],raw[b['file_offset']:b['file_offset']+b['size']])
  obj=0x1000000;stop=0x1200000;sites=[];writes=[];calls=[];ops=[];array=obj+0x100;vt=obj+0x200;paramvt=obj+0xd00;last=[None]
  def w(p,v):u.mem_write(p,struct.pack('<I',v&0xffffffff))
  def child(i):return obj+0x300+i*0x200
  def page(i):return 0 if i<0 else child(i)+0x100 if i<n else obj+0x900
  w(obj+0x58,array);w(obj+0x5c,n);w(vt,0x1300000);w(obj+0xbc,page(current));w(obj+0xc0,page(nextp));w(paramvt+0x58,0x121198)
  for i in range(n):w(array+4*i,child(i));w(child(i),vt);w(child(i)+0x100+0x8c,tags[i])
  for i in range(3):w(obj+0xa00+i*0x80,paramvt)
  before=bytes(u.mem_read(obj,4096))
  def ret(v):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  def hook(uc,a,size,user):
   if a==0x1300000:
    ptr=uc.reg_read(UC_ARM_REG_R0);i=(ptr-obj-0x300)//0x200;assert i in range(n) and ptr==child(i);assert uc.reg_read(UC_ARM_REG_R1)==1348560741;casts=observed[3*i];last[0]=i;calls.append(['actual-child-cast',i,casts]);ret(page(i) if casts else 0);return
   if a==0x11f24c:
    i=last[0];assert uc.reg_read(UC_ARM_REG_R0)==obj+0x28 and uc.reg_read(UC_ARM_REG_R1)==(tags[i]&0xffffffff);index=observed[3*i+2];calls.append(['actual-ParamList-byTag',tags[i],index]);ret(obj+0xa00+index*0x80 if index>=0 else 0);return
   if a==0x121198:
    ptr=uc.reg_read(UC_ARM_REG_R0);index=(ptr-obj-0xa00)//0x80;assert index in range(3) and ptr==obj+0xa00+index*0x80 and (params&(1<<index));bits=uc.reg_read(UC_ARM_REG_R1);edit=uc.reg_read(UC_ARM_REG_R2);assert bits in [0,0x3f800000] and edit==0;ops.append([index,bits,edit]);calls.append(['NumericParam::setValue',index,bits,edit]);ret(0);return
   assert any(b['address']<=a<a+size<=b['address']+b['size'] for b in ranges),hex(a);sites.append(a)
  def write(uc,access,a,size,v,user):
   if obj<=a<a+size<=obj+4096:writes.append([a-obj,size,v])
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for r,v in [(UC_ARM_REG_SP,0x1100800),(UC_ARM_REG_LR,stop),(UC_ARM_REG_R0,obj)]:u.reg_write(r,v)
  u.emu_start(body['address'],stop,count=500);assert u.reg_read(UC_ARM_REG_PC)==stop;assert not writes and before==bytes(u.mem_read(obj,4096))
  provider_inputs.append(' '.join(map(str,[*inp,len(ops),*[x for op in ops for x in op]])))
  cases.append(dict(input=inp,provider_lookup_observations=line,expected_operations=ops,native_calls=calls,native_instructions=sites,object_writes=writes))
 result=subprocess.check_output([str(exe),'provider'],input=('\n'.join(provider_inputs)+'\n').encode()).decode().splitlines();assert len(result)==len(cases)
 for c,line in zip(cases,result):c['expected']=line
 return dict(producer={'path':str(BASE.relative_to(ROOT)/'native.py'),'sha256':sha(__file__),'unicorn_version':__import__('unicorn').__version__,'method':'independent original ARM instruction execution and separately observed source providers'},case_count=len(cases),elf_sha256=target['original_elf_sha256'],target_range={k:body[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},helper_ranges=[{k:helper[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}],cases=cases,slot_evidence={'path':str(slot),'sha256':sha(slot),'original_target':slotentry},scope='864 bounded cases: empty/1/3 actual CCL children, page/nonpage casts, missing/present/duplicate-tag parameters, current/next identity precedence including external selected page, signed tag extremes, sorted/unsorted actual CCL ParamList. Full original syncPageParams and Page getter execute; casts/ParamList lookup bridge independently observed real canonical providers. Original exact NumericParam::setValue virtual address is a native boundary; ordered float bits/edit arguments feed separate actual pinned NumericParam calls, whose final values and call sequence are compared with compiled product. No Core binary execution, null CCL children, concurrent mutation, notification reentry, original return/layout/ABI or hardware claim.')
