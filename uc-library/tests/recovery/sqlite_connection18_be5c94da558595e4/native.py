"""Exact Outgoing process plus its actual same-ELF Connection process body.

Core, queue/I/O/factory and other app boundaries remain intercepted. Native
control flow, not the source port, defines the expected immediate join behavior.
"""
import hashlib,io,json,pathlib,struct,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
ROOT=pathlib.Path(__file__).resolve().parents[4];HERE=pathlib.Path(__file__).resolve().parent
PACKETS=ROOT/'temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/connection_eighteen_sol61/packet-r3/tasks'
OUT='_ZN8Presonus2UC18OutgoingConnection7processEb'
BASE='_ZN8Presonus2UC10Connection7processEb'
sha=lambda data:hashlib.sha256(data).hexdigest()
results=[]
for entry in json.loads((PACKETS/HERE.name/'CONTEXT.json').read_text())['originals']:
 original=entry['original'];data=(ROOT/original['elf_path']).read_bytes();assert sha(data)==original['elf']
 elf=ELFFile(io.BytesIO(data));symbols=elf.get_section_by_name('.symtab')
 def sym(name):
  rows=symbols.get_symbol_by_name(name);assert rows and len(rows)==1,name;return rows[0]
 def verify(record):
  s=sym(record['mangled']);section=elf.get_section(s['st_shndx']);off=section['sh_offset']+s['st_value']-section['sh_addr']
  assert (s['st_value'],s['st_size'],s['st_shndx'],off)==(record['address'],record['size'],record['section'],record['file_offset'])
  assert sha(data[off:off+s['st_size']])==record['range_sha256']
  return s['st_value'],s['st_value']+s['st_size']
 base_record=next(x['original'] for x in json.loads((PACKETS/'sqlite_connection18_b9e611f2d3b25ff5/CONTEXT.json').read_text())['originals'] if x['original']['elf']==original['elf'])
 ranges=[verify(original),verify(base_record)]
 names={'_ZNK8Presonus2UC10EventQueue7isEmptyEv':'empty','_ZN8Presonus2UC18OutgoingConnection8activateEv':'activate','_ZN8Presonus2UC10EventQueue5flushEv':'flush','_ZN8Presonus2UC10Connection10readEventsEv':'read','_ZN8Presonus2UC10Connection11writeEventsEb':'write','_ZN8Presonus2UC10EventQueue13retrieveEventEv':'retrieve','_ZN8Presonus2UC16SocketConnection7Channel9hasErrorsEi':'error','UCReportMessage':'report'}
 boundaries={sym(name)['st_value']:kind for name,kind in names.items()}
 channel_table=sym('_ZTVN8Presonus2UC16SocketConnection7ChannelE');section=elf.get_section(channel_table['st_shndx']);off=section['sh_offset']+channel_table['st_value']-section['sh_addr'];table=data[off:off+channel_table['st_size']]
 assert struct.unpack_from('<I',table,8+6*4)[0]==sym('_ZN8Presonus2UC16SocketConnection7Channel9hasErrorsEi')['st_value']
 cases=[]
 for mode,queued,resolve,error in [('empty',0,0,0),('failure',1,0,0),('success',1,1,0),('posterror',1,1,1)]:
  cpu=Uc(UC_ARCH_ARM,UC_MODE_ARM);cpu.mem_map(0,0x1000000)
  for segment in elf.iter_segments():
   if segment['p_type']=='PT_LOAD':cpu.mem_write(segment['p_vaddr'],segment.data())
  receiver,channel,vtable,stack,stop=0x800000,0x820000,0x890000,0x901000,0xa00000
  def put(address,value):cpu.mem_write(address,struct.pack('<I',value))
  def get(address):return int.from_bytes(cpu.mem_read(address,4),'little')
  put(channel,vtable);put(vtable+24,sym('_ZN8Presonus2UC16SocketConnection7Channel9hasErrorsEi')['st_value'])
  for reg,value in ((UC_ARM_REG_R0,receiver),(UC_ARM_REG_R1,0),(UC_ARM_REG_SP,stack),(UC_ARM_REG_LR,stop)):cpu.reg_write(reg,value)
  state={'remaining':queued,'base':0,'errors':0,'sent':0};calls=[];writes=[]
  def code(cpu,pc,size,_):
   if pc==ranges[1][0]:
    state['base']+=1;calls.append({'boundary':'actual-native-Connection::process','address':pc})
   if any(start<=pc<end for start,end in ranges):return
   assert pc in boundaries,('unmodeled native edge',hex(pc))
   kind=boundaries[pc];value=0;r0=cpu.reg_read(UC_ARM_REG_R0);r1=cpu.reg_read(UC_ARM_REG_R1)
   record={'boundary':kind,'address':pc,'r0':r0,'r1':r1}
   if kind=='empty':value=int(state['remaining']==0)
   elif kind=='activate':
    value=resolve
    if resolve:put(receiver+0x1b0,channel);put(receiver+0x13c,channel)
   elif kind=='flush':state['remaining']=0
   elif kind=='read':value=1
   elif kind=='write':state['sent']+=state['remaining'];state['remaining']=0;value=1
   elif kind=='retrieve':value=0 # Live, empty actual incoming-queue contract.
   elif kind=='error':state['errors']+=1;value=error
   elif kind=='report':record['format']=bytes(cpu.mem_read(r1,128)).split(b'\0')[0].decode()
   calls.append(record);cpu.reg_write(UC_ARM_REG_R0,value);cpu.reg_write(UC_ARM_REG_PC,cpu.reg_read(UC_ARM_REG_LR))
  def write(cpu,access,address,size,value,_):
   if receiver<=address<receiver+0x1c0:writes.append([address-receiver,size,value])
  cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write);cpu.emu_start(ranges[0][0],stop,count=1000)
  assert cpu.reg_read(UC_ARM_REG_PC)==stop and cpu.reg_read(UC_ARM_REG_SP)==stack
  cases.append({'input':{'mode':mode,'queued':queued,'resolve':resolve,'post_error':error},'calls':calls,'writes':writes,'projection':[state['base'],state['errors'],int(state['remaining']!=0),cpu.mem_read(receiver+0x30,1)[0],int(get(receiver+0x1b0)!=0),state['sent']]})
 results.append({'original':original,'nested_original':base_record,'cases':cases,'channel_vtable':{'address':channel_table['st_value'],'section':channel_table['st_shndx'],'file_offset':off,'sha256':sha(table),'hasErrors_slot6':sym('_ZN8Presonus2UC16SocketConnection7Channel9hasErrorsEi')['st_value']}})
output=json.dumps({'kind':'original same-ELF native caller AND actual assigned base-body execution; external effects intercepted','producer_sha256':sha(pathlib.Path(__file__).read_bytes()),'observations':results},indent=2)+'\n'
fixture=HERE/'fixtures.json'
if '--verify' in sys.argv:assert fixture.read_text()==output
else:fixture.write_text(output)
print('Outgoing process:2 exact outer ranges +2 exact same-ELF base ranges,8 native caller/base executions; inactive join and post-error effects observed')
