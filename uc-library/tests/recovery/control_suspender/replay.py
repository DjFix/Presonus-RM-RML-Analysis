import argparse,hashlib,json,subprocess,sys,shlex,time,datetime
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
BASE=Path('uc-library/tests/recovery/control_suspender'); WORK=Path('temp/recovery-work/control-suspender-sol61'); WORK.mkdir(parents=True,exist_ok=True)
OWN=['uc-library/include/presonus/dsp/ControlSuspender.hpp','uc-library/include/presonus/dsp/audio_hal.hpp','uc-library/src/Presonus/Dsp/ControlSuspender.cpp','uc-library/tests/recovery/ControlSuspenderReplay.cpp','uc-library/tests/noaa_tcard_receive_start_tests.cpp','uc-library/tests/recovery/CardFirmwareReplay.cpp','uc-library/tests/recovery/CardHandlerLifecyclePropertiesReplay.cpp']
EXE=WORK/'replay'
def run(a,**kw):
 print(shlex.join(map(str,a)),flush=True)
 start=time.time();r=subprocess.run(list(map(str,a)),text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,**kw)
 with (WORK/'commands.jsonl').open('a') as f:f.write(json.dumps({'argv':list(map(str,a)),'cwd':str(kw.get('cwd',Path.cwd())),'start':start,'seconds':time.time()-start,'returncode':r.returncode,'stdout':r.stdout})+'\n')
 if r.returncode:raise RuntimeError(r.stdout)
 return r.stdout
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def native():
 p=Path('rootfs/RML16AI_Rack_13731/home/root/mixer');assert sha(p)=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
 data=p.read_bytes();assert hashlib.sha256(data[306348:306572]).hexdigest()=='9a50b1189572502672de8744a4227271e238189af9a600f2b5066f78fcb7b74b';code=data[159744:159800];assert hashlib.sha256(code).hexdigest()=='3198180a2da3425a5d7dc76cdd3c33fe98d2e48094ea760df3b50e22640fae91'
 def machine():
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x0,0x1100000)
  with p.open('rb') as f:
   for s in ELFFile(f).iter_segments():
    if s['p_type']=='PT_LOAD':u.mem_write(s['p_vaddr'],s.data())
  u.reg_write(UC_ARM_REG_SP,0xf00000);u.reg_write(UC_ARM_REG_LR,0xe00000);return u
 cases=[]
 for n in range(256):
  u=machine();u.mem_write(0xc00000,bytes([n]));u.mem_write(0xc01000,(0xc02000).to_bytes(4,'little'));u.mem_write(0xc0200c,(0xd00000).to_bytes(4,'little'));u.reg_write(UC_ARM_REG_R0,0xc00000);trace=[]
  def hook(u,a,s,x):
   if a==0x4c3c4:trace.append(['getter']);u.reg_write(UC_ARM_REG_R0,0xc01000);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   if a==0xd00000:trace.append(['suspend',u.reg_read(UC_ARM_REG_R0),u.reg_read(UC_ARM_REG_R1)]);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook);u.emu_start(192512,0xe00000,count=100);assert u.reg_read(UC_ARM_REG_PC)==0xe00000
  cases.append({'saved':n,'trace':trace,'return_this':u.reg_read(UC_ARM_REG_R0)==0xc00000})
 # Real provider's true path with a nonzero saved state avoids unrelated container calls.
 provider=[]
 for n in range(256):
  u=machine();literal=int.from_bytes(data[306348+216:306348+220],'little');u.mem_write(literal,bytes([n]));u.reg_write(UC_ARM_REG_R0,0xc01000);u.reg_write(UC_ARM_REG_R1,1);u.emu_start(339116,0xe00000,count=100);assert u.reg_read(UC_ARM_REG_PC)==0xe00000;assert u.reg_read(UC_ARM_REG_R0)==n;provider.append(n)
 # Complete native FX normal path, six channel loops and null mapping table.
 fx=[]
 fxcode=data[245860-32768:245860-32768+496]
 assert hashlib.sha256(fxcode).hexdigest()=='c71d20494b7b2ff4a61a03888ef4278eb4d6f1c46d9208f2a0a8bdc9393d19c2'
 for n in range(256):
  u=machine();trace=[]
  def word(a,v):u.mem_write(a,v.to_bytes(4,'little'))
  word(0xc00000,0xc02000);word(0xc01000,0xc03000);word(0xc02058,0xd01000);word(0xc0300c,0xd00000)
  for j in range(12):word(0xc000e8+4*j,0xc04000)
  word(0xc04000,0xc05000)
  for slot in [0x24,0x58]:word(0xc05000+slot,0xd01000)
  u.reg_write(UC_ARM_REG_R0,0xc00000);u.reg_write(UC_ARM_REG_R1,0)
  def fxhook(u,a,z,x):
   if a in [0x4c3c4,0xd00000,0xd01000,0x3a9e8,0x116a38]:
    ret=0
    if a==0x4c3c4:ret=0xc01000
    if a==0xd00000:trace.append([u.reg_read(UC_ARM_REG_R0),u.reg_read(UC_ARM_REG_R1)]);ret=0x12340000+n
    u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,fxhook);u.emu_start(245860,0xe00000,count=2000);assert u.reg_read(UC_ARM_REG_PC)==0xe00000
  saved=u.mem_read(0xf00000-4-0x25,1)[0];assert saved==n
  assert trace==([[0xc01000,1],[0xc01000,0]] if n==0 else [[0xc01000,1]])
  fx.append({'return_word':0x12340000+n,'saved_byte':saved,'hal_trace':trace})
 return {'elf_sha256':sha(p),'range_sha256':hashlib.sha256(code).hexdigest(),'d1_cases':cases,'provider_true_return':provider,'fx_normal_cases':fx,'boundaries':'getter and virtual HAL call stubbed for D1; provider true nonzero path executed without boundary calls; zero path executed with empty provider containers; no original ctor execution'}
p=argparse.ArgumentParser();p.add_argument('mode');p.add_argument('--record',action='store_true');p.add_argument('--executable');p.add_argument('--fixtures',default=str(BASE/'native_observations.json'));p.add_argument('--fixture-sha256');o=p.parse_args()
if o.executable:EXE=Path(o.executable)
if o.mode=='format':print(run(['uc-library/.venv/bin/clang-format','--version']));print(run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWN]))
elif o.mode=='compile':print(run(['c++','-std=c++17','-Iuc-library/include',OWN[2],OWN[3],'-o',EXE]))
elif o.mode=='symbols':
 s=run(['nm','--defined-only',EXE]);assert '_ZN8Presonus3Dsp16ControlSuspenderD1Ev' in s;print('D1 present; emitted D2 is compiler alias, not additional recovered identity')
elif o.mode=='native':
 n=native();f=BASE/'native_observations.json'
 if f.exists() and not o.record:assert json.loads(f.read_text())==n
 else:f.write_text(json.dumps(n,indent=2)+'\n')
 print('Native D1: 256 saved-byte cases; real provider true: 256; full FX normal caller: 256')
elif o.mode=='replay':
 assert not o.fixture_sha256 or sha(o.fixtures)==o.fixture_sha256
 n=json.loads(Path(o.fixtures).read_text());lines=run([EXE]).splitlines();assert len(lines)==256
 for row,line in zip(n['d1_cases'],lines):assert line==str(row['saved'])+':'+str(int(bool(row['trace'])));assert row['return_this']
 print('256 native/portable destructor traces agree; nested/unwind/failure assertions passed')
elif o.mode=='regressions':
 canonical=Path('/home/rs/projects/opencs/ai-line-analysis');build=canonical/'temp/core-upstream/root-integration-01';cc=json.loads((build/'compile_commands.json').read_text());here=Path.cwd()
 for source,target in [(OWN[4],'noaa_tcard_receive_start_tests'),(OWN[5],'card_firmware_replay'),(OWN[6],'noaa_tcard_handler_lifecycle_properties_replay')]:
  entry=next(x for x in cc if x['file'].endswith('/'+source.removeprefix('uc-library/')));a=shlex.split(entry['command']);obj=WORK/(target+'.o');a[a.index('-o')+1]=str((here/obj).resolve());a[-1]=str((here/source).resolve());a[1:1]=['-MMD','-MF',str((here/WORK/(target+'.d')).resolve()),'-I'+str(here/'uc-library/include')];print(run(a,cwd=entry['directory']))
  link=shlex.split((build/('CMakeFiles/'+target+'.dir/link.txt')).read_text());link=[v for v in link if not v.startswith('-Wl,--dependency-file=')];idx=next(i for i,v in enumerate(link) if v.endswith('.o') and target+'.dir/' in v);link[idx]=str((here/obj).resolve());link[link.index('-o')+1]=str((here/WORK/target).resolve());print(run(link,cwd=build))
 print('Three affected prior executables freshly rebuilt against owned header')
