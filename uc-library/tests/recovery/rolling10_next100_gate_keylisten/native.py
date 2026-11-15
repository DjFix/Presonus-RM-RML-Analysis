import hashlib,json,struct,subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4]
EXE=R/'temp/recovery-work/rolling10_next100_gate_keylisten/replay'
ELF=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared06/snapshot/rootfs/CS18_v13840/home/root/surface')
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
NAME='_ZN8Presonus7Surface17GatePageComponent11onKeyListenEb'
def generate():
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 with ELF.open('rb') as f:
  e=ELFFile(f);s=next(x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name==NAME);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];body=data[off:off+s['st_size']];assert (s['st_value'],s['st_size'],hashlib.sha256(body).hexdigest())==(579964,84,'286c5f37ab931fec6412d7948cae281d96ade46c187daef255694b6cde123fe1')
  def raw(a,n):
   sec=next(z for z in e.iter_sections() if z['sh_addr']<=a and a+n<=z['sh_addr']+z['sh_size'] and z['sh_type']!='SHT_NOBITS');return data[sec['sh_offset']+a-sec['sh_addr']:sec['sh_offset']+a-sec['sh_addr']+n]
  literal=raw(1700296,14);assert literal==b'ch_key_listen\0';assert hashlib.sha256(literal).hexdigest()=='6e65830ffcdbbeef2b1d4fdd62538b69ee1e648e3f6d86235579c74e2dd35c24'
  gate=raw(1705928,136);numeric=raw(2118056,128)
  assert hashlib.sha256(gate).hexdigest()=='e343e1f8a224a72b9e05246d360110b99e6f658aa5245a6ab3cc409db5831495'
  assert hashlib.sha256(numeric).hexdigest()=='a344a8b1f9c2b18928687658fae5f83bc3a196a213b7a0b48cad61f5dea7dbeb'
  lookup=struct.unpack_from('<I',gate,8+6*4)[0];setter=struct.unpack_from('<I',numeric,8+22*4)[0];assert (lookup,setter)==(1158360,1184152)
 cases=[]
 inputs=[(p,b,v) for p in [0,1] for b in [0,1] for v in [-1,0,0.5,1]]
 payload=''.join(f'{p} {b} {v}\n' for p,b,v in inputs)
 provider=subprocess.check_output([str(EXE),'--provider'],input=payload,text=True).splitlines();assert len(provider)==len(inputs)
 for (present,enabled,initial),observed in zip(inputs,provider):
  actual=observed.split();found=int(actual[0]);u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000);u.mem_write(s['st_value'],body);u.mem_write(1700296,literal)
  def put(a,v):u.mem_write(a,struct.pack('<I',v))
  put(0x400000,0x410000);put(0x410018,lookup);put(0x420000,0x430000);put(0x430058,setter)
  trace=[];sites=[];writes=[]
  def code(u,a,n,_):
   if s['st_value']<=a<s['st_value']+s['st_size']:sites.append(a);return
   if a==lookup:
    assert u.reg_read(UC_ARM_REG_R0)==0x400000;addr=u.reg_read(UC_ARM_REG_R1);assert bytes(u.mem_read(addr,14))==literal
    trace.append(['findParameter','ch_key_listen',found]);u.reg_write(UC_ARM_REG_R0,0x420000 if found else 0)
   elif a==setter:
    assert u.reg_read(UC_ARM_REG_R0)==0x420000
    bits=u.reg_read(UC_ARM_REG_R1);edit=u.reg_read(UC_ARM_REG_R2);trace.append(['setValue',bits,edit]);assert bits==(0x3f800000 if enabled else 0) and edit==1
   else:raise RuntimeError(hex(a))
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,lambda u,k,a,n,v,_:writes.append([a,n,v]))
  for reg,val in [(UC_ARM_REG_R0,0x400000),(UC_ARM_REG_R1,enabled),(UC_ARM_REG_SP,0x801000),(UC_ARM_REG_LR,0xf00000),(UC_ARM_REG_R4,0x12345678)]:u.reg_write(reg,val)
  u.emu_start(s['st_value'],0xf00000,count=100);assert u.reg_read(UC_ARM_REG_PC)==0xf00000;assert u.reg_read(UC_ARM_REG_SP)==0x801000 and u.reg_read(UC_ARM_REG_R4)==0x12345678
  assert len(trace)==1+found;nonstack=[w for w in writes if not 0x800000<=w[0]<0x801000];assert not nonstack
  cases.append(dict(stdin=f'{present} {enabled} {initial}',stdout=observed,sites=sites,trace=trace,nonstack_writes=nonstack))
 return dict(elf_sha256=SHA,ranges=[dict(mangled=NAME,address=s['st_value'],size=s['st_size'],section=sec.name,file_offset=off,sha256=hashlib.sha256(body).hexdigest())],cases=cases,provider='Actual pinned CCL Component::findParameter / NumericParam::setValue through independent executable --provider branch; no reconstructed method called; firmware Core bodies excluded',literal_sha256=hashlib.sha256(literal).hexdigest())
if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
