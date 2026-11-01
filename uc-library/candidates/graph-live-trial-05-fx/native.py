#!/usr/bin/env python3
"""Execute only target original ARM ranges. All external boundaries are explicit stubs.
No Core binary instructions are executed; count/getAt boundary uses supplied lists.
"""
import hashlib,json,struct,pathlib,itertools,datetime,time,unicorn,elftools
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[3]
OUT=pathlib.Path(__file__).parent
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
EXPECTED='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def fbits(f):return struct.unpack('<I',struct.pack('<f',f))[0]
def run(op,b,count,wanted,dirty,pending,edit,number,target,raw):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 u.mem_map(0x10000,0x180000);u.mem_write(target,raw)
 u.mem_map(0x200000,0x20000);u.mem_map(0x300000,0x10000)
 obj,typ,rec,controller,vt,vr=0x200000,0x201000,0x202000,0x203000,0x204000,0x205000
 def word(a,v):u.mem_write(a,struct.pack('<I',v))
 word(obj+0xb0,controller);word(obj+0x120,typ);word(obj+0x128,rec)
 word(typ,vt);word(rec,vr);word(vr+0x44,0x170000);word(vt+0x58,0x170010);word(vr+0x58,0x170010)
 u.mem_write(obj+0x12c,bytes([dirty]));u.mem_write(obj+0x12e,bytes([pending]))
 stack=0x30f000;stop=0x171000
 u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R0,obj)
 u.reg_write(UC_ARM_REG_R1,(0 if wanted<0 else rec) if op==2 else ((0x206000+wanted*16) if wanted>=0 else rec) if op==4 else edit)
 trace=[];rawtrace=[];writes=[]
 def ret(v=None):
  if v is not None:u.reg_write(UC_ARM_REG_R0,v)
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def hook(uc,a,size,_):
  r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);r2=uc.reg_read(UC_ARM_REG_R2)
  if a==stop:uc.emu_stop();return
  if a==0xbd8a0:
   assert r0==controller
   trace.append('dirty:'+str(uc.mem_read(obj+0x12c,1)[0]));ret();return
  if a==0x170000:
   assert r0==rec
   trace.append('get:recalled');ret(b);return
  if a==0x170010:
   assert r0 in (typ,rec)
   trace.append('set:'+('type' if r0==typ else 'recalled')+f':{r1}:{r2}');ret();return
  if a==0x3a9e8:assert r0==obj;trace.append('type-number');ret(number);return
  if a==0x15746c:rawtrace.append(['ui2f',r0]);ret(fbits(float(r0)));return
  if a==0x3b8ac:assert r0==obj;trace.append('update-name');ret();return
  if a==0x3c064:assert r0==obj;trace.append('type-change:'+str(r1));ret();return
  if a==0x119624:assert r0==obj;rawtrace.append(['count',count]);ret(count);return
  if a==0x119638:
   assert r0==obj and r1<count
   rawtrace.append(['at',r1]);ret(0x206000+r1*16);return
  assert target<=a<target+len(raw),hex(a)
 def write(uc,access,a,size,val,_):
  if obj<=a<obj+0x200:writes.append({'address':a,'offset':a-obj,'size':size,'value':val})
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.emu_start(target,0,count=1000)
 assert u.reg_read(UC_ARM_REG_PC)==stop
 result=u.reg_read(UC_ARM_REG_R0) if op!=1 else 0
 output=f'{result} {u.mem_read(obj+0x12c,1)[0]} {u.mem_read(obj+0x12e,1)[0]}|'+''.join(t+';' for t in trace)
 return {'output':output,'external_provider_trace':rawtrace,'target_writes':writes,'original_instructions':True}
def main():
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==EXPECTED
 ranges=[];targets=[]
 for i in range(1,6):
  packet=ROOT/f'temp/recovery-work/graph-live-trial-05/trial05_fx_{i}-packet'
  bindings=['6eb4cbc133d291e3c2d3ed51344ba3e1b1894b8ba995d7ff6512717191083e51','62c75860bdc718332a312427dcc218a2ff8d715c1f4d1fe061a63053e0f8f54c','56050c43ee56bc200b90431790d861254c0457ae73a8a8226a74fcfdf4daee42','ff7047070c4300b554ee4633e5e59cf73114bf84cbfbaa36cb6f55d8c2911c50','14e18c264985ff88d1f7bc8d266937e414dfb1a3eea6f5d1a4f5a14ef30586e3']
  assert hashlib.sha256((packet/'context.json').read_bytes()).hexdigest()==bindings[i-1]
  req=json.loads((packet/'request.json').read_text());orig=req['originals'][0]['original']
  with ELF.open('rb') as f:
   elf=ELFFile(f);sec=elf.get_section(int(orig['section_json']));offset=sec['sh_offset']+orig['address']-sec['sh_addr']
   rows=[s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name==orig['mangled']]
   assert len(rows)==1 and rows[0]['st_value']==orig['address'] and rows[0]['st_size']==orig['size']
  raw=data[offset:offset+orig['size']]
  text=(packet/'ELF_CONTEXT.md').read_text();digest=hashlib.sha256(raw).hexdigest();assert digest in text
  ranges.append(dict(orig,file_offset=offset,range_sha256=digest,section='.text',elf_sha256=EXPECTED))
  targets.append((orig['address'],raw))
 cases=[]
 def add(op,b=0,count=0,wanted=-1,dirty=0,pending=0,edit=0,number=0):
  args=[op,b,count,wanted,dirty,pending,edit,number]
  obs=run(*args,*targets[op-1]);cases.append(dict(args=args,**obs))
 for dirty,pending in itertools.product([0,1],repeat=2):add(1,dirty=dirty,pending=pending)
 for b in [0,0x80000000,0x3f800000,0xbf800000,0x3f000001,0x7f800000,0xff800000,0x7fc01234]:
  for wanted in [-1,0]:add(2,b,wanted=wanted)
 for n in [0,1,17,16777215,16777216,16777217,0x7fffffff,0x80000000,0xffffffff]:
  for pending in [0,1]:add(3,number=n,pending=pending)
 for count in range(5):
  for wanted in [-1,*range(count)]:add(4,count=count,wanted=wanted)
 for b,edit in itertools.product([0,0x3f800000,0xbf800000,0x3f000001,0x4f800000],[0,1]):add(5,b,edit=edit)
 doc={'started_utc':started,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'duration_seconds':time.monotonic()-tick,'producer_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'versions':{'unicorn':unicorn.__version__,'pyelftools':elftools.__version__},'elf_path':str(ELF.relative_to(ROOT)),'elf_sha256':EXPECTED,'ranges':ranges,'oracle':'Unicorn target execution with explicit external stubs; no Core firmware executed','cases':cases}
 (OUT/'fixtures.json').write_text(json.dumps(doc,indent=2)+'\n')
 print(f'Original executions: {len(cases)}')
if __name__=='__main__':main()
