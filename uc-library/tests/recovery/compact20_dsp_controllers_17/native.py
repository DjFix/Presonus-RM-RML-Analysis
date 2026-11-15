"""Execute exact original application instructions; pinned Core remains a boundary."""
import argparse,hashlib,json,struct
from pathlib import Path
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
CANONICAL=Path('/home/rs/projects/opencs/ai-line-analysis')
TASK=Path(__file__).parent.name
PACKET=CANONICAL/'temp/recovery-work/compact-10x20-20261113/generated-implementation40/prepared03/packets'/TASK
HASH='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
def main():
 p=argparse.ArgumentParser();p.add_argument('--elf',default=str(CANONICAL/'rootfs/CS18_v13840/home/root/surface'));p.add_argument('--out',required=True);a=p.parse_args()
 req=json.loads((PACKET/'request.json').read_text());t=req['targets'][0];blob=Path(a.elf).read_bytes();assert hashlib.sha256(blob).hexdigest()==HASH
 with open(a.elf,'rb') as f:
  elf=ELFFile(f);syms=[s for sec in elf.iter_sections() if sec['sh_type']=='SHT_SYMTAB' for s in sec.iter_symbols() if s.name==t['mangled']];assert len(syms)==1;s=syms[0];sec=elf.get_section(s['st_shndx']);assert(s['st_value'],s['st_size'],sec.name)==(t['address'],t['size'],'.text');off=sec['sh_offset']+s['st_value']-sec['sh_addr'];segments=[(seg['p_vaddr'],seg.data()) for seg in elf.iter_segments() if seg['p_type']=='PT_LOAD']
 body=blob[off:off+t['size']];cases=[];kind=int(TASK[-2:])
 configs=[(old,new) for old in [0,1,2] for new in [0,1,2]] if kind==1 else [(0,0)]
 for old,new in configs:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x290000)
  for addr,data in segments:u.mem_write(addr,data)
  u.mem_map(0x300000,0x30000);u.mem_write(0x300000,b'\xa5'*256);u.reg_write(UC_ARM_REG_SP,0x32ff00);u.reg_write(UC_ARM_REG_LR,0x1000);u.reg_write(UC_ARM_REG_R0,0x300000);trace=[];observers={0x301000:[11],0x302000:[22]};ptrs=[0,0x301000,0x302000]
  def word(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
  if kind==1:
   if old:observers[ptrs[old]].extend([0x30000c,33])
   u.mem_write(0x303000,struct.pack('<I',ptrs[old]));u.reg_write(UC_ARM_REG_R1,0x303000);u.reg_write(UC_ARM_REG_R2,ptrs[new])
  def hook(uc,pc,size,data):
   r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);r2=uc.reg_read(UC_ARM_REG_R2)
   if pc==0x1000:uc.emu_stop();return
   if pc==0x11e2e0:trace.append(['remove',r0,r1]);observers[r0].remove(r1)
   elif pc==0x11f4f0:trace.append(['add',r0,r1]);observers[r0].append(r1)
   elif pc==0x11f77c:trace.append(['ParamList_destroy',r0])
   elif pc==0xad5c:
    assert r0==0x300000;trace.append(['operator_delete',r0]);uc.mem_write(r0,b'\xdd'*256)
   elif pc==0x11af30:
    raw=bytes(uc.mem_read(r1,32)).split(b'\0')[0].decode();trace.append(['Component_construct',raw])
   elif pc==0x120c50:
    records=bytes(uc.mem_read(r1,r2*84));trace.append(['ParamList_add',r0,r1,r2]);descriptors=[]
    for j in range(r2):
     raw=records[j*84:(j+1)*84];typ,tag=struct.unpack_from('<ii',raw);descriptors.append({'type':typ,'tag':tag,'name':raw[8:40].split(b'\0')[0].decode(),'values':list(struct.unpack_from('<5f',raw,40)),'flags':struct.unpack_from('<i',raw,60)[0]})
    case['descriptors']=descriptors;case['descriptor_range']={'address':r1,'size':len(records),'sha256':hashlib.sha256(records).hexdigest(),'hex':records.hex()}
   elif not(t['address']<=pc<t['address']+t['size']):raise RuntimeError('Unexpected execution outside target '+hex(pc))
   else:return
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  case={'old':old,'new':new};u.hook_add(UC_HOOK_CODE,hook);u.emu_start(t['address'],0x290000,count=1000);case['trace']=trace
  if kind==1:case.update(slot=ptrs.index(word(0x303000)),observers=[[11 if x==11 else 22 if x==22 else 33 if x==33 else 99 for x in observers[p]] for p in ptrs[1:]])
  elif kind in [4,5]:case.update(paramlist_offset=trace[0][1]-0x300000,deleted=any(x[0]=='operator_delete' for x in trace))
  else:case.update(daw_null=word(0x30008c)==0)
  cases.append(case)
 out={'version':1,'target':t,'elf_sha256':HASH,'file_offset':off,'section':'.text','range_sha256':hashlib.sha256(body).hexdigest(),'producer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'unicorn_version':unicorn.__version__,'cases':cases,'limitations':['Only original application target instructions execute. Core observer/list/component operations intercepted, not Core binary execution.','Native allocator delete boundary observed at actual original call then mapped storage poisoned; libc allocator semantics assumed.','Exception unwind paths not executed; no original hardware/layout/ABI claim.']};Path(a.out).write_text(json.dumps(out,indent=2)+'\n');print(TASK,len(cases),'native cases')
if __name__=='__main__':main()
