"""Independent exact-range ARM execution. No Core binary body or syscall executes.
Only eleven sealed application ranges are executable. Clock, signed division,
diagnostic, original getPort and existing onIdle callees are intercepted boundaries.
Actual providers are exercised separately by the C++ executable and regressions.
"""
import hashlib,json,pathlib,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
PACKETS=ROOT/'temp/recovery-work/rolling200-02/next-implementation135/prepared135/packets'
PATHS={'server':'rootfs/RML16AI_Rack_13731/home/root/mixer','client':'rootfs/CS18_v13840/home/root/surface'}
SELF=0x1000000;REG=SELF+0x4000;VT=SELF+0x8000;PORT=SELF+0xa000;MSG=SELF+0xc000
STACK=0x2000000;STOP=0x3000000;GET=STOP+4;PRIMARY=STOP+8;SECONDARY=STOP+12
MASK=(1<<64)-1
RANGES=[];LOADS={};AUDIT={'ranges':RANGES,'observed_pcs':{},'intercept_counts':{},'unexpected_pcs':[],'executed_core_body_pcs':[],'frames':0,'burnin_state_observations':[]}
def sha(b):return hashlib.sha256(b).hexdigest()
for role,path in PATHS.items():
 raw=(ROOT/path).read_bytes();loads=[]
 with (ROOT/path).open('rb') as f:
  e=ELFFile(f)
  for s in e.iter_segments():
   if s['p_type']=='PT_LOAD':loads.append((s['p_vaddr'],s.data(),s['p_memsz']))
  for d in sorted(PACKETS.glob('*rack*')):
   ctx=json.loads((d/'context.json').read_text());nat=json.loads((d/'native-context.json').read_text())
   for record in ctx['originals']:
    original=record['original'];original=dict(original,elf_sha256=original['elf'],section=original['section_json'])
    if original['role']!=role:continue
    assert sha(raw)==original['elf_sha256']
    b=next(x for x in nat['bodies'].values() if x['address']==original['address'] and x['size']==original['size'])
    s=e.get_section(b['section_index']);offset=s['sh_offset']+b['address']-s['sh_addr']
    assert offset==b['file_offset'] and sha(raw[offset:offset+b['size']])==b['bytes_sha256']
    RANGES.append(dict(original,packet=str(d.relative_to(ROOT)),file_offset=offset,bytes_sha256=b['bytes_sha256'],section_name=s.name))
 LOADS[role]=loads

def machine(role):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);maps=[]
 for va,data,size in LOADS[role]:
  lo=va&~4095;hi=(va+size+4095)&~4095
  if maps and lo<=maps[-1][1]:maps[-1][1]=max(maps[-1][1],hi)
  else:maps.append([lo,hi])
 for lo,hi in maps:u.mem_map(lo,hi-lo)
 for va,data,size in LOADS[role]:u.mem_write(va,data)
 u.mem_map(SELF,0x10000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
 return u

def run(case):
 role=case['role'];u=machine(role);ranges=[r for r in RANGES if r['role']==role]
 def address(part):return next(r['address'] for r in ranges if part in r['mangled'])
 def w(a,n):u.mem_write(a,struct.pack('<I',n&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def w64(a,n):w(a,n);w(a+4,n>>32)
 def reg(n):return u.reg_read([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3][n])
 def ret(value=None):
  if value is not None:u.reg_write(UC_ARM_REG_R0,value&0xffffffff)
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 allout=[];trace=[];frame=None;clockindex=0;receiver=REG
 base=address('16ControlRegistrar12writeDualMsg');led=address('16ControlRegistrar10setAllLeds');meter=address('16ControlRegistrar12setAllMeters');scan=address('16ControlRegistrar11scanSurface')
 panel=address('14PanelRegistrar12writeDualMsg') if role=='server' else None
 allowed={r['address'] for r in ranges}
 boundaries={GET:'original abstract getPort boundary',PRIMARY:'primary IPanelPort::writeMsg',SECONDARY:'secondary IPanelPort::writeMsg'}
 if role=='server':boundaries.update({0x116908:'legacy Core clock (no body executes)',0x157a08:'signed division runtime',0x116a38:'Core diagnostic (no body executes)',0x7d190:'existing permissions provider',0x7ee48:'existing network provider',0x7d218:'existing idleTasks provider'})
 AUDIT['boundaries_'+role]={hex(a):b for a,b in boundaries.items()}
 for i in range(2):
  obj=SELF+i*0x1000;registrar=REG+i*0x1000;vtable=VT+i*0x100
  w(obj+0x90,registrar);w(registrar,vtable);w(vtable+0x50,GET);w(vtable+0x68,led);w(vtable+0x80,panel or base)
 w(PORT,VT+0x400);w(VT+0x404,PRIMARY);w(PORT+0x100,VT+0x500);w(VT+0x504,SECONDARY)
 def hook(uc,pc,size,user):
  nonlocal clockindex
  AUDIT['observed_pcs'][hex(pc)]=AUDIT['observed_pcs'].get(hex(pc),0)+1
  if pc==STOP:u.emu_stop();return
  if pc in boundaries:
   AUDIT['intercept_counts'][hex(pc)]=AUDIT['intercept_counts'].get(hex(pc),0)+1
   if pc==GET:
    assert reg(0)==receiver
    trace.append('get');ret(PORT if frame['primary'] else 0)
   elif pc in [PRIMARY,SECONDARY]:
    assert reg(1)!=0 and reg(0)==(PORT if pc==PRIMARY else PORT+0x100)
    trace.append(('p:' if pc==PRIMARY else 's:')+bytes(u.mem_read(reg(1),4)).hex())
    if pc==PRIMARY and frame['mutate']:
     u.mem_write(reg(1)+3,b'\x7e')
     if frame['mutate']==2:u.mem_write(receiver+0xb8,b'\x01')
     if frame['mutate']==3:u.mem_write(receiver+0xb8,b'\x00')
    ret(1)
   elif pc==0x116908:
    trace.append('clock');v=frame['ns0'] if clockindex==0 else frame['ns1'];clockindex+=1
    u.reg_write(UC_ARM_REG_R0,v&0xffffffff);u.reg_write(UC_ARM_REG_R1,(v&MASK)>>32);ret()
   elif pc==0x157a08:
    v=reg(0)|(reg(1)<<32);v=v-(1<<64) if v>>63 else v;den=reg(2)|(reg(3)<<32);assert den==1000000
    v=(abs(v)//den)*(-1 if v<0 else 1);u.reg_write(UC_ARM_REG_R0,v&0xffffffff);u.reg_write(UC_ARM_REG_R1,(v&MASK)>>32);ret()
   elif pc==0x116a38:
    string=bytes(u.mem_read(reg(0),64)).split(b'\0')[0];assert string==b'FPR: Entering burn-in mode.\n';trace.append('debug');ret()
   else:
    assert reg(0)==SELF+frame['object']*0x1000
    trace.append({0x7d190:'permissions',0x7ee48:'network',0x7d218:'tasks'}[pc]);ret()
   return
  if pc==led:trace.append('led')
  if not any(r['address']<=pc<r['address']+r['size'] for r in ranges):
   AUDIT['unexpected_pcs'].append(hex(pc));raise AssertionError(('Unexpected PC',hex(pc)))
 u.hook_add(UC_HOOK_CODE,hook)
 for frame in case['frames']:
  trace=[];clockindex=0;obj=SELF+frame['object']*0x1000;receiver=REG+frame['object']*0x1000
  w(obj+0x1d0,frame['held']);u.mem_write(obj+0x88,bytes([frame['active']]))
  u.mem_write(receiver+0xb8,bytes([frame['secondary']]));w(receiver+0xc0,PORT+0x100 if frame['secondary_present'] else 0)
  w(VT+frame['object']*0x100+0x80,(panel if frame['derived'] and panel else base))
  target=frame['target'];entry={2:led,3:meter,4:scan,5:base,6:panel}.get(target)
  if target in [0,1]:entry=address('18RackPanelComponent20doFactoryBurnInCheck' if target==0 else '18RackPanelComponent6onIdle')
  u.mem_write(MSG,b'\x4c\x0f\x56\x01')
  u.reg_write(UC_ARM_REG_R0,obj if target<2 else receiver)
  u.reg_write(UC_ARM_REG_R1,frame['enabled'] if target in [2,3] else MSG)
  u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP)
  u.emu_start(entry,STOP,count=10000);assert u.reg_read(UC_ARM_REG_PC)==STOP
  allout.append(trace);AUDIT['frames']+=1
  if target in [0,1]:
   AUDIT['burnin_state_observations'].append({'input':frame,'lastTimeMs':r(0x494be0)|(r(0x494be4)<<32),'inBurnInMode':u.mem_read(0x494bd8,1)[0],'intervalCount':r(0x494bdc),'active':u.mem_read(obj+0x88,1)[0],'held':r(obj+0x1d0)})
 return allout

def frame(**kw):
 d=dict(target=0,enabled=1,ns0=501000000,ns1=501000000,held=0,active=0,object=0,primary=1,secondary=1,secondary_present=1,mutate=0,derived=1);d.update(kw);return d

def inputs():
 cases=[]
 for role in ['server','client']:
  for target in [2,3,4,5]+([6] if role=='server' else []):
   for enabled in [0,1]:
    for primary in [0,1]:
     for derived in ([0,1] if role=='server' else [0]):
      for secondary in [0,1]:
       for mutate in [0,1,2,3]:
        cases.append(dict(role=role,frames=[frame(target=target,enabled=enabled,primary=primary,secondary=secondary,mutate=mutate,derived=derived)]))
 # Fresh process per sequence; process-shared cells survive all frames/receivers.
 for target in [0,1]:
  for held in [0,3,4,5,0xffffffff]:
   for active in [0,1]:
    cases.append(dict(role='server',frames=[frame(target=target,held=held,active=active,ns0=n,ns1=n+11000000,object=i%2) for i,n in enumerate([0,500000000,500999999,501000000,1012000000,1013000000,1514000000,2016000000,2518000000,3020000000,3522000000,4024000000,4526000000,5028000000])]))
  for transition in [0,1,2]:
   frames=[frame(target=target,held=4,ns0=i*501000000,ns1=i*501000000,object=i%2) for i in range(1,11)]
   frames += [frame(target=target,held=4 if transition==0 else 0,active=1,ns0=5511000000,ns1=5523000000),frame(target=target,held=0,ns0=6025000000,ns1=6037000000,object=1),frame(target=target,held=4,ns0=6539000000,ns1=6539000000)]
   cases.append(dict(role='server',frames=frames))
  for n in [-1,-1000001,-9223372036854775808,9223372036854775807]:cases.append(dict(role='server',frames=[frame(target=target,held=4,ns0=n,ns1=n)]))
 return cases

SUPPLEMENT=ROOT/'temp/recovery-work/rolling200-03/provider-supplements189/uart189'
def encode_observations(messages):
 manifest=json.loads((SUPPLEMENT/'TRANSPORT189.json').read_text())
 for name,expected in manifest['files'].items():assert sha((ROOT/name).read_bytes())==expected
 native=json.loads((SUPPLEMENT/'native-context.json').read_text());bodies=[native['bodies'][root] for root in native['roots']]
 raw=(ROOT/PATHS['server']).read_bytes();ranges=[]
 with (ROOT/PATHS['server']).open('rb') as file:
  elf=ELFFile(file)
  for original in manifest['originals']:
   assert sha(raw)==original['elf_sha256']
   body=next(b for b in bodies if b['address']==original['address'])
   sec=elf.get_section(body['section_index']);off=sec['sh_offset']+body['address']-sec['sh_addr']
   assert off==body['file_offset'] and sha(raw[off:off+body['size']])==body['bytes_sha256']
   ranges.append(dict(original,file_offset=off,bytes_sha256=body['bytes_sha256']))
 observations={};pcs=set()
 for message in sorted(messages):
  u=machine('server');u.mem_write(MSG,bytes.fromhex(message));u.mem_write(MSG+0x100,b'\xcc'*16)
  def hook(uc,pc,size,user):
   if pc==STOP:u.emu_stop();return
   if pc==0xac1c:raise AssertionError('Invalid encoder assertion outside selected domain')
   if not any(b['address']<=pc<b['address']+b['size'] for b in bodies):raise AssertionError(('Unexpected provider PC',hex(pc)))
   pcs.add(hex(pc))
  u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_ARM_REG_R0,MSG);u.reg_write(UC_ARM_REG_R1,MSG+0x100);u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP)
  u.emu_start(0x9a2c4,STOP,count=10000);assert u.reg_read(UC_ARM_REG_PC)==STOP
  count=u.reg_read(UC_ARM_REG_R0);assert 0<count<=16
  observations[message]=bytes(u.mem_read(MSG+0x100,count)).hex()
 AUDIT['encoder']={'ranges':ranges,'executed_pcs':sorted(pcs),'messages':observations,'assertion_domain':'No malformed LED/switch group or unsupported opcode is passed; __assert_fail never executes.'}
 return observations,ranges

def produce():
 cases=[dict(c,expected=run(c)) for c in inputs()]
 messages={event.split(':')[1] for case in cases for trace in case['expected'] for event in trace if event.startswith(('p:','s:'))}
 encoder,ranges=encode_observations(messages)
 return {'ranges':RANGES,'cases':cases,'encoder':encoder,'encoder_ranges':ranges}
if __name__=='__main__':
 out=produce();(ROOT/'uc-library/tests/recovery/rack_burnin/fixtures.json').write_text(json.dumps(out,indent=2)+'\n')
 evidence=ROOT/'evidence/recovery/2026-11-06/rolling200-02/rack-burnin135';evidence.mkdir(parents=True,exist_ok=True)
 (evidence/'native-audit.json').write_text(json.dumps(AUDIT,indent=2)+'\n');print('Exact native frames:',AUDIT['frames'])
