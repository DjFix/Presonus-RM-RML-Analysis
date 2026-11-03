"""Execute exact original ARM target ranges. BLs are intercepted app boundaries.
This does not decode Core implementations or assert original return declarations.
"""
import hashlib,json,pathlib,struct,sys
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
ROOT=pathlib.Path(__file__).resolve().parents[5]
PACKETS=ROOT/'temp/recovery-work/frontier-small01/batch01/packets'
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
OBJ,ARRAY,ITEM,OUT,STACK,STOP=0x400000,0x410000,0x420000,0x430000,0x500000,0x600000
REGS=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]

def execute(raw,b,n,arg):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x10000,0x380000)
 u.mem_write(b['address'],raw[b['file_offset']:b['file_offset']+b['size']])
 u.mem_map(OBJ,0x40000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
 def put(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 for i in range(4):
  put(ARRAY+4*i,ITEM+0x1000*(i%3));u.mem_write(ITEM+0x1000*i+0x145,bytes([i%2]))
 if n==1:args=[OUT,OBJ,arg,0x9876]
 else:args=[OBJ,0x430100,arg,0x9876]
 if n in (4,5):
  put(OBJ+(8 if n==4 else 0xd0),ARRAY);put(OBJ+(12 if n==4 else 0xd4),arg)
 for reg,v in zip(REGS,args):u.reg_write(reg,v&0xffffffff)
 u.reg_write(UC_ARM_REG_SP,STACK+0x8000);u.reg_write(UC_ARM_REG_LR,STOP)
 calls=[];writes=[]
 targets={int(i['operands'].lstrip('#'),16) for i in b['instructions'] if i['mnemonic']=='bl'}
 def call(uc,address,size,_):
  if address not in targets:return
  a=[uc.reg_read(r) for r in REGS]
  calls.append({'target':address,'args':a,'dirty':uc.mem_read(a[0]+0x145,1)[0] if n==4 else None})
  if n==1 and address==0x83cac:uc.reg_write(UC_ARM_REG_R0,ITEM)
  if n==1 and address==0x85ae0:uc.mem_write(OUT,b'provider-sret-marker\0')
  if n==4:uc.mem_write(a[0]+0x145,b'\x00')
  # Clobber caller-saved registers at every boundary to expose retention errors.
  for reg in REGS[1:]:uc.reg_write(reg,0xcc000000+reg)
  uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 def write(uc,access,address,size,value,_):
  if OBJ<=address<OBJ+0x40000:writes.append([address,size,value])
 u.hook_add(UC_HOOK_CODE,call);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.emu_start(b['address'],STOP,count=3000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 if n==1:
  assert [c['target'] for c in calls]==[0x83cac,0x85ae0]
  assert calls[0]['args'][0]==OBJ
  assert calls[1]['args'][:4]==[OUT,ITEM,arg&0xffffffff,1]
  assert u.reg_read(UC_ARM_REG_R0)==OUT
  normalized=['lookup','file:'+str(arg&0xffffffff)+':1']
 elif n in (2,3):
  assert len(calls)==1 and calls[0]['args'][0]==OBJ
  assert u.reg_read(UC_ARM_REG_R0)==OBJ
  normalized=['base']
 else:
  assert len(calls)==arg
  assert [c['args'][0] for c in calls]==[ITEM+0x1000*(i%3) for i in range(arg)]
  if n==4:assert all(c['dirty']==1 for c in calls)
  normalized=[('rebuild:' if n==4 else 'fx:')+str(i%3)+(":1" if n==4 else '') for i in range(arg)]
 return {'packet':n,'argument':arg,'calls':calls,'writes':writes,'r0_observation':u.reg_read(UC_ARM_REG_R0),'normalized':normalized}

def produce():
 raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 ranges=[];cases=[]
 with ELF.open('rb') as f:
  elf=ELFFile(f)
  for n in range(1,6):
   j=json.loads((PACKETS/f'frontier01_w01_{n:02}'/'native-context.json').read_text());b=j['bodies'][j['roots'][0]]
   sec=elf.get_section(b['section_index']);offset=sec['sh_offset']+b['address']-sec['sh_addr']
   assert offset==b['file_offset'] and sec.name==b['section']
   code=raw[offset:offset+b['size']];assert hashlib.sha256(code).hexdigest()==b['bytes_sha256']
   ranges.append({'packet':n,**{k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}})
   for arg in ([0,1,2,15,0xffffffff] if n==1 else [0,1] if n in (2,3) else [0,1,2,3,4]):cases.append(execute(raw,b,n,arg))
 return {'version':1,'elf_sha256':SHA,'unicorn_version':unicorn.__version__,'ranges':ranges,'cases':cases,'domain':'Five full target ranges; caller-saved clobbers; sret sentinel app boundary; borrowed arrays length 0..4 with repeats; dirty byte observed at rebuild entry and reset by modeled callee. D1 base calls intercepted; vptr writes recorded; no callee native execution, no D0 claim, no Core decompilation.'}
if __name__=='__main__':
 result=produce();p=pathlib.Path(__file__).with_name('fixtures.json')
 if '--write' in sys.argv:p.write_text(json.dumps(result,indent=2)+'\n')
 else:assert result==json.loads(p.read_text())
 print(len(result['cases']),'original ARM executions; five separately range-verified targets')
