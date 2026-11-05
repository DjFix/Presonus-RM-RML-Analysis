"""Exact ARM constructor oracle; every provider entry is intercepted, never run.
Successful construction only. No guest syscalls, hardware, or Core instructions.
"""
from pathlib import Path
import json, hashlib, struct, random
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
R=Path(__file__).resolve().parents[5]; T=Path(__file__).resolve().parent
P=R/'temp/recovery-work/rolling200-02/implementation-plan01/packets-eq-constructors02/packets'
ELF=R/'rootfs/CS18_v13840/home/root/surface'; SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
OBJ=0x400000;RECT=0x401000;STACK=0x500000;STOP=0x600000
BOUNDARIES={0xfb6f4:'Control(rect,null)',0x6f280:'Vector<BandParams>::resize',0xe817c:'LinearInterpolator(0,1)',0xe87d0:'LogInterpolator(0,1)',0x6f434:'Vector<BackgroundPainter*>::resize',0x11f430:'ParamList()',0x120c50:'ParamList::add'}
def digest(b): return hashlib.sha256(b).hexdigest()
def ranges():
 raw=ELF.read_bytes();assert digest(raw)==SHA
 bodies=[]
 with ELF.open('rb') as stream:
  elf=ELFFile(stream);syms=elf.get_section_by_name('.symtab')
  for packet in sorted(P.glob('rolling200_02_eq_constructors_*')):
   req=json.loads((packet/'request.json').read_text());target=req['targets'][0]
   symbol=next(x for x in syms.iter_symbols() if x.name==target['mangled'])
   section=elf.get_section(symbol['st_shndx']);off=section['sh_offset']+symbol['st_value']-section['sh_addr']
   bound=json.loads((packet/'native-context.json').read_text());body=bound['bodies'][bound['roots'][0]]
   assert (symbol['st_value'],symbol['st_size'],symbol['st_shndx'])==(target['address'],target['size'],12)
   assert (off,digest(raw[off:off+symbol['st_size']]))==(body['file_offset'],body['bytes_sha256'])
   bodies.append({'mangled':symbol.name,'address':symbol['st_value'],'size':symbol['st_size'],'section':section.name,'section_index':symbol['st_shndx'],'file_offset':off,'sha256':body['bytes_sha256']})
 return raw,bodies
RAW,RANGES=ranges()
def table(u,address,count):
 assert address==0x19c048 and count==3
 out=[]
 def string(a):
  data=bytearray()
  while a and len(data)<128:
   b=u.mem_read(a,1)[0];a+=1
   if not b:break
   data.append(b)
  return data.decode('ascii')
 for i in range(count):
  b=bytes(u.mem_read(address+i*84,84));kind,tag=struct.unpack_from('<ii',b)
  values=struct.unpack_from('<5f',b,40);flags,unit,curve,strings,title,short=struct.unpack_from('<6I',b,60)
  assert (strings,title,short)==(0,0,0)
  out.append({'type':kind,'tag':tag,'name':b[8:40].split(b'\0')[0].decode(),'values':list(values),'flags':flags,'unit':string(unit),'curve':string(curve),'null_optional_fields':True})
 return out

def execute(body,rectangle):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x300000)
 with ELF.open('rb') as stream:
  for segment in ELFFile(stream).iter_segments():
   if segment['p_type']=='PT_LOAD':u.mem_write(segment['p_vaddr'],segment.data())
 u.mem_protect(0,0x300000,5)
 u.mem_map(OBJ,0x2000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
 u.mem_write(OBJ,b'\xa5'*0x180);u.mem_write(RECT,struct.pack('<4i',*rectangle))
 def w(a,v):u.mem_write(a,struct.pack('<I',v))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 trace=[];pcs=[];writes=[];providers=[];tables=[]
 def write(uc,access,address,size,value,unused):
  assert (OBJ<=address and address+size<=OBJ+0x180) or (STACK<=address and address+size<=STACK+0x10000),(hex(address),size)
  writes.append([address-OBJ if address<STACK else address-STACK,size,value,'object' if address<STACK else 'stack'])
 def code(uc,address,size,unused):
  if address==STOP:uc.emu_stop();return
  if address in BOUNDARIES:
   regs=[uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
   trace.append({'entry':address,'name':BOUNDARIES[address],'receiver_offset':regs[0]-OBJ,'args':regs[1:]})
   if address==0xfb6f4:
    assert regs==[OBJ,RECT,0,0];assert list(struct.unpack('<4i',uc.mem_read(RECT,16)))==rectangle
    # Pinned TViewBase options(0), explicitly modeled boundary observation.
    w(OBJ+0x40,0)
   elif address in (0xe817c,0xe87d0):
    assert regs[1:3]==[0,0x3f800000];providers.append([regs[0]-OBJ,BOUNDARIES[address],0,1])
   elif address in (0x6f280,0x6f434):assert regs[1]==0
   elif address==0x120c50:
    assert regs[0]==OBJ+0x11c and regs[3]==0
    tables.extend(table(uc,regs[1],regs[2]))
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
  assert body['address']<=address and address+size<=body['address']+body['size'],('unbound PC',hex(address))
  assert size==4;pcs.append(address)
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,RECT);u.reg_write(UC_ARM_REG_R3,0)
 u.reg_write(UC_ARM_REG_SP,STACK+0xff00);u.reg_write(UC_ARM_REG_LR,STOP)
 u.emu_start(body['address'],STOP,count=10000)
 assert u.reg_read(UC_ARM_REG_PC)==STOP and u.reg_read(UC_ARM_REG_R0)==OBJ
 expected_offsets=[0x5c,0x60,0x64,0x70,0x78,0x7c,0x80,0x88,0x8c,0x90,0x94,0x98,0x9c,0xf0,0xf8,0xfc,0x104,0x108,0x10c,0x114]
 assert all(r(OBJ+x)==0 for x in expected_offsets)
 color=list(u.mem_read(OBJ+0x6c,4));assert color==[0,0,0,255]
 assert r(OBJ+0x68)==10 and r(OBJ+0x40)==16 and list(u.mem_read(OBJ+0x118,2))==[0,0]
 assert [x['name'] for x in trace]==['Control(rect,null)','Vector<BandParams>::resize','LinearInterpolator(0,1)','LinearInterpolator(0,1)','LogInterpolator(0,1)','LinearInterpolator(0,1)','Vector<BackgroundPainter*>::resize','ParamList()','ParamList::add']
 return {'variant':body['mangled'],'rectangle':rectangle,'state':{'handle':r(OBJ+0x68),'color':color,'requested':r(OBJ+0x70),'buffered':0,'present':r(OBJ+0x114),'valid':0,'clock':r(OBJ+0xf8)+2**32*r(OBJ+0xfc),'empty_containers':True,'null_borrowed_slots':True},'curve_range':[struct.unpack('<f',u.mem_read(OBJ+o,4))[0] for o in [0x88,0x8c]],'providers':providers,'table':tables,'trace':trace,'native_object_writes':writes,'executed_pcs':pcs,'Core_instructions_executed':0}

def curve_range_mapping():
 from capstone import Cs,CS_ARCH_ARM,CS_MODE_ARM
 provenance=R/'uc-library/tests/recovery/rolling200-02/eq-curves/native-execution.json'
 old=json.loads(provenance.read_text());assert old['elf_sha256']==SHA
 with ELF.open('rb') as stream:
  e=ELFFile(stream);symbol=next(x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name=='_ZNK8Presonus9EQControl8getCurveEPfii')
  section=e.get_section(symbol['st_shndx']);off=section['sh_offset']+symbol['st_value']-section['sh_addr']
  body=next(x for x in old['cases'][0]['ranges'] if x['address']==symbol['st_value'])
  assert (off,symbol['st_size'],symbol['st_shndx'])==(body['file_offset'],body['size'],body['section_index'])
  assert digest(RAW[off:off+symbol['st_size']])==body['bytes_sha256']
  observed={i.address:(i.mnemonic,i.op_str) for i in Cs(CS_ARCH_ARM,CS_MODE_ARM).disasm(RAW[off:off+0x80],symbol['st_value'])}
  assert observed[0x6b514]==('ldr','r0, [sl, #0x88]') and observed[0x6b528]==('ldr','r0, [sl, #0x8c]')
 return {'scope':'Static hash/range recheck and original getCurve prologue reads only; not a new native getCurve execution or recovery.', 'provenance':str(provenance.relative_to(R)), 'provenance_sha256':digest(provenance.read_bytes()), 'mangled':symbol.name,'range':body, 'reads':{'0x6b514':'ldr r0, [sl, #0x88]','0x6b528':'ldr r0, [sl, #0x8c]'},'meaning':'Existing source getCurve curveMinimum/curveMaximum bind independent native offsets0x88/0x8c, each initialized0 by original constructor. They do not model frequency-provider bootstrap min/max(0,1).'}

def cases():
 rectangles=[[0,0,100,80],[13,-7,329,154],[0,0,0,0],[-1000,-1000,-999,-998],[50,50,10,10]]
 rand=random.Random(191);rectangles += [[x,y,x+w,y+h] for x,y,w,h in [[rand.randint(-5000,5000),rand.randint(-5000,5000),rand.randint(1,8000),rand.randint(1,8000)] for _ in range(20)]]
 return [execute(body,r) for body in RANGES for r in rectangles]
if __name__=='__main__':
 data={'elf_sha256':SHA,'ranges':RANGES,'curve_range_mapping':curve_range_mapping(),'policy':'Exact original app ranges only; named provider entries intercepted before execution. Private object/stack writes only. No Core/native runtime bodies or syscalls. Successful normal path only, exception landing pads range-verified but unexecuted.','cases':cases()}
 (T/'fixtures.json').write_text(json.dumps(data,indent=2)+'\n');print('50 original constructor executions, two independently checked ranges')
