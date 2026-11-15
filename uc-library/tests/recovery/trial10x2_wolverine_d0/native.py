#!/usr/bin/env python3
"""Execute only exact Wolverine ARM destructor; real host providers handle boundaries."""
import hashlib,io,json,struct,subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent;TASK=T.name
PACKET=R/'temp/recovery-work/trial10x2-20261115/prepared01/packets'/TASK
READ=R/'temp/recovery-work/trial10x2-20261115/READ_INPUTS-prepared01-trial10x2_wolverine.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def generate(exe):
 target=json.loads((PACKET/'request.json').read_text())['targets'][0]
 raw=Path(json.loads(READ.read_text())['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path']).read_bytes()
 assert hashlib.sha256(raw).hexdigest()==target['original_elf_sha256']
 e=ELFFile(io.BytesIO(raw));syms=list(e.get_section_by_name('.symtab').iter_symbols());s=next(s for s in syms if s.name==target['mangled']);sec=e.get_section(s['st_shndx']);offset=sec['sh_offset']+s['st_value']-sec['sh_addr'];body=raw[offset:offset+s['st_size']]
 variant=int(TASK.endswith('_d0'));expected=['9fdf11f1308ed8e138dd042b42f199556e041904a7a52c7959243d5511c4f572','446f62a424443f2ed51c54f31f61c4c3c615fee5ac656be4012b1728a4f46588'][variant]
 assert (s['st_value'],s['st_size'],s['st_shndx'],hashlib.sha256(body).hexdigest())==(target['address'],target['size'],12,expected)
 base=next(x for x in syms if x.name=='_ZN8Presonus5Panel18RackPanelComponentD2Ev');delete=0xac10
 assert base['st_value']==0x7e824
 rows=[]
 for count in [1,2,5,16,64]:
  for location in [0x2000100,0x2000500]:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
   for a in [s['st_value']&~4095,base['st_value']&~4095,delete&~4095,0x2000000,0x3000000,0x4000000]:u.mem_map(a,4096)
   u.mem_write(s['st_value'],body);u.mem_write(0x2000000,b'\xa5'*4096)
   sp=0x3000800;stop=0x4000000;calls=[];writes=[];pcs=[]
   def hook(uc,pc,n,d):
    if pc==stop:uc.emu_stop();return
    if pc in [base['st_value'],delete]:
     assert uc.reg_read(UC_ARM_REG_R0)==location
     calls.append('base' if pc==base['st_value'] else 'delete')
     # Provider boundary is fulfilled below by genuine host lifecycle/free;
     # only opaque return transfer is represented in ARM, not fake cleanup.
     uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
    assert s['st_value']<=pc<s['st_value']+s['st_size'];pcs.append(pc)
   def write(uc,access,a,n,v,d):
    if location<=a<a+n<=location+256:writes.append([a-location,n,v])
    else:assert sp-24<=a<a+n<=sp
   u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
   u.reg_write(UC_ARM_REG_R0,location);u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,stop)
   u.emu_start(s['st_value'],stop+4,count=100)
   assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==sp and u.reg_read(UC_ARM_REG_R0)==location
   assert writes==[[4,4,0x34feac],[132,4,0x34febc],[240,4,0x34fed8],[0,4,0x34fe58]]
   assert calls==(['base','delete'] if variant else ['base'])
   inp=[variant,count,calls.count('base'),calls.count('delete')]
   result=subprocess.run([str(exe),'--provider'],input=' '.join(map(str,inp))+'\n',text=True,capture_output=True,check=True).stdout.strip()
   assert result==f'{count} {count} {count} {variant} 0 borrowed 1'
   rows.append(dict(input=inp,location=location,calls=calls,writes=writes,pcs=pcs,provider_observation=result))
 return dict(task_id=TASK,elf_sha256=hashlib.sha256(raw).hexdigest(),mangled=s.name,range=dict(address=s['st_value'],size=s['st_size'],section=sec.name,section_index=s['st_shndx'],file_offset=offset,sha256=hashlib.sha256(body).hexdigest()),cases=rows,unicorn_version=unicorn.__version__,producer_sha256=sha(__file__),scope='Exact original ARM caller instructions and writes only; recorded boundary sequence executes actual canonical Rack/CCL destruction and actual host unsized global deallocation. Host provider state is independent source-port state, never original ARM layout/ABI or native base-body equivalence.')
