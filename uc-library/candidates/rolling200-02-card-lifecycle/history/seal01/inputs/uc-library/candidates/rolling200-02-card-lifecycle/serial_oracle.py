from pathlib import Path
import hashlib,json,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[3];E=R/'evidence/recovery/2026-11-05/rolling200-02/card-lifecycle';raw=(R/'rootfs/RML16AI_Rack_13731/home/root/mixer').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
providers={}
for line in (E/'provider-observations.txt').read_text().splitlines():
 x=line.split();providers[int(x[0])]=dict(decimal=x[1],chunks=x[2:5],combined=x[5],a=int(x[6]),b=int(x[7]),c=int(x[8]),result=int(x[9]))
with (R/'rootfs/RML16AI_Rack_13731/home/root/mixer').open('rb') as f:
 ef=ELFFile(f);segments=[(int(s['p_vaddr']),s.data(),int(s['p_memsz'])) for s in ef.iter_segments() if s['p_type']=='PT_LOAD'];s=ef.get_section(12);sh=dict(s.header)
ranges=[(0x9da98,324,'f30e466dc1df91f9eed3d8c2564ccf51f51c021670afdd3407a5b2f2b6a21710'),(0x9cce4,300,'17b13f2f01ae489d5ef7e44729e7831c3681b6b2ae55c23587a8a66c31c6458c'),(0xa468c,76,'d84b5e489320a5a313d93284642889436b2b26497a908712985c9099a77a4345')]
for a,n,h in ranges:
 off=sh['sh_offset']+a-sh['sh_addr'];assert hashlib.sha256(raw[off:off+n]).hexdigest()==h
OBJ=0x1000000;STACK=0x1100000;STOP=0x1300000;cases=[];lines=[]
for typ in (0,1,2,3,0xffffffff):
 for serial,p in providers.items():
  for ack in (0,1,255):
   index=len(cases);word30=(0,255,0x12345678)[index%3];tick=(-2000003,1234567,0x12345678000000)[index%3]
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
   for a,b,n in segments:
    for pg in range(a&~4095,(a+n+4095)&~4095,4096):
     if pg not in pages:u.mem_map(pg,4096);pages.add(pg)
    u.mem_write(a,b)
   for a,n in ((OBJ,4096),(STACK,16384),(STOP,4096)):u.mem_map(a,n)
   state=bytearray([0xa5]*104);struct.pack_into('<I',state,0,0x35a638)
   for off,v in ((0x14,typ),(0x2c,serial),(0x30,word30),(0x3c,0xabcdef12)):struct.pack_into('<I',state,off,v)
   u.mem_write(OBJ,bytes(state));u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_SP,STACK+12000);u.reg_write(UC_ARM_REG_LR,STOP)
   events=[];imports=[];writes=[];packet={};done=[False];clocks=[];strings={};sub=[0]
   def reg(i):return u.reg_read((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)[i])
   def readstr(a):
    b=bytes(u.mem_read(a,100));return b.split(b'\0')[0].decode()
   def ret():u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   def word(a):return struct.unpack('<I',u.mem_read(a,4))[0]
   def setstr(a,s):assert STACK<=a<STACK+16384;strings[a]=s;u.mem_write(a,s.encode()+b'\0')
   def hook(uc,pc,size,data):
    if pc==STOP:done[0]=True;u.emu_stop();return
    if any(a<=pc<a+n for a,n,h in ranges):return
    if pc==0xae68:
     assert reg(2) in (14,);dst,src,n=reg(0),reg(1),reg(2);assert STACK<=dst and dst+n<=STACK+16384;u.mem_write(dst,bytes(u.mem_read(src,n)));ret()
    elif pc==0xaa60:
     assert reg(2)==255 and reg(1)&255==0x45,(reg(0),reg(1),reg(2));assert STACK<=reg(0) and reg(0)+255<=STACK+16384;u.mem_write(reg(0),bytes([reg(1)&255])*reg(2));ret()
    elif pc==0x116908:
     assert len(clocks)<2;t=tick+len(clocks)*1000003;clocks.append(t);events.append('clock');u.reg_write(UC_ARM_REG_R0,t&0xffffffff);u.reg_write(UC_ARM_REG_R1,(t>>32)&0xffffffff);ret()
    elif pc==0x157a08:
     assert reg(2)==1000000 and reg(3)==0;v=reg(0)|(reg(1)<<32);v=v-(1<<64) if v>>63 else v;q=(abs(v)//1000000)*(-1 if v<0 else 1);u.reg_write(UC_ARM_REG_R0,q&0xffffffff);u.reg_write(UC_ARM_REG_R1,(q>>32)&0xffffffff);ret()
    elif pc==0x1debc:assert reg(1)==0;setstr(reg(0),'');imports.append('ccl_ctor');ret()
    elif pc==0x3987c:
     fmt=readstr(reg(1))
     if fmt=='%08u':assert reg(2)==serial;out=p['decimal']
     else:
      assert fmt=='%02d%02d%04d' and reg(2)==p['b'] and reg(3)==p['a']+30 and word(u.reg_read(UC_ARM_REG_SP))==p['c'];out=p['combined']
     setstr(reg(0),out);imports.append('ccl_format');ret()
    elif pc==0x45c48:
     k=sub[0];assert strings[reg(0)]==p['decimal'] and (reg(2),reg(3))==((0,2),(2,2),(4,4))[k];setstr(reg(1),p['chunks'][k]);sub[0]+=1;imports.append('ccl_substring');ret()
    elif pc==0xafdc:
     fmt=readstr(reg(1));text=strings[reg(0)];assert fmt in ('%u','%08u');assert text in p['chunks']+[p['combined']];assert STACK<=reg(2) and reg(2)+4<=STACK+16384;out=int(text[:8] if fmt=='%08u' else text);assert out in (p['a'],p['b'],p['c'],p['result']);u.mem_write(reg(2),struct.pack('<I',out));imports.append('libc_scan');ret()
    elif pc==0x116a38:
     fmt=readstr(reg(0));assert fmt in ('Generated alternate AVB MAC %d from %d\n','programming serial reset\n');events.append('alternate_debug' if fmt.startswith('Generated') else 'debug');ret()
    elif pc==0xa4e24:
     assert reg(0)==OBJ and len(clocks)==2;a=reg(1);n=bytes(u.mem_read(a+264,1))[0];assert n==14
     packet.update(bytes=bytes(u.mem_read(a+8,n)).hex(),header=list(struct.unpack('<II',u.mem_read(a,8))),timestamp=struct.unpack('<q',u.mem_read(a+272,8))[0],trailing=list(struct.unpack('<IIII',u.mem_read(a+280,16))));assert packet['header']==[0,0] and packet['trailing']==[0]*4;events.append('post');ret()
    elif pc==0x10e948:assert reg(0)==4000;events.append('sleep4000');ret()
    elif pc==0xa4ce4:assert reg(0)==OBJ and reg(2)==500 and reg(3)==0;events.append('wait500');u.reg_write(UC_ARM_REG_R0,ack);ret()
    else:raise AssertionError(('unapproved pc',hex(pc)))
   def write(uc,access,a,n,v,data):
    assert STACK<=a and a+n<=STACK+16384,('unapproved native write',hex(a),n);writes.append([a-STACK,n,v])
   u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write);u.emu_start(0x9da98,STOP+4,count=2000)
   assert done[0] and u.reg_read(UC_ARM_REG_R0)==ack and bytes(u.mem_read(OBJ,104))==bytes(state)
   assert events==(['alternate_debug'] if typ in (1,2) else [])+['clock','clock','post','debug','sleep4000','wait500']
   c=dict(type=typ,serial=serial,word30=word30,tick=tick,ack=ack,packet=packet,events=events,clocks=clocks,provider_imports=imports,writes=writes);cases.append(c)
   lines.append(f"{typ} {serial} {word30} {tick} {ack} {packet['bytes']} {packet['timestamp']} {';'.join(events)}")
(E/'serial-native.json').write_text(json.dumps(dict(elf_sha256=hashlib.sha256(raw).hexdigest(),ranges=[dict(address=a,size=n,section=12,file_offset=sh['sh_offset']+a-sh['sh_addr'],sha256=h) for a,n,h in ranges],provider_fixture_sha256=hashlib.sha256((E/'provider-observations.txt').read_bytes()).hexdigest(),cases=cases,limitations=['Pinned CCL provider observations imported; native Core bodies never executed','Finite memcpy/memset/division/time/debug/post/sleep/ack imports only; no device, host syscall or network','Unencoded original return declaration remains unresolved']),indent=2)+'\n')
(E/'serial-fixtures.txt').write_text('\n'.join(lines)+'\n');print(len(cases),'serial original runs plus exact native alternate/pack32 helper execution')
