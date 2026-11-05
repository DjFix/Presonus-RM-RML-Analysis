import hashlib,json,subprocess,sys
from pathlib import Path
own=Path('uc-library/candidates/rolling200_impl_c17');out=Path('temp/recovery-work/rolling200_impl_c17');out.mkdir(exist_ok=True,parents=True)
sdk=Path('temp/core-upstream/root-integration-01/upstream-core/sdk')
mode=sys.argv[1]
def run(argv):
 print(' '.join(map(str,argv)),flush=True)
 p=subprocess.run(list(map(str,argv)),text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (out/(mode+'.log')).write_text(p.stdout);print(p.stdout);assert p.returncode==0
if mode=='compile':
 run(['g++','-std=c++17','-O0','-fno-inline','-ffunction-sections','-fdata-sections','-DCORE_USE_OPENSSL=1','-DNDEBUG=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Iuc-library/include','-isystem',sdk/'include/presonus-core-5','uc-library/src/Presonus/Panel/PresetNameCache.cpp',own/'replay.cpp','-Wl,--gc-sections',sdk/'lib/libcorelib.a',sdk/'lib/libpresonus_core_allocator.a','-pthread','-ldl','-lm','-o',out/'replay'])
elif mode=='symbols':
 p=subprocess.check_output(['nm','--defined-only',out/'replay'],text=True);(out/'symbols.log').write_text(p)
 for symbol in ['_ZNK8Presonus5Panel15PresetNameCache11getCapacityEv','_ZN8Presonus5Panel15PresetNameCache9CacheInfoC1Ev','_ZN8Presonus5Panel15PresetNameCache9CacheInfoC2Ev']:
  assert any(line.split()[-1]==symbol for line in p.splitlines()),symbol
 print('3 exact ELF mangled symbols retained; host C1/C2 may alias, native ranges remain separate')
elif mode=='replay':
 native=json.loads((own/'native.json').read_text());assert native['constructors'][0]['calls'][0]['text']=='* Empty Location *'
 assert native['constructors'][1]['calls'][0]['text']=='* Empty Location *'
 assert (own/'capacity.txt').read_text()==''.join(str(v)+'\n' for v in native['capacity_u32'])
 run([Path(sys.argv[2]) if len(sys.argv)>2 else out/'replay',own/'capacity.txt'])
else:raise SystemExit('unknown check')
