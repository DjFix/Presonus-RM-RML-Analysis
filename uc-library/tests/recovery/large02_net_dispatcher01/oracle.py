"""Execute exact original application ARM ranges; CCL provider/runtime calls are
explicit modeled boundaries. No Core firmware implementation is executed.
Expected lifecycle observations never come from the reconstructed C++.
"""
import argparse, hashlib, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'uc-library/tools/recovery/accept_worker.py').exists())
PACKETS=ROOT/'temp/recovery-work/large02-network-owning03/batch02/packets'
INSPECTION=ROOT/'evidence/recovery/2026-10-28/uc-event-queue-lifecycle/inspection.json'
HISTORICAL_PRODUCER=ROOT/'uc-library/candidates/uc-event-queue-lifecycle/original_oracle.py'
BASE=0x1000000; OBJ=BASE+0x1000; SP=BASE+0xf000; STOP=BASE+0xff00

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def w32(u,a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
def r32(u,a):return struct.unpack('<I',u.mem_read(a,4))[0]

class Binary:
 def __init__(self,relative,expected):
  self.path=ROOT/relative;self.sha=sha(self.path);assert self.sha==expected
  self.raw=self.path.read_bytes()
  with self.path.open('rb') as f:
   e=ELFFile(f);self.sections=[dict(address=s['sh_addr'],offset=s['sh_offset'],size=s['sh_size'],name=s.name) for s in e.iter_sections()]
   self.segments=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
   self.syms={s.name:s['st_value'] for s in e.get_section_by_name('.symtab').iter_symbols()}
   self.symbol_sizes={s.name:s['st_size'] for s in e.get_section_by_name('.symtab').iter_symbols()}
  self.ranges=[];self.extra=[];self.vtables=[]
  for name in ['_ZTVN8Presonus2UC9EventItemE','_ZTVN4Core6VectorINS_7HashMapIiPN8Presonus2UC13IEventHandlerEE12TAssociationEEE']:
   a=self.syms[name];size=self.symbol_sizes[name];sec=next(s for s in self.sections if s['address']<=a and a+size<=s['address']+s['size']);off=sec['offset']+a-sec['address'];raw=self.raw[off:off+size]
   self.vtables.append(dict(mangled=name,address=a,size=size,section=sec['name'],file_offset=off,sha256=hashlib.sha256(raw).hexdigest(),words=list(struct.unpack('<'+'I'*(size//4),raw))))
  assert self.vtables[0]['words'][3]==self.address('_ZN8Presonus2UC9EventItemD0Ev')
  assert self.vtables[1]['words'][2]==self.address('_ZN4Core6VectorINS_7HashMapIiPN8Presonus2UC13IEventHandlerEE12TAssociationEED1Ev')
  inspection=json.loads(INSPECTION.read_text())
  meta=next(m for m in inspection['roles'].values() if m['original_elf_sha256']==self.sha)
  self.historical_source=meta['source']
  for f in meta['functions']:
   body=dict(address=f['address'],size=f['size'],section=f['section_name'],section_index=f['section'],file_offset=f['file_offset'],bytes_sha256=f['bytes_sha256'])
   self.verify(body,f['mangled']);self.extra.append(body)
 def verify(self,body,mangled):
  s=self.sections[body['section_index']];off=s['offset']+body['address']-s['address'];assert off==body['file_offset']
  assert hashlib.sha256(self.raw[off:off+body['size']]).hexdigest()==body['bytes_sha256']
  self.ranges.append(dict(mangled=mangled,**{k:body[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}))
 def address(self,name):
  if name in self.syms:return self.syms[name]
  return next(a for n,a in self.syms.items() if n.startswith(name+'@'))
 def run(self,ctor,dtor,n):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x1000,0xc00000);u.mem_map(BASE,0x10000)
  for a,b in self.segments:u.mem_write(a,b)
  hooks={};allocated={};next_alloc=0x2000000;trace=[];writes=[];calls=[];bucket_cleanup=[];stage='ctor';held=False;queue_sync=[];items={};executed_entries=[];observed_addresses=set();bucket_writes=[];item_writes=[]
  def reg():return u.reg_read(UC_ARM_REG_R0)
  def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  def allocate(size,label):
   nonlocal next_alloc
   p=next_alloc;next_alloc+=0x1000;u.mem_map(p,0x1000);allocated[p]=label;return p
  def release(p):
   if not p:return
   label=allocated.pop(p);u.mem_unmap(p,0x1000)
   try:u.mem_read(p,1)
   except UcError:pass
   else:raise AssertionError('native modeled runtime allocation not unmapped')
   trace.append(label)
  def core_lock_ctor():calls.append(['source_Core_lock_ctor',reg()-OBJ]);ret()
  def core_lock_dtor():
   off=reg()-OBJ;calls.append(['source_Core_lock_dtor',off]);trace.append(702 if off==0x68 else 700);ret()
  hooks[self.address('_ZN4Core7Threads8CoreLockC1Ev')]=core_lock_ctor
  hooks[self.address('_ZN4Core7Threads8CoreLockD1Ev')]=core_lock_dtor
  def new_array():
   size=reg();calls.append(['modeled_operator_new_array',size]);ret(allocate(size,1001))
  hooks[self.address('_Znaj')]=new_array
  def delete_array():release(reg());ret()
  hooks[self.address('_ZdaPv')]=delete_array
  def vector_resize():
   p=reg();size=u.reg_read(UC_ARM_REG_R1);calls.append(['source_Core_vector_resize',p-OBJ,size]);
   if size:
    assert p==OBJ+0x4c and size==4
    w32(u,p+4,allocate(16,1002));w32(u,p+12,4)
   ret(1)
  for name in ['_ZN4Core6VectorIiE6resizeEi','_ZN4Core6VectorIjE6resizeEi','_ZN4Core6VectorINS_7HashMapIiPN8Presonus2UC13IEventHandlerEE12TAssociationEE6resizeEi']:
   hooks[self.address(name)]=vector_resize
  def vector_dtor():
   p=reg()
   if p==OBJ+0x4c:release(r32(u,p+4))
   elif p==OBJ+0x30:release(r32(u,p+4))
   else:
    table=r32(u,OBJ+0x24);index=(p-table)//20;assert 0<=index<64
    bucket_cleanup.append(index);release(r32(u,p+4))
   ret()
  for name in ['_ZN4Core6VectorIiED1Ev','_ZN4Core6VectorIjED1Ev','_ZN4Core6VectorINS_7HashMapIiPN8Presonus2UC13IEventHandlerEE12TAssociationEED1Ev']:
   hooks[self.address(name)]=vector_dtor
  # The prior producer is reused only for its bound range/topology evidence.
  # Current execution enters the actual Queue D1/flush/retrieve and Item D0.
  def queue_lock():
   nonlocal held
   assert reg()==OBJ+0x68 and not held;held=True;queue_sync.append('lock');ret()
  def queue_unlock():
   nonlocal held
   assert reg()==OBJ+0x68 and held;held=False;queue_sync.append('unlock');ret()
  hooks[self.address('_ZN4Core7Threads8CoreLock4lockEv')]=queue_lock
  hooks[self.address('_ZN4Core7Threads8CoreLock6unlockEv')]=queue_unlock
  def item_delete():
   p=reg();assert p in items and not held
   assert r32(u,p)==self.address('_ZTVN8Presonus2UC9EventItemE')+8
   release(p);ret()
  hooks[self.address('_ZdlPv')]=item_delete
  def code(uc,a,size,_):
   if a==STOP:uc.emu_stop();return
   if a==self.address('_ZN8Presonus2UC9EventItemD0Ev'):
    p=reg();assert p in items and not held and r32(u,p+4)==r32(u,p+8)==0
    trace.append(100+items[p]);executed_entries.append(a)
   if a in hooks:hooks[a]();return
   observed_addresses.add(a)
   # Only original application ranges; no Core firmware body execution.
   assert any(b<=a<b+z for b,z in active_ranges),(hex(a),'outside bound app body')
  def write(uc,access,a,size,value,_):
   if OBJ<=a<OBJ+0x8c:writes.append(dict(stage=stage,offset=a-OBJ,size=size,value=value))
   for base,label in allocated.items():
    if label==1001 and base<=a<base+1288:bucket_writes.append(dict(stage=stage,offset=a-base,size=size,value=value))
    elif base in items and base<=a<base+64:item_writes.append(dict(item=items[base],offset=a-base,size=size,value=value))
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
  active_ranges=[(b['address'],b['size']) for b in [ctor,dtor]+self.extra]
  def execute(address):
   u.reg_write(UC_ARM_REG_SP,SP);u.reg_write(UC_ARM_REG_LR,STOP);u.reg_write(UC_ARM_REG_R0,OBJ)
   u.emu_start(address,STOP+4,count=200000);assert u.reg_read(UC_ARM_REG_PC)==STOP
  execute(ctor['address'])
  table=r32(u,OBJ+0x24)
  initialized=dict(hash_modulus=r32(u,OBJ+0x1c),buckets=r32(u,table-4),bucket_stride=r32(u,table-8),id_offset=r32(u,OBJ+0x60),id_delta=r32(u,OBJ+0x64),id_capacity=r32(u,OBJ+0x48),queue_empty=r32(u,OBJ+0x84)==r32(u,OBJ+0x88)==0)
  assert initialized==dict(hash_modulus=64,buckets=64,bucket_stride=20,id_offset=100,id_delta=128,id_capacity=128,queue_empty=True)
  assert len([c for c in calls if c[:1]==['source_Core_vector_resize'] and c[1]!=0x30 and c[1]!=0x4c])==64
  if n==-1:return dict(initialized=initialized,writes=writes,calls=calls)
  # Populate valid live CCL-source boundary state for normal destructor.
  w32(u,OBJ+0x34,allocate(20,600));w32(u,OBJ+0x38,1);w32(u,OBJ+0x3c,5)
  for index in [1,63]:
   p=table+20*index;w32(u,p+4,allocate(40,800+index));w32(u,p+8,1);w32(u,p+12,5)
  item_addresses=[]
  for i in range(n):
   p=allocate(64,200+i);items[p]=i;item_addresses.append(p);w32(u,p,self.address('_ZTVN8Presonus2UC9EventItemE')+8)
  for i,p in enumerate(item_addresses):
   w32(u,p+4,item_addresses[i+1]+4 if i+1<n else 0);w32(u,p+8,item_addresses[i-1]+4 if i else 0)
  w32(u,OBJ+0x84,item_addresses[0]+4 if n else 0);w32(u,OBJ+0x88,item_addresses[-1]+4 if n else 0)
  stage='dtor'
  execute(dtor['address'])
  assert bucket_cleanup==list(range(63,-1,-1))
  assert not allocated,allocated
  assert not held and queue_sync==['lock','unlock']*(n+1)
  assert r32(u,OBJ+0x84)==r32(u,OBJ+0x88)==0
  assert len(executed_entries)==n
  return dict(initialized=initialized,trace=trace,writes=writes,calls=calls,bucket_cleanup=bucket_cleanup,queue_sync=queue_sync,actual_item_D0_entries=executed_entries,executed_app_entries=sorted({b['address'] for b in [ctor,dtor]+self.extra}&observed_addresses),bucket_writes=bucket_writes,item_writes=item_writes)

def main():
 binaries={}
 for path,sha256 in [('rootfs/CS18_v13840/home/root/surface','304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'),('rootfs/RML16AI_Rack_13731/home/root/mixer','9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07')]:
  b=Binary(path,sha256);binaries[b.sha]=b
 targets={}
 for i in range(1,5):
  p=PACKETS/f'large02_net_dispatcher01_0{i}'/'native-context.json';d=json.loads(p.read_text())
  for key in d['roots']:
   m=d['nodes'][key]['metadata'];body=d['bodies'][key];b=binaries[m['elf']];b.verify(body,m['mangled']);targets[(m['elf'],m['mangled'])]=body
 cases=[]
 for sha256,b in binaries.items():
  for ci,di in [('C1','D1'),('C2','D2')]:
   c=targets[(sha256,'_ZN8Presonus2UC15EventDispatcher'+ci+'Ev')];d=targets[(sha256,'_ZN8Presonus2UC15EventDispatcher'+di+'Ev')]
   for n in [0,1,3,17]:cases.append(dict(elf_sha256=sha256,ctor=ci,dtor=di,count=n,observed=b.run(c,d,n)))
 return dict(version=1,binaries=[dict(path=str(b.path.relative_to(ROOT)),historical_source_path=b.historical_source,elf_sha256=b.sha,ranges=b.ranges,vtables=b.vtables) for b in binaries.values()],cases=cases,context_bindings=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in [INSPECTION,HISTORICAL_PRODUCER,ROOT/'evidence/recovery/2026-10-28/uc-event-queue-lifecycle/original-01/fixtures.json',ROOT/'evidence/recovery/2026-10-28/uc-event-queue-lifecycle/original-01/validation.json',ROOT/'temp/recovery-work/large02-network-owning03/expansions/queue-cs18-01/native-context.json',ROOT/'temp/recovery-work/large02-network-owning03/expansions/queue-rm-01/native-context.json',ROOT/'evidence/recovery/2026-11-04/dependency-graph/large02-network-owning03/PROVIDER_REUSE_REVIEW01.json']],historical_reuse='Prior producer/range/topology evidence, not attributed as a fresh old-producer run. Current oracle executes original Queue/Item instructions and physically unmaps each guest item at real original D0 allocator call; previous logging-only delete boundary is not reused as deallocation proof.',unicorn_version=__import__('unicorn').__version__)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();Path(a.out).write_text(json.dumps(main(),indent=2)+'\n')
