from pathlib import Path
import hashlib,json,struct,itertools
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
R=Path.cwd(); A=Path(__file__).resolve().parent; E=R/'evidence/recovery/2026-11-05/rolling200-02/stage04-w03';E.mkdir(parents=True,exist_ok=True)
p=R/'rootfs/CS18_v13840/home/root/surface';data=p.read_bytes();sha=hashlib.sha256(data).hexdigest();assert sha=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
with p.open('rb') as f:
 elf=ELFFile(f);table=elf.get_section_by_name('.symtab'); symbols={s.name:s for s in table.iter_symbols()};ranges=[]
 for name in ['_ZN8Presonus11LinkControl4drawERKN4Core8Portable9DrawEventE','_ZNK8Presonus11LinkControl8isLinkedEv','_ZNK8Presonus11LinkControl17isRightSideOfLinkEv']:
  s=symbols[name];sec=elf.get_section(s['st_shndx']);offset=sec['sh_offset']+s['st_value']-sec['sh_addr'];raw=data[offset:offset+s['st_size']];ranges.append(dict(mangled=name,address=s['st_value'],size=s['st_size'],section=sec.name,file_offset=offset,sha256=hashlib.sha256(raw).hexdigest(),raw=raw))
print(json.dumps([{k:v for k,v in r.items() if k!='raw'} for r in ranges],indent=2))
expected_hashes=['fe6596ef40061f17ae48af3d12cf118a20214a369dd71cf60b755ebaa2695e79','6356f69cc66b8b057c1c1d5a1b84e8b4912a6863f926f998e03f602cdf5f83e9','3c39d56cdc87ac3698dbd0923a8cc77a07c1679b0c242cc74d4e4c412877ee21']
assert [r['sha256'] for r in ranges]==expected_hashes
u=Uc(UC_ARCH_ARM,UC_MODE_ARM);obj=0x300000;event=obj+0x200;graphics=obj+0x400;gv=obj+0x500;lp=obj+0x600;sp=obj+0x700;pv=obj+0x800;stack=0x400000;stop=0x500000;getvalue=0x510000;draw=0x510004
for base in [0x64000,0x65000,obj,stack,stop,getvalue,0xf6000,0x187000]:u.mem_map(base,4096)
for r in ranges:u.mem_write(r['address'],r['raw'])
def write(a,*vals):u.mem_write(a,struct.pack('<'+'I'*len(vals),*(v&0xffffffff for v in vals)))
def read(a,n):return list(struct.unpack('<'+'i'*n,u.mem_read(a,n*4)))
trace=[];pcs=set();state={}
def hook(uc,pc,size,_):
 if pc==stop:uc.emu_stop();return
 if pc==0xf6cf8:
  assert uc.reg_read(UC_ARM_REG_R0)==obj;trace.append('Control::getParameter');uc.reg_write(UC_ARM_REG_R0,lp if state['linked']>=0 else 0)
 elif pc==getvalue:
  p=uc.reg_read(UC_ARM_REG_R0);assert p in [lp,sp];trace.append('Parameter::getValue:'+('linked' if p==lp else 'side'));v=state['linked' if p==lp else 'side'];uc.reg_write(UC_ARM_REG_R0,struct.unpack('<I',struct.pack('<f',float(v)))[0])
 elif pc==0x187780:
  a=struct.unpack('<f',struct.pack('<I',uc.reg_read(UC_ARM_REG_R0)))[0];b=struct.unpack('<f',struct.pack('<I',uc.reg_read(UC_ARM_REG_R1)))[0];trace.append('__aeabi_fcmpeq');uc.reg_write(UC_ARM_REG_R0,int(a==b))
 elif pc==draw:
  assert uc.reg_read(UC_ARM_REG_R0)==graphics;point=read(uc.reg_read(UC_ARM_REG_R1),2);bitmap=uc.reg_read(UC_ARM_REG_R2);src=uc.reg_read(UC_ARM_REG_R3);assert src==event+4;state['observed']=[1 if bitmap==obj+0x900 else 2,*point];trace.append(dict(call='Graphics::drawBitmap',point=point,bitmap=bitmap,source=read(src,4)))
 else:
  assert any(r['address']<=pc<r['address']+r['size'] for r in ranges),hex(pc);pcs.add(pc);return
 uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
u.hook_add(UC_HOOK_CODE,hook);records=[];lines=[];allpcs=set()
for linked,left,right,side,geometry in itertools.product([-1,0,1],[0,1],[0,1],[-1,0,1],[(0,0,20,30,0,0),(-17,29,95,102,80,-90),(123,-456,789,-12,-33,77)]):
 x,y,z,w,ox,oy=geometry;state=dict(linked=linked,side=side,observed=[0,0,0]);trace=[];pcs=set();u.mem_write(obj,b'\0'*4096);write(obj+0x58,obj+0x900 if left else 0,obj+0xa00 if right else 0);write(obj+0x64,sp if side>=0 else 0);write(event,graphics,x,y,z,w,ox,oy);write(graphics,gv);write(gv+0x28,draw);write(lp,pv);write(sp,pv);write(pv+0x44,getvalue);before=bytes(u.mem_read(obj,4096));u.reg_write(UC_ARM_REG_CPSR,0x10);u.reg_write(UC_ARM_REG_SP,stack+4000);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,event);u.emu_start(0x65c60,stop,count=300);assert u.reg_read(UC_ARM_REG_PC)==stop;assert bytes(u.mem_read(obj,4096))==before
 obs=state['observed'];lines.append(' '.join(map(str,[linked,left,right,side,*geometry,*obs])));records.append(dict(inputs=[linked,left,right,side,*geometry],observation=obs,calls=trace,executed_pcs=sorted(pcs)));allpcs.update(pcs)
(E/'native-cases.json').write_text(json.dumps(records,indent=2)+'\n');(E/'fixtures.txt').write_text('\n'.join(lines)+'\n');proof=dict(passed=True,cases=len(records),elf_sha256=sha,ranges=[{k:v for k,v in r.items() if k!='raw'} for r in ranges],executed_pcs=sorted(allpcs),target_pc_coverage=[hex(pc) for pc in sorted(allpcs) if 0x65c60<=pc<0x65d10],boundaries={'0xf6cf8':'real CCL getParameter receiver contract, supplied pointer','0x510000':'synthetic Parameter::getValue vtable boundary, supplied numeric float','0x187780':'runtime __aeabi_fcmpeq float equality','0x510004':'synthetic Graphics::drawBitmap slot records geometry only'},limitations='Original target and two hash-bound app helpers executed. Provider/runtime boundaries intercepted, never executed. Initialized synthetic native state does not establish original field types/layout, ARM ABI or hardware. Source uses real CCL parameter and bitmap objects, recording abstract Graphics boundary. Ordinary return unresolved; source-port void and modern null mode intentional.')
(E/'native-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(dict(passed=True,cases=len(records))))
