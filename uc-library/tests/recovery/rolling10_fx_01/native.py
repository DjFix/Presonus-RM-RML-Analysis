#!/usr/bin/env python3
"""Independent bounded original ARM execution, no reconstructed source imports."""
import argparse, hashlib, io, json, random, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
T=Path(__file__).resolve().parent
R=T.parents[3]
TASK=T.name
PACKET=R/'temp/recovery-work/rolling10x10-20261114/prepared05/packets'/TASK
READS=json.loads((R/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-rolling10_fx.json').read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def generate():
 t=json.loads((PACKET/'request.json').read_text())['targets'][0]
 raw=Path(READS['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path']).read_bytes()
 assert sha(raw)==t['original_elf_sha256']
 elf=ELFFile(io.BytesIO(raw))
 def get(addr,n):
  sec=next(s for s in elf.iter_sections() if s['sh_type']!='SHT_NOBITS' and s['sh_addr']<=addr<addr+n<=s['sh_addr']+s['sh_size'])
  off=sec['sh_offset']+addr-sec['sh_addr'];return raw[off:off+n],sec.name,off
 def string(addr):
  b=bytearray()
  for i in range(256):
   c=get(addr+i,1)[0]
   if c==b'\0':break
   b+=c
  else:raise AssertionError('unterminated string')
  data=bytes(b)+b'\0';return {'address':addr,'size':len(data),'sha256':sha(data),'text':bytes(b).decode('ascii'),'section':get(addr,len(data))[1],'file_offset':get(addr,len(data))[2]}
 sym=next(s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name==t['mangled'])
 assert (sym['st_value'],sym['st_size'])==(t['address'],t['size'])
 start,size=t['address'],t['size'];body,section,offset=get(start,size)
 assert section=='.text' and sym['st_shndx']==t['section']
 kind={'rolling10_fx_01':'identity','rolling10_fx_02':'constant','rolling10_fx_03':'table'}.get(TASK,'network')
 rng=random.Random(71114)
 inputs=([0,1,2,3,9,16,0x7fffffff,0x80000000,0xffffffff]+[rng.getrandbits(32) for _ in range(128)]) if kind=='identity' else list(range(8))
 rows=[];data_ranges=[];table=[]
 for obj in [0x2000100,0x2000300]:
  for arg in inputs:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
   u.mem_map(start&~4095,8192);u.mem_write(start,body)
   u.mem_map(0x2000000,4096);u.mem_map(0x3000000,4096)
   initial=bytes((i+arg)%256 for i in range(4096));u.mem_write(0x2000000,initial)
   sp=0x3000800;stop=0x4000000;u.mem_map(stop,4096)
   port=0x2000800;info=0x2000900;pcs=[];writes=[]
   def code(uc,pc,n,d):
    if pc==stop:uc.emu_stop();return
    assert start<=pc<start+size,hex(pc)
    pcs.append(pc)
   def write(uc,access,addr,n,value,d):
    assert sp-16<=addr and addr+n<=sp or kind=='network' and ((port<=addr and addr+n<=port+2) or (info<=addr and addr+n<=info+24)),(addr,n)
    writes.append([addr,n,value & ((1<<(8*n))-1)])
   u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
   u.reg_write(UC_ARM_REG_CPSR,0x10);u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,stop)
   u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,port if kind=='network' else arg);u.reg_write(UC_ARM_REG_R2,info)
   u.emu_start(start,stop+4,count=32)
   assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==sp
   actual=bytes(u.mem_read(0x2000000,4096));expected_unchanged=bytearray(initial)
   if kind=='network':
    expected_unchanged[port-0x2000000:port-0x2000000+2]=actual[port-0x2000000:port-0x2000000+2]
    for o in [4,12]:expected_unchanged[info-0x2000000+o:info-0x2000000+o+4]=actual[info-0x2000000+o:info-0x2000000+o+4]
   assert actual==bytes(expected_unchanged)
   result=u.reg_read(UC_ARM_REG_R0)
   row={'input':[obj,arg], 'r0':result,'pcs':pcs,'writes':writes,'stack_restored':True,'unmodified_bytes_preserved':True,'external_calls':[]}
   if kind=='network':
    out=bytes(u.mem_read(info,24));portvalue=struct.unpack('<H',u.mem_read(port,2))[0]
    ptr0,ptr2=struct.unpack_from('<I',out,4)[0],struct.unpack_from('<I',out,12)[0]
    row['expected']={'port':portvalue,'name':string(ptr0)['text'],'guid':string(ptr2)['text']}
    row['initial_info_hex']=initial[info-0x2000000:info-0x2000000+24].hex();row['final_info_hex']=out.hex()
    if not data_ranges:data_ranges=[string(ptr0),string(ptr2)]
   rows.append(row)
 if kind=='table':
  addresses={x['r0'] for x in rows};assert len(addresses)==1
  addr=addresses.pop();b,sec,off=get(addr,480)
  assert sha(b)=='debc51f2fbf0b67fdc8ceca7aa44e7cebc0547c50af87113581d996e6c71f5e6'
  data_ranges=[dict(address=addr,size=480,sha256=sha(b),section=sec,file_offset=off)]
  for i in range(24):
   family,index,effect,value,ptr=struct.unpack_from('<iiIII',b,i*20)
   text=string(ptr);data_ranges.append(text)
   table.append(dict(family=family,index=index,effect_bits=effect,value_bits=value,name=text['text']))
 return dict(task_id=TASK,kind=kind,elf_sha256=sha(raw),mangled=t['mangled'],address=start,size=size,section=section,file_offset=offset,range_sha256=sha(body),producer_sha256=sha(Path(__file__).read_bytes()),unicorn_version=unicorn.__version__,cases=rows,table=table,data_ranges=data_ranges,limitations='Only exact app body executed. Stack writes recorded; caller object unchanged. No original static return declaration, inheritance/layout, ARM interoperability or hardware proof; normalized table/string pointers are relocations, not numeric pointer equality.')
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(generate(),indent=2)+'\n');print(out)
if __name__=='__main__':main()
