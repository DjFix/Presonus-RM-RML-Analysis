import hashlib, json, pathlib, sys, time
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_SP, UC_ARM_REG_LR
ROOT=pathlib.Path(__file__).resolve().parents[3]
OUT=pathlib.Path(__file__).resolve().parent
elf=ROOT/'rootfs/CS18_v13840/home/root/surface'
data=elf.read_bytes()
assert hashlib.sha256(data).hexdigest()=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
body=data[0x6f93c:0x6f950]
assert hashlib.sha256(body).hexdigest()=='427a74a3e346dc87ca8bacf71c047923492e75543ef5014f706af440f0268430'
rows=[]
traces=[]
for pattern in range(4):
 for value in range(256):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for addr in (0x77000,0x100000,0x200000,0x300000):u.mem_map(addr,4096)
  u.mem_write(0x7793c,body)
  obj=bytearray(((i*37+pattern*71)&255) for i in range(512));obj[0x134]=value
  u.mem_write(0x100000,bytes(obj));u.reg_write(UC_ARM_REG_R0,0x100000)
  u.reg_write(UC_ARM_REG_SP,0x200800);u.reg_write(UC_ARM_REG_LR,0x300000)
  events=[]
  def hook(uc,access,address,size,val,user):events.append([access,address,size,val if access==17 else None])
  u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,hook)
  u.emu_start(0x7793c,0x300000,count=20)
  result=u.reg_read(UC_ARM_REG_R0)
  assert bytes(u.mem_read(0x100000,512))==bytes(obj)
  obj_events=[x for x in events if 0x100000<=x[1]<0x100200]
  assert len(obj_events)==1 and obj_events[0][1:3]==[0x100134,1]
  rows.append(f'{pattern} {value} {result}\n')
  traces.append({'pattern':pattern,'value':value,'r0':result,'events':events,'object_unchanged':True})
(OUT/'fixtures.txt').write_text(''.join(rows))
(OUT/'native-observations.json').write_text(json.dumps({'oracle':'original ARM instructions executed by Unicorn','elf_sha256':hashlib.sha256(data).hexdigest(),'address':0x7793c,'file_offset':0x6f93c,'size':20,'section':'.text','range_sha256':hashlib.sha256(body).hexdigest(),'cases':traces,'assumptions':['512-byte readable borrowed object image','mapped 4096-byte stack','no external calls; no stubs','ARM little endian; sentinel LR']},indent=2)+'\n')
print('native cases',len(rows))
