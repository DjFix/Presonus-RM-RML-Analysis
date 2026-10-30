"""Original ARM UC Connection methods; no Core framework body executed."""
import sys,json,struct,hashlib,collections
from pathlib import Path
import unicorn
from unicorn import arm_const as arm
from elftools.elf.elffile import ELFFile
import core_uc_oracle as base
METHODS=[('_ZN8Presonus2UC10Connection13adjustRoutingERNS0_5EventEb','adjustRouting'),('_ZN8Presonus2UC10Connection17sendPeriodicEventERKNS0_5EventE','sendPeriodicEvent'),('_ZN8Presonus2UC10Connection5resetEv','reset'),('_ZNK8Presonus2UC10Connection10findSenderEi','findSender'),('_ZNK8Presonus2UC10Connection21findSenderWithLocalIDEi','findSenderWithLocalID'),('_ZN8Presonus2UC10Connection11initChannelEv','initChannel'),('_ZN8Presonus2UC10Connection14handleInternalERKNS0_5EventE','handleInternal')]
PALETTE=[0,1,0xffffffff,0x80000000,0x7fffffff,19537,0x12345678,0x87654321]
pack=lambda *x:struct.pack('<'+'I'*len(x),*x)
class Oracle:
 def __init__(self,repo,role):
  hooks=[];original=unicorn.Uc.hook_add
  def capture(u,*a,**kw):
   h=original(u,*a,**kw);hooks.append(h);return h
  unicorn.Uc.hook_add=capture
  try:self.loader=base.Oracle(repo,role)
  finally:unicorn.Uc.hook_add=original
  self.u=self.loader.u
  for h in hooks:self.u.hook_del(h)
  inv=json.loads((repo/'uc-library/recovered'/role/'all-symbols.json').read_text());by={s['mangled']:s for s in inv}
  self.functions=[dict(by[n]) for n,_ in METHODS]
  with (repo/self.loader.manifest['path']).open('rb') as f:
   elf=ELFFile(f)
   for s in self.functions:
    sec=elf.get_section(s['section']);off=s['address']-sec['sh_addr'];raw=sec.data()[off:off+s['size']]
    assert len(raw)==s['size'];s['file_offset']=sec['sh_offset']+off;s['sha256']=hashlib.sha256(raw).hexdigest()
  self.obj=self.loader.obj;self.event=self.loader.data;self.senders=self.loader.aux
  self.array=self.obj+0x3000;self.table=self.obj+0x4000;self.channel=self.obj+0x5000;self.channelTable=self.obj+0x6000
  def guard(u,access,p,n,value,user):
   regions=[(self.obj,self.obj+512),(self.event,self.event+24),(self.senders,self.senders+128),(self.array,self.array+32),(self.table,self.table+32),(self.channel,self.channel+4),(self.channelTable,self.channelTable+32),(self.loader.stack,self.loader.stack+0x10000)]
   if access!=unicorn.UC_MEM_WRITE:regions+=self.loader.loads
   assert any(a<=p and p+n<=b for a,b in regions),f'outside domain {p:x}+{n}'
  self.u.hook_add(unicorn.UC_HOOK_MEM_READ|unicorn.UC_HOOK_MEM_WRITE,guard)
  def callback(u,p,n,user):
   if p==self.loader.stop+4:
    assert u.reg_read(arm.UC_ARM_REG_R0)==self.channel
    self.granCalls+=1;u.reg_write(arm.UC_ARM_REG_R0,self.arg)
   elif p==self.loader.stop+8:
    assert u.reg_read(arm.UC_ARM_REG_R0)==self.obj
    q=u.reg_read(arm.UC_ARM_REG_R1);assert self.loader.stack<=q<=self.loader.stack+0x10000-24
    self.reply=list(struct.unpack('<6I',u.mem_read(q,24)));self.sendCalls+=1;u.reg_write(arm.UC_ARM_REG_R0,self.arg&1)
   u.reg_write(arm.UC_ARM_REG_PC,u.reg_read(arm.UC_ARM_REG_LR))
  self.u.hook_add(unicorn.UC_HOOK_CODE,callback,begin=self.loader.stop+4,end=self.loader.stop+8)
 def run(self,record):
  op,arg,n,seed,limit,eventType,routeA,routeB,p0,p1=record;u=self.u
  self.arg=arg;self.reply=[0]*6;self.granCalls=self.sendCalls=0
  obj=bytearray([0xa5]*512);obj[:4]=pack(self.table);obj[0x13c:0x144]=pack(self.channel,limit);obj[0x16c:0x174]=pack(self.array,n)
  event=pack(eventType,0x12345678,routeA,routeB,p0,p1)
  sender=b''.join(pack(0xdead0000+i,PALETTE[(seed+i)%8],PALETTE[(seed+2*i)%8],0xcafe0000+i) for i in range(8))
  u.mem_write(self.obj,bytes(obj));u.mem_write(self.event,event);u.mem_write(self.senders,sender)
  u.mem_write(self.array,pack(*(self.senders+16*i for i in range(8))))
  u.mem_write(self.table,pack(0,self.loader.stop+8,0,0,0,0,0,0));u.mem_write(self.channel,pack(self.channelTable));u.mem_write(self.channelTable,pack(0,0,0,0,self.loader.stop+4,0,0,0))
  for i in range(13):u.reg_write(getattr(arm,'UC_ARM_REG_R'+str(i)),0)
  u.reg_write(arm.UC_ARM_REG_CPSR,0x10);u.reg_write(arm.UC_ARM_REG_SP,self.loader.stack+0xff00);u.reg_write(arm.UC_ARM_REG_LR,self.loader.stop)
  u.reg_write(arm.UC_ARM_REG_R0,self.obj)
  u.reg_write(arm.UC_ARM_REG_R1,arg if op in (3,4) else self.event)
  u.reg_write(arm.UC_ARM_REG_R2,arg&1)
  u.emu_start(self.functions[op]['address'],self.loader.stop,count=20000)
  assert u.reg_read(arm.UC_ARM_REG_PC)==self.loader.stop and u.reg_read(arm.UC_ARM_REG_SP)==self.loader.stack+0xff00
  result=u.reg_read(arm.UC_ARM_REG_R0)
  if op in (0,5):result=0 # unencoded void/unspecified register return excluded
  if op in (3,4):
   result=0xffffffff if result==0 else (result-self.senders)//16
   assert result==0xffffffff or result<n
  after=bytes(u.mem_read(self.obj,512));actualLimit=struct.unpack_from('<I',after,0x140)[0]
  obj[0x140:0x144]=pack(actualLimit)
  assert after==bytes(obj) and bytes(u.mem_read(self.event,24))==event and bytes(u.mem_read(self.senders,128))==sender
  return pack(result,actualLimit,self.granCalls,self.sendCalls,*self.reply)

def main():
 repo=Path(sys.argv[1]).resolve();target=repo/'uc-library/validation/uc-connection';target.mkdir(parents=True,exist_ok=True)
 cases=[]
 for seed in range(16):
  for n in range(9):
   for arg in PALETTE:
    for op in [0,1,2,3,4,6]:
     for eventType in ([0,19536,19537,19538,0xffffffff] if op==6 else [19537]):
      cases.append((op,arg,n,seed,0x89abcdef,eventType,PALETTE[(seed+1)%8],PALETTE[(seed+2)%8],PALETTE[(seed+3)%8],PALETTE[(seed+4)%8]))
 for gran in [1,2,3,7,15,31,127,255,1023,1024,1025,2047,2048,2049,4095,4096,4097,65535,0x7fffffff,0xffffffff,0xfffffffd,0xfffff001,0x80000000]:
  cases.append((5,gran,0,0,0x89abcdef,19537,0,0,0,0))
 metadata=[];counts=collections.Counter()
 with (target/'arm-vectors.bin').open('wb') as f:
  f.write(b'UCCNv001'+pack(2*len(cases)))
  for role in ['client','server']:
   oracle=Oracle(repo,role)
   for record in cases:
    f.write(pack(*record)+oracle.run(record));counts[role+':'+METHODS[record[0]][1]]+=1
   metadata.append(dict(role=role,original_elf_sha256=oracle.loader.manifest['sha256'],functions=oracle.functions))
   print(role,len(cases),'Connection fixtures passed',flush=True)
 proof=dict(records=2*len(cases),cases=dict(counts),originals=metadata,vectors_sha256=hashlib.sha256((target/'arm-vectors.bin').read_bytes()).hexdigest(),domain='Bounded0..8 nonnull sender pointers,16ordered/collidingtables,fullintbitqueries,firstmatch/missing; routing/reset/periodic unchangedmemory.23nonzero signed channelgranularities includingnegative/highbit,exact4096boundaries. Loopbackquerytype19537only sends ephemeralreply19538/legacybyteSize24 with SWAPPED rawrouteA/routeB and unchanged payload2words, ignoresfalse/true send result. Inputevent/object/sender nonmutationchecked except channelword140. No Core container implementation/execution, allocation/network/device/hardware IO; zero division,invalid/nullsenderentries/concurrency/alias excluded.',dependencies='Only actual original UC functions and original compiler signeddivision helper executed. Independent bounded sender array, explicit original channel/sendvirtualcallback contracts. No Core function reconstructed or invoked.',limitations=['Portable declarations/fields/callbackstate/returnspelling and sender opaque pointer type; original class fields/inheritance/ownership/layout/ARMABI unresolved.','initChannel andadjustRouting useportablevoid; ARM incidentalr0ignored, nooriginalreturntypeclaim.','No constructor/addSender/makeLocalID/process/transport/pool/Corecontainer/network operations recovered.'])
 (target/'oracle.json').write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
