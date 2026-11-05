"""Original application instruction observations, with explicit providers only.
Core and compiler runtime bodies never execute. No original C++ ABI claim.
"""
from pathlib import Path
import hashlib,json,struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[5]
PKT=ROOT/'temp/recovery-work/rolling200-02/implementation-plan01/packets-current-eq01/packets'
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
OBJ,RECT,STACK,STOP=0x400000,0x401000,0x500000,0x600000

def run(case):
 raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 t=case['target'];p=PKT/f'rolling200_02_current_eq_{t:02d}'
 ctx=json.loads((p/'native-context.json').read_text());body=ctx['bodies'][ctx['roots'][0]]
 with ELF.open('rb') as f:
  e=ELFFile(f);s=e.get_section(body['section_index']);offset=s['sh_offset']+body['address']-s['sh_addr'];assert offset==body['file_offset'];assert hashlib.sha256(raw[offset:offset+body['size']]).hexdigest()==body['bytes_sha256']
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x300000)
 with ELF.open('rb') as f:
  for seg in ELFFile(f).iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 for address,size in [(OBJ,0x10000),(STACK,0x10000),(STOP,0x1000)]:u.mem_map(address,size)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 w(OBJ+0x70,case.get('initial_count',0));u.mem_write(OBJ+0xf8,struct.pack('<q',case.get('last',0)))
 rectangle=case.get('rectangle',[0,0,8,80]);u.mem_write(RECT,struct.pack('<4i',*rectangle));trace=[];pcs=set()
 allowed={1:{0x6dbe0:'initBands'},2:{0x1116b4:'View::setSize',0x6dbe0:'initBands'},5:{0xf8588:'Control::onIdle',0x1178a4:'GetAbsoluteTime',0x1878a8:'signed64divide',0x6c62c:'rebuildCurves'}}[t]
 def hook(uc,pc,size,_):
  if pc==STOP:u.emu_stop();return
  if pc in allowed:
   name=allowed[pc];trace.append({'call':name,'count':r(OBJ+0x70),'time':struct.unpack('<q',u.mem_read(OBJ+0xf8,8))[0]})
   if name=='View::setSize':assert uc.reg_read(UC_ARM_REG_R1)==RECT;trace[-1]['rectangle']=list(struct.unpack('<4i',u.mem_read(RECT,16)))
   elif name=='GetAbsoluteTime':
    now=case['now_ns'];uc.reg_write(UC_ARM_REG_R0,now&0xffffffff);uc.reg_write(UC_ARM_REG_R1,(now>>32)&0xffffffff)
   elif name=='signed64divide':
    n=(uc.reg_read(UC_ARM_REG_R1)<<32)|uc.reg_read(UC_ARM_REG_R0);n=n if n<2**63 else n-2**64
    divisor=(uc.reg_read(UC_ARM_REG_R3)<<32)|uc.reg_read(UC_ARM_REG_R2);assert divisor==1000000
    quotient=(abs(n)//divisor)*(-1 if n<0 else 1);uc.reg_write(UC_ARM_REG_R0,quotient&0xffffffff);uc.reg_write(UC_ARM_REG_R1,(quotient>>32)&0xffffffff)
   if name in ['initBands','rebuildCurves']:
    # Tail branch and ordinary BL both return through original LR.
    uc.reg_write(UC_ARM_REG_R0,1)
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
  assert body['address']<=pc and pc+size<=body['address']+body['size'],f'unbound PC {pc:#x}'
  pcs.add(pc)
 u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_ARM_REG_SP,STACK+0x8000);u.reg_write(UC_ARM_REG_LR,STOP);u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,RECT if t==2 else case.get('count',0)&0xffffffff)
 u.emu_start(body['address'],STOP,count=10000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 return {'trace':trace,'count':r(OBJ+0x70),'last':struct.unpack('<q',u.mem_read(OBJ+0xf8,8))[0],'pcs':sorted(pcs),'range':{k:body[k] for k in ['address','size','file_offset','bytes_sha256','section','section_index']}}
def cases():
 out=[]
 for n in [0,1,3]:out.append({'target':1,'count':n})
 for rect in [[0,0,8,80],[0,0,8,80],[2,3,3,4],[0,0,0,5],[0,0,-1,5],[0,0,5,0]]:out.append({'target':2,'rectangle':rect})
 for last,now in [(100,132),(100,133),(100,134),(100,100),(100,99),(0,2**32+34),(2**32+100,2**32+133),(2**32+100,2**32+134)]:out.append({'target':5,'last':last,'now_ns':now*1000000})
 return [{**c,'expected':run(c)} for c in out]
if __name__=='__main__':
 import sys
 result={'elf_sha256':SHA,'cases':cases(),'limitations':'Original target instruction execution; initBands/rebuildCurves, Core and arithmetic are intercepted provider/application boundaries. Actual canonical implementations execute separately in C++ replay; no instruction-derived claim for intercepted bodies.'}
 Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n');print(len(result['cases']))
