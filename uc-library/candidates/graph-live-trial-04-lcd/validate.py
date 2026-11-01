import sys,subprocess,json,hashlib,re
from pathlib import Path
from elftools.elf.elffile import ELFFile
base=Path('uc-library/candidates/graph-live-trial-04-lcd');scratch=Path('temp/recovery-work/graph-live-trial-04/lcd-worker');exe=scratch/'replay'
source=['uc-library/include/presonus/panel/MixerLCD.hpp','uc-library/src/Presonus/Panel/MixerLCD.cpp','uc-library/tests/graph_trial04_lcd_tests.cpp']
mode=sys.argv[1]
if mode=='format': subprocess.run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*source],check=True)
elif mode=='compile': subprocess.run(['c++','-std=c++17','-Iuc-library/include',source[1],source[2],'-o',str(exe)],check=True)
elif mode=='symbols':
 symbols=subprocess.check_output(['nm',str(exe)],text=True)
 for n in ['8previous','4next','2up','4down','5store']:assert '_ZNK8Presonus5Panel8MixerLCD'+n+'Ev' in symbols
 (scratch/'symbols.txt').write_text(symbols)
elif mode=='replay':
 if len(sys.argv)>2: exe=Path(sys.argv[2])
 actual=list(map(int,subprocess.check_output([str(exe)],text=True).split()));fixtures=json.loads((base/'native-fixtures.json').read_text())
 for row in fixtures:assert actual[row['packet']-1]==row['trace'][1][1]
 print('20 boundary observations matched; void source return intentionally unresolved')
elif mode=='ranges':
 path=Path('rootfs/RML16AI_Rack_13731/home/root/mixer');assert hashlib.sha256(path.read_bytes()).hexdigest()=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
 ranges=[]
 with path.open('rb') as f:
  elf=ELFFile(f)
  for i in range(1,6):
   text=Path(f'temp/recovery-work/graph-live-trial-04/trial04_lcd_{i}-packet/ELF_CONTEXT.md').read_text();addr=int(re.search(r'address `0x([a-f0-9]+)',text)[1],16);section=elf.get_section(12);offset=addr-section['sh_addr']+section['sh_offset'];f.seek(offset);digest=hashlib.sha256(f.read(32)).hexdigest();assert digest==re.search(r'SHA256 `([a-f0-9]+)',text)[1];ranges.append(dict(packet=i,address=addr,size=32,section=section.name,file_offset=offset,sha256=digest))
 (base/'range-proof.json').write_text(json.dumps(ranges,indent=2)+'\n')
