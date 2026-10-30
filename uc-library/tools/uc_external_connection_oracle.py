"""Original external-handler dispatch/routing, with sealed common ARM fallback."""
import sys,json,struct,hashlib,collections
from pathlib import Path
import unicorn
from unicorn import arm_const as arm
from elftools.elf.elffile import ELFFile
from uc_connection_oracle import Oracle as CommonOracle,PALETTE,pack
METHODS=[('_ZN8Presonus2UC18ExternalConnection13adjustRoutingERNS0_5EventEb','adjustRouting'),('_ZN8Presonus2UC18ExternalConnection14handleInternalERKNS0_5EventE','handleInternal'),('_ZNK8Presonus2UC18ExternalConnection7getTypeEv','getType'),('_ZNK8Presonus2UC18ExternalConnection10getAddressERPKcRt','getAddress')]
class Oracle(CommonOracle):
 def __init__(self,repo,role):
  super().__init__(repo,role)
  inv=json.loads((repo/'uc-library/recovered'/role/'all-symbols.json').read_text());by={s['mangled']:s for s in inv}
  self.functions=[dict(by[n]) for n,_ in METHODS]
  with (repo/self.loader.manifest['path']).open('rb') as f:
   elf=ELFFile(f)
   for s in self.functions:
    sec=elf.get_section(s['section']);off=s['address']-sec['sh_addr'];raw=sec.data()[off:off+s['size']]
    assert len(raw)==s['size'];s['file_offset']=sec['sh_offset']+off;s['sha256']=hashlib.sha256(raw).hexdigest()
  def handler(u,p,n,user):
   assert u.reg_read(arm.UC_ARM_REG_R0)==self.channel
   assert u.reg_read(arm.UC_ARM_REG_R1)==0
   assert u.reg_read(arm.UC_ARM_REG_R2)==self.event
   self.handlerCalls+=1
   self.handlerSnapshot=bytes(u.mem_read(self.event,24))
   u.reg_write(arm.UC_ARM_REG_R0,self.handlerResult)
   u.reg_write(arm.UC_ARM_REG_PC,u.reg_read(arm.UC_ARM_REG_LR))
  self.u.hook_add(unicorn.UC_HOOK_CODE,handler,begin=self.loader.stop+12,end=self.loader.stop+12)
 def run(self,record):
  op,arg,orientation,route,present,handlerResult,eventType,a,b,p0,p1=record;u=self.u
  self.arg=arg;self.reply=[0]*6;self.sendCalls=self.granCalls=self.handlerCalls=0
  self.handlerSnapshot=None;self.handlerResult=handlerResult
  obj=bytearray([0xa5]*512);obj[:4]=pack(self.table);obj[0x188:0x18c]=pack(route);obj[0x18c]=orientation;obj[0x190:0x194]=pack(self.channel if present else 0)
  event=pack(eventType,0x12345678,a,b,p0,p1)
  u.mem_write(self.obj,bytes(obj));u.mem_write(self.event,event)
  u.mem_write(self.table,pack(0,self.loader.stop+8,0,0,0,0,0,0));u.mem_write(self.channel,pack(self.channelTable));u.mem_write(self.channelTable,pack(self.loader.stop+12,0,0,0,0,0,0,0))
  u.mem_write(self.senders,bytes([0xa5])*128)
  for i in range(13):u.reg_write(getattr(arm,'UC_ARM_REG_R'+str(i)),0)
  u.reg_write(arm.UC_ARM_REG_CPSR,0x10);u.reg_write(arm.UC_ARM_REG_SP,self.loader.stack+0xff00);u.reg_write(arm.UC_ARM_REG_LR,self.loader.stop)
  u.reg_write(arm.UC_ARM_REG_R0,self.obj);u.reg_write(arm.UC_ARM_REG_R1,self.senders if op==3 else self.event);u.reg_write(arm.UC_ARM_REG_R2,self.senders+4 if op==3 else arg)
  u.emu_start(self.functions[op]['address'],self.loader.stop,count=20000)
  assert u.reg_read(arm.UC_ARM_REG_PC)==self.loader.stop and u.reg_read(arm.UC_ARM_REG_SP)==self.loader.stack+0xff00
  result=u.reg_read(arm.UC_ARM_REG_R0) if op in (1,2) else 0
  out=bytes(u.mem_read(self.senders,128));addressOK=0;port=struct.unpack_from('<H',out,4)[0]
  if op==3:
   pointer=struct.unpack_from('<I',out)[0]
   addressOK=int(bytes(u.mem_read(pointer,11))==b'(External)\0');assert addressOK
   assert out[6:]==bytes([0xa5])*122
  else:assert out==bytes([0xa5])*128
  assert bytes(u.mem_read(self.obj,512))==bytes(obj)
  after=bytes(u.mem_read(self.event,24))
  if op!=0:assert after==event
  if self.handlerCalls:assert self.handlerSnapshot==event
  return pack(result,self.handlerCalls,self.sendCalls,addressOK,port,*struct.unpack('<6I',after),*self.reply)
def main():
 repo=Path(sys.argv[1]).resolve();target=repo/'uc-library/validation/uc-external-connection';target.mkdir(parents=True,exist_ok=True)
 cases=[]
 for orientation in [0,1,2,255]:
  for route in PALETTE:
   for seed in range(8):
    for op in range(4):
     for arg in [0,1]:
      for present in ([0,1] if op==1 else [0]):
       for result in ([0,1,2,3,0xffffffff,0x80000000] if op==1 and present else [0]):
        for eventType in ([0,19536,19537,19538,0xffffffff] if op==1 else [19537]):
         cases.append((op,arg,orientation,route,present,result,eventType,PALETTE[seed],PALETTE[(seed+3)%8],PALETTE[(seed+1)%8],PALETTE[(seed+5)%8]))
 counts=collections.Counter();metadata=[]
 with (target/'arm-vectors.bin').open('wb') as f:
  f.write(b'UCEXv001'+pack(2*len(cases)))
  for role in ['client','server']:
   oracle=Oracle(repo,role)
   for record in cases:
    f.write(pack(*record)+oracle.run(record));counts[role+':'+METHODS[record[0]][1]]+=1
   metadata.append(dict(role=role,original_elf_sha256=oracle.loader.manifest['sha256'],functions=oracle.functions))
   print(role,len(cases),'ExternalConnection fixtures passed',flush=True)
 proof=dict(records=2*len(cases),cases=dict(counts),originals=metadata,vectors_sha256=hashlib.sha256((target/'arm-vectors.bin').read_bytes()).hexdigest(),domain='Orientationbytes0/1/2/255,directionbool0/1,all32routeIDs inclnegative/highbit; nonselectedroute/payload unchanged. Externalhandler absent/present,returns0/1/2/3/ffffffff/80000000 withoriginNULL,exact2suppressessealedcommonfallback;othersallowLoopbackQuery19537temporaryReply19538/swappedroutes,callbackfalse/trueignored. Fiveeventtypesinclnegativebits,8rawpayload/routingpatterns. getType2/getAddressliteral(External)port0,disjointvalidoutputs; originalobject/inputevent/unusedoutputbyteschecked unchanged. No Core function execution,allocation/network/device operations; invalidcallbacks/pointers/alias/concurrencyexcluded.',dependencies='Actual original ExternalConnection and sealed original Connection::handleInternal ARM bodies. Externalhandler and synchronous replysend virtualtargets modeled as explicit independentcallbacks. No Core method invoked/reconstructed.',limitations=['Portablecomposition/statebridge/returnspelling; originalinheritance/ctor/layout/vtable/ARMABIunresolved.','getAddress/adjustRouting portablevoid declarations; incidentalARMreturnregisterignored.','Addressliteralcontent/terminationmatched;originalELFpointeridentitynotnativepointeridentity.','process/IDataChannel/networksocket/constructor/ownershipremainpending.'])
 (target/'oracle.json').write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
