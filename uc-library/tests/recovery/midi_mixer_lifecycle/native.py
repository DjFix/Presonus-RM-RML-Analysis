"""Execute only exact original application destructor instructions.
Core calls are named boundaries; allocator boundary releases modeled arena.
No allocator internals, Core body, hardware or system calls are executed.
"""
import hashlib,json,pathlib,struct,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UcError,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
PACKETS=pathlib.Path('temp/recovery-work/rolling200-02/next-implementation16/prepared-midi-lifecycle16/packets')
FIXTURE=pathlib.Path('uc-library/tests/recovery/midi_mixer_lifecycle/fixtures.json')
ELF=pathlib.Path('rootfs/CS18_v13840/home/root/surface');SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
O=0x400000;REG=0x410000;ARR=0x411000;NORMAL=0x412000;PARAM=0x413000;STACK=0x500000;SP=STACK+0x8000;STOP=0x600000

def verified():
 raw=(ROOT/ELF).read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 bodies=[]
 with (ROOT/ELF).open('rb') as f:
  elf=ELFFile(f)
  symbols=list(elf.get_section_by_name('.symtab').iter_symbols())
  error=[x for x in symbols if x.name=='_ZN4Core11ConstVectorIPN8Presonus5Panel16ControlRegistrar8DelegateEE5errorE'];assert len(error)==1
  error=error[0];assert error['st_value']==0x26b15c and error['st_size']==4 and elf.get_section(error['st_shndx'])['sh_type']=='SHT_NOBITS'
  for n in [5,6,7]:
   j=json.loads((ROOT/PACKETS/f'rolling200_02_midi_lifecycle16_{n:02}'/'native-context.json').read_text());b=j['bodies'][j['roots'][0]];req=json.loads((ROOT/PACKETS/f'rolling200_02_midi_lifecycle16_{n:02}'/'request.json').read_text());s=elf.get_section(b['section_index']);offset=s['sh_offset']+b['address']-s['sh_addr'];assert offset==b['file_offset'] and s.name==b['section'];code=raw[offset:offset+b['size']];assert hashlib.sha256(code).hexdigest()==b['bytes_sha256']
   record={k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']};record['mangled']=req['targets'][0]['mangled'];rows=[x for x in symbols if x.name==record['mangled']];assert len(rows)==1
   row=rows[0];assert row['st_value']==b['address'] and row['st_size']==b['size'] and row['st_shndx']==b['section_index']
   assert req['targets'][0]['address']==b['address'] and req['targets'][0]['size']==b['size']
   bodies.append((record,code))
 return bodies

def execute(body,present,entries):
 b,code=body;u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 for a,z in [(b['address']&~4095,8192),(0x110000,0x10000),(0xa000,4096),(0x26b000,4096),(O,4096),(REG,0x10000),(STACK,0x10000),(STOP,4096)]:u.mem_map(a,z)
 u.mem_write(b['address'],code)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 values={0:0,1:O+0x90,2:REG+0x9000,3:REG+0xa000}
 w(O+0xe4,REG);w(O+0xe8,NORMAL);w(NORMAL,REG+0xb000);w(REG+8,ARR);w(REG+12,len(entries));w(0x26b15c,0)
 for i,v in enumerate(entries):w(ARR+4*i,values[v])
 trace=[];writes=[];release=[];cleanup=[]
 def ret():u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def hook(uc,a,size,user):
  r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1)
  if a==0x11acf0:
   assert r0==REG+0xb000 and r1==0xa007;trace.append('lookup');uc.reg_write(UC_ARM_REG_R0,PARAM if present else 0);ret()
  elif a==0x11e2e0:
   assert present and r0==PARAM and r1==O+0x10;trace.append('remove');ret()
  elif a==0x11b5e0:
   assert r0==O+0xc;trace.append('cleanup');cleanup.extend([next(k for k,v in values.items() if v==r(ARR+4*i)) for i in range(r(REG+12))]);ret()
  elif a==0xad5c:
   assert r0==O and not release;trace.append('delete');release.append({'target':a,'receiver':r0,'scope':'observed exact D0 call; modeled allocator arena release, not original allocator body'});u.mem_unmap(O,4096);ret()
  else:assert b['address']<=a and a+size<=b['address']+b['size'],hex(a)
 def write(uc,access,a,size,value,user):
  assert STACK<=a and a+size<=SP or O<=a and a+size<=O+0x100 or ARR<=a and a+size<=ARR+len(entries)*4 or a==REG+12,(hex(a),size)
  if not STACK<=a<STACK+0x10000:writes.append([a,size,value])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.reg_write(UC_ARM_REG_R0,O);u.reg_write(UC_ARM_REG_SP,SP);u.reg_write(UC_ARM_REG_LR,STOP);u.emu_start(b['address'],STOP,count=2000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 freed=False
 try:u.mem_read(O,4)
 except UcError:freed=True
 assert freed==b['mangled'].endswith('D0Ev')
 if 1 in entries:assert r(ARR+4*(len(entries)-1))==0
 return {'variant':int(b['mangled'][-3]),'present':present,'entries':entries,'trace':trace,'remaining_at_cleanup':cleanup,'modeled_arena_released':freed,'deallocation_calls':release,'writes':writes}

def produce():
 bodies=verified();patterns=[[],[0],[2],[1],[2,1,0],[1,2,1,0],[0,2,1,3],[2,3,1],[1,1],[0,1,0]]
 cases=[execute(body,present,entries) for body in bodies for present in [0,1] for entries in patterns]
 assert bodies[1][0]['address']!=bodies[2][0]['address']
 return {'elf_sha256':SHA,'firmware':'CS18AI surface 13840','role':'client','ranges':[b for b,_ in bodies],'d1_d2_alias':False,'scope':'restricted original ARM application execution; named Core/allocator boundaries, no Core or original allocator internals','cases':cases}
if __name__=='__main__':
 result=produce();path=ROOT/FIXTURE
 if '--verify' in sys.argv:assert result==json.loads(path.read_text());print('PASS native re-observation',len(result['cases']),'cases; three separately verified original identities/ranges')
 else:path.write_text(json.dumps(result,indent=2)+'\n');print('Generated',len(result['cases']),'original instruction cases')
