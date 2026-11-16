#!/usr/bin/env python3
"""Deterministic supplied-binary aux update replay. Never rebuild in four-option mode."""
import argparse,datetime,hashlib,importlib.util,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
TD=Path(__file__).parent
TASK="real10_g05_s03"
SYMBOL="_ZN8Presonus5Mixer14InputComponent14auxLevelUpdateERNS_3Dsp18MultiParamPropertyE"
SOURCES=['third_party/ccl-framework/core/malloc/coremalloc.cpp', 'third_party/ccl-framework/core/platform/corefeatures.h', 'third_party/ccl-framework/core/platform/linux/corethread.linux.h', 'third_party/ccl-framework/core/platform/shared/coreplatformfilesystem.h', 'third_party/ccl-framework/core/platform/shared/coreplatformthread.h', 'third_party/ccl-framework/core/platform/shared/corerecursivereadwritelock.h', 'third_party/ccl-framework/core/platform/shared/posix/corefilesystem.posix.h', 'third_party/ccl-framework/core/platform/shared/posix/corethread.posix.h', 'third_party/ccl-framework/core/portable/coreattributes.cpp', 'third_party/ccl-framework/core/portable/coreattributes.h', 'third_party/ccl-framework/core/portable/corecomponent.cpp', 'third_party/ccl-framework/core/portable/corecomponent.h', 'third_party/ccl-framework/core/portable/corecomponentflags.h', 'third_party/ccl-framework/core/portable/corefile.h', 'third_party/ccl-framework/core/portable/corefilename.h', 'third_party/ccl-framework/core/portable/coreparaminfo.h', 'third_party/ccl-framework/core/portable/coreparams.cpp', 'third_party/ccl-framework/core/portable/coreparams.h', 'third_party/ccl-framework/core/portable/corepersistence.h', 'third_party/ccl-framework/core/portable/coresingleton.h', 'third_party/ccl-framework/core/portable/corestorage.h', 'third_party/ccl-framework/core/portable/coretypeinfo.h', 'third_party/ccl-framework/core/public/corebasicmacros.h', 'third_party/ccl-framework/core/public/corebuffer.h', 'third_party/ccl-framework/core/public/coreclassmacros.h', 'third_party/ccl-framework/core/public/coreclibrary.h', 'third_party/ccl-framework/core/public/corecontainer.h', 'third_party/ccl-framework/core/public/coreformatter.h', 'third_party/ccl-framework/core/public/coreinterpolator.h', 'third_party/ccl-framework/core/public/coreintrusivelist.h', 'third_party/ccl-framework/core/public/corelinkedlist.h', 'third_party/ccl-framework/core/public/coremacros.h', 'third_party/ccl-framework/core/public/coremalloc.h', 'third_party/ccl-framework/core/public/corememstream.h', 'third_party/ccl-framework/core/public/coreplatform.h', 'third_party/ccl-framework/core/public/coreproperty.h', 'third_party/ccl-framework/core/public/corestream.h', 'third_party/ccl-framework/core/public/corestringbuffer.h', 'third_party/ccl-framework/core/public/corestringtraits.h', 'third_party/ccl-framework/core/public/corethreading.h', 'third_party/ccl-framework/core/public/coretypes.h', 'third_party/ccl-framework/core/public/coreuid.h', 'third_party/ccl-framework/core/public/corevector.h', 'third_party/ccl-framework/core/system/corethread.h', 'third_party/ccl-framework/core/text/coreattributehandler.h', 'uc-library/include/presonus/AltMemoryFilter.hpp', 'uc-library/include/presonus/LinkableComponent.hpp', 'uc-library/include/presonus/mixer/ChannelComponent.hpp', 'uc-library/include/presonus/mixer/InputComponent.hpp', 'uc-library/include/presonus/mixer/TalkbackInputComponent.hpp', 'uc-library/src/Presonus/LinkableComponent.cpp', 'uc-library/src/Presonus/Mixer/ChannelComponent.cpp', 'uc-library/src/Presonus/Mixer/InputComponent.cpp']
FLAGS=["-std=c++17","-O3","-DNDEBUG=1","-DCORE_USE_OPENSSL=1","-DPRESONUS_HAS_UPSTREAM_CORE=1","-DCORE_DISABLE_NEW_OPERATOR=1","-pthread","-Ulinux","-ffp-contract=off","-ffunction-sections","-fdata-sections","-Iuc-library/include","-isystem","third_party/ccl-framework"]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,stdin=None):
 r=subprocess.run([str(x) for x in argv],cwd=ROOT,input=stdin,text=True,capture_output=True,timeout=120)
 if r.returncode:raise RuntimeError(str(argv)+"\n"+r.stdout+r.stderr)
 return r.stdout
def build(where,core):
 d=Path(where);d.mkdir(parents=True,exist_ok=True);commands=[]
 for i,source in enumerate(["uc-library/src/Presonus/Mixer/InputComponent.cpp",str(TD.relative_to(ROOT)/"Replay.cpp"),"uc-library/src/Presonus/LinkableComponent.cpp","uc-library/src/Presonus/Mixer/ChannelComponent.cpp","third_party/ccl-framework/core/malloc/coremalloc.cpp"]):
  a=["c++",*FLAGS,"-MD","-MF",str(d/f"{i}.d"),"-c",source,"-o",str(d/f"{i}.o")];run(a);commands.append(a)
 a=["c++",*[str(d/f"{i}.o") for i in range(5)],core,"-Wl,--gc-sections","-pthread","-ldl","-lz","-o",str(d/"Replay")];run(a);commands.append(a)
 (d/"commands.json").write_text(json.dumps(commands,indent=2)+"\n");print("built actual Input object and canonical/provider replay")
def symbol(obj):
 n=run(["nm","--defined-only",obj]);assert any(x.split()[-1]==SYMBOL for x in n.splitlines()),"selected exact original missing"
 return n

def bind_canonical_input(obj, exe, integration):
 if Path(integration).resolve() != (ROOT/'uc-library/validation/integration.json').resolve():return None
 import shlex
 helper=ROOT/'uc-library/tools/recovery/canonical_compile_bindings.py'
 spec=importlib.util.spec_from_file_location('canonical_compile_bindings',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 value=module.bind(ROOT,Path(obj),'uc-library/src/Presonus/Mixer/InputComponent.cpp',exe_path=Path(exe),required_provider_sources=('uc-library/src/Presonus/LinkableComponent.cpp','uc-library/src/Presonus/Mixer/ChannelComponent.cpp'),required_archive_names=('libcorelib.a','libpresonus_core_allocator.a'))
 entry=value['objects'][0]['compile_entry'];argv=entry.get('arguments') or shlex.split(entry['command'])
 contractions=[x.split('=',1)[1] for x in argv if x.startswith('-ffp-contract=')]
 assert contractions and contractions[-1]=='off', 'Actual canonical Input TU must compile with -ffp-contract=off'
 unexpected=[p for p in value['files'] if p.startswith('third_party/ccl-framework/') and not p.startswith('third_party/ccl-framework/core/')]
 assert not unexpected, 'Unexpected non-Core CCL dependency paths: '+repr(unexpected)
 return {'binding':value,'argv':argv,'transition':module.load_transition(ROOT,'temp/recovery-work/reconstruction10x10-20261116/workflow/checker-canonical-audit/review02/CANONICAL_BINDING_TRANSITION.json'),'helper':{'path':'uc-library/tools/recovery/canonical_compile_bindings.py','sha256':sha(helper)}}

def replay(exe,obj,integration,out):
 canonical_binding=bind_canonical_input(obj,exe,integration)
 start=time.monotonic();stamp=datetime.datetime.now(datetime.timezone.utc).isoformat();symbol(obj)
 fmt=["uc-library/include/presonus/mixer/InputComponent.hpp","uc-library/src/Presonus/Mixer/InputComponent.cpp",str(TD.relative_to(ROOT)/"Replay.cpp")]
 run([str(ROOT/"uc-library/.venv/bin/clang-format"),"--style=file","--fallback-style=LLVM","--dry-run","--Werror",*fmt])
 f=json.loads((TD/"fixtures.json").read_text());assert f['mangled']==SYMBOL and f['case_count']==256
 lines=[]
 for row in f['cases']:
  c=row['input'];values=[c[k] for k in ('n','talkback','global_mute','mute','self_link','linked_pan','parity','law','base','prop_count')]
  for a in c['aux']:values.extend(a[k] for k in ('send','post','sub','assigned','linked','slave','pan','width'))
  lines.append(' '.join(str(int(x)) if isinstance(x,bool) else str(x) for x in values))
 stdout=run([str(Path(exe).resolve())],'\n'.join(lines)+'\n');actual=stdout.splitlines();assert len(actual)==len(f['cases'])
 for i,(line,row) in enumerate(zip(actual,f['cases'])):
  expected=row['cache']+[row['property_count']]+[v for pair in row['entries'] for v in pair]
  assert list(map(int,line.split()))==expected,f"native cache/property mismatch case {i}"
 source_map={p.removeprefix('uc-library/'):sha(ROOT/p) for p in SOURCES if p.startswith(('uc-library/include/','uc-library/src/'))}
 core_map={p:sha(ROOT/p) for p in SOURCES if p.startswith('third_party/ccl-framework/core/')}
 if canonical_binding is not None:
  source_map.update({p.removeprefix('uc-library/'):h for p,h in canonical_binding['binding']['files'].items() if p.startswith('uc-library/')})
  core_map.update({p:h for p,h in canonical_binding['binding']['files'].items() if p.startswith('third_party/ccl-framework/core/')})
  assert source_map and core_map and all(p.startswith('third_party/ccl-framework/core/') for p in core_map), 'Actual nonempty canonical library/Core closure required'
 domain=f['producer_domain']+'; 256 bit-exact portable comparisons including real CCL param factory/tag lookup/value reads, canonical Linkable isLinked/isLinkSlave and C++ RTTI on canonical Channel/Talkback types; initial aux cache0.125 and finite sends0/.25/.8/1, pan0/.25/.5/1, linked widths-1/0/.5/1, base.75.'
 uncertainty=['Source-port declaration void chosen; original ordinary return declaration unresolved.','Original Input inheritance/layout/ARM ABI unresolved. Receiver RTTI uses borrowed actual canonical Channel/Talkback identity, not claimed original Input object layout.','Native Core/app virtual/global/link/RTTI boundaries explicitly intercepted; their actual canonical/pinned host providers executed separately. Soft-float firmware runtime instructions executed by native oracle.','Property opaque adaptation uses existing Providers boundary. Inputs require stable bound providers and valid nonnull required parameters. No NaN/Inf, negative counts, concurrent mutation, hardware, EH or original ABI validation.']
 row={'original_elf_sha256':f['original_elf_sha256'],'mangled':SYMBOL,'sources':source_map,'cpp_compiled':True,'mangling_namespace_checked':True,'portable_ready':False,'declaration_uncertainties':uncertainty,'validation_domain':domain}
 if canonical_binding is not None:row['repository_sources']=core_map
 proof={'task_id':TASK,'success':True,'functions':[row],'proposed_readiness':{'ready':[],'pending':[row]},'sources':source_map,'repository_sources':core_map,'formatting':{'version':run([str(ROOT/'uc-library/.venv/bin/clang-format'),'--version']).strip(),'paths':{p:sha(ROOT/p) for p in fmt},'dry_run_passed':True},'native_range':{k:v for k,v in f.items() if k not in ('cases','visited_original_instruction_addresses')},'fixture_sha256':sha(TD/'fixtures.json'),'oracle_producer_sha256':sha(TD/'native.py'),'checker_sha256':sha(__file__),'executable_sha256':sha(exe),'object_sha256':sha(obj),'integration_sha256':sha(integration),'compiler_options':FLAGS,'start_utc':stamp,'seconds':time.monotonic()-start,'case_count':len(actual),'limitations':uncertainty,'canonical_supplied_binary_mode':True,'readiness_admitted':False}
 if canonical_binding is not None:
  proof['canonical_compile_binding']=canonical_binding['binding']
  proof['canonical_binding_transition']=canonical_binding['transition']
  proof['canonical_producer_helper']=canonical_binding['helper']
  proof['provider_archives']={p['path']:p['sha256'] for p in canonical_binding['binding']['link']['archives']}
  proof['compiler_options']=canonical_binding['argv']
  proof['compiler_options_scope']='Actual canonical Input production OBJECT compile entry; separately-rounded float contraction gate checked'
  proof['local_compile_defaults']=FLAGS
 Path(out).parent.mkdir(parents=True,exist_ok=True);Path(out).write_text(json.dumps(proof,indent=2)+'\n');print('256 original ARM/actual provider cache+property comparisons passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out');p.add_argument('--build');p.add_argument('--core-library');p.add_argument('--symbols',action='store_true');p.add_argument('--native-elf');a=p.parse_args()
 if a.build:
  assert a.core_library,'--build requires explicit actual --core-library';build(a.build,a.core_library)
 elif a.symbols:symbol(a.object);print('exact original mangling verified')
 elif a.native_elf:
  spec=importlib.util.spec_from_file_location('oracle',TD/'native.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);fresh=m.produce(a.native_elf,str(Path(a.out).with_suffix('.native-observations.json')));assert fresh==json.loads((TD/'fixtures.json').read_text());Path(a.out).write_text(json.dumps({'task_id':TASK,'independent_native_replayed':True,'case_count':fresh['case_count'],'elf_sha256':fresh['original_elf_sha256'],'producer_sha256':sha(TD/'native.py'),'fixture_sha256':sha(TD/'fixtures.json')},indent=2)+'\n');print('256 original ARM application/soft-float runtime executions passed')
 else:
  assert all((a.exe,a.object,a.integration,a.out));replay(a.exe,a.object,a.integration,a.out)
