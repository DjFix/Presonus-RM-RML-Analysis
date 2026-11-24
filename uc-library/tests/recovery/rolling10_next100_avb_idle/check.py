import argparse,datetime,hashlib,json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
PHASE_RECORDS={'session_id': '/root/rolling10_spi', 'started': '2026-11-14T10:15:33.049377+00:00', 'target': {'original_elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07', 'mangled': '_ZN8Presonus3AVB12AvbComponent6onIdleEv', 'address': 690980, 'size': 96, 'section': 12, 'anchor': 'd9bb4ec7117e18150911a0abd7711d6482232f886aa45d163c0d648ce894962c', 'firmware': 'RM/RML mixer 13731', 'role': 'server'}, 'typed_frozen_evidence': {'/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/snapshot/temp/recovery-work/rolling10x10-20261114/selection/next100/avb-idle01/contracts/rolling10_next100_avb_idle.json': '216ffb2d7dec98571e3c09eaadcadde6d31013b3c07ed0dcb635a8d3100f10b8', '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/snapshot/temp/recovery-work/rolling10x10-20261114/selection/next100/avb-idle01/native/rolling10_next100_avb_idle.json': 'da7ed63c7db285537471eb11739f1176637f4a1bb2bee21bac44e60969a75290', '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/snapshot/temp/recovery-work/rolling10x10-20261114/selection/next100/avb-idle01/provider/PROVIDER.json': '27bf1b41f79e1e8582dabc2ac8909dad7c81643e9032cb7c5da34d32af5d1e02', '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/snapshot/uc-library/include/presonus/dice/packet_services.hpp': 'cf3e9129780ef49c137ebb8d7e904ca1e3ab1d1aa0b45a1288622143c695b079', '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/snapshot/uc-library/src/Presonus/DICE/PacketClockGateway.cpp': 'a44a01a71a9ac8be0abf8d886a0075b57ca6eea6405dedb3982ad50606ec15a0', '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/snapshot/third_party/ccl-framework/core/system/coretime.h': '112daede39c5e3fdf85a2a813afa729fbfeef05eb07dd831fccb1c1e401ebea1', '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/snapshot/third_party/ccl-framework/core/platform/shared/posix/coretime.posix.h': 'f58e058d5bcf234615fc2a7dad635bc6688fee34d253e419352f9cc5696c0555', '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/snapshot/uc-library/include/presonus/avb/AvbComponent.hpp': '952b4c4320aa83a1abc82e3f1fbea59fe86f29020c0728d9744d837f1f1c0143', '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/snapshot/uc-library/src/Presonus/AVB/AvbComponent.cpp': '7ed21e245c83bf8ebcc3f736b923cc549a7d2cad0bc21bef96ab9c28ce6dd34f'}, 'baseline_sources': {'uc-library/include/presonus/avb/AvbComponent.hpp': '952b4c4320aa83a1abc82e3f1fbea59fe86f29020c0728d9744d837f1f1c0143', 'uc-library/src/Presonus/AVB/AvbComponent.cpp': '7ed21e245c83bf8ebcc3f736b923cc549a7d2cad0bc21bef96ab9c28ce6dd34f'}}
PINNED_PROVIDER_SOURCES={'third_party/ccl-framework/core/portable/corecomponent.cpp': '79fc17cf36a2946eac7293284ce693072a1875844736e4f1d70c48e6757ce7f6', 'third_party/ccl-framework/core/portable/coreparams.cpp': 'd7986b98e2de685b206e0b26303e2dbcfafa56d7290345ac6fa9516bc79502b5'}
CONFIG={'task': 'rolling10_next100_avb_idle', 'cls': 'AvbComponent', 'other': 'SurfaceAvbComponent', 'mixer': True}
O=R/'temp/recovery-work'/CONFIG['task'];O.mkdir(parents=True,exist_ok=True)
OWNED=['uc-library/include/presonus/avb/'+CONFIG['cls']+'.hpp','uc-library/src/Presonus/AVB/'+CONFIG['cls']+'.cpp',str((T/'Replay.cpp').relative_to(R)),str((T/'RuntimeProvider.cpp').relative_to(R))]
SDK=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib')
ARCHIVES={str(SDK/'libcorelib.a'):'3c4f0825acb529fda135587b7ff5cb92ca0100bb417a20c034d3fdef80a93e0c',str(SDK/'libpresonus_core_allocator.a'):'69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d'}
FLAGS=['/usr/bin/c++','-std=c++17','-O0','-fno-rtti','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework']
COMPILE_SOURCES=[OWNED[1],OWNED[2],'uc-library/src/Presonus/AVB/'+CONFIG['other']+'.cpp','uc-library/src/Presonus/DICE/PacketClockGateway.cpp']+(['uc-library/src/Presonus/AVB/AvbComponentRouting.cpp','uc-library/src/Presonus/UC/ServerComponent.cpp'] if CONFIG['mixer'] else [])
WRAP='--wrap=_ZN8presonus4dice19packetClockRawTicksEv'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,**kwargs):
 argv=list(map(str,argv));print(json.dumps(argv),flush=True)
 p=subprocess.run(argv,cwd=R,capture_output=True,env={**os.environ,'TMPDIR':str(O)},**kwargs)
 if p.returncode:print(p.stdout.decode(),p.stderr.decode());p.check_returncode()
 return p.stdout.decode()
def main():
 sys.path.insert(0,str(T.parent))
 from canonical_source_transition import current_source_digest, load_transition
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='proof',choices=['format','compile','symbols','native','replay','proof']);p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out');p.add_argument('--runtime-provider');p.add_argument('--source-transition',type=Path);p.add_argument('--source-transition-sha256');a=p.parse_args()
 transition=load_transition(a.source_transition,a.source_transition_sha256)
 exe=Path(a.exe) if a.exe else O/'replay';obj=Path(a.object) if a.object else O/'production.o';runtime=Path(a.runtime_provider) if a.runtime_provider else O/'runtime.so'
 if a.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED]);return
 sys.path.insert(0,str(R/'uc-library/tools/recovery'))
 from pinned_codec_replay_binding import validate_archives
 provider_binding=validate_archives(R,a.exe,a.integration,ARCHIVES)
 supplement_path=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/root-review/provider-supplements/spi-ROOT_ADDENDUM.json')
 assert sha(supplement_path)=='529b32a59d6801d1d225ad9aabcd5e2bdec599e433030e9fdeeaa2cba7cba65a'
 supplement=json.loads(supplement_path.read_text());plan_path=Path('/home/rs/projects/opencs/ai-line-analysis')/supplement['plan'];assert sha(plan_path)==supplement['plan_sha256']
 assert set(transition)<=set(map(Path,supplement['read_inputs']))
 for path,binding in supplement['read_inputs'].items():
  assert sha(binding['frozen_read_path'])==binding['sha256'],'Frozen supplement source changed: '+path
  expected=current_source_digest(path,binding['sha256'],transition)
  assert sha(R/path)==expected,'Supplement source changed: '+path
 for path,expected in PINNED_PROVIDER_SOURCES.items():
  assert sha(R/path)==expected and sha(Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/snapshot')/path)==expected,'Pinned provider implementation differs from frozen generation'
 if a.mode=='compile':
  objects=[]
  for i,source in enumerate(COMPILE_SOURCES):
   target=obj if i==0 else O/('part'+str(i)+'.o');objects.append(target)
   run([*FLAGS,'-MMD','-MF',str(target)+'.d','-c',source,'-o',target])
  run(['/usr/bin/c++',*objects,'-Wl,--gc-sections','-Wl,'+WRAP,*ARCHIVES,'-lz','-lpthread','-ldl','-lm','-o',exe])
  run(['/usr/bin/c++','-std=c++17','-O0','-fPIC','-shared',OWNED[3],'-Wl,--no-as-needed','-lgcc_s','-o',runtime]);return
 import native
 native.PROVIDER=runtime
 runtime_symbols=run(['nm','-D','--undefined-only',runtime]);assert '__divti3@GCC_3.0' in runtime_symbols and '__modti3@GCC_3.0' in runtime_symbols
 if a.mode=='symbols':
  symbols=run(['nm','--defined-only',obj]);assert native.NAME in {x.split()[-1] for x in symbols.splitlines() if x.split()};return
 fresh=native.generate();fixture=json.loads((T/'fixtures.json').read_text());assert fresh==fixture,'Fresh original/provider observations differ'
 if a.mode=='native':print(len(fresh['cases']),'fresh original ARM/GCC-provider cases');return
 symbols=run(['nm','--defined-only',obj]);assert native.NAME in {x.split()[-1] for x in symbols.splitlines() if x.split()}
 if a.mode=='symbols':return
 cases=fresh['cases'];payload=''.join(str(c['last'])+' '+str(c['ticks'])+' '+str(c['receiver'])+'\n' for c in cases);out=run([exe],input=payload.encode()).splitlines();assert len(out)==len(cases)
 for c,line in zip(cases,out):assert list(map(int,line.split()))==[c['after'],1,0],(c,line)
 smoke=list(map(int,run([exe,'--clock']).split()));assert len(smoke)==2 and 0<=smoke[0]<=smoke[1]
 print(len(cases),'fresh native-vs-portable cases, two live receiver identities, sibling isolation, process-state persistence and real monotonic-clock smoke pass')
 if a.mode=='replay' and not a.out:return
 assert a.out,'proof output required'
 files=set(OWNED)|set(COMPILE_SOURCES)|set(PINNED_PROVIDER_SOURCES)|set(supplement['read_inputs'])|{str((T/n).relative_to(R)) for n in ['check.py','native.py','fixtures.json']}
 for dep in O.glob('*.o.d'):
  files.update(x for x in dep.read_text().replace('\\\n',' ').split(':',1)[1].split() if (R/x).is_file())
 phase_records=PHASE_RECORDS
 app={f.removeprefix('uc-library/'):sha(R/f) for f in sorted(files) if f.startswith('uc-library/')};providers={f:sha(R/f) for f in sorted(files) if f.startswith('third_party/ccl-framework/core/')}
 for path,digest in phase_records['typed_frozen_evidence'].items():assert sha(path)==digest,'Typed immutable evidence changed'
 domain='Exact original96-byte ARM app executed over '+str(len(cases))+' nonnegative signed64 raw-clock/static cases: below/equal/above strict500 threshold, carry across low32, q/raw extrema, remainder0/1/999999 and seeded cases; actual GCC signed128 provider supplies q/r independently. Original statics NOBITS8 verified separately per ELF. Portable replay uses two valid live same-class objects, actual lifecycle and child ownership, no base-idle/provider calls, shared state after destruction and other-class timestamp isolation. Actual source-preferred monotonic-ns gateway smoke is separate from deterministic clock-boundary fixtures.'
 limitations=['Original ordinary onIdle return, inheritance/layout and ARM ABI remain unresolved; source-port void override only.','One portable class-static int64 state maps each original function-static NOBITS identity; portable data symbol differs and original data-symbol binary ABI is not claimed. Mixer/surface globals remain distinct.','Native oracle executes exact original app instructions only. Original Core clock and size-zero ARM division helper never execute. Real pinned clock gateway is an intentional source adaptation; deterministic raw ticks use its explicit test boundary. Actual GCC __divti3/__modti3 provider is independently executed through signed128 widening and register-pair translation, not new-product/Python expected division.','Domain: raw ticks >=0, lastMaintenance >=0 and <=INT64_MAX-500. Signed-overflow timestamp initialization, negative time, concurrent callers and unknown listener/resource/hardware services excluded. No hardware maintenance/poll behavior exists in this recovered body.','Mixer construction-only ListenerServices sentinel throws if any unused service is touched; it supplies no provider behavior or oracle expectations. Caller-owned empty ListenerState and actual Component/ServerComponent/AVB destruction are used; no original constructor/destructor credit.']
 entry=dict(original_elf_sha256=native.SHA,mangled=native.NAME,sources=app,repository_sources=providers,domain=domain,declaration_uncertainties=limitations,portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,canonical_binding_pending=True)
 assert all(k in entry for k in ['original_elf_sha256','domain','portable_ready','cpp_compiled','mangling_namespace_checked'])
 proof=dict(version=1,task_id=CONFIG['task'],session_id='/root/rolling10_spi',phase_timestamps=dict(start=phase_records['started'],validation_end=datetime.datetime.now(datetime.timezone.utc).isoformat()),compiled=True,cpp_compiled=True,compiled_mangled_names_matched=True,mangling_namespace_checked=True,cpp_differential_passed=True,formatting_verified=True,native_behavior_verified=True,original_declaration_verified=False,original_arm_abi_verified=False,hardware_verified=False,portable_ready=False,canonical_binding_pending=True,domain=domain,limitations=limitations,ranges=fresh['ranges'],original_process_static=fresh['original_process_static'],native_observations=fresh,native_observations_sha256=hashlib.sha256(json.dumps(fresh,sort_keys=True).encode()).hexdigest(),fresh_native_execution=True,sources=app,repository_sources=providers,source_sha256={f:sha(R/f) for f in sorted(files)},typed_frozen_evidence=phase_records['typed_frozen_evidence'],archives=provider_binding["archives"],historical_provider_archives=provider_binding["historical"],pinned_codec_provider_binding=provider_binding,runtime_provider=dict(path=str(runtime),sha256=sha(runtime),undefined_symbols=runtime_symbols,gcc_library=fresh['provider']),object=dict(path=str(obj),sha256=sha(obj)),executable=dict(path=str(exe),sha256=sha(exe)),compiled_symbols=symbols,clock_smoke=dict(raw_ticks=smoke,scope='Actual existing PacketClockGateway to pinned CCL SystemClock::getTime; real Linux CLOCK_MONOTONIC, no original clock equivalence'),formatter_version=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler_version=run(['/usr/bin/c++','--version']).splitlines()[0],unicorn_version=__import__('unicorn').__version__,integration=dict(path=a.integration,sha256=sha(a.integration)) if a.integration else None,proposed_readiness=dict(canonical_binding_pending=True,ready=[],pending=[entry]))
 proof['source_addendum']=dict(path=str(supplement_path),sha256=sha(supplement_path),plan=dict(path=str(plan_path),sha256=sha(plan_path)),scope=supplement['scope'],owned_sources_preserved=supplement['owned_source_preserved'])
 if transition:proof['source_transition']=dict(path=str(a.source_transition),sha256=a.source_transition_sha256)
 Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
