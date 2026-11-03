"""Exact hash-bound application ARM instructions; no Core instructions execute.

Direct MappingTable/sendMidiMessage/Component calls are intercepted, recording
arguments and returning to the original LR. The control callback can replace
borrowed descriptions. These traces prove application call boundaries only.
"""
from pathlib import Path
import hashlib,json,struct,random,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
PACKETS=Path('temp/recovery-work/frontier-small01/batch01/packets')
OBJ,TABLE,SECOND,STACK,STOP=0x1000000,0x1001000,0x1002000,0x1100000,0x1200000
NAMES=['','alpha','beta','gamma','delta']
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(index,case):
 case=json.loads(json.dumps(case)) # Canonical JSON inputs, including row arrays.
 p=PACKETS/f'frontier01_w04_{index:02}'
 c=json.loads((p/'context.json').read_text());nc=c['native_context'];nid=c['native_roots'][0];m=nc['nodes'][nid]['metadata'];b=nc['bodies'][nid]
 path=Path(nc['binaries'][m['elf']]['path']);raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==m['elf']
 block=raw[b['file_offset']:b['file_offset']+b['size']];assert hashlib.sha256(block).hexdigest()==b['bytes_sha256']
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 with path.open('rb') as f:
  elf=ELFFile(f);sec=elf.get_section(b['section_index']);assert sec['sh_addr']<=b['address'] and b['address']+b['size']<=sec['sh_addr']+sec['sh_size'];assert sec['sh_offset']+b['address']-sec['sh_addr']==b['file_offset']
  pages=set()
  for s in elf.iter_segments():
   if s['p_type']!='PT_LOAD':continue
   a,n=int(s['p_vaddr']),int(s['p_memsz'])
   for page in range(a&~4095,(a+n+4095)&~4095,4096):
    if page not in pages:u.mem_map(page,4096);pages.add(page)
   u.mem_write(a,s.data())
 u.mem_map(OBJ,0x4000);u.mem_map(STACK,0x10000);u.mem_map(STOP,4096);u.mem_write(OBJ,bytes([0xa5])*0x1000)
 if index==1:
  for base,rows in [(TABLE,case['rows']),(SECOND,case['replacement'])]:
   for i,(name,eligible) in enumerate(rows):
    record=bytearray(44);record[:len(NAMES[name])]=NAMES[name].encode();record[37]=eligible;u.mem_write(base+44*i,bytes(record))
   u.mem_write(base+44*len(rows),bytes(44))
  u.mem_write(OBJ+4,struct.pack('<I',0x1003000));u.mem_write(OBJ+0x98,struct.pack('<I',TABLE))
 if index==2:u.mem_write(OBJ+0xaec,bytes(case['identity']))
 u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,case.get('enabled',case.get('accepted',0)));u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP)
 calls=[];writes=[];executed=[]
 boundary={1:0x7630c,2:0xc0480}.get(index,0x11b5e0)
 def code(uc,a,size,_):
  if a==boundary:
   r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);r2=uc.reg_read(UC_ARM_REG_R2)
   if index==1:
    name=bytes(uc.mem_read(r1,32)).split(b'\0')[0].decode();calls.append({'name':name,'enabled':r2,'mapping_identity':r0})
    if case['mutate'] and len(calls)==1:uc.mem_write(OBJ+0x98,struct.pack('<I',SECOND))
   elif index==2:calls.append({'message':list(uc.mem_read(r1,r2)),'size':r2,'this':r0})
   else:calls.append({'provider':'Core::Portable::Component::~Component()','this':r0})
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
  assert b['address']<=a<b['address']+b['size'],hex(a)
  executed.append(a)
 def write(uc,access,a,size,value,_):
  if OBJ<=a<OBJ+0x1000:writes.append({'offset':a-OBJ,'size':size,'value':value})
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write);u.emu_start(b['address'],STOP,count=10000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 if index==1:observed=[x for call in calls for x in [NAMES.index(call['name']),call['enabled']]]
 elif index==2:observed=calls[0]['message'];assert len(calls)==1
 else:observed=None;assert len(calls)==1
 return {'input':case,'observed':observed,'calls':calls,'writes':writes,'executed_addresses':executed,'return_word':u.reg_read(UC_ARM_REG_R0),'range':{k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},'original':{'elf_sha256':m['elf'],'mangled':m['mangled']},'packet_sha256':digest(p/'context.json')}
def generate():
 controls=[]
 for enabled in [0,1]:
  for rows in [[],[(1,0)],[(1,1)],[(1,255),(2,0),(3,1),(4,128)],[(1,0),(2,1),(3,0),(4,1)],[(1,1),(0,255),(2,1)]]:
   for mutate in [0,1]:controls.append(run(1,{'enabled':enabled,'rows':rows,'replacement':[(4,1),(3,255),(2,0),(1,1)],'mutate':mutate}))
 rng=random.Random(20261103);identities=[[0]*8,[255]*8,list(range(8)),[128,127,128,129,254,255,0,1]]+[[rng.randrange(256) for _ in range(8)] for _ in range(64)]
 messages=[run(2,{'accepted':accepted,'identity':identity}) for accepted in [0,1] for identity in identities]
 destructors=[run(i,{}) for i in range(3,9)]
 return {'schema':1,'native_domain':'Exact original application execution with direct external-call interception; no Core instructions. Descriptor rebind after first call, terminated lists and eligibility bytes; 136 connection messages. D1 app dispatch writes and provider call only.','controls':controls,'messages':messages,'destructors':destructors}
if __name__=='__main__':
 result=generate()
 if len(sys.argv)>2:assert result==json.loads(Path(sys.argv[2]).read_text())['native']
 Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n');print('native ARM:',len(result['controls']),len(result['messages']),len(result['destructors']))
