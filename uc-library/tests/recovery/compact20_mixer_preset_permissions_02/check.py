"""Local checks and fresh canonical executable/proof adapter for getDelay."""
import argparse,datetime,hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
TEST=Path(__file__).resolve().parent
TASK="compact20_mixer_preset_permissions_02"
SCRATCH=ROOT/"temp/recovery-work"/TASK
SOURCES=["uc-library/src/Presonus/Mixer/OutputComponent.cpp","uc-library/include/presonus/mixer/OutputComponent.hpp","uc-library/include/presonus/mixer/ChannelComponent.hpp","uc-library/include/presonus/mixer/InputComponent.hpp"]
PROVIDERS=["third_party/ccl-framework/core/portable/coreparams.h","third_party/ccl-framework/core/portable/coreparams.cpp","third_party/ccl-framework/core/portable/corecomponent.h"]
MANGLED="_ZN8Presonus5Mixer15OutputComponent8getDelayEv"
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv):
    start=time.monotonic();p=subprocess.run([str(x) for x in argv],cwd=ROOT,text=True,capture_output=True)
    if p.returncode:raise RuntimeError(str(argv)+"\n"+p.stdout+p.stderr)
    return dict(argv=[str(x) for x in argv],returncode=p.returncode,stdout=p.stdout,stderr=p.stderr,seconds=time.monotonic()-start)
def compile_local():
    SCRATCH.mkdir(parents=True,exist_ok=True)
    common=["c++","-std=c++17","-O0","-ffunction-sections","-fdata-sections","-Iuc-library/include","-Ithird_party/ccl-framework"]
    records=[run(common+["-c",SOURCES[0],"-o",SCRATCH/"output.o"])]
    records.append(run(common+[TEST/"Replay.cpp",SCRATCH/"output.o","-Wl,--gc-sections","temp/provider-baseline08/libcorelib.a","temp/provider-baseline08/libpresonus_core_allocator.a","-lpthread","-ldl","-o",SCRATCH/"replay"]))
    (SCRATCH/"compile.json").write_text(json.dumps(dict(checks=records,object_sha256=sha(SCRATCH/"output.o"),executable_sha256=sha(SCRATCH/"replay")),indent=2)+"\n")
    return records
def symbols(obj):
    result=run(["nm","--defined-only",obj]);assert MANGLED in {line.split()[-1] for line in result['stdout'].splitlines() if line.split()};return result
def replay(executable,fixtures):
    data=json.loads(Path(fixtures).read_text());r=run([executable]);rows=[[int(v) for v in line.split()] for line in r['stdout'].splitlines()]
    expected=[[c['object_index'],c['token'],c['token'] if c['return_word']==c['input_word'] else -1,c['object_writes']] for c in data['cases']]
    assert rows==expected,(rows,expected)
    r['cases']=len(rows);return r
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("mode",choices=["compile","symbols","replay","proof"]);p.add_argument("--executable",type=Path);p.add_argument("--object",type=Path);p.add_argument("--fixtures",type=Path,default=TEST/"fixtures.json");p.add_argument("--proof-out",type=Path);p.add_argument("--integration",type=Path);p.add_argument("--formatter",default="/home/rs/projects/opencs/ai-line-analysis/uc-library/.venv/bin/clang-format");a=p.parse_args();exe=a.executable or SCRATCH/"replay";obj=a.object or SCRATCH/"output.o"
    if a.mode=="compile":print(json.dumps(compile_local()));raise SystemExit
    if a.mode=="symbols":print(json.dumps(symbols(obj)));raise SystemExit
    if a.mode=="replay":print(json.dumps(replay(exe,a.fixtures)));raise SystemExit
    assert a.proof_out and not a.proof_out.exists(), "Proof output must be NEW"
    canonical_mode=a.executable is not None or a.object is not None
    if canonical_mode:
        assert a.executable is not None and a.object is not None and a.integration is not None, "Canonical proof requires explicit executable, object and actual integration receipt"
        assert a.integration.is_file(), "Canonical integration receipt absent"
    begin=datetime.datetime.now(datetime.timezone.utc).isoformat()
    format_paths=SOURCES[:2]+[str((TEST/"Replay.cpp").relative_to(ROOT))]
    checks=[run([a.formatter,"--style=file","--fallback-style=LLVM","--dry-run","--Werror"]+format_paths),symbols(obj),replay(exe,a.fixtures)]
    # Fresh reexecution of exact original instructions, independent of C++.
    canonical=Path("/home/rs/projects/opencs/ai-line-analysis")
    checks.append(run([str(canonical/"uc-library/.venv/bin/python"),TEST/"native.py","--elf",canonical/"rootfs/RML16AI_Rack_13731/home/root/mixer","--verify",a.fixtures]))
    native=json.loads(a.fixtures.read_text());sources={s.removeprefix("uc-library/"):sha(ROOT/s) for s in SOURCES}
    sources.update({str((TEST/n).relative_to(ROOT/"uc-library")):sha(TEST/n) for n in ["Replay.cpp","native.py","check.py","fixtures.json"]})
    producers={str((TEST/n).relative_to(ROOT)):sha(TEST/n) for n in ["Replay.cpp","native.py","check.py","fixtures.json"]}
    uncertainty=["Original unencoded static return declaration unresolved; Core::Portable::Parameter* is intentional portable source contract","Original layout, inheritance, ownership, ARM ABI and hardware interoperability unverified"]
    domain="10 native ARM executions across2 receiver addresses and5 pointer words, mapped by identity token to null and4 live CCL NumericParams; repeated calls after rebinding, unchanged native object memory and host parameter values/flags. No parameter dereference by accessor."
    record=dict(original_elf_sha256=native['original_elf_sha256'],mangled=MANGLED,sources=sources,repository_sources={s:sha(ROOT/s) for s in PROVIDERS},domain=domain,portable_ready=False,declaration_uncertainties=uncertainty,cpp_compiled=True,mangling_namespace_checked=True)
    proof=dict(version=1,task_id=TASK,phase_start_utc=begin,phase_end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cpp_differential_passed=True,arm_differential_passed=True,compiled_mangled_names_matched=True,mangling_namespace_checked=True,cpp_compiled=True,functions=[dict(record,native_cases=len(native['cases']),native_range={k:native[k] for k in ['address','size','section','section_index','file_offset','range_sha256']})],sources=sources,repository_sources=record['repository_sources'],producers=producers,native_fixture_sha256=sha(a.fixtures),native_producer='original ELF ARM range independently executed by Unicorn '+native['unicorn_version'],checks=checks,executable=dict(path=str(exe),sha256=sha(exe)),object=dict(path=str(obj),sha256=sha(obj)),formatter=run([a.formatter,'--version'])['stdout'].strip(),limitations=uncertainty,proposed_readiness=dict(canonical_binding_pending=True,ready=[],pending=[record]))
    if not canonical_mode:
        compilation=json.loads((SCRATCH/"compile.json").read_text());assert compilation["object_sha256"]==sha(obj) and compilation["executable_sha256"]==sha(exe);proof["compilation"]=compilation
    proof["compiler_version"]=run(["c++","--version"])["stdout"].splitlines()[0]
    proof["provenance_mode"]="canonical_explicit_artifacts" if canonical_mode else "worker_local_baseline"
    if not canonical_mode:
        proof["provider_archives"]={p:sha(ROOT/p) for p in ["temp/provider-baseline08/libcorelib.a","temp/provider-baseline08/libpresonus_core_allocator.a"]}
    else:
        proof["provider_binding_scope"]="Actual supplied canonical executable/object and integration receipt plus pinned provider sources; no baseline archive link provenance asserted"
    if a.integration:proof['fresh_integration']=dict(path=str(a.integration),sha256=sha(a.integration))
    a.proof_out.parent.mkdir(parents=True,exist_ok=True);a.proof_out.write_text(json.dumps(proof,indent=2)+'\n');print('Fresh proof produced',a.proof_out)
