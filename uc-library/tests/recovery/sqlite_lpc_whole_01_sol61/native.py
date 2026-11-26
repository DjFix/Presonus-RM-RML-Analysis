"""Independent ARM execution; no native instruction is executed on the host."""
import hashlib, io, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn as U
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parents[4]
P=ROOT/'temp/recovery-work/sqlite-issued/packet-current'
OBJ=0x51000000; DATA=OBJ+0x10000; OUT=OBJ+0x30000; STOP=0x53000000; SP=0x52010000
REG=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def sha(b): return hashlib.sha256(b).hexdigest()
def sx(v): return v if v<0x80000000 else v-0x100000000
class Native:
 def __init__(self,role):
  self.role=role;self.refs=[]
  for p in sorted(P.glob('sqlite_lpc_whole_*')):
   j=json.loads((p/'CONTEXT.json').read_text())
   self.refs += [r['original'] for r in j['originals'] if r['original']['role']==role]
  ref=self.refs[0]; self.blob=(ROOT/ref['elf_path']).read_bytes();assert sha(self.blob)==ref['elf']
  self.elf=ELFFile(io.BytesIO(self.blob));self.syms={}
  for s in self.elf.get_section_by_name('.symtab').iter_symbols():
   if s['st_value']:self.syms[s['st_value']]=s.name
  self.symaddr={n:a for a,n in self.syms.items()}
  for r in self.refs:
   sec=self.elf.get_section(r['section']);off=sec['sh_offset']+r['address']-sec['sh_addr'];b=self.blob[off:off+r['size']]
   assert off==r['file_offset'] and sha(b)==r['range_sha256'] and b.hex()==r['range_hex']
 def run(self,c):
  v=U.Uc(U.UC_ARCH_ARM,U.UC_MODE_ARM);self.vm=v;self.events=[];self.responses=list(c['responses']);self.reads=[];self.n=0;self.tail_state=[]
  for seg in self.elf.iter_segments():
   if seg['p_type']=='PT_LOAD':
    lo=seg['p_vaddr']&~4095;hi=(seg['p_vaddr']+seg['p_memsz']+4095)&~4095
    v.mem_map(lo,hi-lo);v.mem_write(seg['p_vaddr'],seg.data())
  for a,n in [(OBJ,0x50000),(0x52000000,0x20000),(STOP,4096)]:v.mem_map(a,n)
  def w(a,x):v.mem_write(a,struct.pack('<I',x&0xffffffff))
  def rd(a):return struct.unpack('<I',v.mem_read(a,4))[0]
  def s(a):
   b=bytearray()
   while (x:=v.mem_read(a+len(b),1)[0]):b.append(x)
   return b.decode('latin1')
  self.s=s;self.rd=rd;self.w=w
  image=bytes((0 if c.get('a')==0 else 255 if c.get('a')==1 else (i*37+11)&255) if c['method']=='raw' else (i*37+11)&255 for i in range(70000));v.mem_write(DATA,image);v.mem_write(OUT,b'\xa5'*1024)
  v.mem_write(OBJ,b'\0'*4096);w(OBJ+4,DATA);w(OBJ+8,c['size']);w(OBJ+0x50,0x10000400);w(OBJ+0x54,100000)
  for o,k in [(0x30,'first'),(0x48,'sectors'),(0x34,'destination')]:w(OBJ+o,c[k])
  w(OBJ+0x18,620761368);w(OBJ+0x38,7);w(OBJ+0x40,c['first']);w(OBJ+0x4c,4096)
  for i in range(4):w(OBJ+0x1c+4*i,i+1)
  w(OBJ+0x2c,123)
  if c['listener']:w(OBJ+0x14,OBJ+0x2000)
  w(OBJ+0x2000,OBJ+0x2100);w(OBJ+0x2100,STOP+4)
  # Time global is decoded from the exact printProgress literal, role-specific.
  pp=self.symaddr['_ZN8Presonus13LPCProgrammer13printProgressEPKc'];glob=rd(pp+104);w(glob,1000);w(glob+4,0)
  r=next(x for x in self.refs if x['mangled']==c['mangled']);name=c['method']
  args=[OBJ,c['a'],c['b'],c['d']]
  if name=='raw': args=[OUT,c['size'],DATA,0]
  elif name=='ctor':args=[OBJ,DATA,c['size'],0]
  elif name=='writeRAM':args=[OBJ,0x10000400,c['size'],DATA]
  elif name in ['open','printProgress']:
   v.mem_write(OUT,(c['text']+'\0').encode());args=[OBJ,OUT,0,0]
  elif name=='update':args=[OBJ,OBJ+0x2000 if c['listener'] else 0,0,0]
  for reg,x in zip(REG,args):v.reg_write(reg,x)
  v.reg_write(UC_ARM_REG_SP,SP);v.reg_write(UC_ARM_REG_LR,STOP)
  def ret(x=0):v.reg_write(UC_ARM_REG_R0,x&0xffffffff);v.reg_write(UC_ARM_REG_PC,v.reg_read(UC_ARM_REG_LR))
  def fmt(f,values):
   import re
   it=iter(values)
   def sub(m):
    spec=m.group();x=next(it)
    if spec.endswith('s'):return s(x)
    if spec.endswith('d'):x=sx(x)
    return spec%x
   return re.sub(r'%[0-9]*[duXxs]',sub,f)
  def hook(vm,pc,size,_):
   self.n+=1
   if self.n>4000000:raise RuntimeError(('instruction budget',name,c))
   rr=[vm.reg_read(x) for x in REG];a,b,d,e=rr
   if pc==STOP:vm.emu_stop();return
   if pc==STOP+4:
    self.events.append(['progress',s(b),d]);ret();return
   sym=self.syms.get(pc,'')
   if c.get('guard') and pc==r['address']+0x250:
    self.tail_state.append({'pc':pc,'r7':vm.reg_read(UC_ARM_REG_R7),'tail_minus_one':a})
   if c.get('guard') and pc==r['address']+0x2f4:
    self.tail_state.append({'pc':pc,'bound':vm.reg_read(UC_ARM_REG_R3),'counter':vm.reg_read(UC_ARM_REG_R12)})
    if len(self.tail_state)==4:vm.emu_stop();return
   # Existing providers remain native boundaries; their portable bodies are linked.
   if sym=='_ZN8Presonus13LPCProgrammer11writeStringEPKc':self.events.append(['send',s(b).encode('latin1').hex()]);ret(2);return
   if sym=='_ZN8Presonus13LPCProgrammer12waitResponseEi':
    response=self.responses.pop(0) if self.responses else '0'
    self.events.append(['wait',sx(b)])
    vm.mem_write(OBJ+0x258,response.encode()+b'\0');ret(bool(response));return
   if sym=='_ZN8Presonus13LPCProgrammer8openPortEPKc':self.events.append(['open',s(b)]);w(OBJ+0xc,23 if c['port'] else -1);ret(c['port']);return
   if sym=='_ZN8Presonus13LPCProgrammer9writeCharEh':self.events.append(['char',b]);ret(1);return
   if sym=='_ZN8Presonus13LPCProgrammer5closeEv':self.events.append(['close',sx(rd(OBJ+0xc))]);w(OBJ+0xc,0);ret();return
   if sym.startswith('_ZN4Core20MutableCStringTraits') and 'appendFormat' in sym:
    vals=[d,e]+[rd(vm.reg_read(UC_ARM_REG_SP)+4*i) for i in range(4)];text=fmt(s(b),vals);vm.mem_write(a,text.encode()+b'\0');ret();return
   if sym=='_ZN4Core11DebugPrintfEPKcz' or sym.startswith('printf@'):
    vals=[b,d,e]+[rd(vm.reg_read(UC_ARM_REG_SP)+4*i) for i in range(4)]
    self.events.append(['debug',fmt(s(a),vals).encode('latin1').hex()]);ret();return
   if sym=='_ZN4Core15GetAbsoluteTimeEv':
    ticks=(c['d'] if name=='printProgress' else 1250)*1000000;vm.reg_write(UC_ARM_REG_R1,ticks>>32);ret(ticks);return
   if sym=='__aeabi_ldivmod':
    n=(b<<32)|a;div=(e<<32)|d;q=n//div;vm.reg_write(UC_ARM_REG_R1,q>>32);ret(q);return
   if sym=='__aeabi_l2f':
    value=(b<<32)|a;value=value if value<(1<<63) else value-(1<<64);ret(struct.unpack('<I',struct.pack('<f',float(value)))[0]);return
   if sym=='__aeabi_fdiv':ret(struct.unpack('<I',struct.pack('<f',struct.unpack('<f',struct.pack('<I',a))[0]/struct.unpack('<f',struct.pack('<I',b))[0]))[0]);return
   if sym=='_ZN4Core7Threads5sleepEj':self.events.append(['sleep',a]);ret();return
   if sym.startswith('memset@'):vm.mem_write(a,bytes([b&255])*d);ret(a);return
   if sym.startswith('memcpy@'):vm.mem_write(a,bytes(vm.mem_read(b,d)));ret(a);return
   if sym.startswith('snprintf@'):
    vals=[e]+[rd(vm.reg_read(UC_ARM_REG_SP)+4*i) for i in range(4)];text=fmt(s(d),vals);vm.mem_write(a,text.encode()[:b-1]+b'\0');ret(len(text));return
   if sym.startswith('strcasecmp@'):ret(0 if s(a).lower()==s(b).lower() else 1);return
   if sym.startswith('strcmp@'):ret(0 if s(a)==s(b) else 1);return
   if sym.startswith('strtol@'):
    import re
    match=re.match(r'\s*([+-]?\d+)',s(a));ret(int(match.group(1)) if match else 0);return
   if sym.startswith('fflush@'):ret();return
   if sym.startswith('_ZdlPv@'):self.events.append(['delete']);ret();return
   # Fail closed at any unhandled external entry or syscall instruction.
   if sym and ('@' in sym or sym.startswith('_ZN4Core') or sym.startswith('__aeabi')):raise RuntimeError(('unhandled provider',sym,hex(pc)))
   if bytes(vm.mem_read(pc,4))[3]==0xef:raise RuntimeError('native syscall rejected')
  def mem(vm,access,address,size,value,_):
   if DATA<=address<DATA+70000:self.reads.append([address-DATA,size])
  v.hook_add(U.UC_HOOK_CODE,hook);v.hook_add(U.UC_HOOK_MEM_READ,mem)
  v.emu_start(r['address'],STOP+8,count=4000001)
  result={'events':self.events,'remaining_count':len(self.responses),'instructions':self.n,'reads':self.reads}
  assert bytes(v.mem_read(DATA,len(image)))==image
  if name=='raw':result.update(ret=v.reg_read(UC_ARM_REG_R0),output=bytes(v.mem_read(OUT,260)).hex())
  elif name=='ctor':result['state']=[rd(OBJ+o) for o in [8,0xc,0x10,0x14,0x18,0x30,0x34,0x50,0x54]]
  elif c.get('guard'):result['tail_state']=self.tail_state
  elif name not in ['printInfo','printProgress','dtor']:result['ret']=sx(v.reg_read(UC_ARM_REG_R0))
  if name=='update':result['block']=bytes(v.mem_read(OBJ+0x58,512)).hex()
  return result

def cases():
 result=[]
 for p in sorted(P.glob('sqlite_lpc_whole_*')):
  j=json.loads((p/'CONTEXT.json').read_text());m=j['originals'][0]['original']['mangled']
  method=next((n for k,n in [('copyRAM2Flash','copyRAM2Flash'),('LPCProgrammerC1','ctor'),('LPCProgrammerC2','ctor'),('eraseSector','eraseSector'),('printProgress','printProgress'),('unlockFlash','unlockFlash'),('D0','dtor'),('D1','dtor'),('D2','dtor'),('4open','open'),('6update','update'),('writeRAM','writeRAM'),('printInfo','printInfo'),('prepareSector','prepareSector'),('eraseAll','eraseAll'),('raw_uu','raw')] if k in m),None)
  base=dict(task=p.name,mangled=m,method=method,size=512,a=3,b=9,d=512,first=0,sectors=1,destination=0,listener=0,text='message',port=1,responses=['0','OK'])
  variants=[{}]
  if method=='raw':variants=[{'size':n,'a':pattern} for n in range(0,64) for pattern in [0,1,3]]
  if method=='writeRAM':variants=[{'size':n,'responses':r} for n in [855,1,2,3,44,45,46,89,512,854,901,945,1801] for r in [['0','OK','OK','OK'],['1'],['0',''],['0','BAD','OK','OK']]]
  if method=='writeRAM':variants += [{'size':n,'responses':['0','OK','OK'],'guard':True} for n in [0,856,899,900,1756,1800]]
  if method in ['prepareSector','eraseSector','unlockFlash','copyRAM2Flash','eraseAll']:variants=[{'responses':r,'a':a,'b':b} for r in [['0','0'],['1','1'],['','']] for a,b in [(0,0),(3,9),(0xffffffff,0x80000000)]]
  if method=='ctor':variants=[{'size':n} for n in [0,1,512,0xffffffff]]
  if method=='printProgress':variants=[{'listener':l,'text':t,'d':clock} for l in [0,1] for t in ['', 'programming'] for clock in [0,1000,1250,301000,601000,0xffffffff]]
  if method=='open':
   good=['Synchronized','Synchronized','OK','10000','OK','A 0','0','0','620761368','0','123','0','0','1','2','3','4','0']
   variants=[{'text':'fixture-port','responses':good},{'port':0,'text':'fixture-port','responses':good}]+[{'text':'fixture-port','responses':good[:i]+['']+good[i+1:]} for i in [0,1,2,3,4,5,6,11,12,17]]
  if method=='update':variants=[{'size':n,'sectors':sectors,'listener':l,'responses':['0','OK']*300} for n,sectors,l in [(0,0,0),(1,1,1),(512,1,1),(513,1,0),(4096,1,1),(8192,2,1),(65536,16,1)]]+ [{'size':513,'listener':1,'responses':['1']*100}]+[{'size':513,'listener':1,'responses':[response]*100} for response in ['000','0abcdefgh']]
  for variant in variants:result.append(base|variant)
 return result

def generate(out,task=None):
 machines={r:Native(r) for r in ['client','server']};rows=[]
 for i,c in enumerate(cases()):
  if task and c['task']!=task:continue
  if i%20==0:print('ARM case',i,c['method'],flush=True)
  values={role:m.run(c) for role,m in machines.items()}
  # Role machine addresses and instruction counts may differ; observations must match.
  for key in ['events','ret','state','output','reads']:
   assert values['client'].get(key)==values['server'].get(key),(c,key)
  rows.append({'case':c,'native':values})
 Path(out).write_text(json.dumps({'version':1,'unicorn':U.__version__,'rows':rows},indent=2)+'\n')
 print('native cases',len(rows),'role executions',2*len(rows))
if __name__=='__main__':
 import sys
 generate(sys.argv[1])
