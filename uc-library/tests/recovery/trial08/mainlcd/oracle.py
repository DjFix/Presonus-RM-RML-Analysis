"""Execute original ARM targets; app/provider calls are observed boundary stubs.
No provider firmware body executes. Fixture expectations are emulator observations.
"""
import hashlib,json,struct,argparse
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[5]
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
THIS=0x200000;VIEW=0x210000;PAGE=0x220000;STOP=0x600000

def capture():
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 records=[];ranges=[]
 for i in range(1,11):
  packet=ROOT/f'temp/recovery-work/graph-live-trial-08/batch03/packets/trial08_mainlcd_{i}'
  context=json.loads((packet/'context.json').read_text());native=context['native_context'];body=native['bodies'][native['roots'][0]]
  original=context['originals'][0]['original'];code=data[body['file_offset']:body['file_offset']+body['size']]
  assert hashlib.sha256(code).hexdigest()==body['bytes_sha256']
  with ELF.open('rb') as stream:
   section=ELFFile(stream).get_section(body['section_index']);assert body['file_offset']==section['sh_offset']+body['address']-section['sh_addr']
  ranges.append(dict(task_id=f'trial08_mainlcd_{i}',original=original,file_offset=body['file_offset'],sha256=body['bytes_sha256'],section=body['section']))
  for variant in range(8):
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x10000,0x200000);u.mem_map(0x210000,0x20000);u.mem_map(0x400000,0x10000);u.mem_map(STOP,0x1000)
   u.mem_write(body['address'],code)
   if i==10:
    linked=json.loads((ROOT/'temp/recovery-work/graph-live-trial-08/batch03/packets/trial08_mainlcd_8/context.json').read_text())['native_context']
    linked=linked['bodies'][linked['roots'][0]]
    u.mem_write(linked['address'],data[linked['file_offset']:linked['file_offset']+linked['size']])
   u.mem_write(THIS,bytes(0x1000));u.mem_write(VIEW,bytes(0x1000))
   w=lambda a,v:u.mem_write(a,struct.pack('<I',v&0xffffffff))
   lcd=VIEW if variant&1 else 0;current=PAGE if variant&2 else 0;modal=PAGE+0x100 if variant&4 else 0;back=[0,1,0xffffffff,VIEW][variant%4]
   for off,val in [(0x90,lcd),(0xbc,current),(0xc0,modal),(0xc8,back)]:w(THIS+off,val)
   w(THIS,0x230000-0x1000);w(0x230000-0x1000+0x2c,0x180000)
   arg=[0,1,0xffffffff,1296843588,1131375984,VIEW,VIEW+4,0x80000000][variant]
   if i==4:arg=VIEW if variant&2 else VIEW+4
   if i==5:arg=VIEW if variant&2 else 0
   if i==6:arg=variant&2!=0
   trace=[];writes=[]
   def hook(uc,addr,size,unused):
    if addr==STOP:uc.emu_stop();return
    names={0xf704c:'isEditing',0xf6ff4:'stopTextInput',0x11a74c:'componentIdle',0x74168:'showNextPage',0x7394c:'getPageByTag',0x73b1c:'showPagePointer',0x180000:'startTag'}
    if addr in names:
     name=names[addr];trace.append([name,uc.reg_read(UC_ARM_REG_R0),uc.reg_read(UC_ARM_REG_R1)])
     if name=='getPageByTag':uc.reg_write(UC_ARM_REG_R0,PAGE if variant&1 else 0)
     elif name=='isEditing':uc.reg_write(UC_ARM_REG_R0,int(bool(variant&2)))
     elif name=='startTag':uc.reg_write(UC_ARM_REG_R0,variant)
     uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   def write(uc,access,a,size,value,unused):
    if THIS<=a<THIS+0x1000 or VIEW<=a<VIEW+0x1000:writes.append([a,size,value])
   u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
   u.reg_write(UC_ARM_REG_R0,THIS);u.reg_write(UC_ARM_REG_R1,int(arg));u.reg_write(UC_ARM_REG_SP,0x408000);u.reg_write(UC_ARM_REG_LR,STOP)
   u.emu_start(body['address'],STOP+4,count=1000)
   assert u.reg_read(UC_ARM_REG_PC)==STOP,(i,variant,hex(u.reg_read(UC_ARM_REG_PC)),trace)
   r=lambda a:struct.unpack('<I',bytes(u.mem_read(a,4)))[0]
   records.append(dict(target=i,variant=variant,inputs=dict(lcd=lcd,current=current,modal=modal,back=back,arg=int(arg),provider_editing=int(bool(variant&2)),lookup=PAGE if variant&1 else 0,start_tag=variant),observed=dict(r0=u.reg_read(UC_ARM_REG_R0),lcd=r(THIS+0x90),observer=r(VIEW+0x204),trace=trace,writes=writes)))
 return dict(elf_sha256=SHA,range_checks=ranges,cases=records,boundary_scope='Original target instructions only; named app/provider callees hooked with explicit scripted observations; arbitrary volatile values excluded.')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out');ap.add_argument('--verify');args=ap.parse_args();result=capture()
 if args.verify:
  assert result==json.loads(Path(args.verify).read_text());print('80 original ARM executions and 10 original ELF section/range checks reproduced')
 else:
  assert args.out;Path(args.out).write_text(json.dumps(result,indent=2)+'\n')
