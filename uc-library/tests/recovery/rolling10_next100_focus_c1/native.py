import json,hashlib,struct,subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import *
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4];T=Path(__file__).parent;TASK=T.name;VARIANT=TASK.rsplit('_',1)[1];SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
B=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114');SNAP=B/'prepared-idle-refill-proposed01/snapshot';PACKET=R/'temp/recovery-work/rolling10x10-20261114/prepared-idle-refill-proposed01/packets'/TASK

def inventory(exe):return [list(map(int,l.split())) for l in subprocess.check_output([str(exe),'--provider'],text=True).splitlines()]
def generate(provider=None, forced_variant=None):
 variant=forced_variant or VARIANT
 if provider is None:provider=json.loads((T/'fixtures.json').read_text())['provider_observations']
 req=json.loads((PACKET/'request.json').read_text());target=req['targets'][0];contract=SNAP/req['reconstruction_contract']['path'];assert hashlib.sha256(contract.read_bytes()).hexdigest()==req['reconstruction_contract']['sha256'];cj=json.loads(contract.read_text());evidences={}
 for scope in cj['requirements'].values():
  for item in scope['evidence']:
   p=SNAP/item['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
   if item['kind']=='native_observation':evidences[item['path']]=json.loads(p.read_text())
 bodies={x['original']['original_mangled']:x['verified_body'] for x in evidences.values() if 'verified_body' in x}
 path=SNAP/'rootfs/CS18_v13840/home/root/surface';raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 with path.open('rb') as f:
  elf=ELFFile(f);symbols={s.name:s for s in elf.get_section_by_name('.symtab').iter_symbols()};ranges=[]
  for name,body in bodies.items():
   sym=symbols[name];sec=elf.get_section(sym['st_shndx']);offset=sec['sh_offset']+sym['st_value']-sec['sh_addr'];assert (sym['st_value'],sym['st_size'],offset)==(body['address'],body['size'],body['file_offset']);assert hashlib.sha256(raw[offset:offset+body['size']]).hexdigest()==body['bytes_sha256'];ranges.append(dict(mangled=name,**body))
  corevt=symbols['_ZTVN4Core8Portable13ContainerViewE'];sec=elf.get_section(corevt['st_shndx']);off=sec['sh_offset']+corevt['st_value']-sec['sh_addr'];getroot=struct.unpack_from('<I',raw,off+8+0x14)[0]
  rootvt=symbols['_ZTVN4Core8Portable8RootViewE'];sec=elf.get_section(rootvt['st_shndx']);off2=sec['sh_offset']+rootvt['st_value']-sec['sh_addr'];setfocus=struct.unpack_from('<I',raw,off2+8+0x70)[0]
 NAME=('_ZN8Presonus13FocusRestorerC'+variant[1]+'ERN4Core8Portable13ContainerViewE') if variant.startswith('c') else ('_ZN8Presonus13FocusRestorerD'+variant[1]+'Ev');body=bodies[NAME];cases=[]
 for row in provider:
  case,has_initial_root,has_initial_focus,has_current_root,found,before,*snapshot=row;state=snapshot[:7];namebytes=bytes(snapshot[7:39]);assert len(namebytes)==32
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x2000000)
  for b in bodies.values():u.mem_write(b['address'],raw[b['file_offset']:b['file_offset']+b['size']])
  obj,container,cvtable,rvtable,initialroot,currentroot,view=0x400000,0x410000,0x420000,0x421000,0x430000,0x430000 if case not in [7,10] else 0x440000,0x500000
  put=lambda a,v:u.mem_write(a,struct.pack('<I',v&0xffffffff));get=lambda a:struct.unpack('<I',u.mem_read(a,4))[0]
  u.mem_write(obj,b'\xa5'*128);put(container,cvtable);put(cvtable+0x14,getroot)
  for root in [initialroot,currentroot]:put(root,rvtable)
  put(rvtable+0x70,setfocus);u.mem_write(view+8,namebytes);u.mem_write(0x510000,struct.pack('<iiii',10,10,100,100))
  if variant.startswith('d'):
   put(obj,container);u.mem_write(obj+4,struct.pack('<7I',*state));u.mem_write(obj+32,namebytes)
  trace=[];sites=[];writes=[]
  def ret(value=None):
   if value is not None:u.reg_write(UC_ARM_REG_R0,value)
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  def hook(u,a,n,_):
   if a==0x1f00000:u.emu_stop();return
   if any(b['address']<=a<a+n<=b['address']+b['size'] for b in bodies.values()):sites.append(a);return
   r0,r1,r2,r3=[u.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
   if a==getroot:
    assert r0==container;trace.append(['root',case]);ret((initialroot if has_initial_root else 0) if variant.startswith('c') else (currentroot if has_current_root else 0))
   elif a==0x10ef80:
    assert r0==initialroot;trace.append(['focus']);ret(view if has_initial_focus else 0)
   elif a==0x24268:
    assert r0==obj+32 and r1==0;trace.append(['empty-name']);u.mem_write(r0,b'\0');ret(r0)
   elif a==0x10e9bc:
    assert r0==view and r1==obj+8;trace.append(['client-rect']);u.mem_write(r1,struct.pack('<4I',*state[1:5]));ret(r1)
   elif a==0x10e9a8:
    assert r0==view;trace.append(['size']);ret(0x510000)
   elif a==0x10e928:
    assert r0==view and r1==obj+24;trace.append(['client-to-root']);u.mem_write(r1,struct.pack('<2I',*state[5:7]));ret()
   elif a==0x111be8:
    assert r0==currentroot and r1==obj+24 and r2==1;assert list(struct.unpack('<2I',u.mem_read(r1,8)))==state[5:7];assert get(r3+4)==obj+4;trace.append(['find-point',state[5],state[6],1]);ret(0x600000+found*0x100 if found else 0)
   elif a==setfocus:
    assert r0==currentroot and r1==0x600000+found*0x100 and found;trace.append(['set-focus',found]);ret()
   else:raise RuntimeError(hex(a))
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,lambda u,ac,a,n,v,_:writes.append([a,n,v]))
  for reg,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,container),(UC_ARM_REG_SP,0x8ff000),(UC_ARM_REG_LR,0x1f00000)]:u.reg_write(reg,v)
  u.emu_start(body['address'],0x1f00000,count=400);assert u.reg_read(UC_ARM_REG_PC)==0x1f00000, ('native did not return before instruction budget', hex(u.reg_read(UC_ARM_REG_PC)));assert u.reg_read(UC_ARM_REG_SP)==0x8ff000
  if variant.startswith('c'):
   actualstate=list(struct.unpack('<7I',u.mem_read(obj+4,28)));assert actualstate==state;actualname=bytes(u.mem_read(obj+32,32));assert actualname==namebytes if has_initial_focus else actualname[0]==0;assert get(obj)==container
  else:assert not any(obj<=w[0]<obj+128 for w in writes)
  cases.append(dict(case=case,terminal_pc=u.reg_read(UC_ARM_REG_PC),terminal_sp=u.reg_read(UC_ARM_REG_SP),returned=True,trace=trace,sites=sites,object_writes=[w for w in writes if obj<=w[0]<obj+128],stack_writes=[w for w in writes if 0x8fe000<=w[0]<0x8ff000]))
 return dict(elf_sha256=SHA,mangled=NAME,target_range={k:body[k] for k in ['address','size','section','file_offset','bytes_sha256']},native_ranges=ranges,provider_observations=provider,cases=cases,boundary='Native target and original FocusInfo helpers execute; actual CCL provider geometry/getter/find observations bridge only Core calls. Destructor FindFilter construction is observed raw vtable+snapshot pointer; original helper matches compatibility replay separate. No cached old root, original Core execution, D0 or deallocation claim.')
if __name__=='__main__':
 import sys
 Path(sys.argv[2]).write_text(json.dumps(generate(inventory(sys.argv[1])),indent=2)+'\n')
