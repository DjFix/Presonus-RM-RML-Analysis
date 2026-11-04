"""Exact app ARM instructions; pinned Core call is a recorded boundary, never executed."""
import hashlib, json, struct, argparse
from pathlib import Path
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[5]
PACKETS=ROOT/'temp/recovery-work/reconstruction-200-01/large-batch01/packets'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def original(i):
 p=PACKETS/f'large01_w01_{i:02}'
 d=json.loads((p/'context.json').read_text()); n=d['native_context']; b=n['bodies'][d['native_roots'][0]]
 r=json.loads((p/'request.json').read_text())['originals'][0]['original']
 path=ROOT/n['binaries'][r['elf']]['path']; assert digest(path)==r['elf']
 with path.open('rb') as f:
  e=ELFFile(f); s=e.get_section(b['section_index']); assert s.name==b['section']
  off=s['sh_offset']+r['address']-s['sh_addr'];assert off==b['file_offset']
 raw=path.read_bytes();body=raw[off:off+r['size']];assert hashlib.sha256(body).hexdigest()==b['bytes_sha256']
 return r,b,raw
CACHE={i:original(i) for i in range(1,11)}
def observe(args):
 op,mask,a,b,c,d,x,alias=args
 r,body,raw=CACHE[op]
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x4f8000)
 # Load ELF segments faithfully, including literals; only app target executes.
 path=ROOT/('rootfs/RML16AI_Rack_13731/home/root/mixer' if op<7 or op==9 else 'rootfs/CS18_v13840/home/root/surface')
 with path.open('rb') as f:
  for seg in ELFFile(f).iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 O=0x500000;u.mem_map(O,0x10000); SP=O+0xf000; STOP=O+0xff00
 def put(addr,val):u.mem_write(addr,struct.pack('<I',val&0xffffffff))
 def get(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
 def signed(v):return v if v<2**31 else v-2**32
 put(O+0x800,111);put(O+0x804,222)
 for j,v in enumerate([a,b,c,d]):
  put(O+0xa0+4*j,O+0x1000+16*j if mask&(1<<j) else 0);put(O+0x1000+16*j,v)
 u.reg_write(UC_ARM_REG_R0,O);u.reg_write(UC_ARM_REG_R1,O+0x800);u.reg_write(UC_ARM_REG_R2,O+0x800 if alias else O+0x804);u.reg_write(UC_ARM_REG_R3,x&0xffffffff)
 put(SP,mask&1);u.reg_write(UC_ARM_REG_SP,SP);u.reg_write(UC_ARM_REG_LR,STOP)
 traces=[];writes=[]
 if op==6:u.reg_write(UC_ARM_REG_R1,x&0xffffffff)
 if op==9:u.reg_write(UC_ARM_REG_R1,a)
 if op==10:
  item=O+0x2000;u.reg_write(UC_ARM_REG_R1,item);put(item,a);put(O+0xd8,b);put(O+0xd4,O+0x3000)
  for j in range(max(0,b)):
   entry=O+0x4000+0x200*j;put(O+0x3000+4*j,entry);put(entry+0x1d4,item if j==c else O+0x2500)
 def code(uc,addr,size,_):
  if addr==0x11b5e0 and op in (7,8):
   traces.append({'target':addr,'self':uc.reg_read(UC_ARM_REG_R0),'state':[get(O),get(O+4),get(O+0x88)]})
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  elif not(r['address']<=addr<r['address']+r['size']):
   raise RuntimeError(f'Unexpected execution {addr:x}')
 def write(uc,access,addr,size,value,_):
  if O<=addr<O+0x900:writes.append([addr-O,size,value])
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.emu_start(r['address'],STOP,count=1000)
 ret=signed(u.reg_read(UC_ARM_REG_R0))
 if op in (1,2,3,4):out=[ret,signed(get(O+0x800)),signed(get(O+0x800 if alias else O+0x804))]
 elif op in (5,6,10):out=[ret]
 elif op==9:out=[get(O+0x90),int(get(O+0x90)!=0)]
 else:
  assert len(traces)==1 and traces[0]['self']==O and ret==O
  assert traces[0]['state']==[0x194428,0x194464,0x1f2e14]
  out=[1] # One actual provider delegation, compared with one child cleanup.
 return {'args':args,'expected':out,'native_return':ret,'writes':writes,'provider_calls':traces}
def generate():
 cases=[]
 for op in (1,2,3,4,5,6):
  for mask in range(16):
   for x in ([-2**31,-1,0,3,4,29,30,31,2**31-1] if op in (3,4,6) else [0]):
    for alias in ([0,1] if op in (1,2,3,4) else [0]):
     cases.append(observe([op,mask,0,127,128,255,x,alias]))
 for op in (7,8):cases.append(observe([op,0,0,0,0,0,0,0]))
 for ptr in (0,0x1234,0x7fffffff):cases.append(observe([9,0,ptr,0,0,0,0,0]))
 for kind in (0,1,-1):
  for count in (0,1,3):
   for match in (-1,0,2):cases.append(observe([10,0,kind,count,match,0,0,0]))
 return {'unicorn_version':unicorn.__version__,'ranges':[{'original':r,'range':b} for r,b,_ in CACHE.values()],'cases':cases}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args();Path(args.out).write_text(json.dumps(generate(),indent=2)+'\n')
