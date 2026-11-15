"""Exact original app ARM execution, with explicit source-provider boundaries.
No firmware Core body executes. Native writes and boundary args remain fixtures.
"""
import hashlib,itertools,json,pathlib,struct,datetime,subprocess
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,__version__
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4];NAME=pathlib.Path(__file__).parent.name
PROVIDER_CACHE={}
PACKET=pathlib.Path('temp/recovery-work/rolling10x10-20261114/prepared06/packets')/NAME
class Native:
 def __init__(self):
  self.req=json.loads((ROOT/PACKET/'request.json').read_text());t=self.req['targets'][0];self.sha=t['original_elf_sha256']
  mapping=json.loads((ROOT/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared06-rolling10_mixer_base.json').read_text())
  match=next(v for k,v in mapping.items() if v['sha256']==self.sha and k.startswith('rootfs/'));p=pathlib.Path(match['frozen_read_path']);raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==self.sha
  j=json.loads((ROOT/PACKET/'native-context.json').read_text());self.body=j['bodies'][j['roots'][0]];b=self.body
  self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM);self.u.mem_map(0,0x600000)
  with p.open('rb') as f:
   e=ELFFile(f)
   for s in e.iter_sections():
    a,n,o=s['sh_addr'],s['sh_size'],s['sh_offset']
    if a and a+n<0x600000 and s['sh_type']!='SHT_NOBITS':self.u.mem_write(a,raw[o:o+n])
   s=e.get_section(b['section_index']);assert s.name==b['section'];assert s['sh_offset']+b['address']-s['sh_addr']==b['file_offset']
  assert hashlib.sha256(raw[b['file_offset']:b['file_offset']+b['size']]).hexdigest()==b['bytes_sha256']
  self.u.mem_map(0x1000000,0x40000);self.u.mem_map(0x1100000,0x10000);self.u.mem_map(0x1200000,0x1000)
  self.u.hook_add(UC_HOOK_CODE,self.hook);self.u.hook_add(UC_HOOK_MEM_WRITE,self.write)
  self.vtable=None
  if 'fatled' in NAME or 'monitor_radio' in NAME:
   snap=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared06/snapshot')
   c=self.req['reconstruction_contract'];cb=(snap/c['path']).read_bytes();assert hashlib.sha256(cb).hexdigest()==c['sha256'];contract=json.loads(cb)
   ev=contract['dependencies'][0]['evidence'][0];eb=(snap/ev['path']).read_bytes();assert hashlib.sha256(eb).hexdigest()==ev['sha256'];j=json.loads(eb)
   if 'fatled' in NAME:
    v=j['verified_original_vtable'];self.vtable=v;self.setvalue=v['slots']['22'];address=v['address'];n=v['size'];off=v['file_offset'];sha=v['bytes_sha256']
   else:
    v=j['numeric_vtable'];self.vtable=v;self.setvalue=v['slots']['22'];address=v['address'];n=v['size'];off=v['file_offset'];sha=v['sha256']
   assert hashlib.sha256(raw[off:off+n]).hexdigest()==sha
   # address point follows offset-to-top and RTTI entries. Verify actual slot.
   assert struct.unpack('<I',raw[off+8+22*4:off+12+22*4])[0]==self.setvalue
   self.vt=address+8
 def w(self,a,v):self.u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def write(self,u,access,a,size,value,data):
  if 0x1000000<=a<0x1040000:self.writes.append([a,size,value])
 def hook(self,u,a,size,data):
  if a==0x1200000:u.emu_stop();return
  b=self.body
  if b['address']<=a<b['address']+b['size']:
   self.visited.add(a);return
  r0,r1,r2=[u.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2]]
  if a==0x3928c and 'mixer_base' in NAME:
   self.trace.append(['resize',r1,not self.case['fail']]);u.reg_write(UC_ARM_REG_R0,int(not self.case['fail']))
   if not self.case['fail']:self.w(r0+12,r1)
  elif a==0x11acf0 and 'monitor_radio' in NAME:
   tag=struct.unpack('<i',struct.pack('<I',r1))[0];ptr=self.by_tag.get(tag,0);self.trace.append(['lookup',tag,self.tags_by_ptr.get(ptr)]);u.reg_write(UC_ARM_REG_R0,ptr)
  elif self.vtable and a==self.setvalue:
   identity=self.tags_by_ptr[r0];self.trace.append(['setValue',identity,r1,r2])
  else:raise RuntimeError('Unbound execution '+hex(a))
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def execute(self,c):
  self.case=c;self.trace=[];self.writes=[];self.visited=set();self.u.mem_write(0x1000000,bytes(0x40000));self.by_tag={};self.tags_by_ptr={}
  if 'mixer_base' in NAME:
   self.w(0x1000090,0x1010000);self.w(0x1000094,len(c['seed']));self.w(0x1000098,c['capacity'])
   for i,v in enumerate(c['seed']):self.w(0x1010000+4*i,v)
   args=[0x1000000,c['pointer'],0,0]
  else:
   for i,tag in enumerate(c.get('tags',[0])):
    ptr=0x1001000+0x100*i;info=0x1020000+0x100*i;self.w(ptr,self.vt);self.w(ptr+12,info);self.w(info+4,tag);self.by_tag.setdefault(tag,ptr);self.tags_by_ptr[ptr]=i
   if 'fatled' in NAME:
    self.w(0x100011c,0x1001000 if c['present'] else 0);args=[0x1000000,0,0,0]
   else:
    # Query the actual CCL registry independently, not application behavior.
    key=tuple(c['tags'])
    if key not in PROVIDER_CACHE:
     line=' '.join(map(str,[0,-3,4,len(key),0,0,*key]))+'\n'
     exe=ROOT/'temp/recovery-work'/NAME/'replay'
     result=subprocess.run([str(exe),'--lookup'],input=line,text=True,capture_output=True,check=True)
     fields=result.stdout.split();offset=len(key)+2;assert int(fields[offset])==8
     PROVIDER_CACHE[key]=list(map(int,fields[offset+1:]));assert len(PROVIDER_CACHE[key])==8
    self.by_tag={tag:(0x1001000+0x100*index if index>=0 else 0) for tag,index in zip(range(-3,5),PROVIDER_CACHE[key])}
    # selected is independent of registry identity but has a stable actual tag.
    selected=0x1030000;self.w(selected+12,selected+0x100);self.w(selected+0x104,c['selected']);args=[0x1000000,selected,c['first'],c['last']]
  for reg,val in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):self.u.reg_write(reg,val&0xffffffff)
  self.u.reg_write(UC_ARM_REG_SP,0x1108000);self.u.reg_write(UC_ARM_REG_LR,0x1200000);self.u.emu_start(self.body['address'],0x1200004,count=100000)
  d={'input':c,'trace':self.trace,'writes':self.writes,'visited':sorted(self.visited)}
  if 'mixer_base' in NAME:d['items']=[self.r(0x1010000+4*i) for i in range(self.r(0x1000094))]
  return d

def generate():
 n=Native();cases=[]
 if 'mixer_base' in NAME:
  for seed in [[],[0],[1],[1,1],[1,0,2]]:
   for cap in sorted({len(seed),len(seed)+1,len(seed)+3}):
    for pointer,fail in itertools.product([0,1,2],[False,True]):cases.append(n.execute(dict(seed=seed,capacity=cap,pointer=pointer,fail=fail)))
  domain='Borrowed opaque channel identities only (never dereferenced), null/duplicates retained in order; seeds 0..3, capacity count/count+1/count+3, success/failure resize boundary. Real CCL Vector uses unit delta in replay; native allocator growth/layout unclaimed.'
 elif 'fatled' in NAME:
  for present,initial,minv,maxv in itertools.product([False,True],[-2,0,0.25,1,2],[0,0.5],[1,2]):cases.append(n.execute(dict(present=present,initial=initial,min=minv,max=maxv)))
  domain='Null or actual borrowed NumericParam, finite initial values -2,0,.25,1,2 and bounds [0/.5,1/2]; original setter slot22 independently verified; setValue(0,false), no Core binary execution or unknown override.'
 else:
  for tags in [[],[0],[1,3],[3,1],[1,1,2],[-2,-1,0,1,2]]:
   for first,last in [(-2,2),(0,0),(1,3),(3,1),(-3,-1)]:
    for selected in [-3,-2,-1,0,1,2,3,4]:cases.append(n.execute(dict(tags=tags,first=first,last=last,selected=selected)))
  domain='Non-null NumericParam selected with stable tag, real Component registry; tags sparse/dense, duplicate tags resolved by independently executed actual CCL registry, negative tags, empty registry, valid/inverted ranges and selected outside; bounded finite interval -3..4 excludes int32 increment overflow, reentrant mutations and unknown virtual overrides.'
 return {'task_id':NAME,'elf_sha256':n.sha,'range':n.body,'vtable':n.vtable,'provider_lookup_observations':[{'tags':list(k),'interval':[-3,4],'indices':v} for k,v in sorted(PROVIDER_CACHE.items())],'emulator_version':__version__,'cases':cases,'boundary_scope':domain,'core_scope':'Original Core bodies excluded. Captured provider call arguments; actual source-provider replay independently applies those captured arguments.'}
if __name__=='__main__':
 (ROOT/'uc-library/tests/recovery'/NAME/'fixtures.json').write_text(json.dumps(generate(),indent=2)+'\n')
