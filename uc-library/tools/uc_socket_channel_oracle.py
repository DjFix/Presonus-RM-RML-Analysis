"""Original ARM UC socket-channel control flow; external I/O bodies not executed."""
import sys,json,struct,hashlib,collections
from pathlib import Path
import unicorn
from unicorn import arm_const as arm
from elftools.elf.elffile import ELFFile
import core_uc_oracle as base
METHODS=[('_ZN8Presonus2UC16SocketConnection7Channel4readEPvi','read'),('_ZN8Presonus2UC16SocketConnection7Channel5writeEPKvi','write'),('_ZN8Presonus2UC16SocketConnection7Channel10isReadableEi','isReadable'),('_ZN8Presonus2UC16SocketConnection7Channel10isWritableEi','isWritable'),('_ZN8Presonus2UC16SocketConnection7Channel9hasErrorsEi','hasErrors'),('_ZN8Presonus2UC16SocketConnection7Channel17getBytesAvailableEv','getBytesAvailable'),('_ZN8Presonus2UC16SocketConnection7Channel14getGranularityEv','getGranularity')]
EXTERNAL=['Core::Sockets::CoreSocket::receive(void*, int, int)','Core::Sockets::CoreSocket::sendAll(void const*, int, int)','Core::Sockets::CoreSocket::isReadable(int) const','Core::Sockets::CoreSocket::isWritable(int) const','Core::Sockets::CoreSocket::isAnyError(int) const','Core::Sockets::CoreSocket::getBytesAvailable(int&)']
pack=lambda *v:struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
signed=lambda v:v if v<0x80000000 else v-0x100000000
def resultFor(mode,index,requested):
 if mode==0:return requested
 if mode==1:return min(1,requested)
 if mode==2:return min([2,3,5][index%3],requested)
 if mode==3:return -1
 if mode==4:return -37
 if mode==5:return min(1,requested) if index==0 else -1
 if mode==6:return [0,min(2,requested),-7][min(index,2)]
 if mode==7:return 0 if index<3 else -11
 if mode==8:return [min(3,requested),0,min(1,requested),-2][min(index,3)]
 if mode==9:return 0 if index%3!=2 else min(2,requested)
 return min(3,requested) if index==0 else -0x80000000
class Oracle:
 def __init__(self,repo,role):
  hooks=[];original=unicorn.Uc.hook_add
  def capture(u,*a,**kw):h=original(u,*a,**kw);hooks.append(h);return h
  unicorn.Uc.hook_add=capture
  try:self.loader=base.Oracle(repo,role)
  finally:unicorn.Uc.hook_add=original
  self.u=self.loader.u
  for h in hooks:self.u.hook_del(h)
  self.obj=self.loader.obj;self.io=self.loader.data;self.socket=self.obj+0x4000
  inv=json.loads((repo/'uc-library/recovered'/role/'all-symbols.json').read_text());by={s['mangled']:s for s in inv};self.functions=[dict(by[n]) for n,_ in METHODS]
  with (repo/self.loader.manifest['path']).open('rb') as f:
   elf=ELFFile(f)
   for s in self.functions:
    sec=elf.get_section(s['section']);off=s['address']-sec['sh_addr'];raw=sec.data()[off:off+s['size']]
    assert len(raw)==s['size'];s['file_offset']=sec['sh_offset']+off;s['sha256']=hashlib.sha256(raw).hexdigest()
  def allowed(p,n):return any(a<=p and p+n<=b for a,b in [(self.obj,self.obj+8),(self.io,self.io+128),(self.loader.stack,self.loader.stack+0x10000)])
  def guard(u,access,p,n,value,user):assert allowed(p,n) or access!=unicorn.UC_MEM_WRITE and any(a<=p and p+n<=b for a,b in self.loader.loads),f'outside channel domain {p:x}+{n}'
  self.u.hook_add(unicorn.UC_HOOK_MEM_READ|unicorn.UC_HOOK_MEM_WRITE,guard)
  self.contracts=[]
  def callback(method):
   def run(u,p,n,user):
    r=[u.reg_read(getattr(arm,'UC_ARM_REG_R'+str(i))) for i in range(4)]
    assert r[0]==self.socket
    if method==0:
     offset=r[1]-self.io;requested=signed(r[2]);assert r[3]==0 and 0<requested<=64 and 0<=offset and offset+requested<=128
     result=resultFor(self.mode,len(self.trace),requested)
     if result>0:
      data=bytes(((self.received+i)*11+self.seed*17)&255 for i in range(result));u.mem_write(r[1],data);self.received+=result
     row=[method,offset,requested,0,result]
    elif method==1:
     requested=signed(r[2]);offset=0xffffffff if r[1]==0 else r[1]-self.io
     assert r[3]==0 and (requested<=0 or 0<=offset and offset+requested<=128)
     result=signed(self.reply)
     if result>0:assert result<=requested;self.sent[:result]=u.mem_read(r[1],result)
     row=[method,offset,requested,0,result]
    elif method in (2,3,4):result=self.reply;assert result in (0,1);row=[method,r[1],0,0,result]
    else:
     assert self.loader.stack<=r[1]<self.loader.stack+0x10000-4
     initial=struct.unpack('<I',u.mem_read(r[1],4))[0];assert initial==0
     if self.mutate:u.mem_write(r[1],pack(self.outValue))
     result=self.reply;row=[method,initial,self.outValue if self.mutate else initial,0,result]
    self.trace.append(row);assert len(self.trace)<=256
    u.reg_write(arm.UC_ARM_REG_R0,result&0xffffffff);u.reg_write(arm.UC_ARM_REG_PC,u.reg_read(arm.UC_ARM_REG_LR))
   return run
  for i,name in enumerate(EXTERNAL):
   s=next(s for s in inv if s.get('demangled')==name and s['address']);self.contracts.append(dict(mangled=s['mangled'],demangled=name,address=s['address'],size=s['size'],body_executed=False))
   self.u.hook_add(unicorn.UC_HOOK_CODE,callback(i),begin=s['address'],end=s['address'])
 def run(self,record):
  op,arg,offset,self.mode,self.reply,self.outValue,self.mutate,self.seed=record;u=self.u
  self.trace=[];self.received=0;self.sent=bytearray(128)
  before=bytes((29*i+71*self.seed)&255 for i in range(128));u.mem_write(self.io,before);obj=pack(0,self.socket);u.mem_write(self.obj,obj)
  for i in range(13):u.reg_write(getattr(arm,'UC_ARM_REG_R'+str(i)),0)
  u.reg_write(arm.UC_ARM_REG_CPSR,0x10);u.reg_write(arm.UC_ARM_REG_SP,self.loader.stack+0xff00);u.reg_write(arm.UC_ARM_REG_LR,self.loader.stop);u.reg_write(arm.UC_ARM_REG_R0,self.obj)
  u.reg_write(arm.UC_ARM_REG_R1,(0 if offset==0xffffffff else self.io+offset) if op in (0,1) else arg);u.reg_write(arm.UC_ARM_REG_R2,arg)
  u.emu_start(self.functions[op]['address'],self.loader.stop,count=100000)
  assert u.reg_read(arm.UC_ARM_REG_PC)==self.loader.stop and u.reg_read(arm.UC_ARM_REG_SP)==self.loader.stack+0xff00
  result=u.reg_read(arm.UC_ARM_REG_R0);after=bytes(u.mem_read(self.io,128));assert bytes(u.mem_read(self.obj,8))==obj
  if op!=0:assert after==before
  return result,self.trace,after,bytes(self.sent)
def main():
 repo=Path(sys.argv[1]).resolve();target=repo/'uc-library/validation/uc-socket-channel';target.mkdir(parents=True,exist_ok=True);cases=[]
 for seed in range(4):
  for count in [0,1,2,3,4,7,8,15,31,32,63,64,0xffffffff,0x80000000]:
   for offset in ([0,7,0xffffffff] if signed(count)<=0 else [0,7]):
    for mode in range(11):cases.append((0,count,offset,mode,0,0,0,seed))
    for result in sorted({0,-1,-37} | ({1,signed(count)} if signed(count)>0 else set())):cases.append((1,count,offset,0,result&0xffffffff,0,0,seed))
  for timeout in [0,1,50,0xffffffff,0x80000000,0x7fffffff]:
   for result in [0,1]:
    for op in [2,3,4]:cases.append((op,timeout,0,0,result,0,0,seed))
  for status in [0,1,0xffffffff,0x80000000]:
   for value in [0,1,65535,0xffffffff,0x80000000,0x7fffffff]:
    for mutate in [0,1]:cases.append((5,0,0,0,status,value,mutate,seed))
  cases.append((6,0,0,0,0,0,0,seed))
 counts=collections.Counter();metadata=[]
 with (target/'arm-vectors.bin').open('wb') as f:
  f.write(b'UCCHv001'+pack(2*len(cases)))
  for role in ['client','server']:
   oracle=Oracle(repo,role)
   for record in cases:
    result,trace,after,sent=oracle.run(record);f.write(pack(*record,result,len(trace))+b''.join(pack(*row) for row in trace)+after+sent);counts[role+':'+METHODS[record[0]][1]]+=1
   metadata.append(dict(role=role,original_elf_sha256=oracle.loader.manifest['sha256'],functions=oracle.functions,external_io_entrypoints=oracle.contracts));print(role,len(cases),'SocketChannel fixtures passed',flush=True)
 proof=dict(records=2*len(cases),cases=dict(counts),originals=metadata,vectors_sha256=hashlib.sha256((target/'arm-vectors.bin').read_bytes()).hexdigest(),domain='Live128byteIO/channelstate,requestedreads0..64andnegativecountINTMIN/-1,offsets0/7,nullonlynonpositive;11finitebackendreadscriptsfull/partial/errors/zero-retrysequences,eventualprogressorerror,returnedbytes<=request. writeflags0/sourcebytes/returncount/errorforwarding,negative/zero requestswithnonaccessingbackend;boolpoll0/1andfullsignedtimeoutbits;availableinitialout0,statusignored,optionaloutmutationinclnegative/highbits;granularity4096. Exactorderedcallbackarguments/offsets/remainders/flags/resultsandIO/sentbyteschecked. Endlesszero providerwouldspinoriginally—notexecuted/fixed;invalidpointer/alias/concurrency/backendover-return/signedoverflowexcluded.',dependencies='ActualoriginalUCChannelARMcontrolflow;CoreSocketentrypoints interceptedONLYasexplicitindependentexternalI/Ocallbacks,nobodyexecuted/reconstructed. NativecomposesgenuineexistingportableEventFactory/codecs and scriptedI/O;noCoreclass/OSsocket/hardware/networkaccess.',limitations=['PortableIOcompositionandconstructor;originalSocketConnection/Channelinheritance/fields/ownership/dtorvariants/layout/ARMABIunproved.','Allordinaryreturnsunencoded;portableintcounts/boolpollmatchboundedobservedcontracts.','Zero-byte read retries indefinitely unlessproviderprogresses/errors;nochangedtimeout/retrycap.','CoreSocketreceive/sendAll/poll/availabilityimplementationsandrealOStransportbehaviornotclaimed.'])
 (target/'oracle.json').write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
