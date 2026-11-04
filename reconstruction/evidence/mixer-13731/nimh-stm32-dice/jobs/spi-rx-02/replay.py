from pathlib import Path
import hashlib,json,struct,platform
import unicorn as u
from unicorn import arm_const as a
from capstone import *
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'evidence/recovery/2026-10-28/nimh-spi-rx'
B=(ROOT/'evidence/recovery/2026-10-27/xmen-stm32/images/mixer-analysis/_ZL13nimh_arm_code.bin').read_bytes()
assert hashlib.sha256(B).hexdigest()=='b0979352e18a1093051fc6118a47694773cb9240e88087eca03aaa2ffe0f5e17'
REG=[a.UC_ARM_REG_R0,a.UC_ARM_REG_R1,a.UC_ARM_REG_R2,a.UC_ARM_REG_R3]
class Machine:
 def __init__(self):
  self.m=u.Uc(u.UC_ARCH_ARM,u.UC_MODE_THUMB|u.UC_MODE_MCLASS)
  for base,size in [(0x08000000,0x80000),(0x20000000,0x10000),(0x40000000,0x30000)]:
   self.m.mem_map(base,size)
  self.m.mem_write(0x08000000,B)
  self.m.mem_write(0x20000400,B[0x340e8:0x34f4c])
  self.calls=[];self.trace=[];self.writes=[];self.dispatch=False;self.dequeues=0;self.responses=[]
  self.m.hook_add(u.UC_HOOK_CODE,self.hook)
  self.m.hook_add(u.UC_HOOK_MEM_WRITE,lambda m,t,p,n,v,_: self.writes.append([hex(p),n,v]) if 0x40000000<=p<0x40030000 else None)
 def word(self,p):return struct.unpack('<I',self.m.mem_read(p,4))[0]
 def put(self,p,v):self.m.mem_write(p,struct.pack('<I',v))
 def ret(self,v=0):
  self.m.reg_write(REG[0],v);self.m.reg_write(a.UC_ARM_REG_PC,self.m.reg_read(a.UC_ARM_REG_LR))
 def hook(self,m,pc,n,_):
  self.trace.append(pc)
  regs=[m.reg_read(r) for r in REG]
  if self.dispatch:
   if pc==0x08000ce8:
    self.dequeues+=1
    if self.dequeues==2:m.emu_stop();return
   if pc==0x08014dac:self.ret(1);return
   if pc==0x08014d68:self.ret();return
   if pc==0x08000e00:
    data=bytes(m.mem_read(regs[0],255));self.responses.append(data[:data.index(0xf7)+1].hex())
    self.ret(1);return
  if pc==0x08040000:m.emu_stop();return
  if pc in (0x08004720,0x0800478c,0x0800611c,0x08006080,0x080060a2,0x080060aa,0x080047cc,
            0x080060b8,0x080060b2,0x080060d4,0x080060c4,0x080060f0,0x08005f14,0x08005f1c,0x0800612c):
   self.calls.append([hex(pc),regs])
   if pc==0x080060b2:self.put(regs[1],0x2000f000)
   if pc==0x080060d4:self.put(self.word(m.reg_read(a.UC_ARM_REG_SP)),0x2000f100)
   if pc==0x080060c4:m.reg_write(REG[1],0)
   self.ret()
  elif pc==0x08005eb2:
   m.mem_write(regs[0],bytes([regs[1]&255])*regs[2]);self.ret(regs[0])
 def run(self,pc,*args):
  for r,v in zip(REG,args):self.m.reg_write(r,v)
  self.m.reg_write(a.UC_ARM_REG_SP,0x2000fc00)
  self.m.reg_write(a.UC_ARM_REG_LR,0x08040001)
  try:self.m.emu_start(pc|1,0,count=200000)
  except Exception as e:raise RuntimeError((hex(pc),hex(self.m.reg_read(a.UC_ARM_REG_PC)),[hex(x) for x in self.trace[-15:]])) from e
  assert self.m.reg_read(a.UC_ARM_REG_PC)==0x08040000 or (self.dispatch and self.dequeues==2),hex(self.m.reg_read(a.UC_ARM_REG_PC))
  return self.m.reg_read(REG[0])
 def init(self):
  self.run(0x08000f2c)
  self.desc=0x2000b480+0x1854
  self.dma=self.word(self.desc+12)+20*self.word(self.desc+16)
  self.buf=self.word(self.dma)
  self.count=self.dma-8
  assert self.word(self.count)==1024
  assert self.word(self.dma-4)==0x4001300c
  self.pos=0
 def feed(self,data):
  for x in data:
   self.m.mem_write(self.buf+self.pos,bytes([x]));self.pos=(self.pos+1)%1024
  self.put(self.count,1024-self.pos)
  self.run(0x08000aa4)
 def drain(self,q=0x2000b480,release=0x08000d28,get=0x08000ce8):
  result=[]
  while self.m.mem_read(q,1)!=self.m.mem_read(q+1,1):
   p=self.run(get,0x2000ef00);n=self.m.mem_read(0x2000ef00,1)[0]
   result.append(bytes(self.m.mem_read(p,n)).hex());self.run(release)
  return result
cases=[]
def case(name,chunks,expected,start=0):
 x=Machine();x.init()
 if start:x.feed(bytes([0xf8])*start)
 for chunk in chunks:x.feed(chunk)
 got=x.drain()
 assert got==[p.hex() for p in expected],(name,got,expected)
 cases.append(dict(name=name,chunks=[c.hex() for c in chunks],prefill=start,packets=got,
  parser_state=x.m.mem_read(0x2000d114,1)[0],native_instructions=len(x.trace),
  wake_calls=sum(c[0]=='0x800612c' for c in x.calls)))
 return x
p=bytes.fromhex('f0110000f7');q=bytes.fromhex('f0280102f7')
case('single',[p],[p])
for i in range(1,len(p)):case('split-'+str(i),[p[:i],p[i:]],[p])
case('bytewise',[bytes([v]) for v in p],[p])
case('noise-and-idle',[bytes.fromhex('00127ff8')+p+b'\xf8'],[p])
case('two-packets',[p+q],[p,q])
case('idle-aborts-header',[bytes.fromhex('f0f8')+p],[p])
case('start-restarts-header',[bytes.fromhex('f0f0')+p],[p])
for start in (1018,1020,1021,1022,1023):case('dma-wrap-'+str(start),[p],[p],start)
case('incomplete',[p[:-1]],[])
x=case('queue-full',[p*8],[p]*7)
assert x.word(0x2000b480+12)==1
case('max-packet',[b'\xf0\x11'+b'\x01'*252+b'\xf7'],[b'\xf0\x11'+b'\x01'*252+b'\xf7'])
x=case('oversize-recover',[b'\xf0\x11'+b'\x01'*254+b'\xf7'+p],[p])
assert x.word(0x2000b480+16)==1
alternate=[]
for cmd,queue,get,release in [(0x15,0x2000c4b8,0x08000d40,0x08000d94),(0x40,0x2000bc9c,0x08000db4,0x08000de0),(0x7f,0x2000bc9c,0x08000db4,0x08000de0)]:
 x=Machine();x.init();packet=bytes([0xf0,cmd,1,0xf7]);x.feed(packet)
 got=x.drain(queue,release,get)
 assert got==[packet.hex()],(hex(cmd),got)
 alternate.append(dict(command=cmd,queue=hex(queue),packets=got))
case('idle-inside-body',[bytes.fromhex('f01101f802f7')],[bytes.fromhex('f01101f802f7')])
end_to_end=[]
for split in range(1,len(p)):
 x=Machine();x.init();x.feed(p[:split]);x.feed(p[split:])
 x.dispatch=True;x.run(0x080014a2)
 assert x.responses==['f01101f7'],x.responses
 assert x.m.mem_read(0x2000b480,1)==x.m.mem_read(0x2000b481,1)
 assert x.m.mem_read(0x20002b90,2)==bytes([1,1])
 end_to_end.append(dict(split=split,response=x.responses,pending_state=bytes(x.m.mem_read(0x20002b90,4)).hex(),
  executed_native_dequeue_release=True,instructions=len(x.trace)))
setup=Machine();setup.init()
data=dict(image_sha256=hashlib.sha256(B).hexdigest(),tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 host=platform.node(),platform=platform.platform(),unicorn=u.__version__,root=str(ROOT),
 init_mmio_writes=setup.writes,init_boundary_calls=setup.calls,
 dma_descriptor=hex(setup.desc),dma_buffer=hex(setup.buf),dma_count_register=hex(setup.count),
 cases=cases,alternate_queues=alternate,end_to_end=end_to_end,scope='Native NIMH init, DMA register programming, RX framing, queue publish/dequeue/release. MMIO backed by RAM; DMA delivery injected; GPIO, interrupts and eCos scheduling modeled. No physical SPI or concurrency proof.')
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'replay.json').write_text(json.dumps(data,indent=2)+'\n')
print('PASS',len(cases),'cases', 'DMA buffer',hex(setup.buf),'count',hex(setup.count))
