"""Negative-domain witness: existing original and portable helper require tag600."""
import hashlib,json,os,subprocess,struct,datetime
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_INVALID,UcError
from unicorn.arm_const import *
BASE=Path('uc-library/candidates/rolling200-02-groups-page');WORK=Path('temp/recovery-work/rolling200-02/groups-page');OUT=Path('evidence/recovery/2026-11-05/rolling200-02/groups-page')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
elf=Path('rootfs/CS18_v13840/home/root/surface');assert sha(elf)=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x280000);u.mem_map(0x300000,0x10000);u.mem_map(0x800000,0x10000)
with elf.open('rb') as f:
 e=ELFFile(f);s=e.get_section(12);assert s.name=='.text';offset=0x928d8-s['sh_addr']+s['sh_offset'];body=elf.read_bytes()[offset:offset+316];assert hashlib.sha256(body).hexdigest()=='c0fa80c366dd95821b354a0e600c9c5a9ed9f695525950db85b2a097b67d2ea7'
 for segment in e.iter_segments():
  if segment['p_type']=='PT_LOAD':u.mem_write(segment['p_vaddr'],segment.data())
trace=[];faults=[]
def ret(v=None):
 if v is not None:u.reg_write(UC_ARM_REG_R0,v)
 u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
def code(uc,pc,size,_):
 trace.append(pc)
 if pc==0x11acf0:
  assert uc.reg_read(UC_ARM_REG_R1)==600;ret(0)
 elif pc==0x24268:
  assert uc.reg_read(UC_ARM_REG_R1)==0;uc.mem_write(uc.reg_read(UC_ARM_REG_R0),b'\0');ret()
 else:assert 0x928d8<=pc<0x928d8+316,hex(pc)
def invalid(uc,access,address,size,value,_):faults.append(dict(pc=uc.reg_read(UC_ARM_REG_PC),access=access,address=address,size=size));return False
u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_INVALID,invalid);u.reg_write(UC_ARM_REG_SP,0x808000);u.reg_write(UC_ARM_REG_LR,0x810000);u.reg_write(UC_ARM_REG_R0,0x300000);u.reg_write(UC_ARM_REG_R1,0x300400)
try:u.emu_start(0x928d8,0x810000,count=100)
except UcError as ex:error=str(ex)
else:raise AssertionError('expected original missing-tag600 read fault')
assert faults[0]['pc']==0x92918 and faults[0]['address']==0
(OUT/'missing-tag600-native-witness.json').write_text(json.dumps(dict(elf_sha256=sha(elf),helper_mangled='_ZNK8Presonus7Surface19GroupsPageComponent12isValidGroupEPN4Core8Portable9ComponentE',range=dict(address=0x928d8,size=316,section='.text',section_index=12,file_offset=offset,sha256=hashlib.sha256(body).hexdigest()),native_entry='direct helper with getParameterByTag(600) capture returning null; no Core binary body executed',instructions=trace,faults=faults,error=error,unicorn_version=unicorn.__version__,producer_sha256=sha(__file__)),indent=2)+'\n')
env=os.environ.copy();env['TMPDIR']=str(WORK.resolve());env['LD_LIBRARY_PATH']=str(WORK.resolve());commands=[]
def run(argv,name,input=None):
 p=subprocess.run(argv,input=input,text=True,capture_output=True,env=env);(OUT/(name+'.stdout')).write_text(p.stdout);(OUT/(name+'.stderr')).write_text(p.stderr);commands.append(dict(argv=argv,returncode=p.returncode,stdout_sha256=hashlib.sha256(p.stdout.encode()).hexdigest(),stderr_sha256=hashlib.sha256(p.stderr.encode()).hexdigest()));return p
flags=['-std=c++17','-g','-O0','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework','-fsanitize=address,undefined','-fno-sanitize=vptr','-fno-omit-frame-pointer']
p=run(['c++',*flags,'-finstrument-functions','-c','uc-library/src/Presonus/Surface/GroupsPageRecovery.cpp','-o',str(WORK/'recovery-current-asan.o')],'witness-current-compile');assert p.returncode==0,p.stderr
p=run(['c++',*flags,'-rdynamic',str(BASE/'replay.cpp'),str(WORK/'unit0.o'),str(WORK/'recovery-current-asan.o'),'temp/core-upstream/root-integration-01/libpresonus_uc.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-pthread','-ldl','-lm','-o',str(WORK/'witness-current-asan')],'witness-current-link');assert p.returncode==0,p.stderr
link=WORK/'libdns_sd.so.1'
if not link.exists():link.symlink_to(Path('temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so').resolve())
input='4 999 3 1065353216 0 0 -1 0 -1 1 4 0 0 0 0\n';p=run([str(WORK/'witness-current-asan')],'witness-current-portable',input);assert p.returncode!=0
assert 'GroupsPageComponent::isValidGroup' in p.stderr and 'GroupsPageComponent::updateGroups' in p.stderr and 'GroupsPageComponent::addGroup' in p.stderr,p.stderr
paths=[str(BASE/'witness.py'),str(BASE/'replay.cpp'),'uc-library/src/Presonus/Surface/GroupsPageRecovery.cpp','uc-library/src/Presonus/Surface/GroupsPageComponent.cpp','uc-library/include/presonus/surface/GroupsPageComponent.hpp']
(OUT/'missing-tag600-comparison.json').write_text(json.dumps(dict(date=datetime.datetime.now(datetime.timezone.utc).isoformat(),input=input,commands=commands,sources={p:sha(p) for p in paths},native_witness_sha256=sha(OUT/'missing-tag600-native-witness.json'),conclusion='Original isValidGroup and existing source both require tag600 on every group traversed by updateGroups. addGroup skips missing tag600 in its scan but its final updateGroups can fault. This negative input is preserved; safe full-tree handling is not claimed. No helper change or reconstructed helper credit.',retry_condition='Intentional input-validation adaptation authorized in separately owned dependency work, or caller enforces every child tag600; do not retry unchanged original-invalid input as successful reconstruction.'),indent=2)+'\n');print('negative original and portable witnesses agree')
