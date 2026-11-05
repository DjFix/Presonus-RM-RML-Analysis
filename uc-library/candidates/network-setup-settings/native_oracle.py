#!/usr/bin/env python3
"""Execute exact ARM target bodies; explicit CCL/app boundaries, no hardware.
CCL is not decompiled/executed. Boundary memory models below capture original
call arguments, normal nonthrowing provider results, and target writes. Native
loadSettings executes native isStoredItem; existing syncListParam is a boundary.
"""
import hashlib, json, struct, sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
BASE=Path('uc-library/candidates/network-setup-settings')
PACKETS=Path('temp/recovery-work/rolling200-02/implementation-plan01/packets-isolated-network_setup02/packets')
ELF=Path('rootfs/CS18_v13840/home/root/surface')
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
REG=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def bits(f): return struct.unpack('<I',struct.pack('<f',f))[0]
def flt(v): return struct.unpack('<f',struct.pack('<I',v))[0]
def signed(v): return v if v<2**31 else v-2**32

def cases():
 rows=[]
 for present in (0,1): rows.append(dict(method=5,present=present))
 for value in (0.,1.,2.,-1.,.5,-.5,1.9,-2.9,100.):
  rows.append(dict(method=7,value=value,present=1));rows.append(dict(method=8,value=value,present=1))
 rows.append(dict(method=8,present=0,value=0.))
 for method in (4,6):
  for index in (-2147483648,-1,0,2,2147483647):
   for section in (0,1):
    for saved in ('','MIDI-'+str(index),'MIDI-3','X'*80):
     rows.append(dict(method=method,index=index,section=section,saved=saved,flags=2,key='selectedDAW',section_name='networksetup'))
  rows.append(dict(method=method,index=2,section=1,saved='MIDI-2',flags=0,key='K'*100,section_name='S'*100))
  if method==4:
   for flags in (0,1,3,4,6,-1): rows.append(dict(method=4,index=2,section=0,saved='',flags=flags,key='selectedDAW',section_name='networksetup'))
 for count in (0,1,4):
  for selected in (-1,0,3,9):
   for optional in (0,1):
    rows.append(dict(method=3,count=count,saved='' if selected<0 else 'MIDI-'+str(selected),optional=optional,section=1,section_name='networksetup',key='selectedDAW'))
 return rows

def produce():
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 requests={};ranges=[]
 with ELF.open('rb') as f:
  ef=ELFFile(f);segs=[(s['p_vaddr'],s.data()) for s in ef.iter_segments() if s['p_type']=='PT_LOAD'];sections=list(ef.iter_sections())
  for p in sorted(PACKETS.iterdir()):
   req=json.loads((p/'request.json').read_text());o=req['originals'][0]['original'];n=int(p.name[-2:]);requests[n]=o
   sec=sections[int(o['section_json'])];offset=sec['sh_offset']+o['address']-sec['sh_addr'];body=data[offset:offset+o['size']]
   ranges.append(dict(original=o,file_offset=offset,section=sec.name,sha256=hashlib.sha256(body).hexdigest()))
 outputs=[]
 for c in cases():
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x800000)
  for addr,b in segs:u.mem_write(addr,b)
  w=lambda a,v:u.mem_write(a,struct.pack('<I',v&0xffffffff))
  read=lambda a:struct.unpack('<I',u.mem_read(a,4))[0]
  def string(a):
   if not a:return ''
   out=bytearray()
   while (v:=bytes(u.mem_read(a,1)))!=b'\0':out.extend(v);a+=1
   return out.decode()
  def put(a,s):u.mem_write(a,s.encode()+b'\0')
  obj=0x400000;param=0x410000;vtable=0x420000;key=0x430000;result=0x440000;section_obj=0x450000;attr=0x460000;handler=0x470000
  w(0x26ac08,1);w(0x26ae24,0x480000);w(obj+0xcc,handler);w(obj+0x100,-1);put(obj+8,c.get('section_name','networksetup'));put(key,c.get('key','selectedDAW'))
  w(param,vtable);w(vtable+0x44,0x500000);w(vtable+0x58,0x500004)
  has_section=bool(c.get('section',0));saved=c.get('saved','') if has_section else '';dirty=0;events=[];active=-1;calls=[]
  # CCL source provider copies attribute IDs into CString32 (31 chars).
  # A longer full lookup therefore cannot find that stored identifier.
  long_section=len(c.get('section_name','networksetup'))>31
  long_key=len(c.get('key','selectedDAW'))>31
  def ret(v=None):
   if v is not None:u.reg_write(UC_ARM_REG_R0,v&0xffffffff)
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  def hook(uc,a,size,user):
   nonlocal saved,has_section,dirty,active
   r=[uc.reg_read(x) for x in REG]
   if a==0x600000:uc.emu_stop();return
   if a==0x124108:
    calls.append(['section',string(r[1])]);ret(section_obj if has_section and not long_section else 0)
   elif a==0x124ae8:
    calls.append(['lookup',string(r[1])]);ret(attr)
   elif a==0x1260ec:
    has_section=True
    if long_section:saved=''
    ret(section_obj)
   elif a==0x124200:
    calls.append(['get',string(r[1])]);put(result,'' if long_key else saved);ret(result)
   elif a==0x1263cc:
    saved=string(r[1]);calls.append(['set',saved]);ret()
   elif a==0x3ae34:
    put(r[0],string(r[1])[:63]);ret(r[0])
   elif a==0x8c1a8:
    assert string(r[1])=='MIDI-%d';put(r[0],'MIDI-'+str(signed(r[2])));ret(r[0])
   elif a==0xb0f8:
    x,y=string(r[0]),string(r[1]);ret((x>y)-(x<y))
   elif a in (0x11acf0,0x11f24c):
    tag=r[1];calls.append(['param',tag]);ret(param if c.get('present',1) and (tag!=17 or c.get('optional')) else 0)
   elif a==0x500000:ret(bits(c['value']))
   elif a==0x500004:
    event=['set7' if uc.reg_read(UC_ARM_REG_LR)==0xa062c else 'set17',flt(r[1]),r[2]]
    if event[0]=='set17':event.append(active)
    events.append(event);ret()
   elif a==0x1877f8:ret(int(flt(r[0])))
   elif a==0x187314:ret(bits(signed(r[0])))
   elif a==0x187150:ret(bits(flt(r[0])+flt(r[1])))
   elif a==0xb86a8:ret(c['count'])
   elif a==0xb86e8:active=signed(r[1]);events.append(['active',active]);ret()
   elif a==0x9ff50:
    assert r[1]==7 and r[2]==obj+0xe4 and r[3]==0
    events.append(['sync',7,0,active]);ret()
   elif not (requests[c['method']]['address']<=a<requests[c['method']]['address']+requests[c['method']]['size']) and not (c['method']==3 and 0xa0470<=a<0xa0594):
    raise AssertionError(('unexpected execution',hex(a),c))
  u.hook_add(UC_HOOK_CODE,hook)
  for reg,value in zip(REG,[obj,key,c.get('index',0)&0xffffffff,c.get('flags',0)&0xffffffff]):u.reg_write(reg,value)
  u.reg_write(UC_ARM_REG_SP,0x7f0000);u.reg_write(UC_ARM_REG_LR,0x600000)
  u.emu_start(requests[c['method']]['address'],0x600004,count=5000)
  assert u.reg_read(UC_ARM_REG_PC)==0x600000
  method=c['method'];observed={}
  if method in (7,8):observed={'result':signed(u.reg_read(UC_ARM_REG_R0))}
  elif method==5:observed={'result':int(u.reg_read(UC_ARM_REG_R0)==param)}
  elif method in (4,6):
   observed={'saved':saved if has_section and not long_section and not long_key else '', 'section':int(has_section and not long_section),'dirty':int(bool(read(0x26ac0c+0x20c)&4))}
   if method==6:observed['result']=u.reg_read(UC_ARM_REG_R0)
  else:observed={'selected':signed(read(obj+0x100)),'active':active,'events':events}
  outputs.append(dict(input=c,observed=observed,native_provider_calls=calls))
 return dict(version=1,elf_sha256=SHA,unicorn_version=unicorn.__version__,ranges=ranges,cases=outputs,limitations='Original target instructions, initialized singleton, nonthrowing explicit CCL/runtime/app boundary doubles. Native isStoredItem executes inside loadSettings. No Core binary recovery, layouts, original return declarations, exceptional paths, hardware or ARM interoperability claimed. syncListParam boundary checks original arguments; its behavior is existing source dependency, not reconstructed here.')
if __name__=='__main__':
 result=produce();path=BASE/'fixtures.json'
 if '--verify' in sys.argv:assert result==json.loads(path.read_text())
 else:path.write_text(json.dumps(result,indent=2)+'\n')
 print('Original ARM cases:',len(result['cases']))
