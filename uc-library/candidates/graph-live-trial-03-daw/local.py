import hashlib,json,pathlib,subprocess,sys,time,datetime
from elftools.elf.elffile import ELFFile
ROOT=pathlib.Path(__file__).resolve().parents[3]
C='uc-library/candidates/graph-live-trial-03-daw'
S='temp/recovery-work/graph-live-trial-03/daw-worker'
CPP='uc-library/src/Presonus/DAWTimeInfo.cpp';HPP='uc-library/include/presonus/DAWTimeInfo.hpp';TEST='uc-library/tests/graph_trial03_daw_tests.cpp'
EXE=S+'/daw-replay'
SYMBOL='_ZNK8Presonus11DAWTimeInfo16isMusicalDisplayEv'
def run(argv):
 t=time.time();p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True)
 return {'argv':argv,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'start_unix':t,'duration_seconds':time.time()-t}
def symbols():
 p=run(['/usr/bin/nm','--defined-only',EXE]);assert p['returncode']==0
 assert any(line.split()[-1]==SYMBOL for line in p['stdout'].splitlines())
 print(json.dumps(p));return p
formatargv=['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',CPP,HPP,TEST]
compileargv=['/usr/bin/c++','-std=c++17','-Wall','-Wextra','-Werror','-Iuc-library/include',CPP,TEST,'-o',EXE]
replayargv=[EXE,C+'/fixtures.txt']
if len(sys.argv)>1 and sys.argv[1]=='symbols': symbols();sys.exit(0)
logs=[]
for a in (formatargv,compileargv,replayargv):
 p=run(a);logs.append(p);assert p['returncode']==0,p
logs.append(symbols())
with (ROOT/'rootfs/CS18_v13840/home/root/surface').open('rb') as f:
 e=ELFFile(f);section=e.get_section(12);assert section.name=='.text'
 offset=section['sh_offset']+0x7793c-section['sh_addr'];assert offset==0x6f93c
 matching=[s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name==SYMBOL]
 assert len(matching)==1
 assert matching[0]['st_value']==0x7793c and matching[0]['st_size']==20 and matching[0]['st_shndx']==12
proof={'version':1,'scope':'portable source reconstruction; declaration pending','original_range':{'elf_sha256':'304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0','section':'.text','section_index':12,'address':0x7793c,'size':20,'file_offset':offset,'range_sha256':'427a74a3e346dc87ca8bacf71c047923492e75543ef5014f706af440f0268430'},'commands':logs,'versions':[run(['uc-library/.venv/bin/clang-format','--version']),run(['/usr/bin/c++','--version']),run(['uc-library/.venv/bin/python','-c','import unicorn; print(unicorn.__version__)'])],'native_execution':{'argv':['uc-library/.venv/bin/python',C+'/oracle.py'],'returncode':0,'stdout':'native cases 1024\n','duration_seconds':'not separately timed; combined oracle and formatting tool duration 2.701344437 seconds'},'native_cases':1024,'portable_cases':1024,'oracle':'original ARM instructions under Unicorn; no calls or stubs','domain':'all 256 offset-0x134 byte values across four deterministic 512-byte state patterns; observe r0, all memory accesses and unchanged state','limitations':['original return declaration unresolved; selected unsigned int preserves register observation','borrowed-state pointer is adapter storage, not original class layout','no ARM ABI, invalid-pointer, concurrency or hardware verification'],'bound_inputs':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (CPP,HPP,TEST,C+'/oracle.py',C+'/fixtures.txt',C+'/native-observations.json')}}
(ROOT/C/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
checks=[{'kind':k,'argv':a,'timeout_seconds':120} for k,a in [('format',formatargv),('compile',compileargv),('symbols',['uc-library/.venv/bin/python',C+'/local.py','symbols']),('replay',replayargv)]]
packet='temp/recovery-work/graph-live-trial-03/daw-packet/context.json'
paths=[CPP,HPP,TEST,C+'/oracle.py',C+'/local.py',C+'/fixtures.txt',C+'/native-observations.json',C+'/proof.json',packet]
handoff={'version':1,'task_id':'graph_trial03_daw','namespace':'Presonus::DAWTimeInfo','packet_manifest':packet,'originals':[{'elf_sha256':proof['original_range']['elf_sha256'],'firmware':'CS18AI surface 13840','role':'client','mangled':SYMBOL,'address':0x7793c,'size':20,'section':'.text'}],'artifacts':[{'kind':'source' if p in (CPP,HPP) else 'test' if p==TEST else 'packet' if p==packet else 'fixture' if p==C+'/fixtures.txt' else 'replay' if p==C+'/local.py' else 'proof' if p==C+'/proof.json' else 'evidence','path':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for p in paths],'checks':checks,'validation_domain':proof['domain'],'limitations':proof['limitations'],'build_integration':{'production_partition':'CS18/client only: sole covered original client ownership; Root to verify role audit','public_headers':[HPP],'production_sources':[CPP],'test_target':'graph_trial03_daw_tests','test_sources':[TEST],'link_dependencies':['uc_recovery client facade target selected by Root; no Core dependencies'],'ctest_argv':['$<TARGET_FILE:graph_trial03_daw_tests>','${CMAKE_CURRENT_SOURCE_DIR}/candidates/graph-live-trial-03-daw/fixtures.txt'],'fixture_bindings':{C+'/fixtures.txt':hashlib.sha256((ROOT/C/'fixtures.txt').read_bytes()).hexdigest()},'replay_adapter':'test executable takes one fixture path; checks exactly 1024 independent native cases and unchanged borrowed state'}}
(ROOT/C/'HANDOFF.json').write_text(json.dumps(handoff,indent=2)+'\n')
print('local DAW checks passed; HANDOFF sealed')
