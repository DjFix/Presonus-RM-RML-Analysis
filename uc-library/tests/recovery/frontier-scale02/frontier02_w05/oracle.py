"""Execute exact selected original ARM app ranges. Core bodies never execute.
Call boundaries and their modeled memory effects are explicit in every fixture.
"""
import hashlib,itertools,json,pathlib,struct,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
ROOT=pathlib.Path(__file__).resolve().parents[5]
P=ROOT/'temp/recovery-work/frontier-scale02/batch01/packets'
E=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
OBJ,PARAM,INFO,PARENT,ARRAY,CHILD,STACK,STOP,OUT=0x400000,0x410000,0x420000,0x430000,0x440000,0x450000,0x500000,0x600000,0x470000
REGS=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def run(raw,b,n,inp,send):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x10000,0x380000);u.mem_map(OBJ,0x80000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
 u.mem_write(b['address'],raw[b['file_offset']:b['file_offset']+b['size']])
 if n==2:u.mem_write(send['address'],raw[send['file_offset']:send['file_offset']+send['size']])
 def put(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def word(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def text(a):return bytes(u.mem_read(a,256)).split(b'\x00')[0].decode()
 tag,msg,count,initial,dirty,mutate=inp
 put(PARAM+12,INFO);put(INFO+4,tag);put(OBJ+0x174,PARENT);put(OBJ+0x88,PARENT)
 put(PARENT+0x1d4,ARRAY);put(PARENT+0x1d8,count)
 for i in range(count):put(ARRAY+4*i,CHILD+0x1000*i)
 for addr in [OBJ]+[CHILD+0x1000*i for i in range(count)]:
  for off in [0x178,0x17c,0x18c,0x194]:put(addr+off,initial)
  u.mem_write(addr+0x85,bytes([dirty]))
 if n==1:
  # Hash-bound literal bytes from source ELF, section/file mapping verified below.
  u.mem_write(0x176a04,raw[0x16ea04:0x16ea04+32])
  args=[OUT,OBJ,0,0]
 else:args=[OBJ,PARAM,msg,0]
 for reg,val in zip(REGS,args):u.reg_write(reg,val&0xffffffff)
 u.reg_write(UC_ARM_REG_SP,STACK+0x8000);u.reg_write(UC_ARM_REG_LR,STOP)
 calls=[];writes=[];pcs=[]
 def state(a):return [word(a+0x178),word(a+0x17c),word(a+0x18c),word(a+0x194),u.mem_read(a+0x85,1)[0]]
 targets={int(i['operands'].lstrip('#'),16) for i in b['instructions'] if i['mnemonic']=='bl'}
 if n==2:targets={0x46978}
 def hook(uc,a,size,data):
  if n==2 and a==send['address']:
   calls.append({'target':a,'args':[uc.reg_read(r) for r in REGS],'tag_at_call':word(INFO+4),'boundary':False});pcs.append(a);return
  if a not in targets:
   assert b['address']<=a<b['address']+b['size'] or (n==2 and send['address']<=a<send['address']+send['size']),hex(a)
   pcs.append(a);return
  item={'target':a,'args':[uc.reg_read(r) for r in REGS],'state_at_call':state(OBJ),'children_at_call':[state(CHILD+0x1000*i) for i in range(count)]}
  if n==1:item['literal']=text(uc.reg_read(UC_ARM_REG_R2 if a==0x321c4 else UC_ARM_REG_R1))
  else:
   item['tag_at_call']=word(INFO+4)
   # Fixture-only Output boundary mutates only tag; actual Output state is
   # independently observed in replay and forms the portable baseline.
   if mutate:put(INFO+4,410 if mutate==1 else 14)
  calls.append(item)
  uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 def write(uc,access,a,size,val,data):
  if OBJ<=a<OBJ+0x800 or CHILD<=a<CHILD+0x4000:writes.append([a,size,val,uc.reg_read(UC_ARM_REG_PC)])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.emu_start(b['address'],STOP,count=10000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 return {'packet':n,'inputs':inp,'calls':calls,'writes':writes,'state':state(OBJ),'children':[state(CHILD+0x1000*i) for i in range(count)],'r0_observation':u.reg_read(UC_ARM_REG_R0),'executed_addresses':pcs}
def produce():
 raw=E.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 ranges=[];cases=[]
 expansion=ROOT/'temp/recovery-work/frontier-scale02/expansions01/w05-send/native-context.json'
 sj=json.loads(expansion.read_text());send=sj["bodies"][sj["roots"][0]]
 with E.open('rb') as f:
  elf=ELFFile(f)
  sec=elf.get_section(send['section_index']);soff=sec['sh_offset']+send['address']-sec['sh_addr'];assert soff==send['file_offset']
  assert hashlib.sha256(raw[soff:soff+send['size']]).hexdigest()==send['bytes_sha256']
  ranges.append({'dependency':'SendOutputComponent',**{k:send[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}})
  for n in [1,2]:
   j=json.loads((P/f'frontier02_w05_{n:02}'/'native-context.json').read_text());b=j['bodies'][j['roots'][0]]
   sec=elf.get_section(b['section_index']);off=sec['sh_offset']+b['address']-sec['sh_addr'];assert off==b['file_offset'] and sec.name==b['section']
   assert hashlib.sha256(raw[off:off+b['size']]).hexdigest()==b['bytes_sha256']
   ranges.append({'packet':n,**{k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}})
   inputs=[[0,0,0,0,0,0]] if n==1 else itertools.product([-1,0,14,21,400,409,410,411,412,413],[-1,0,2,3,4],[0,1,3],[0,7],[0,1],[0,1,2])
   cases.extend(run(raw,b,n,list(inp),send) for inp in inputs)
  for addr,want in [(0x176a04,b'temp\x00'),(0x176a0c,b'mixer.scene\x00')]:
   sec=next(s for s in elf.iter_sections() if s['sh_addr']<=addr<s['sh_addr']+s['sh_size']);off=sec['sh_offset']+addr-sec['sh_addr'];assert raw[off:off+len(want)]==want
 return {'version':1,'elf_sha256':SHA,'ranges':ranges,'cases':cases,'boundary':'Global getDataDir/FileName descend are intercepted, only native order/arguments verified; actual provider source executes in portable replay. FX and expanded Send app bodies execute natively; Output boundary intercepted with tag-only mutation. Native stores are applied to independently executed actual Output baseline; actual Send and FX portable results are checked separately. No native Output/Channel behavior claim.'}
if __name__=='__main__':
 j=produce();p=pathlib.Path(__file__).with_name('fixtures.json')
 if '--write' in sys.argv:p.write_text(json.dumps(j,indent=2)+'\n')
 else:assert j==json.loads(p.read_text())
 print(len(j['cases']),'native cases')
