"""Original ARM target observations with explicitly stubbed application boundaries."""
import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
ROOT=Path(__file__).resolve().parents[5]
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
ORIGINALS=[{'address': 468868,
  'demangled': 'Presonus::Panel::StormFrontPanelComponent::cleanup()',
  'elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07',
  'firmware': 'RM/RML mixer 13731',
  'mangled': '_ZN8Presonus5Panel24StormFrontPanelComponent7cleanupEv',
  'range': {'address': 468868,
            'file_offset': 436100,
            'section': '.text',
            'section_index': 12,
            'sha256': 'a183d57173bc0f8ff20545d5ebeca7937507daf648232158e20bae335c377065',
            'size': 20},
  'role': 'server',
  'section': 12,
  'size': 20},
 {'address': 469308,
  'demangled': 'Presonus::Panel::StormFrontPanelComponent::mixSceneRecalled(Presonus::StormMixSceneComponent '
               'const&)',
  'elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07',
  'firmware': 'RM/RML mixer 13731',
  'mangled': '_ZN8Presonus5Panel24StormFrontPanelComponent16mixSceneRecalledERKNS_22StormMixSceneComponentE',
  'range': {'address': 469308,
            'file_offset': 436540,
            'section': '.text',
            'section_index': 12,
            'sha256': '39a5c358e8324c276566125503d7ce7ba90766898f2a011cdf5e8b58143d013d',
            'size': 20},
  'role': 'server',
  'section': 12,
  'size': 20},
 {'address': 469276,
  'demangled': 'Presonus::Panel::StormFrontPanelComponent::mixSceneEnterStoreState(Presonus::StormMixSceneComponent '
               'const&)',
  'elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07',
  'firmware': 'RM/RML mixer 13731',
  'mangled': '_ZN8Presonus5Panel24StormFrontPanelComponent23mixSceneEnterStoreStateERKNS_22StormMixSceneComponentE',
  'range': {'address': 469276,
            'file_offset': 436508,
            'section': '.text',
            'section_index': 12,
            'sha256': '435f8c87cacaa375e82104cb65e6f4fc34bcc426e6799db12fa102027da909d6',
            'size': 24},
  'role': 'server',
  'section': 12,
  'size': 24},
 {'address': 469244,
  'demangled': 'Presonus::Panel::StormFrontPanelComponent::mixSceneExitStoreState(Presonus::StormMixSceneComponent '
               'const&)',
  'elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07',
  'firmware': 'RM/RML mixer 13731',
  'mangled': '_ZN8Presonus5Panel24StormFrontPanelComponent22mixSceneExitStoreStateERKNS_22StormMixSceneComponentE',
  'range': {'address': 469244,
            'file_offset': 436476,
            'section': '.text',
            'section_index': 12,
            'sha256': '39eaf5ce35017af975f9506bbe675d28cb408812eced787e746a50ff74867fb8',
            'size': 24},
  'role': 'server',
  'section': 12,
  'size': 24},
 {'address': 469336,
  'demangled': 'Presonus::Panel::StormFrontPanelComponent::setMuteGroupDirty(Presonus::StormMuteGroupComponent '
               'const&, int, bool)',
  'elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07',
  'firmware': 'RM/RML mixer 13731',
  'mangled': '_ZN8Presonus5Panel24StormFrontPanelComponent17setMuteGroupDirtyERKNS_23StormMuteGroupComponentEib',
  'range': {'address': 469336,
            'file_offset': 436568,
            'section': '.text',
            'section_index': 12,
            'sha256': '49b317a6fb12f18b299736c35e56f395858cbea5c31d17fe2fb9265bf930765d',
            'size': 28},
  'role': 'server',
  'section': 12,
  'size': 28},
 {'address': 469372,
  'demangled': 'Presonus::Panel::StormFrontPanelComponent::setAllMutesGroupDirty(Presonus::StormMuteGroupComponent '
               'const&, bool)',
  'elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07',
  'firmware': 'RM/RML mixer 13731',
  'mangled': '_ZN8Presonus5Panel24StormFrontPanelComponent21setAllMutesGroupDirtyERKNS_23StormMuteGroupComponentEb',
  'range': {'address': 469372,
            'file_offset': 436604,
            'section': '.text',
            'section_index': 12,
            'sha256': 'c7a85d914b10b3d7c59df52db55703ab7e90d3c05348e90190df599dab7d19cb',
            'size': 32},
  'role': 'server',
  'section': 12,
  'size': 32},
 {'address': 467404,
  'demangled': 'Presonus::Panel::StormFrontPanelComponent::doFatChannelUpdate()',
  'elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07',
  'firmware': 'RM/RML mixer 13731',
  'mangled': '_ZN8Presonus5Panel24StormFrontPanelComponent18doFatChannelUpdateEv',
  'range': {'address': 467404,
            'file_offset': 434636,
            'section': '.text',
            'section_index': 12,
            'sha256': '4d1de92c201606c676bd15bb18a831e92e8059c3e802701238f51f5c64f7b007',
            'size': 96},
  'role': 'server',
  'section': 12,
  'size': 96},
 {'address': 469404,
  'demangled': 'Presonus::Panel::StormFrontPanelComponent::createLCD()',
  'elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07',
  'firmware': 'RM/RML mixer 13731',
  'mangled': '_ZN8Presonus5Panel24StormFrontPanelComponent9createLCDEv',
  'range': {'address': 469404,
            'file_offset': 436636,
            'section': '.text',
            'section_index': 12,
            'sha256': '11be2aaed35897ec410b8be0b2d6f4ac9777ccb43fc89fc0454d842673e11ffd',
            'size': 108},
  'role': 'server',
  'section': 12,
  'size': 108},
 {'address': 467500,
  'demangled': 'Presonus::Panel::StormFrontPanelComponent::doFatMeterUpdate(Presonus::Mixer::ChannelComponent&)',
  'elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07',
  'firmware': 'RM/RML mixer 13731',
  'mangled': '_ZN8Presonus5Panel24StormFrontPanelComponent16doFatMeterUpdateERNS_5Mixer16ChannelComponentE',
  'range': {'address': 467500,
            'file_offset': 434732,
            'section': '.text',
            'section_index': 12,
            'sha256': '67febf375879157085a559224a1f7078dcfea62262dc2f13b9b5d809f3d32db4',
            'size': 140},
  'role': 'server',
  'section': 12,
  'size': 140},
 {'address': 469092,
  'demangled': 'Presonus::Panel::StormFrontPanelComponent::blinkSceneButtons(bool)',
  'elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07',
  'firmware': 'RM/RML mixer 13731',
  'mangled': '_ZN8Presonus5Panel24StormFrontPanelComponent17blinkSceneButtonsEb',
  'range': {'address': 469092,
            'file_offset': 436324,
            'section': '.text',
            'section_index': 12,
            'sha256': 'b6423e093955ee75be9df70b439466f009341f41c4ff1ff3fe0f091ff1e52166',
            'size': 144},
  'role': 'server',
  'section': 12,
  'size': 144}]
REG=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
STOP=0x900000; OBJ=0x800000; REGISTRAR=0x801000; GROUP=0x802000; CTRL=0x810000; VTABLE=0x820000; SET=0x830000; LCD=0x840000

def execute(target,index,flag,scenario):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 with ELF.open('rb') as f:
  e=ELFFile(f)
  segs=[s for s in e.iter_segments() if s['p_type']=='PT_LOAD']
  lo=min(s['p_vaddr'] for s in segs)&~4095; hi=max(s['p_vaddr']+s['p_memsz'] for s in segs)
  u.mem_map(lo,(hi-lo+4095)&~4095)
  for s in segs:u.mem_write(s['p_vaddr'],s.data())
 u.mem_map(OBJ,0x110000);u.mem_map(0xa00000,0x10000)
 w=lambda a,v:u.mem_write(a,struct.pack('<I',v&0xffffffff))
 w(OBJ+0x90,REGISTRAR);w(OBJ+0x8c,0x850000)
 for i in range(64):w(CTRL+0x100*i,VTABLE);w(CTRL+0x100*i+0x18,i)
 w(VTABLE+0x10,SET)
 trace=[];groups={};current={};count=[-1,0,1,10][scenario]; tags=[0,1,2,7,8,3,4,5,6,9]
 def hook(u,a,size,data):
  r=[u.reg_read(x) for x in REG]
  event=None;out=None
  if a==STOP:u.emu_stop();return
  if a in [0x68c14,0x659f8,0x6fbe8,0x6f348]:
   event=[{0x68c14:1,0x659f8:2,0x6fbe8:3,0x6f348:4}[a],int(r[0]==OBJ),int(r[1]==0x860000) if a==0x6f348 else 0,0]
  elif a==0x8e4ac:
   out=GROUP+r[1]*0x100;groups[out]=r[1];event=[5,r[1],0,0]
  elif a==0x8d9ec:
   g=groups[r[0]];out=CTRL+r[1]*0x100;current[out]=(g,r[1]);event=[6,g,r[1],0]
  elif a==SET:
   g,t=current[r[0]];event=[7,g,t,r[2],r[1]]
  elif a==0x8db08:out=count;event=[8,count,0,0]
  elif a==0x8d9a8:
   i=r[1];out=0 if i==0 else CTRL+i*0x100;event=[9,i,0,0]
  elif a==0xacf4:
   i=(r[0]-CTRL)//0x100;out=0 if i==1 else r[0];w(r[0]+0x18,tags[i]);event=[10,i,0,0]
  elif a==0x8fbc8:event=[11,tags[(r[0]-CTRL)//0x100],r[1],0]
  elif a==0x525c4:event=[12,r[1],r[2],r[3]]
  elif a==0xa7e4:out=LCD;event=[13,r[0],0,0]
  elif a==0x622cc:event=[14,int(r[1]==OBJ),int(r[2]==0x850000),0]
  elif a==0x96628:event=[15,r[1],r[2],0]
  if event is not None:
   trace.append(event)
   if out is not None:u.reg_write(UC_ARM_REG_R0,out&0xffffffff)
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook)
 args=[OBJ,0x860000,index&0xffffffff,int(flag)]
 if target in [6,10]:args[2 if target==6 else 1]=int(flag)
 for r,v in zip(REG,args):u.reg_write(r,v)
 u.reg_write(UC_ARM_REG_SP,0xa0ff00);u.reg_write(UC_ARM_REG_LR,STOP)
 u.emu_start(ADDRESSES[target-1],STOP,count=20000)
 assert u.reg_read(UC_ARM_REG_PC)==STOP
 if target==8:trace.append([16,int(u.reg_read(UC_ARM_REG_R0)==LCD),0,0])
 return trace
ADDRESSES=[0x72784,0x7293c,0x7291c,0x728fc,0x72958,0x7297c,0x721cc,0x7299c,0x7222c,0x72864]
def main():
 raw=ELF.read_bytes()
 assert hashlib.sha256(raw).hexdigest()==SHA
 with ELF.open('rb') as f:
  e=ELFFile(f)
  table=e.get_section_by_name('.symtab')
  symbols={s.name:s for s in table.iter_symbols()}
  for o in ORIGINALS:
   r=o['range'];sec=e.get_section(o['section']);offset=sec['sh_offset']+o['address']-sec['sh_addr']
   assert offset==r['file_offset']
   assert hashlib.sha256(raw[offset:offset+o['size']]).hexdigest()==r['sha256']
   symbol=symbols[o['mangled']]
   assert symbol['st_value']==o['address'] and symbol['st_size']==o['size'] and symbol['st_shndx']==o['section']
 cases=[]
 for t in range(1,11):
  for i in ([-2147483648,-2,-1,0,1,5,2147483647] if t==5 else [0]):
   for flag in ([0,1] if t in [5,6,10] else [0]):
    for s in (range(4) if t in [3,4,10] else [3]):
     cases.append(dict(target=t,index=i,flag=flag,scenario=s,trace=execute(t,i,flag,s)))
 out=ROOT/'uc-library/tests/recovery/trial08/stormpanel/native-fixtures.json'
 observed={'elf_sha256':SHA,'originals':ORIGINALS,'cases':cases}
 import sys
 if '--verify' in sys.argv:
  assert json.loads(out.read_text())==observed
 else:out.write_text(json.dumps(observed,indent=2)+'\n')
 print('Original ARM executions:',len(cases))
if __name__=='__main__':main()
