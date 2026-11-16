#!/usr/bin/env python3
"""Four-option canonical replay; supplied binaries are checked, never rebuilt implicitly."""
import argparse,hashlib,importlib.util,json,subprocess,time
from pathlib import Path
TASK=Path(__file__).parent.name
ROOT=Path(__file__).resolve().parents[4]
TD=Path(__file__).parent
S10=TASK.endswith("10")
CLASS="AliasMapping" if S10 else "ChannelDCAComponent"
SOURCE=f"uc-library/src/Presonus/Mixer/{CLASS}.cpp"
HEADER=f"uc-library/include/presonus/mixer/{CLASS}.hpp"
SYMBOL="_ZN8Presonus5Mixer12AliasMappingC2EPN4Core8Portable10AliasParamEPNS3_9ParameterEPKc" if S10 else "_ZN8Presonus5Mixer19ChannelDCAComponent"+{"07":"D1","08":"D2","09":"D0"}[TASK[-2:]]+"Ev"
CORELIB="/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/build/artifacts/linux/Release/libcorelib.a"
ELF="/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/prepared-input/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer"
FLAGS=["-std=c++17","-O3","-DNDEBUG=1","-DCORE_USE_OPENSSL=1","-DPRESONUS_HAS_UPSTREAM_CORE=1","-pthread","-Ulinux","-Iuc-library/include","-isystem","third_party/ccl-framework"]
if not S10: FLAGS += ["-fno-sized-deallocation"]
COMPILE_DEPENDENCIES=['third_party/ccl-framework/core/malloc/coremalloc.cpp', 'third_party/ccl-framework/core/portable/corecomponent.h', 'third_party/ccl-framework/core/portable/corecomponentflags.h', 'third_party/ccl-framework/core/portable/coreparaminfo.h', 'third_party/ccl-framework/core/portable/coreparams.h', 'third_party/ccl-framework/core/portable/coretypeinfo.h', 'third_party/ccl-framework/core/public/corebasicmacros.h', 'third_party/ccl-framework/core/public/coreclassmacros.h', 'third_party/ccl-framework/core/public/coreclibrary.h', 'third_party/ccl-framework/core/public/corecontainer.h', 'third_party/ccl-framework/core/public/coreformatter.h', 'third_party/ccl-framework/core/public/coreinterpolator.h', 'third_party/ccl-framework/core/public/coremacros.h', 'third_party/ccl-framework/core/public/coremalloc.h', 'third_party/ccl-framework/core/public/coreplatform.h', 'third_party/ccl-framework/core/public/corestringbuffer.h', 'third_party/ccl-framework/core/public/corestringtraits.h', 'third_party/ccl-framework/core/public/coretypes.h', 'third_party/ccl-framework/core/public/coreuid.h', 'third_party/ccl-framework/core/public/corevector.h', 'uc-library/include/presonus/mixer/ChannelDCAComponent.hpp', 'uc-library/include/presonus/uc/ServerComponent.hpp', 'uc-library/src/Presonus/Mixer/ChannelDCAComponent.cpp', 'uc-library/src/Presonus/UC/ServerComponent.cpp', 'uc-library/tests/recovery/real10_g05_s07/Replay.cpp']
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv):
 r=subprocess.run([str(x) for x in argv],cwd=ROOT,text=True,capture_output=True,timeout=120)
 if r.returncode: raise RuntimeError(str(argv)+"\n"+r.stdout+r.stderr)
 return r.stdout
def build(dest):
 dest=Path(dest);dest.mkdir(parents=True,exist_ok=True)
 obj=dest/(CLASS+".o"); cmds=[]
 sources=[SOURCE,str(TD.relative_to(ROOT)/"Replay.cpp"),"uc-library/src/Presonus/Mixer/ControlMapping.cpp" if S10 else "uc-library/src/Presonus/UC/ServerComponent.cpp","third_party/ccl-framework/core/malloc/coremalloc.cpp"]
 objects=[]
 for i,src in enumerate(sources):
  out=obj if i==0 else dest/(str(i)+".o")
  argv=["c++",*FLAGS,"-DCORE_DISABLE_NEW_OPERATOR=1","-MD","-MF",str(out)+".d","-c",src,"-o",str(out)]
  run(argv);cmds.append(argv);objects.append(str(out))
 argv=["c++",*objects,CORELIB,"-pthread","-ldl","-o",str(dest/"Replay")];run(argv);cmds.append(argv)
 (dest/"commands.json").write_text(json.dumps(cmds,indent=2)+"\n")
 print(json.dumps({"object":str(obj),"exe":str(dest/"Replay")}))
def symbols(obj):
 out=run(["nm","--defined-only",obj]); assert any(x.split()[-1]==SYMBOL for x in out.splitlines()),SYMBOL
 if not S10:
  undefined=run(["nm","-u",obj]);assert "_ZdlPv" in undefined; assert "_ZdlPvm" not in undefined
 return out

# Root canonical-only source/OBJECT/link provenance; local execution is retained.
def _canonical_observation(root, obj, exe, integration, source, providers=(), archives=()):
 if not integration or Path(integration).resolve() != (root/'uc-library/validation/integration.json').resolve():return None
 import importlib.util
 path=root/'uc-library/tools/recovery/canonical_compile_bindings.py'
 spec=importlib.util.spec_from_file_location('canonical_compile_bindings',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 result=module.bind(root,obj,source,exe_path=exe,required_provider_sources=providers,required_archive_names=archives)
 result['Root_canonical_transition']=module.load_transition(root,'temp/recovery-work/reconstruction10x10-20261116/workflow/checker-canonical-audit/review02/CANONICAL_BINDING_TRANSITION.json')
 result['Root_helper']={'path':'uc-library/tools/recovery/canonical_compile_bindings.py','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 return result

def _canonical_fields(binding):
 return {} if binding is None else {'canonical_compile_binding':binding,'canonical_binding_transition':binding['Root_canonical_transition'],'canonical_producer_helper':binding['Root_helper']}

def replay(exe,obj,integration,out):
 binding=_canonical_observation(ROOT,Path(obj),Path(exe),integration,SOURCE,providers=('uc-library/src/Presonus/UC/ServerComponent.cpp',),archives=('libcorelib.a','libpresonus_core_allocator.a'))
 start=time.time();run([str(ROOT/"uc-library/.venv/bin/clang-format"),"--style=file","--fallback-style=LLVM","--dry-run","--Werror",SOURCE,HEADER,str(TD.relative_to(ROOT)/"Replay.cpp")]);nm=symbols(obj); fixture=json.loads((TD/"fixtures.json").read_text())
 spec=importlib.util.spec_from_file_location("native",TD/"native.py");mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 fresh=mod.produce(ELF); assert fresh==fixture,"independent native fixture mismatch"
 for case in fixture["cases"]:
  calls=case["calls"]; objaddr=0x800100
  assert case["return"]==objaddr
  if S10:
   assert len(calls)==1 and calls[0]["boundary"]=="ControlMapping"
   assert calls[0]["args"]==[objaddr,case["parameter"],case["name"]]
   assert [40,4,case["alias"]] in case["receiver_writes"]
  else:
   names=[x["boundary"] for x in calls];assert names==["CoreVector","CoreComponent"]+(["delete"] if TASK.endswith("09") else [])
   assert calls[0]["args"][0]==objaddr+0x90 and calls[1]["args"][0]==objaddr
   if TASK.endswith("09"): assert calls[2]["args"][0]==objaddr
 stdout=run([str(Path(exe).resolve())])
 if S10: assert len(stdout.splitlines())==20
 else:
  expected=[f"{n} 1 {int(n>0)} {int(TASK.endswith('09'))} 12345" for n in (0,1,8)]
  assert stdout.splitlines()==expected
 actual_corelib=CORELIB if binding is None else next(p['path'] for p in binding['link']['archives'] if Path(p['path']).name=='libcorelib.a')
 actual_corelib=str(ROOT/actual_corelib) if binding is not None and not Path(actual_corelib).is_absolute() else actual_corelib
 actual_dependencies=COMPILE_DEPENDENCIES if binding is None else list(binding['files'])
 source_paths=[SOURCE,HEADER,"uc-library/src/Presonus/Mixer/ControlMapping.cpp" if S10 else "uc-library/src/Presonus/UC/ServerComponent.cpp","uc-library/include/presonus/mixer/ControlMapping.hpp" if S10 else "uc-library/include/presonus/uc/ServerComponent.hpp"]
 dependencies={x:sha(ROOT/x) for x in source_paths}
 domain=("6 original ARM constructor executions with explicit ControlMapping boundary; 20 host constructor/canonical provider/CCL string comparisons incl null,empty,31 and overlong strings and borrowed pointers" if S10 else "3 original ARM normal-path executions with explicit Vector/Component boundaries; host selected exact destructor variant with 0,1,8 borrowed entries, vector-storage release before owned-child cleanup, actual receiver deallocation only for D0; separate actual pinned Vector and Component observations")
 limitations=["Portable source state only; original inheritance/layout/ARM ABI unresolved; no hardware or EH validation; original provider bodies not executed natively.","CString32 source-provider truncation retained; original ControlMapping native behavior not claimed." if S10 else "Original DCALevelHandler ownership beyond observed pointer-vector destruction unresolved; source-port handlers remain borrowed."]
 entry={"original_elf_sha256":fixture["elf_sha256"],"mangled":SYMBOL,"sources":{x.removeprefix("uc-library/"):sha(ROOT/x) for x in actual_dependencies if x.startswith(("uc-library/src/","uc-library/include/"))},"cpp_compiled":True,"mangling_namespace_checked":True,"portable_ready":False,"declaration_uncertainties":limitations,"validation_domain":domain}
 providers=["third_party/ccl-framework/core/public/corestringbuffer.h","third_party/ccl-framework/core/public/corestringbuffer.cpp"] if S10 else ["third_party/ccl-framework/core/public/corevector.h","third_party/ccl-framework/core/portable/corecomponent.h","third_party/ccl-framework/core/portable/corecomponent.cpp","third_party/ccl-framework/core/portable/coreparams.h","third_party/ccl-framework/core/portable/coreparams.cpp"]
 providers += ["third_party/ccl-framework/core/malloc/coremalloc.cpp"]
 proof={"task_id":TASK,"success":True,"functions":[entry],"proposed_readiness":{"ready":[],"pending":[entry]},"repository_sources":{p:sha(ROOT/p) for p in set(providers+actual_dependencies) if p.startswith("third_party/")},"sources":{p.removeprefix("uc-library/"):h for p,h in dependencies.items()},"compile_dependencies":{p:sha(ROOT/p) for p in actual_dependencies},"commands":json.loads((Path(obj).parent/"commands.json").read_text()) if (Path(obj).parent/"commands.json").exists() else "canonical supplied object/executable; compiler observations owned by Root","native":fixture,"host_case_count":20 if S10 else 3,"stdout":stdout,"exe_sha256":sha(exe),"object_sha256":sha(obj),"fixture_sha256":sha(TD/"fixtures.json"),"producer_sha256":sha(TD/"native.py"),"checker_sha256":sha(__file__),"corelib_sha256":sha(actual_corelib),"corelib_path":actual_corelib,"core_commit":"e8cbdea4a4a20e15111f5a690798a259c0374b31","format_version":run([str(ROOT/"uc-library/.venv/bin/clang-format"),"--version"]).strip(),"flags":(FLAGS if binding is None else binding["objects"][0]["compile_entry"].get("arguments",binding["objects"][0]["compile_entry"].get("command"))),"integration":str(integration),"integration_sha256":sha(integration),"elapsed_seconds":time.time()-start,"limitations":limitations}
 proof.update(_canonical_fields(binding))
 if binding is not None:proof['provider_archives']={p['path']:p['sha256'] for p in binding['link']['archives']}
 Path(out).parent.mkdir(parents=True,exist_ok=True);Path(out).write_text(json.dumps(proof,indent=2)+"\n"); print(TASK+" replay passed")
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--build");p.add_argument("--symbols",action="store_true");p.add_argument("--exe");p.add_argument("--object");p.add_argument("--integration");p.add_argument("--out");a=p.parse_args()
 if a.build: build(a.build)
 elif a.symbols: symbols(a.object);print("exact selected original present")
 else:
  assert all((a.exe,a.object,a.integration,a.out));replay(a.exe,a.object,a.integration,a.out)
