"""Original ARM instructions with explicit app/provider boundary interception.
No Core body is decompiled or emulated. Native boundary traces, not C++ output,
produce expected observations. Full identities and actual ELF mappings checked.
"""
import argparse, hashlib, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
ROOT=Path(__file__).resolve().parents[5]
PACKETS=ROOT/'temp/recovery-work/ranked20-cycle01/batch02/packets'
THIS=0x1000000; ITEM=THIS+0x1000; STACK=0x2000000; STOP=STACK+0x9000

def capture():
 ranges=[];cases=[]
 for i in range(1,21):
  p=PACKETS/f'rank20c01_w06_{i:02}'
  context=json.loads((p/'context.json').read_text());original=context['originals'][0]['original'];native=context['native_context'];body=native['bodies'][native['roots'][0]]
  elf=ROOT/('rootfs/CS18_v13840/home/root/surface' if original['role']=='client' else 'rootfs/RML16AI_Rack_13731/home/root/mixer')
  data=elf.read_bytes();assert hashlib.sha256(data).hexdigest()==original['elf']
  with elf.open('rb') as f:
   e=ELFFile(f);section=e.get_section(body['section_index']);assert body['file_offset']==section['sh_offset']+body['address']-section['sh_addr']
   segments=[(s['p_vaddr'],s.data(),s['p_memsz']) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
  code=data[body['file_offset']:body['file_offset']+body['size']];assert hashlib.sha256(code).hexdigest()==body['bytes_sha256']
  ranges.append(dict(packet=p.relative_to(ROOT).as_posix(),original=original,section=body['section'],file_offset=body['file_offset'],sha256=body['bytes_sha256']))
  if i not in (9,10,15):continue
  variants=range(8) if i==9 else range(6) if i==10 else range(4)
  for variant in variants:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
   bounds=[]
   for a,d,z in sorted(segments):
    lo=a&~4095;hi=(a+z+4095)&~4095
    if bounds and lo<=bounds[-1][1]:bounds[-1][1]=max(hi,bounds[-1][1])
    else:bounds.append([lo,hi])
   for a,b in bounds:u.mem_map(a,b-a)
   for a,d,z in segments:u.mem_write(a,d)
   u.mem_map(THIS,0x10000);u.mem_map(STACK,0x10000)
   u.mem_write(THIS,b'\xa5'*0x100);u.mem_write(ITEM,b'\x5a'*0x100)
   incoming=[0,0x80000000,0xffffffff,0x12345678,0x12345678,0][variant] if i==10 else 0
   u.mem_write(ITEM+0x24,struct.pack('<I',incoming));trace=[];writes=[]
   axis=[0,1,-1,0x7fffffff][variant%4];orientation=[0,-1,0x7fffffff,-2147483648][variant%4]
   name='int' if variant<4 else 'missing'
   if i==9:u.mem_write(THIS+0x2000,name.encode()+b'\0')
   def hook(uc,a,size,_):
    if a==STOP:uc.emu_stop();return
    if i==9 and a==0xe6ebc:
     trace.append(['Core::FormatterRegistry::find',name,struct.unpack('<I',bytes(uc.mem_read(THIS+(0x20 if axis==0 else 0x3c),4)))[0]])
     uc.reg_write(UC_ARM_REG_R0,ITEM if variant<4 else 0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    if i==10 and a==0x762a8:
     trace.append(['findItem',uc.reg_read(UC_ARM_REG_R0),uc.reg_read(UC_ARM_REG_R1)])
     uc.reg_write(UC_ARM_REG_R0,0 if variant==0 else ITEM);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    if i==15 and a==0x116a38:
     ptr=uc.reg_read(UC_ARM_REG_R0);buf=bytearray()
     while True:
      b=bytes(uc.mem_read(ptr+len(buf),1))
      if b==b'\0':break
      buf+=b
     trace.append(['Core::DebugPrintf',buf.decode()]);uc.reg_write(UC_ARM_REG_R0,0xdeadbeef);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   def write(uc,access,a,size,value,_):
    if THIS<=a<THIS+0x10000:writes.append([a-THIS,size,value])
   u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
   for reg,value in [(UC_ARM_REG_R0,THIS),(UC_ARM_REG_R1,THIS+0x2000),(UC_ARM_REG_R2,variant),(UC_ARM_REG_R3,0xffffffff),(UC_ARM_REG_SP,STACK+0x8000),(UC_ARM_REG_LR,STOP)]:u.reg_write(reg,value)
   if i==9:
    u.reg_write(UC_ARM_REG_R1,axis&0xffffffff);u.reg_write(UC_ARM_REG_R2,orientation&0xffffffff);u.reg_write(UC_ARM_REG_R3,THIS+0x2000)
   u.emu_start(body['address'],STOP+4,count=1000);assert u.reg_read(UC_ARM_REG_PC)==STOP
   if i!=9:assert bytes(u.mem_read(THIS,0x100))==b'\xa5'*0x100 and not writes
   else:
    selected=0x20 if axis==0 else 0x3c
    assert writes==[[selected,4,orientation&0xffffffff],[selected+4,4,ITEM if variant<4 else 0]],writes
   cases.append(dict(target=i,variant=variant,input=dict(found=variant!=0,value=incoming,axis=axis,orientation=orientation,name=name),observed=dict(r0=u.reg_read(UC_ARM_REG_R0),trace=trace,writes=writes)))
 return dict(ranges=ranges,cases=cases,scope='18 original target executions; app findItem and pinned Core logging intercepted at explicitly recorded boundaries. No provider native body executes. Other targets range verification only.')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out');ap.add_argument('--verify');args=ap.parse_args();result=capture()
 if args.verify:assert result==json.loads(Path(args.verify).read_text());print('20 exact original ranges and 18 native boundary executions reproduced')
 else:Path(args.out).write_text(json.dumps(result,indent=2)+'\n')
