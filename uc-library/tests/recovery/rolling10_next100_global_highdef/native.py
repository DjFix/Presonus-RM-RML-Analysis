import json,hashlib,struct,random,subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import *
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4];T=Path(__file__).parent;SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07';NAME='_ZN8Presonus5Mixer15GlobalComponent13updateHighDefEv';ADDRESS=296288;SIZE=100

def inputs():
 values=[0,0x80000000,0x3f800000,0x3fffffff,0x40000000,0x40000001,0xc0000000,0x7f800000,0xff800000,0x7fc00000,0x7f800001,0xffc00001,1,0x7f7fffff]+[random.Random(i).getrandbits(32) for i in range(24)]
 return [[b,m] for b in values for m in range(4)]
def inventory(exe):return [list(map(int,l.split())) for l in subprocess.check_output([str(exe),'--inventory'],input=''.join(f'{b} {m}\n' for b,m in inputs()),text=True).splitlines()]
def generate(provider_inventory=None):
 if provider_inventory is None:provider_inventory=json.loads((T/'fixtures.json').read_text())['provider_inventory']
 binding=json.loads((R/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared06-rolling10_surface_input.json').read_text());path=Path(binding['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path']);data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 frozen=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared06/snapshot');evidencepath='temp/recovery-work/rolling10x10-20261114/selection/next100/numeric-state-methods01/native/rolling10_next100_global_highdef.json';raw=(frozen/evidencepath).read_bytes();evidence=json.loads(raw)
 # This typed evidence is hash-bound by the sealed request contract.
 request=json.loads((R/'temp/recovery-work/rolling10x10-20261114/prepared06/packets/rolling10_next100_global_highdef/request.json').read_text());contractpath=request['reconstruction_contract']['path']
 contract=json.loads((frozen/contractpath).read_text());references=[x for d in contract['requirements'].values() for x in d['evidence'] if x['path']==evidencepath];assert references and all(hashlib.sha256(raw).hexdigest()==x['sha256'] for x in references)
 with path.open('rb') as f:
  e=ELFFile(f);symbols=list(e.get_section_by_name('.symtab').iter_symbols());s=next(x for x in symbols if x.name==NAME);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+ADDRESS-sec['sh_addr'];body=data[off:off+SIZE];assert s['st_value']==ADDRESS and s['st_size']==SIZE and hashlib.sha256(body).hexdigest()=='55cd1d3ba590f47ba47360f646fb9dc226de8bf1fbbd2827267fa5c261a44387'
  helpers=[]
  for item in evidence['original_nonCore_helpers'].values():
   b=item['body'];ident=item['identity'];p=data[b['file_offset']:b['file_offset']+b['size']];assert hashlib.sha256(p).hexdigest()==b['bytes_sha256'];sym=next(x for x in symbols if x.name==ident['mangled']);assert sym['st_value']==b['address'] and sym['st_size']==b['size'];helpers.append(dict(mangled=ident['mangled'],address=b['address'],size=b['size'],file_offset=b['file_offset'],sha256=b['bytes_sha256']))
  v=evidence['numeric_vtable'];vbody=data[v['file_offset']:v['file_offset']+v['size']];assert hashlib.sha256(vbody).hexdigest()==v['sha256'];getter=struct.unpack_from('<I',vbody,8+0x44)[0];setter=struct.unpack_from('<I',vbody,8+0x58)[0]
  segments=[(x['p_vaddr'],x.data()) for x in e.iter_segments() if x['p_type']=='PT_LOAD']
 cases=[]
 assert len(provider_inventory)==len(inputs())
 for inp,row in zip(inputs(),provider_inventory):
  bits,mode,has_source,has_dest,alias,initial=row;assert mode==inp[1]
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000)
  for a,b in segments:u.mem_write(a,b)
  put=lambda a,v:u.mem_write(a,struct.pack('<I',v));src=0x500000 if has_source else 0;dst=(0x500000 if alias else 0x500100) if has_dest else 0
  put(0x40008c,src);put(0x400090,dst);put(0x500000,0x510000);put(0x500100,0x510000);put(0x510044,getter);put(0x510058,setter);trace=[];sites=[];hsites=[];writes=[]
  def hook(u,a,n,_):
   if a==0xf00000:u.emu_stop();return
   if ADDRESS<=a<ADDRESS+SIZE:sites.append(a);return
   if any(x['address']<=a<x['address']+x['size'] for x in helpers):hsites.append(a);return
   if a==getter:
    assert u.reg_read(UC_ARM_REG_R0)==src;trace.append(['get',src,bits]);u.reg_write(UC_ARM_REG_R0,bits)
   elif a==setter:
    assert u.reg_read(UC_ARM_REG_R0)==dst;trace.append(['set',dst,u.reg_read(UC_ARM_REG_R1),u.reg_read(UC_ARM_REG_R2)])
   else:raise RuntimeError(hex(a))
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,lambda u,ac,a,n,v,_:writes.append([a,n,v]))
  for reg,value in [(UC_ARM_REG_R0,0x400000),(UC_ARM_REG_SP,0x8ff000),(UC_ARM_REG_LR,0xf00000)]:u.reg_write(reg,value)
  u.emu_start(ADDRESS,0xf00000,count=500);assert all(0x8fe000<=w[0]<0x8ff000 for w in writes)
  cases.append(dict(input=inp,trace=trace,sites=sorted(set(sites)),helper_sites=sorted(set(hsites)),writes=writes))
 return dict(elf_sha256=SHA,mangled=NAME,address=ADDRESS,size=SIZE,file_offset=off,section='.text',range_sha256=hashlib.sha256(body).hexdigest(),helper_ranges=helpers,numeric_vtable=v,provider_inventory=provider_inventory,cases=cases,boundary='Actual CCL NumericParam source getter observations feed Core boundary only; original non-Core float comparison closure executes. Native setter trace drives actual CCL independent setter reference including events/alias state; no original Core instructions execute.')
if __name__=='__main__':
 import sys
 Path(sys.argv[2]).write_text(json.dumps(generate(inventory(sys.argv[1])),indent=2)+'\n')
