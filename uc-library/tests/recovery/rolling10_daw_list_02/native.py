"""Original application ARM execution; Core boundary is observed, never executed."""
import hashlib,json,pathlib,struct,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_R0,UC_ARM_REG_R1
ROOT=pathlib.Path(__file__).resolve().parents[4]
TASK=pathlib.Path(__file__).parent.name
PACKET=ROOT/'temp/recovery-work/rolling10x10-20261114/prepared05/packets'/TASK
ELF=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared05/snapshot/rootfs/CS18_v13840/home/root/surface')
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
def generate():
 raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 ctx=json.loads((PACKET/'native-context.json').read_text());body=ctx['bodies'][ctx['roots'][0]]
 with ELF.open('rb') as f:
  e=ELFFile(f);sec=e.get_section(body['section_index']);off=sec['sh_offset']+body['address']-sec['sh_addr'];assert off==body['file_offset'] and sec.name==body['section']
 code=raw[off:off+body['size']];assert hashlib.sha256(code).hexdigest()==body['bytes_sha256']
 cases=[]
 for n in range(65):
  for cursor in [0,7,0xffffffff]:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);a=body['address'];u.mem_map(a&~4095,8192);u.mem_write(a,code)
   obj=0x1000000;sp=0x1108000;stop=0x1200000
   u.mem_map(obj,4096);u.mem_map(sp-0x8000,0x10000);u.mem_map(stop,4096)
   def w(p,v):u.mem_write(p,struct.pack('<I',v))
   def r(p):return struct.unpack('<I',u.mem_read(p,4))[0]
   u.mem_write(obj,bytes([0xa5])*128);w(obj+0x40,n);w(obj+0x4c,cursor)
   before=bytes(u.mem_read(obj,128));trace=[];writes=[];insns=[]
   def hook(uc,pc,size,user):
    if pc==0x7ab6c:
     trace.append({'site':pc,'object_offset':uc.reg_read(UC_ARM_REG_R0)-obj,'capacity':uc.reg_read(UC_ARM_REG_R1),'count_before':r(obj+0x40),'cursor_before':r(obj+0x4c)})
     assert trace[-1]['object_offset']==0x38 and trace[-1]['capacity']==0
     # Opaque Core boundary; do not simulate its implementation or mutate total.
     uc.reg_write(UC_ARM_REG_R0,0xbad);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
    assert a<=pc<pc+size<=a+body['size'],hex(pc);insns.append(pc)
   def write(uc,access,p,size,value,user):
    if obj<=p<p+size<=obj+128:writes.append([p-obj,size,value])
   u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
   for reg,v in [(UC_ARM_REG_SP,sp),(UC_ARM_REG_LR,stop),(UC_ARM_REG_R0,obj)]:u.reg_write(reg,v)
   u.emu_start(a,stop,count=100);assert u.reg_read(UC_ARM_REG_PC)==stop
   assert writes==([[76,4,0],[64,4,0]] if TASK.endswith('02') else [])
   assert len(trace)==(1 if TASK.endswith('02') else 0)
   after=bytes(u.mem_read(obj,128));changed=[i for i,(x,y) in enumerate(zip(before,after)) if x!=y]
   cases.append(dict(count=n,cursor=cursor,result=u.reg_read(UC_ARM_REG_R0),count_after=r(obj+0x40),cursor_after=r(obj+0x4c),calls=trace,writes=writes,changed_bytes=changed,instructions=insns))
 return dict(elf_sha256=SHA,elf_path=str(ELF),range={k:body[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},cases=cases,boundary='Native resize target 0x7ab6c is opaque; arguments and pre-call state recorded, r0 poisoned, no Core instructions execute. Only application explicit writes observed. Native offsets are not host layout claims.')
if __name__=='__main__':
 j=generate();p=pathlib.Path(__file__).with_name('fixtures.json')
 if '--generate' in sys.argv:p.write_text(json.dumps(j,indent=2)+'\n')
 else:assert json.loads(p.read_text())==j
 print(len(j['cases']),'original ARM executions')
