import hashlib,json,struct,itertools,pathlib,datetime,os
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
START=datetime.datetime.now(datetime.timezone.utc).isoformat()
BASE=pathlib.Path('uc-library/candidates/graph-live-trial-05-page')
elfpath=pathlib.Path('rootfs/CS18_v13840/home/root/surface')
raw=elfpath.read_bytes(); sha=hashlib.sha256(raw).hexdigest(); assert sha=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
ranges=[]
with elfpath.open('rb') as f:
 e=ELFFile(f); sec=e.get_section(12)
 for n in range(1,6):
  p=pathlib.Path(f'temp/recovery-work/graph-live-trial-05/trial05_page_{n}-packet')
  task=json.loads((p/'context.json').read_text()); text=(p/'ELF_CONTEXT.md').read_text()
  import re
  m=re.search(r'original `([^`]+)`; address `0x([0-9a-f]+)`; size (\d+).*?SHA256 `([0-9a-f]+)`',text)
  name,addr,size,digest=m.groups(); addr=int(addr,16);size=int(size); off=sec['sh_offset']+addr-sec['sh_addr']; b=raw[off:off+size];assert hashlib.sha256(b).hexdigest()==digest
  ranges.append(dict(n=n,mangled=name,address=addr,size=size,offset=off,sha256=digest,section='.text'))
def run(n,owner,screen,current,editing,flag,ident):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x60000,0x20000)
 for r in ranges:u.mem_write(r['address'],raw[r['offset']:r['offset']+r['size']])
 u.mem_map(0x300000,0x10000);u.mem_map(0x400000,0x10000);u.mem_map(0x500000,0x1000)
 def word(a,v):u.mem_write(a,struct.pack('<I',v))
 word(0x300050,0x301000 if owner else 0);word(0x301000,0x302000);word(0x302000,0x70000)
 u.reg_write(UC_ARM_REG_R0,0x300000);u.reg_write(UC_ARM_REG_R1,ident if n==1 else flag);u.reg_write(UC_ARM_REG_SP,0x408000);u.reg_write(UC_ARM_REG_LR,0x500000)
 trace=[]; writes=[]
 u.hook_add(UC_HOOK_MEM_WRITE,lambda u,access,a,size,v,data: writes.append([a,size,v]) if not (0x400000<=a<0x410000) else None)
 def hook(u,a,size,data):
  if a==0x500000:u.emu_stop();return
  if a in (0x70000,0x734fc,0x739e4,0x73a04):
   r0=u.reg_read(UC_ARM_REG_R0);r1=u.reg_read(UC_ARM_REG_R1)
   trace.append([a,r0,r1 if a in (0x70000,0x739e4) else 0])
   result={0x70000:0x303000 if screen else 0,0x734fc:0x300000 if current else 0x304000,0x739e4:77,0x73a04:editing}[a]
   u.reg_write(UC_ARM_REG_R0,result);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(ranges[n-1]['address'],0x500004,count=1000)
 assert u.reg_read(UC_ARM_REG_PC)==0x500000
 assert bytes(u.mem_read(0x300000,0x10000))[0x50:0x54]==struct.pack('<I',0x301000 if owner else 0)
 result=u.reg_read(UC_ARM_REG_R0)
 # stop's original return declaration is unknown; compare trace only for it.
 return dict(n=n,owner=owner,screen=screen,current=current,editing=editing,flag=flag,ident=ident,result=result,trace=trace,nonstack_writes=writes)
cases=[]
for ident in [0,1348560741,1131375984,1348560740,1131375985,0x7fffffff,0xffffffff]:cases.append(run(1,0,0,0,0,0,ident))
for n in range(2,6):
 for owner,screen,current,editing,flag in itertools.product([0,1],[0,1],[0,1],[0,1],[0,1]):cases.append(run(n,owner,screen,current,editing,flag,0))
(BASE/'fixtures.json').write_text(json.dumps(dict(elf_sha256=sha,session_id=os.environ.get('CODEX_THREAD_ID'),started=START,finished=datetime.datetime.now(datetime.timezone.utc).isoformat(),ranges=ranges,cases=cases,oracle='original ARM instructions via Unicorn 2.1.4; external slot/MainLCD calls instrumented boundary stubs'),indent=2)+'\n')
print(len(cases))
