"""ARM queue coalescing; Core synchronization bodies remain external contracts."""
import sys,json,struct,hashlib,collections
from pathlib import Path
import unicorn
from unicorn import arm_const as arm
from elftools.elf.elffile import ELFFile
import core_uc_oracle as base
TYPES=['ParamValueEvent','ParamIncrementEvent','ParamColorEvent','ParamStringEvent','ParamStringListEvent','ParamRangeEvent','FileDataRateEvent','TimeCodeEvent']
TAGS=[20566,20553,20547,20563,20556,20562,18003,21571]
METHODS=[('_ZN8Presonus2UC10EventQueue6updateINS0_'+str(len(t))+t+'EEEbRKNS0_5EventE','update'+t) for t in TYPES]+[('_ZN8Presonus2UC10EventQueue11updateEventERKNS0_5EventE','updateEvent')]
SIZE=1216
P=[0,1,0xffff,0xffffffff,0x80000000,0x7fffffff,0x7fc00001,0xff800001]
pack=lambda *v:struct.pack('<'+'I'*len(v),*v)
def put(a,off,value):struct.pack_into('<I',a,off,value&0xffffffff)
def string(a,off,n,key):
 a[off:off+n]=bytes(((i*37+key)%255)+1 for i in range(n));a[off+n]=0
def image(kind,seed,pathlen,textlen):
 a=bytearray((i*29+seed*71)&255 for i in range(SIZE))
 a[:16]=pack(TAGS[kind],0xaabb0000+seed,P[seed%8],P[(seed+1)%8])
 if kind<6:
  string(a,16,pathlen,17);struct.pack_into('<H',a,144,(seed*313+65530)&65535)
  if kind==1:struct.pack_into('<H',a,146,P[seed%8]&65535)
  elif kind==3:string(a,146,min(textlen,255),seed+1)
  elif kind==4:put(a,148,P[seed%8]);string(a,152,min(textlen,1023),seed+1)
  elif kind==5:
   for i in range(5):put(a,148+4*i,P[(seed+i)%8])
   string(a,168,min(textlen,31),seed+1);string(a,200,min(textlen,31),seed+2)
  else:put(a,148,P[seed%8])
 else:
  put(a,16,P[seed%8])
  if kind==6:
   for i in range(3):put(a,20+4*i,P[(seed+i+2)%8])
  else:a[20]=[0,1,4,255][seed%4]
 return a
def patch(before,after):
 runs=[];i=0
 while i<len(before):
  if before[i]==after[i]:i+=1;continue
  start=i
  while i<len(before) and before[i]!=after[i]:i+=1
  runs.append((start,after[start:i]))
 return pack(len(runs))+b''.join(pack(start,len(data))+data for start,data in runs)
class Oracle:
 obj=0x10000000;data=0x11000000;items=0x12000000;table=0x10004000
 def __init__(self,repo,role):
  hooks=[];original=unicorn.Uc.hook_add
  def capture(u,*a,**kw):h=original(u,*a,**kw);hooks.append(h);return h
  unicorn.Uc.hook_add=capture
  try:self.loader=base.Oracle(repo,role)
  finally:unicorn.Uc.hook_add=original
  self.u=self.loader.u
  for h in hooks:self.u.hook_del(h)
  self.u.mem_map(self.data,0x10000);self.u.mem_map(self.items,0x10000)
  inv=json.loads((repo/'uc-library/recovered'/role/'all-symbols.json').read_text());by={s['mangled']:s for s in inv};self.functions=[dict(by[n]) for n,_ in METHODS]
  with (repo/self.loader.manifest['path']).open('rb') as f:
   elf=ELFFile(f)
   for s in self.functions:
    sec=elf.get_section(s['section']);off=s['address']-sec['sh_addr'];raw=sec.data()[off:off+s['size']]
    assert len(raw)==s['size'];s['file_offset']=sec['sh_offset']+off;s['sha256']=hashlib.sha256(raw).hexdigest()
  def allowed(p,n,write=False):
   regions=[(self.obj,self.obj+64),(self.table,self.table+16),(self.data,self.data+5*SIZE),(self.items,self.items+128),(self.loader.stack,self.loader.stack+0x10000)]
   if not write:regions+=self.loader.loads
   return any(a<=p and p+n<=b for a,b in regions)
  def guard(u,access,p,n,value,user):assert allowed(p,n,access==unicorn.UC_MEM_WRITE),f'outsidequeue domain {p:x}+{n}'
  self.u.hook_add(unicorn.UC_HOOK_MEM_READ|unicorn.UC_HOOK_MEM_WRITE,guard)
  def ret(value=0):self.u.reg_write(arm.UC_ARM_REG_R0,value);self.u.reg_write(arm.UC_ARM_REG_PC,self.u.reg_read(arm.UC_ARM_REG_LR))
  def lock(u,p,n,user):
   assert u.reg_read(arm.UC_ARM_REG_R0)==self.obj and not self.held
   self.held=True;self.trace.append(1);ret()
  def unlock(u,p,n,user):
   assert u.reg_read(arm.UC_ARM_REG_R0)==self.obj and self.held
   self.unlockSnapshot=bytes(u.mem_read(self.data,5*SIZE));self.held=False;self.trace.append(2);ret()
  self.sync_contract=[]
  for name,fn in [('_ZN4Core7Threads8CoreLock4lockEv',lock),('_ZN4Core7Threads8CoreLock6unlockEv',unlock)]:
   s=by[name];self.u.hook_add(unicorn.UC_HOOK_CODE,fn,begin=s['address'],end=s['address'])
   self.sync_contract.append(dict(mangled=name,address=s['address'],size=s['size'],body_executed=False,role='external synchronization callback contract only'))
  def getData(u,p,n,user):
   q=u.reg_read(arm.UC_ARM_REG_R0);i=(q-self.items)//32
   assert self.held and 0<=i<4 and q==self.items+32*i
   self.trace.append(16+i);ret(self.data+(i+1)*SIZE)
  self.u.hook_add(unicorn.UC_HOOK_CODE,getData,begin=self.loader.stop+4,end=self.loader.stop+4)
  def cstring(p,maximum):
   for i in range(maximum):
    assert allowed(p+i,1)
    if u8(self.u,p+i)==0:return bytes(self.u.mem_read(p,i))
   raise AssertionError('unboundedCString')
  def strcmp(u,p,n,user):
   assert self.held;a=u.reg_read(arm.UC_ARM_REG_R0);b=u.reg_read(arm.UC_ARM_REG_R1)
   x=cstring(a,128);y=cstring(b,128);ret(0 if x==y else (1 if x>y else 0xffffffff))
  def strcpy(u,p,n,user):
   assert self.held;a=u.reg_read(arm.UC_ARM_REG_R0);b=u.reg_read(arm.UC_ARM_REG_R1);x=cstring(b,1024)+b'\0'
   assert allowed(a,len(x),True) and (a+len(x)<=b or b+len(x)<=a)
   self.u.mem_write(a,x);ret(a)
  for name,fn in [('strcmp',strcmp),('strcpy',strcpy)]:
   s=next(s for s in inv if s['mangled'].startswith(name+'@@') and s['address']);self.u.hook_add(unicorn.UC_HOOK_CODE,fn,begin=s['address'],end=s['address'])
 def run(self,op,n,order,before):
  self.trace=[];self.held=False;self.unlockSnapshot=None;u=self.u
  queue=bytearray([0xa5]*64);struct.pack_into('<I',queue,28,self.items+32*order[0]+4 if n else 0)
  nodes=bytearray([0xa5]*128)
  for i in range(4):struct.pack_into('<I',nodes,32*i,self.table)
  for position,i in enumerate(order[:n]):struct.pack_into('<II',nodes,32*i+4,self.items+32*order[position+1]+4 if position+1<n else 0,self.items+32*order[position-1]+4 if position else 0)
  u.mem_write(self.obj,bytes(queue));u.mem_write(self.items,bytes(nodes));u.mem_write(self.table,pack(0,0,self.loader.stop+4,0));u.mem_write(self.data,before)
  for i in range(13):u.reg_write(getattr(arm,'UC_ARM_REG_R'+str(i)),0)
  u.reg_write(arm.UC_ARM_REG_CPSR,0x10);u.reg_write(arm.UC_ARM_REG_SP,self.loader.stack+0xff00);u.reg_write(arm.UC_ARM_REG_LR,self.loader.stop);u.reg_write(arm.UC_ARM_REG_R0,self.obj);u.reg_write(arm.UC_ARM_REG_R1,self.data)
  u.emu_start(self.functions[op]['address'],self.loader.stop,count=20000)
  assert u.reg_read(arm.UC_ARM_REG_PC)==self.loader.stop and u.reg_read(arm.UC_ARM_REG_SP)==self.loader.stack+0xff00 and not self.held
  result=u.reg_read(arm.UC_ARM_REG_R0);assert result in (0,1)
  after=bytes(u.mem_read(self.data,5*SIZE));assert after[:SIZE]==before[:SIZE]
  assert bytes(u.mem_read(self.obj,64))==bytes(queue) and bytes(u.mem_read(self.items,128))==bytes(nodes)
  if self.trace:assert self.trace[0]==1 and self.trace[-1]==2 and self.unlockSnapshot==after
  return result,bytes(self.trace),after
def u8(u,p):return u.mem_read(p,1)[0]
def main():
 repo=Path(sys.argv[1]).resolve();target=repo/'uc-library/validation/uc-event-queue';target.mkdir(parents=True,exist_ok=True)
 cases=[]
 for kind in range(8):
  for dispatch in [0,1]:
   for scenario in range(10):
    for seed in range(8):
     for n in ([0] if scenario==0 else [1,4]):
      order=[0,1,2,3] if seed%2==0 else [3,2,1,0]
      pathlen=[0,1,7,127][seed%4];textlen=[0,1,31,255,1023][seed%5]
      images=[image(kind,seed+11,pathlen,textlen)]+[image(kind,seed+i+23,pathlen,textlen) for i in range(4)]
      source=images[0]
      if scenario==9:put(source,0,0x80000000+seed)
      for imageIndex in range(1,5):
       a=images[imageIndex];a[:4]=source[:4];a[8:16]=source[8:16]
       if kind>=6:a[16:20]=source[16:20]
       if scenario==1:put(a,0,struct.unpack_from('<I',source)[0]^1)
       elif scenario==2:put(a,8,struct.unpack_from('<I',source,8)[0]^1)
       elif scenario==3:put(a,12,struct.unpack_from('<I',source,12)[0]^1)
       elif scenario in (4,5,6,7,8,9):
        if kind<6:
         a[16]=1 if source[16]!=1 else 2
         if pathlen==0:a[17]=0
        else:put(a,16,struct.unpack_from('<I',source,16)[0]^1)
      matches=[]
      if scenario in (5,8,9):matches=[order[0]]
      elif scenario==6:matches=[order[n-1]]
      elif scenario==7:matches=[order[0],order[n-1]]
      for i in matches:
       a=images[i+1]
       if kind<6:a[16:16+pathlen+1]=source[16:16+pathlen+1]
       else:a[16:20]=source[16:20]
      before=b''.join(map(bytes,images));cases.append((kind,dispatch,n,order,before))
 counts=collections.Counter();metadata=[]
 with (target/'arm-vectors.bin').open('wb') as f:
  f.write(b'UCQUv001'+pack(2*len(cases)))
  for role in ['client','server']:
   oracle=Oracle(repo,role)
   for kind,dispatch,n,order,before in cases:
    op=8 if dispatch else kind;result,trace,after=oracle.run(op,n,order,before)
    orderBits=sum(i<<(2*j) for j,i in enumerate(order));f.write(pack(kind,dispatch,n,orderBits,result,len(trace))+trace.ljust(16,b'\0')+before+patch(before,after));counts[role+':'+METHODS[op][1]]+=1
   metadata.append(dict(role=role,original_elf_sha256=oracle.loader.manifest['sha256'],functions=oracle.functions,external_synchronization_entrypoints=oracle.sync_contract));print(role,len(cases),'queue coalescing fixtures passed',flush=True)
 proof=dict(records=2*len(cases),cases=dict(counts),originals=metadata,vectors_sha256=hashlib.sha256((target/'arm-vectors.bin').read_bytes()).hexdigest(),domain='0/1/4retainedliveitems,forward/reverselists,first/last/duplicatematch,type/routeA/routeB/path/keymiss,128byteCStringpathswithNULtails,empty/maxboundedstrings,rawNaN/intbits,16bitincrementwrap,indexignoredmatch,Range stale2ndword/FileRateonlyfirstword;Timeall4records/count255copied. Directtemplateunknownincomingtypematchesvsdispatcherunknownfalsewithoutlock. Input/source/list/itemownershipunchanged,exactlock/getData/unlocktraceandstateatunlockchecked. Disjointstorage/NULboundedstrings,noCorelockbodyexecution/concurrency/invalidnodes/throwingARMcallbacks.',dependencies='OriginalARMUCupdate/updateEvent bodies;CoreLock entrypoints interceptedonlyasexplicitexternal lock/unlockcallbacks withorderedtrace,neverexecuteorreconstructCorebody. SyntheticexistingEventItemgetDatacallback;strcmp/strcpystandardcontractsbounded,notlibcimplementationproof.',limitations=['Portableexistingitemlist/typedresolver/synchronizationRAII areindependentcontracts,notCorecontainerororiginallayout/ownership/vtable/constructorABI.','OnlynormalARMcontrolflowvalidated;portableRAIIexceptioncleanupcanbenativetestedseparately,notoriginalARMunwindproof.','Templateboolreturnencoded;ordinaryupdateEventreturnspellingunencoded.','Noadd/retrieve/flush/pool/allocation/itemdestructionregistrationorhardwaretests.','Writescomparedasfinalstateatunlock;transientRange/timecopyinstructionstoreorderisnotnativeinstructiontraceequivalence.'])
 proof['vector_format']='UCQUv001 +LEu32recordCount. Perrecord:6LEu32(kind,dispatch,n,order2bitIDs,result,tracelength),16tracebytes(1lock/2unlock/16+itemIDgetData),5canonical1216byteimages(incoming+4retaineditems),LEu32patchruns theneachLEu32offset/length+literalbytes. Patchesapplytofiveimages;sourceimageunchanged. Canonicalfieldsencodedindependentlyofnativeobjectlayout.'
 (target/'oracle.json').write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
