"""Independent ARM entry executions; Core external operations are provider boundaries."""
import hashlib,json,struct,math
from pathlib import Path
from io import BytesIO
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ROOT=Path.cwd()
TASK=Path(__file__).parent.name
PACKET=Path('temp/recovery-work/sqlite-issued/packet')/TASK/'CONTEXT.json'
R,P,IO,VT,PV,IV,Q,STACK,STOP,HOOK=0x20000000,0x20001000,0x20002000,0x20003000,0x20004000,0x20005000,0x20006000,0x2000d000,0x2000e000,0x2000f000

def sha(b): return hashlib.sha256(b).hexdigest()
def observe():
 contexts=[json.loads((PACKET.parent.parent/('sqlite_meter_peak_'+n)/'CONTEXT.json').read_text()) for n in ('param_changed','transmit','broadcast_value')]
 results=[]; proofs=[]
 for roleidx in range(2):
  originals=[c['originals'][roleidx]['original'] for c in contexts]
  image=Path(originals[0]['elf_path']).read_bytes(); assert sha(image)==originals[0]['elf']
  elf=ELFFile(BytesIO(image)); syms=elf.get_section_by_name('.symtab')
  def sym(n):
   s=syms.get_symbol_by_name(n); assert s,n
   return s[0]
  def addr(n):return sym(n)['st_value']
  ranges=[]
  for o in originals:
   s=sym(o['mangled']);sec=elf.get_section(s['st_shndx']); off=sec['sh_offset']+s['st_value']-sec['sh_addr']
   body=image[off:off+s['st_size']]
   assert (s['st_value'],s['st_size'],s['st_shndx'],off)==(o['address'],o['size'],o['section'],o['file_offset'])
   assert sha(body)==o['range_sha256'] and body.hex()==o['range_hex']
   ranges.append(dict(o,verified_file_offset=off))
  vt=addr('_ZTVN8Presonus5Panel16MeterPeakControlE')+8
  def fileword(a):
   for seg in elf.iter_segments():
    if seg['p_type']=='PT_LOAD' and seg['p_vaddr']<=a<seg['p_vaddr']+seg['p_filesz']:
     return struct.unpack_from('<I',image,seg['p_offset']+a-seg['p_vaddr'])[0]
   raise AssertionError(hex(a))
  assert fileword(vt+0x20)==originals[2]['address']
  assert fileword(vt+0x24)==originals[1]['address']
  tx=originals[1]['address']; disabled=fileword(tx+0xd4); dirty=fileword(tx+0xd8)
  assert disabled==addr('_ZN8Presonus5Panel7Control17gDisableBroadcastE')
  assert dirty==addr('_ZN8Presonus5Panel7Control19gBroadcastDirtyListE')
  growword=fileword(tx+0xc4); delta=(growword&0xffffff)<<2
  if delta&(1<<25):delta-=1<<26
  grow=tx+0xc4+8+delta
  cases=[]
  if TASK.endswith('broadcast_value'):
   for value in [-2147483648,-1,0,1,16,17,2147483647]:
    for offset in [0,7,2147483647,-2147483648]:
     for equal in [False,True]:cases.append(dict(kind='broadcast',value=value,offset=offset,last=((value+offset)&0xffffffff) if equal else 0xdeadbeef,tag=0x123))
  elif TASK.endswith('transmit'):
   for tag in [-1,0,0x123,2147483647]:
    for last in [0,16,0x123,0xffffffff]:
     for mode in ['direct','empty','duplicate','room','full']:
      for byte3 in ([0,5,171,255] if mode=='direct' else [0]):cases.append(dict(kind='transmit',tag=tag,last=last,mode=mode,byte3=byte3))
  else:
   for message in [0,1,2,3,4,5]:
    for tag in [-1,19]:
     for table in ['input','output','override','empty']:
      for value in [0.0,0.25,0.5,0.75,1.,2.]:cases.append(dict(kind='param',message=message,tag=tag,table=table,value=value,last=0xffffffff,offset=0))
  for case in cases:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM); pages=set()
   for seg in elf.iter_segments():
    if seg['p_type']!='PT_LOAD':continue
    start=seg['p_vaddr']&~4095;end=(seg['p_vaddr']+seg['p_memsz']+4095)&~4095
    # PT_LOAD page ranges in these two ELFs do not overlap.
    u.mem_map(start,end-start)
    u.mem_write(seg['p_vaddr'],seg.data())
   u.mem_map(R,0x10000)
   u.mem_write(STACK-25,bytes([case.get('byte3',0)]))
   def w(a,*v):u.mem_write(a,struct.pack('<'+'I'*len(v),*[i&0xffffffff for i in v]))
   def rd(a):return struct.unpack('<I',u.mem_read(a,4))[0]
   def ret(value=None):
    if value is not None:u.reg_write(UC_ARM_REG_R0,value&0xffffffff)
    u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   w(R,vt,case['last'],0,0,0,IO,case['tag'],case.get('offset',0),0,0)
   w(IO,IV);w(IV+4,HOOK);w(P,PV);w(PV+0x60,HOOK+4)
   if case.get('message')==5:w(R+8,P)
   thresholds={'input':[0.25,0.5,1.0],'output':[0.5,1.0],'override':[0.125,0.75],'empty':[]}
   for name in ['input','output']:
    a=addr('_ZN8Presonus5Panel12MeterControl'+('10inputTableE' if name=='input' else '11outputTableE'))
    vals=thresholds[name];w(a,len(vals));u.mem_write(a+4,struct.pack('<'+'f'*len(vals),*vals))
   if case['kind']=='param':
    table=case['table']
    if table in ['override','empty']:
     vals=thresholds[table];w(R+0x20,P+0x400);w(P+0x400,len(vals))
     if vals:u.mem_write(P+0x404,struct.pack('<'+'f'*len(vals),*vals))
    else:w(R+0x24,0 if table=='input' else 1)
   mode=case.get('mode','direct');w(disabled,0 if mode=='direct' else 1)
   items=[] if mode in ['direct','empty'] else ([R] if mode=='duplicate' else [R+0x100])
   capacity=len(items) if mode in ['empty','full'] else 4
   w(dirty,0,Q,len(items),capacity);w(Q,*items)
   calls=[];packets=[];growth=[];writes=[]
   base=addr('_ZN8Presonus5Panel7Control12paramChangedEPN4Core8Portable9ParameterEi')
   remove=addr('_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE')
   compare=addr('__aeabi_fcmplt')
   def hook(uc,a,size,data):
    if a==STOP:uc.emu_stop()
    elif a==HOOK:
     assert uc.reg_read(UC_ARM_REG_R0)==IO
     packets.append(list(uc.mem_read(uc.reg_read(UC_ARM_REG_R1),4)));ret(0)
    elif a==HOOK+4:
     assert uc.reg_read(UC_ARM_REG_R0)==P;calls.append('getValue')
     ret(struct.unpack('<I',struct.pack('<f',case['value']))[0])
    elif a==compare:
     f=lambda r:struct.unpack('<f',struct.pack('<I',uc.reg_read(r)))[0]
     ret(int(f(UC_ARM_REG_R0)<f(UC_ARM_REG_R1)))
    elif a==remove:calls.append('removeObserver');ret()
    elif a==base:
     assert uc.reg_read(UC_ARM_REG_R0)==R and uc.reg_read(UC_ARM_REG_R1)==P
     calls.append('Control::paramChanged')
    elif a==originals[2]['address']:
     assert uc.reg_read(UC_ARM_REG_R0)==R
     calls.append('broadcastValue')
    elif a==originals[1]['address']:
     assert uc.reg_read(UC_ARM_REG_R0)==R
     calls.append('transmit')
    elif a==grow:
     assert uc.reg_read(UC_ARM_REG_R0)==dirty
     need=uc.reg_read(UC_ARM_REG_R1);growth.append(need);w(dirty+12,need);ret(1)
   u.hook_add(UC_HOOK_CODE,hook)
   u.reg_write(UC_ARM_REG_SP,STACK);u.reg_write(UC_ARM_REG_LR,STOP);u.reg_write(UC_ARM_REG_R0,R)
   idx={'param':0,'transmit':1,'broadcast':2}[case['kind']]
   u.reg_write(UC_ARM_REG_R1,P if idx==0 else case.get('value',0)&0xffffffff)
   u.reg_write(UC_ARM_REG_R2,case.get('message',0))
   u.emu_start(originals[idx]['address'],STOP+4,count=10000)
   assert u.reg_read(UC_ARM_REG_PC)==STOP
   queue=[rd(Q+i*4)==R for i in range(rd(dirty+8))]
   encoded=[]
   for packet in packets:
    u.mem_write(P+0x800,bytes(packet));u.mem_write(P+0x900,b'\0'*64)
    u.reg_write(UC_ARM_REG_SP,STACK);u.reg_write(UC_ARM_REG_LR,STOP)
    u.reg_write(UC_ARM_REG_R0,P+0x800);u.reg_write(UC_ARM_REG_R1,P+0x900)
    u.emu_start(addr('uart_protocol_encode'),STOP+4,count=10000)
    assert u.reg_read(UC_ARM_REG_PC)==STOP
    length=u.reg_read(UC_ARM_REG_R0);assert 0<length<64
    encoded.append(bytes(u.mem_read(P+0x900,length)).decode('ascii'))
   results.append(dict(role=originals[0]['role'],input=case,level=rd(R+4),queue=queue,packets=packets,encoded=encoded,calls=calls,growth=growth,parameter_pointer=rd(R+8)))
  proofs.append(dict(elf_sha256=sha(image),ranges=ranges,encoder_dependencies=[dict(mangled=n,address=addr(n),size=sym(n)['st_size'],range_sha256=sha(bytes(u.mem_read(addr(n),sym(n)['st_size'])))) for n in ['uart_protocol_encode','utils_ConvertInt2Hex']],vtable=vt,disabled_address=disabled,dirty_address=dirty,provider_boundaries=['float getValue','__aeabi_fcmplt','Parameter::removeObserver','Vector::resize'],cases=len(cases)))
 return dict(version=1,task=TASK,proofs=proofs,cases=results)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();Path(a.out).write_text(json.dumps(observe(),indent=2)+'\n')
