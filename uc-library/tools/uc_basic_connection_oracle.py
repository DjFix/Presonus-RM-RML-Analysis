"""Original BasicConnection composed with real ARM queue/factory control flow."""
import sys,json,struct,hashlib,collections
from pathlib import Path
import unicorn
from unicorn import arm_const as arm
from elftools.elf.elffile import ELFFile
from uc_event_queue_oracle import Oracle as QueueOracle,image,patch,pack,SIZE
METHODS=[('_ZN8Presonus2UC15BasicConnection9sendEventERKNS0_5EventE','sendEvent'),('_ZN8Presonus2UC15BasicConnection10queueEventEPv','queueEvent'),('_ZNK8Presonus2UC15BasicConnection15hasQueuedEventsEv','hasQueuedEvents')]
class Oracle(QueueOracle):
 def __init__(self,repo,role):
  hooks=[];original=unicorn.Uc.hook_add
  def capture(u,*args,**kw):h=original(u,*args,**kw);hooks.append((h,args,kw));return h
  unicorn.Uc.hook_add=capture
  try:super().__init__(repo,role)
  finally:unicorn.Uc.hook_add=original
  for h,args,kw in hooks:
   fn=args[1] if len(args)>1 else None
   if fn and getattr(fn,'__name__','') in ('guard','getData') and fn.__code__.co_filename.endswith('uc_event_queue_oracle.py'):self.u.hook_del(h)
  self.basic=self.obj;self.obj+=12
  self.provider=self.basic+0x7000;self.buckets=self.basic+0x8000+140
  inv=json.loads((repo/'uc-library/recovered'/role/'all-symbols.json').read_text());by={s['mangled']:s for s in inv};self.functions=[dict(by[n]) for n,_ in METHODS]
  with (repo/self.loader.manifest['path']).open('rb') as f:
   elf=ELFFile(f)
   for s in self.functions:
    sec=elf.get_section(s['section']);off=s['address']-sec['sh_addr'];raw=sec.data()[off:off+s['size']]
    assert len(raw)==s['size'];s['file_offset']=sec['sh_offset']+off;s['sha256']=hashlib.sha256(raw).hexdigest()
  self.guard,self.factory,_,_=struct.unpack('<4I',self.u.mem_read(self.functions[0]['address']+self.functions[0]['size']-16,16))
  self.hash=by['_ZN8Presonus2UC12EventFactory13hashEventTypeERKii']['address']
  def allowed(p,n,write=False):
   regions=[(self.basic,self.basic+76),(self.table,self.table+16),(self.provider,self.provider+0x1200),(self.data,self.data+5*SIZE),(self.items,self.items+128),(self.loader.stack,self.loader.stack+0x10000)]
   if not write:regions+=self.loader.loads
   return any(a<=p and p+n<=b for a,b in regions)
  def guard(u,access,p,n,value,user):assert allowed(p,n,access==unicorn.UC_MEM_WRITE),f'outsideBasicdomain {p:x}+{n}'
  self.u.hook_add(unicorn.UC_HOOK_MEM_READ|unicorn.UC_HOOK_MEM_WRITE,guard)
  def ret(value=0):self.u.reg_write(arm.UC_ARM_REG_R0,value);self.u.reg_write(arm.UC_ARM_REG_PC,self.u.reg_read(arm.UC_ARM_REG_LR))
  def itemID(u):
   pointer=u.reg_read(arm.UC_ARM_REG_R0);i=(pointer-self.items)//32
   assert 0<=i<4 and pointer==self.items+32*i and self.alive[i]
   return i
  def getData(u,p,n,user):
   i=itemID(u);assert self.held or i==2
   self.trace.append(16+i);ret(self.data+(i+1)*SIZE)
  def destroy(u,p,n,user):
   i=itemID(u);assert not self.held and i==2
   self.trace.append(32+i);self.alive[i]=False;self.destroyed[i]+=1;ret()
  def clone(u,p,n,user):
   assert not self.held and u.reg_read(arm.UC_ARM_REG_R0)==self.provider and u.reg_read(arm.UC_ARM_REG_R1)==self.data
   self.trace.append(64);self.cloneCalls+=1
   if self.cloneNull:ret(0);return
   self.alive[3]=True;u.mem_write(self.data+4*SIZE,bytes(u.mem_read(self.data,152))+bytes(SIZE-152));ret(self.items+96)
  for off,fn in [(4,getData),(8,destroy),(12,clone)]:self.u.hook_add(unicorn.UC_HOOK_CODE,fn,begin=self.loader.stop+off,end=self.loader.stop+off)
  def append(u,p,n,user):
   assert u.reg_read(arm.UC_ARM_REG_R0)==self.obj and not self.held
   pointer=u.reg_read(arm.UC_ARM_REG_R1);i=(pointer-self.items)//32
   assert 0<=i<4 and pointer==self.items+32*i and self.alive[i]
   self.trace.append(48+i)
  s=by['_ZN8Presonus2UC10EventQueue8addEventEPNS0_9EventItemE'];self.append_dependency=dict(s)
  self.u.hook_add(unicorn.UC_HOOK_CODE,append,begin=s['address'],end=s['address'])
  def forbidden(u,p,n,user):raise AssertionError('uninitialized staticfactory path excluded')
  for s in inv:
   if s['address'] and (s['mangled'].startswith('__cxa_guard_') or s['mangled'] in ('_ZN8Presonus2UC12EventFactoryC1Ev','_ZN8Presonus2UC12EventFactoryC2Ev')):self.u.hook_add(unicorn.UC_HOOK_CODE,forbidden,begin=s['address'],end=s['address'])
 def run(self,record,before):
  op,n,reverse,fallback,cloneNull,itemNull=record;u=self.u
  self.trace=[];self.held=False;self.unlockSnapshot=None;self.alive=[True,True,True,False];self.destroyed=[0]*4;self.cloneCalls=0;self.cloneNull=bool(cloneNull)
  order=list(reversed(range(n))) if reverse else list(range(n));queue=bytearray([0xa5]*76)
  struct.pack_into('<II',queue,12+28,self.items+32*order[0]+4 if n else 0,self.items+32*order[-1]+4 if n else 0)
  nodes=bytearray(128)
  for i in range(4):struct.pack_into('<I',nodes,32*i,self.table)
  for j,i in enumerate(order):struct.pack_into('<II',nodes,32*i+4,self.items+32*order[j+1]+4 if j+1<n else 0,self.items+32*order[j-1]+4 if j else 0)
  u.mem_write(self.basic,bytes(queue));u.mem_write(self.items,bytes(nodes));u.mem_write(self.table,pack(0,self.loader.stop+8,self.loader.stop+4,0));u.mem_write(self.data,before)
  u.mem_write(self.guard,pack(1));u.mem_write(self.factory,pack(0,8,self.hash,self.buckets,0,self.provider if fallback else 0));u.mem_write(self.provider,pack(self.provider+32));u.mem_write(self.provider+32,pack(0,0,self.loader.stop+12))
  for bucket in range(-7,8):u.mem_write(self.buckets+20*bucket,pack(0,self.provider+0x1000,0,0,0))
  for i in range(13):u.reg_write(getattr(arm,'UC_ARM_REG_R'+str(i)),0)
  u.reg_write(arm.UC_ARM_REG_CPSR,0x10);u.reg_write(arm.UC_ARM_REG_SP,self.loader.stack+0xff00);u.reg_write(arm.UC_ARM_REG_LR,self.loader.stop);u.reg_write(arm.UC_ARM_REG_R0,self.basic);u.reg_write(arm.UC_ARM_REG_R1,self.data if op==0 else (0 if itemNull else self.items+64))
  u.emu_start(self.functions[op]['address'],self.loader.stop,count=30000)
  assert u.reg_read(arm.UC_ARM_REG_PC)==self.loader.stop and u.reg_read(arm.UC_ARM_REG_SP)==self.loader.stack+0xff00 and not self.held
  result=u.reg_read(arm.UC_ARM_REG_R0);assert result in (0,1)
  def identity(pointer):
   if pointer==0:return 0xffffffff
   i=(pointer-self.items-4)//32;assert 0<=i<4 and pointer==self.items+32*i+4;return i
  head,tail=struct.unpack('<II',u.mem_read(self.obj+28,8));afterOrder=[];pointer=head
  while pointer:
   i=identity(pointer);assert i not in afterOrder and self.alive[i];afterOrder.append(i);pointer=struct.unpack('<I',u.mem_read(pointer,4))[0]
  assert identity(tail)==(afterOrder[-1] if afterOrder else 0xffffffff)
  nexts=[identity(struct.unpack('<I',u.mem_read(self.items+32*i+4,4))[0]) for i in range(4)]
  prevs=[identity(struct.unpack('<I',u.mem_read(self.items+32*i+8,4))[0]) for i in range(4)]
  after=bytearray(u.mem_read(self.data,5*SIZE));assert after[:SIZE]==before[:SIZE]
  for i in range(4):
   if not self.alive[i]:after[(i+1)*SIZE:(i+2)*SIZE]=bytes(SIZE)
  out=pack(sum(int(live)<<i for i,live in enumerate(self.alive)),*self.destroyed,len(afterOrder),*(afterOrder+[0xffffffff]*(4-len(afterOrder))),*nexts,*prevs,self.cloneCalls)
  return result,bytes(self.trace),out,bytes(after)
def main():
 repo=Path(sys.argv[1]).resolve();target=repo/'uc-library/validation/uc-basic-connection';target.mkdir(parents=True,exist_ok=True)
 cases=[]
 for op in range(3):
  for n in [0,1,2]:
   for reverse in [0,1]:
    for fallback in [0,1]:
     for cloneNull in [0,1]:
      for itemNull in ([0,1] if op==1 else [0]):
       for scenario in range(6):
        for seed in range(4):
         source=image(0,seed+11,[0,1,7,127][seed],0)
         images=[source]+[image(0,seed+i+23,[0,1,7,127][seed],0) for i in range(3)]+[bytearray(SIZE)]
         if scenario==5:struct.pack_into('<I',source,0,0x80000000+seed)
         images[3][:152]=source[:152]
         for i in range(2):
          images[i+1][:4]=source[:4];images[i+1][8:16]=source[8:16]
          if scenario==0:struct.pack_into('<I',images[i+1],0,0)
          elif scenario==1:struct.pack_into('<I',images[i+1],8,struct.unpack_from('<I',source,8)[0]^1)
          else:
           images[i+1][16]=1 if source[16]!=1 else 2
           if source[16]==0:images[i+1][17]=0
         order=list(reversed(range(n))) if reverse else list(range(n))
         matches=order[:1] if scenario in (3,5) else (order if scenario==4 else [])
         for i in matches:images[i+1][16:144]=source[16:144]
         cases.append(((op,n,reverse,fallback,cloneNull,itemNull),b''.join(map(bytes,images))))
 metadata=[];counts=collections.Counter()
 with (target/'arm-vectors.bin').open('wb') as f:
  f.write(b'UCBAv001'+pack(2*len(cases)))
  for role in ['client','server']:
   oracle=Oracle(repo,role)
   for record,before in cases:
    result,trace,small,after=oracle.run(record,before);assert len(trace)<=32 and len(small)==76
    f.write(pack(*record,result,len(trace))+trace.ljust(32,b'\0')+small+before+patch(before,after));counts[role+':'+METHODS[record[0]][1]]+=1
   metadata.append(dict(role=role,original_elf_sha256=oracle.loader.manifest['sha256'],functions=oracle.functions,external_synchronization_entrypoints=oracle.sync_contract,preinitialized_static_factory=dict(guard_address=oracle.guard,factory_address=oracle.factory,guard_word=1),append_dependency_executed_not_promoted=oracle.append_dependency));print(role,len(cases),'BasicConnection fixtures passed',flush=True)
 proof=dict(records=2*len(cases),cases=dict(counts),originals=metadata,vectors_sha256=hashlib.sha256((target/'arm-vectors.bin').read_bytes()).hexdigest(),domain='Alreadyinitializedstaticfactoryguardword1ONLY. ActualARMBasicConnection+EventQueuecoalescing/append+EventFactorylookup/hash;0/1/2existingitems,forward/reverselists,type/route/pathmiss,first/duplicatematch,rawPVNaNbits/indices,empty/max127paths;negativeunknowntypes,missingfactorycodec/clonenull,queueEventnull. Allsource/queuedpayloadsdisjoint,liveintrusivenodesnullnextonnewitem. Destroyincomingexactlyonceonlyaftercoalescedupdate/unlock;missretainsincomingidentity,sendclonesonlyonmiss,cloneNULLfalse. Compareexactlock/getData/clone/append/destructiontraces,livebits/nodeorder/links/rawpayloads. NoCorebodyexecution/network/hardware/constructor/staticinit/pools/concurrency/unsafealiases.',dependencies='Actual originalARMqueue/factory bodies execute with valid synthetic preinitializedregistry; existing external lock/unlockcontract, clone callback+itemgetData/virtualdeletion explicitcontracts. Actual originalEventQueue::addEvent appenddependency executes with intercepted synchronization; portableappend is independentcallback/bridge,addEvent itself NOT promoted. Native composes sealedactualEventQueue andEventFactorysource,virtualdelete,independentcaller-ownednodes.',limitations=['PortableBasicConnectionconstructor/statebridge/returnspelling/layout/inheritance/ownershipABIunproved;ordinaryreturnsunencoded.','Originalstaticfactoryfirst-useguard/constructor/destructor/pools remainunrecovered andexcluded;coalescingproofnotfullinitializationproof.','Originalitemdtorvariants/pooldeallocationnotrecovered;modeledvirtualdeletioncontractnativeactualvirtualdelete.','AppenddependencytestedwithinBasicConnectioncontract,not originalCorecontainer/addEventreadiness.','Allstring/payloadsdisjoint;dead/unallocatedpayloadbytesnormalizedzero,notread-after-freeevidence.'])
 (target/'oracle.json').write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
