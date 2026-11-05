"""Bounded non-programming original ARM observations. No update/wait execution."""
import hashlib,json,struct,sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
BASE=Path('evidence/recovery/2026-11-05/rolling200-02/updater02')
PACKETS=Path('temp/recovery-work/rolling200-02/implementation-plan01/packets-batch03/packets')
ELF=Path('rootfs/RML16AI_Rack_13731/home/root/mixer');raw=ELF.read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(raw)=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
ranges=[]
with ELF.open('rb') as f:
 e=ELFFile(f);segments=[(int(s['p_vaddr']),s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
 for i in range(1,11):
  p=PACKETS/f'rolling200_02_impl_updater_{i:02d}';n=json.loads((p/'native-context.json').read_text());b=n['bodies'][n['roots'][0]];r=json.loads((p/'request.json').read_text())['originals'][0]['original'];s=e.get_section(int(r['section_json']));off=s['sh_offset']+r['address']-s['sh_addr'];assert off==b['file_offset'];assert sha(raw[off:off+r['size']])==b['bytes_sha256'];ranges.append(dict(r,section=s.name,file_offset=off,range_sha256=b['bytes_sha256'],executed=i not in [3,4]))
A=0x1000000;P=A+0x1000;V=A+0x2000;L=A+0x3000;B=A+0x4000;S=A+0x5000;STR=A+0x6000;STACK=0x2000000;STOP=0x3000000;CALLBACK=STOP+0x100
u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x500000);u.mem_map(A,0x10000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
for a,b in segments:u.mem_write(a,b)
def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
def word(a):return struct.unpack('<I',u.mem_read(a,4))[0]
def string(a):return bytes(u.mem_read(a,512)).split(b'\0')[0].decode() if a else None
state={};trace=[]
def hook(uc,a,size,user):
 if a==STOP:state['stopped']=True;uc.emu_stop();return
 if a in (0xa51e4,0xa4fbc):raise RuntimeError('Excluded programming/command method reached')
 ret=None
 if a==0x116908:
  t=state['raw']&((1<<64)-1);uc.reg_write(UC_ARM_REG_R0,t&0xffffffff);uc.reg_write(UC_ARM_REG_R1,t>>32);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
 if a==0x116a38:trace.append(['debug',string(uc.reg_read(UC_ARM_REG_R0)),string(uc.reg_read(UC_ARM_REG_R1))]);ret=0
 elif a==0x10e948:trace.append(['sleep',uc.reg_read(UC_ARM_REG_R0)]);ret=0
 elif a==CALLBACK:trace.append(['listener',string(uc.reg_read(UC_ARM_REG_R1)),uc.reg_read(UC_ARM_REG_R2)]);ret=0
 elif a==0xa4b38:
  trace.append(['base-constructor']);uc.mem_write(A+4,b'\0'*8);ret=A
 elif a==0xa30d4:trace.append(['register',uc.reg_read(UC_ARM_REG_R0)==S,uc.reg_read(UC_ARM_REG_R1)==A]);ret=0
 elif a==0xa2fe0:trace.append(['unregister',uc.reg_read(UC_ARM_REG_R0)==S,uc.reg_read(UC_ARM_REG_R1)==A]);ret=0
 if ret is not None:uc.reg_write(UC_ARM_REG_R0,ret);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
u.hook_add(UC_HOOK_CODE,hook)
def run(i,args,rawticks=0,epoch=0):
 trace.clear();state.update(raw=rawticks,stopped=False);u.mem_write(A,b'\xa5'*256);w(A+16,L if state.get("has_listener",1) else 0);w(L,V);w(V,CALLBACK);u.mem_write(STR,b'hello\0');u.mem_write(STR+32,b'\0');w(0x4953a0,epoch);w(0x4953a4,epoch>>32)
 # SPI singleton cell determined from bound constructor literal pool.
 if i in [7,8,9,10]:
  b=ranges[i-1];# constructor first singleton literal at entry+152; dtor at+132
  addr=b['address'];lit=addr+(156 if i in [7,8] else 132);singleton=word(lit);w(singleton,S)
 for n in range(13):u.reg_write(UC_ARM_REG_R0+n,0)
 u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP)
 for n,v in enumerate(args):u.reg_write(UC_ARM_REG_R0+n,v)
 u.emu_start(ranges[i-1]['address'],STOP+4,count=100000);assert state['stopped'];return u.reg_read(UC_ARM_REG_R0),list(trace),bytes(u.mem_read(A,32))
cases=[];lines=[]
for length in [0,1,2,3,127,255]:
 for command in range(256):
  u.mem_write(P,b'\0'*272);u.mem_write(P+0x108,bytes([length]));u.mem_write(P+9,bytes([command]));ret,t,m=run(5,[A,P]);cases.append(dict(target=5,length=length,command=command,r0=ret));lines.append(f'0 {length} {command} {ret}')
for k in range(256):
 a=k;b=(k*73)&255;c=(255-k);u.mem_write(P+10,bytes([a,b,c]));ret,t,m=run(6,[A,P]);after=[m[4],struct.unpack('<I',m[8:12])[0],m[5]];cases.append(dict(target=6,input=[a,b,c],after=after));lines.append('1 '+' '.join(map(str,[a,b,c]+after)))
for target in [1,2]:
 for listener in [0,1]:
  for message in [0,1,2]:
   for rawticks,epoch in [(0,0),(1000000000000,1000000),(-1000000000,0),(280000000000,0),(560000000000,0),(9223372036000000000,-100)]:
    # run() installs listener before starting; use r0 offset virtual? clear via state hook below.
    # Listener initialization is selected immediately before entry.
    addr=[0,STR+32,STR][message]
    original_hook=state.get('listener')
    state['listener']=listener
    # Store through run's parameterized initializer.
    state['has_listener']=listener
    ret,t,m=run(target,[A,addr],rawticks,epoch)
    cases.append(dict(target=target,listener=listener,message=message,raw=rawticks,epoch=epoch,trace=t))
    bits=next((x[2] for x in t if x[0]=='listener'),0);lines.append('2 '+' '.join(map(str,[target,listener,message,rawticks,epoch,bits,len([x for x in t if x[0]=='debug']),len([x for x in t if x[0]=='sleep'])])))
for target in [7,8,9,10]:
 ret,t,m=run(target,[A,L,B]);assert ret==A;cases.append(dict(target=target,trace=t,object_bytes=m.hex(),r0=ret));lines.append(f'3 {target} {int(any(x[0]=="register" for x in t))} {int(any(x[0]=="unregister" for x in t))}')
BASE.mkdir(parents=True,exist_ok=True);(BASE/'fixtures.txt').write_text('\n'.join(lines)+'\n');(BASE/'native-observations.json').write_text(json.dumps(dict(elf_sha256=sha(raw),ranges=ranges,cases=cases,boundaries='Core time/debug/sleep, listener, base constructor and SPI register/unregister scripted boundaries; no Core instructions or device/update/wait bodies executed',lifecycle_domain='existing singleton; normal allocation, no original allocator/cleanup/deallocation claim',unicorn_version=__import__('unicorn').__version__),indent=2)+'\n');print('Original non-programming ARM cases',len(cases))
