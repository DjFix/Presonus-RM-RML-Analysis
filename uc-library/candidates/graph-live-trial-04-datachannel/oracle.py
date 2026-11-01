import json,hashlib,struct,time,datetime,os
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
BASE=Path('uc-library/candidates/graph-live-trial-04-datachannel')
elfpath=Path('rootfs/RML16AI_Rack_13731/home/root/mixer'); data=elfpath.read_bytes(); sha=hashlib.sha256(data).hexdigest(); assert sha=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
ranges=[]; cases=[]; start=time.time(); stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
with elfpath.open('rb') as f:
 elf=ELFFile(f)
 for i in range(1,6):
  p=Path(f'temp/recovery-work/graph-live-trial-04/trial04_datachannel_{i}-packet'); n=json.loads((p/'native-context.json').read_text()); b=n['bodies'][n['roots'][0]]; sec=elf.get_section(b['section_index']); off=int(sec['sh_offset'])+b['address']-int(sec['sh_addr']); assert off==b['file_offset']; raw=data[off:off+b['size']]; assert hashlib.sha256(raw).hexdigest()==b['bytes_sha256']; ranges.append({k:b[k] for k in ('address','size','section','section_index','file_offset','bytes_sha256')})
  inputs=[]
  if i<5:
   for result in [0,1,2,255,256,4095,4096,4097,2147483647,2147483648,4294967295]:
    for length in [-2147483648,-1,0,1,6,2147483647]: inputs.append((result,length))
  else:
   for length in [-2147483648,-1,0,1,5,6,7,2147483647]:
    for a,c in [(0,0),(0x55,0),(0,0x43),(0x55,0x43),(255,255)]:
     for value in [0,1,255,256,4096,65535]:
      for out in [0,1]: inputs.append((length,a,c,value,out))
  for inp in inputs:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM); u.mem_map(0x100000,0x10000);u.mem_write(b['address'],raw);u.mem_map(0x200000,0x10000);u.mem_map(0x300000,0x10000)
   u.reg_write(UC_ARM_REG_SP,0x30f000); u.reg_write(UC_ARM_REG_LR,0x100100); trace=[]
   u.mem_write(0x200000,struct.pack('<III',0xeeeeeeee,0x200100,0x200200)); u.mem_write(0x200500,struct.pack('<I',0xabcdef01))
   if i<5:
    result,length=inp; u.reg_write(UC_ARM_REG_R0,0x200000);u.reg_write(UC_ARM_REG_R1,0x200400 if i<3 else length&0xffffffff);u.reg_write(UC_ARM_REG_R2,length&0xffffffff); target=[0x1042a0,0x10475c,0x104548,0x1044b0][i-1]
   else:
    length,a,c,value,out=inp;u.mem_write(0x200400,bytes([a,c,0xa5,0x5a,value&255,value>>8]));u.reg_write(UC_ARM_REG_R0,0x200400);u.reg_write(UC_ARM_REG_R1,length&0xffffffff);u.reg_write(UC_ARM_REG_R2,0x200500 if out else 0);target=-1
   def hook(uc,address,size,user):
    if address==0x100100: uc.emu_stop()
    elif address==target:
     trace.append([uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2]])
     uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   u.hook_add(UC_HOOK_CODE,hook);u.emu_start(b['address'],0,count=100); assert u.reg_read(UC_ARM_REG_PC)==0x100100
   cases.append({'method':i,'input':inp,'return':u.reg_read(UC_ARM_REG_R0),'output':struct.unpack('<I',u.mem_read(0x200500,4))[0],'calls':trace})
(BASE/'fixtures.json').write_text(json.dumps({'ranges':ranges,'cases':cases},indent=2)+'\n')
with (BASE/'fixtures.txt').open('w') as f:
 for c in cases:
  inp=c['input']; i=c['method']; trace=c['calls']; nums=([i,*inp,0,0,0] if i<5 else [i,*inp]);nums=nums[:6];nums += [c['return'],c['output'],len(trace)];nums += (trace[0] if trace else [0,0,0]);f.write(' '.join(map(str,nums))+'\n')
(BASE/'oracle-proof.json').write_text(json.dumps({'elf':str(elfpath),'elf_sha256':sha,'ranges':ranges,'case_count':len(cases),'started':stamp,'elapsed_seconds':time.time()-start,'oracle':'Unicorn 2.1.4 original instruction execution; PacketQueue boundary intercepted, arbitrary register return; no PacketQueue implementation claim','session_id':os.environ.get('CODEX_THREAD_ID')},indent=2)+'\n')
print(len(cases))
