"""Replay one sealed metering packet against fresh ARM observations."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
TEST = Path(__file__).resolve().parent.relative_to(ROOT)
TASK = TEST.name
MODE = int(TASK[-2:])
MAID = MODE in (13, 14, 15, 20)
D0 = MODE in (19, 20)
READY = MODE in (8, 13, 19, 20)
SCRATCH = Path("temp/recovery-work") / TASK
PROJECT = Path("/home/rs/projects/opencs/ai-line-analysis")
CONTROL = Path("temp/recovery-work/control10x20-after-4fed70d11")
CAPTURE = CONTROL / "packeting/actual07-authorized-wave01-capture02"
FROZEN = PROJECT / CAPTURE / "snapshot"
SNAPSHOT = FROZEN.parent / "SNAPSHOT.json"
SNAPSHOT_SHA = "9ca771ba7e87295936702a5f9b5c158babed4ed998e04444396e3a1b8ec398fb"
PACKET = CAPTURE / "packets" / TASK
PYTHON = "uc-library/.venv/bin/python"
FORMATTER = "uc-library/.venv/bin/clang-format"
CCL = "third_party/ccl-framework"
REPLAY = TEST / "Replay.cpp"
NAMES = ("MeterBallistics", "MeterMaid") if MAID else ("MeterBallistics",)
HEADERS = [Path(f"uc-library/include/presonus/{name}.hpp") for name in NAMES]
SOURCES = [Path(f"uc-library/src/Presonus/{name}.cpp") for name in NAMES]
FLAGS = ["-std=c++20", "-fno-rtti", "-fno-sized-deallocation", "-fno-fast-math",
         "-ffp-contract=off", "-ffunction-sections", "-fdata-sections", "-Wno-multichar",
         "-Iuc-library/include", f"-I{CCL}"]
LDFLAGS = ["-Wl,--gc-sections", "-lm"]
if D0:
    LDFLAGS.append("-Wl,--wrap=_ZdlPv")
ARCHIVES = {
    Path("temp/provider-baseline08/libcorelib.a"):
        "3c4f0825acb529fda135587b7ff5cb92ca0100bb417a20c034d3fdef80a93e0c",
    Path("temp/provider-baseline08/libpresonus_core_allocator.a"):
        "69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d",
} if MAID else {}
REVIEW_NAMES = {
    8:"meter-ballistics/ctor.native01.json", 9:"meter-ballistics/hold.native01.json",
    10:"meter-ballistics/reset.native01.json",11:"meter-ballistics/decay_delta.native01.json",
    12:"meter-ballistics/peak_decay_delta.native01.json",13:"meter-maid/ctor.native01.json",
    14:"meter-maid/setMeter.native01.json",15:"meter-maid/setPeak.native01.json",
    19:"meter-final-local/METER_LIFETIME_NATIVE01.json",
    20:"meter-final-local/METER_LIFETIME_NATIVE01.json",
}
CONTRACT = Path(json.loads((PACKET / "request.json").read_text())["reconstruction_contract"]["path"])
REVIEW = CONTROL / "selection" / REVIEW_NAMES[MODE]
TABLE = CONTROL / "selection/meter-ballistics/ctor.native01.json"
ELFS = [FROZEN / p for p in ("rootfs/RML16AI_Rack_13731/home/root/mixer","rootfs/CS18_v13840/home/root/surface")]
NATIVE = [PYTHON, "-B", TEST / "native.py", PACKET / "request.json",
          PACKET / "ELF_CONTEXT.md", FROZEN / REVIEW, FROZEN / TABLE, *ELFS]
DOMAINS = {
    8: "Independent cold and warm C1 and C2 in both roles; binary32 initial fields, six reset words, and the ten words of the genuine shared default table.",
    9: "Both original getters copy the exact receiver peak-hold bits across four finite seeds; no receiver writes.",
    10: "Both original reset bodies clear the six working words and preserve adjacent observed receiver data across four seeds.",
    11: "Both original decay delta bodies run actual ARM float helpers with null and real default tables across all reviewed rates and levels; portable results match every binary32 word.",
    12: "Both original peak decay delta bodies run actual ARM float helpers with null and real default tables across all reviewed rates and levels; portable results match every binary32 word.",
    13: "Independent cold and warm C1 and C2 in both roles execute the actual MeterBallistics C2, set four MeterMaid slots to zero, and preserve the ten binary32 default table words.",
    14: "Both original setMeter bodies choose only the meter slot; six unbound/bound native inputs verify exact bits and false edit at the verified NumericParam slot. Linux invokes and observes actual pinned NumericParam behavior and leaves the peer untouched.",
    15: "Both original setPeak bodies choose only the peak slot; six unbound/bound native inputs verify exact bits and false edit at the verified NumericParam slot. Linux invokes and observes actual pinned NumericParam behavior and leaves the peer untouched.",
    19: "Both original MeterBallistics D0 ranges invoke verified unsized delete on the same receiver and unmap it; reads fail after return. The separate original D1 retains storage. Actual portable virtual deletion frees the heap receiver through real unsized global delete, and explicit complete cleanup of placement storage does not deallocate.",
    20: "Both original MeterMaid D0 ranges invoke verified unsized delete on the same receiver and unmap it; reads fail after return. The separate original D1 retains storage. Actual portable virtual deletion frees the heap receiver through real unsized global delete, and explicit complete cleanup of placement storage does not deallocate.",
}
DOMAIN = DOMAINS[MODE]
LIMITS = ["Bounded C++ source port. Original complete fields, ARM layout/ABI, device and hardware behavior are outside scope."]
if not READY:
    LIMITS.append("The unencoded original return declaration remains unresolved.")
if D0:
    LIMITS.append("Native delete is modeled at the verified external boundary by actual receiver unmapping. D1 is separate collateral; original D2 is absent and the compiled D2 alias is outside the admission rows.")
if MODE in (8, 13):
    LIMITS.append("Native runtime guard and dynamically linked powf are explicit boundaries; genuine ARM constructor and float helpers execute. Host uses its genuine C++ local static and Linux libm.")
if MODE in (14, 15):
    LIMITS.append("Native original NumericParam's exact virtual target is observed at the boundary. Genuine pinned CCL NumericParam runs separately on Linux. Borrowed lifetime is the source-port contract.")
TIMES = []


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def binding(path):
    return dict(path=str(path), sha256=digest(path))


def run(argv, payload=None):
    argv = list(map(str, argv))
    start = utc()
    before = time.monotonic()
    result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, input=payload,
                            env={**os.environ, "TMPDIR": str(ROOT / SCRATCH)})
    TIMES.append(dict(argv=argv, start_utc=start, seconds=time.monotonic()-before,
                      exit_code=result.returncode))
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    result.check_returncode()
    return result.stdout


def compile_deps(recipe):
    assert digest(SNAPSHOT)==SNAPSHOT_SHA
    hashes = json.loads(SNAPSHOT.read_text())["files"]
    file_inputs = set()
    compiler_depfiles = []
    sources = SOURCES + [REPLAY]
    for index, src in enumerate(sources):
        if recipe:
            depfile = SCRATCH / f"compile-{index}.d"
            compiler_depfiles.append(binding(depfile))
            raw = depfile.read_text()
        else:
            raw = run(["c++", *FLAGS, "-MM", src])
        file_inputs.update(raw.replace("\\\n"," ").split()[1:])
    paths = set(file_inputs) - set(map(str, SOURCES + HEADERS + [REPLAY]))
    providers = {}
    for name in sorted(paths):
        if not name.startswith(CCL + "/core/"):
            raise ValueError(f"Unexpected imported compiler operand {name}")
        assert digest(name)==hashes[name]==digest(FROZEN/name), name
        providers[name]=hashes[name]
    if MAID:
        source = CCL + "/core/portable/coreparams.cpp"
        assert digest(source)==hashes[source]==digest(FROZEN/source)
        providers[source]=hashes[source]
    receipt = dict(snapshot=binding(SNAPSHOT), depfiles=compiler_depfiles,
                   operands={name: digest(name) for name in sorted(file_inputs)},
                   provider_frozen_paths={name: str(FROZEN/name) for name in providers})
    return providers, receipt


def compile_local():
    assert ROOT == Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/production-20261112/agent-repos/worker11")
    expected_git_root=run(["git","rev-parse","--show-toplevel"]).strip()
    assert expected_git_root==str(ROOT)
    for lib, digest_expected in ARCHIVES.items():
        assert digest(lib)==digest_expected
    object_paths=[]
    for idx, source in enumerate(SOURCES+[REPLAY]):
        obj=SCRATCH / ("production.o" if source==SOURCES[-1] else f"compile-{idx}.o")
        object_paths.append(obj)
        run(["c++",*FLAGS,"-MMD","-MF",SCRATCH/f"compile-{idx}.d","-c",source,"-o",obj])
    run(["c++",*object_paths,*ARCHIVES,*LDFLAGS,"-lz","-ldl","-lpthread",
         f"-Wl,-Map,{SCRATCH/'replay.map'}","-o",SCRATCH/"replay"])
    compile_deps(True)


def bitword(value):
    return struct.unpack("<I",struct.pack("<f",value))[0]


def argwords(values):
    if MODE in (11,12):
        return [int(values[0]),bitword(values[1]),bitword(values[2])]
    return [int(v) if isinstance(v,bool) else v for v in values]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",nargs="?",default="replay", choices=("format","compile","symbols","replay"))
    parser.add_argument("--exe",type=Path)
    parser.add_argument("--object",type=Path)
    parser.add_argument("--integration",type=Path)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    os.chdir(ROOT)
    start=utc()
    if not args.integration:
        assert Path(run(["git","rev-parse","--show-toplevel"]).strip())==ROOT
    SCRATCH.mkdir(parents=True,exist_ok=True)
    run([FORMATTER,"--style=file","--fallback-style=LLVM","--dry-run","--Werror",*HEADERS,*SOURCES,REPLAY])
    if args.mode=="format":
        return
    if args.mode=="compile":
        compile_local()
        return
    obj=args.object or SCRATCH/"production.o"
    exe=args.exe or SCRATCH/"replay"
    expected=json.loads((TEST/"fixtures.json").read_text())
    names={row["target"]["mangled"] for row in expected["originals"]}
    defined={line.split()[-1] for line in run(["nm","--defined-only",obj]).splitlines()
             if len(line.split())>=3}
    assert names<=defined
    if D0:
        name,=names
        assert {name.replace("D0E",part) for part in ("D1E","D2E")} <= defined
        disassembly=run(["objdump","-dr",f"--disassemble={name}",obj])
        assert "_ZdlPv-" in disassembly and "_ZdlPvm" not in disassembly
        all_symbols=run(["nm",exe])
        assert "__wrap__ZdlPv" in all_symbols
    if args.mode=="symbols":
        return
    contract=json.loads(CONTRACT.read_text())
    wanted={i["path"]:i["sha256"] for node in contract["requirements"].values()
            for i in node.get("evidence",[]) if i["path"] in (str(REVIEW),str(TABLE))}
    # Contracts can bind review inputs as dependency evidence instead.
    for dep in contract["dependencies"]:
        for row in dep.get("evidence",[]):
            if row["path"] in (str(REVIEW),str(TABLE)):
                wanted[row["path"]]=row["sha256"]
    assert str(REVIEW) in wanted
    for name, value in wanted.items():
        assert digest(FROZEN/name)==value
    observation=json.loads(run(NATIVE))
    assert observation==expected
    all_cases=[c for row in observation["originals"] for c in row["cases"]]
    payload="".join(" ".join(map(str,argwords(c["input"])))+"\n" for c in all_cases)
    output=run([exe.resolve()],payload).splitlines()
    assert output==[" ".join(map(str,c["output"])) for c in all_cases],(output, all_cases)
    providers, receipt=compile_deps(not bool(args.integration))
    sources={str(path.relative_to("uc-library")):digest(path) for path in HEADERS+SOURCES}
    rows=[]
    for native in observation["originals"]:
        original=native["target"]
        row=dict(original_elf_sha256=original["original_elf_sha256"],mangled=original["mangled"],
                 sources=sources,repository_sources=providers,domain=DOMAIN,cpp_compiled=True,
                 mangling_namespace_checked=True,portable_ready=READY)
        if not READY:
            row["declaration_uncertainties"]=LIMITS
        rows.append(row)
    proof=dict(task_id=TASK,start_utc=start,native=observation,portable_rows=output,
               case_count=len(output),cpp_differential_passed=True,compiled_mangled_names_matched=True,
               mangled_names=sorted(names),functions=rows,
               proposed_readiness={"ready":rows if READY else [],"pending":[] if READY else rows},
               sources=sources,repository_sources=providers,validation_domain=DOMAIN,limitations=LIMITS,
               format_check_passed=True,formatter=run([FORMATTER,"--version"]).strip(),
               compiler=run(["c++","--version"]).splitlines()[0],dependency_receipt=receipt,
               power_provider_boundary="Linux libm powf" if MODE in (8,13) else None,
               fixture=binding(TEST/"fixtures.json"),native_producer=binding(TEST/"native.py"),
               checker=binding(TEST/"check.py"),production=binding(obj),executable=binding(exe),
               session_id=os.environ.get("CODEX_THREAD_ID"))
    if args.integration:
        proof["integration"]=binding(args.integration)
    else:
        proof["local_archives"]=[binding(path) for path in ARCHIVES]
        proof["linker_map"]=binding(SCRATCH/"replay.map")
    if MODE in (8,13):
        linked=run(["ldd",exe.resolve()]).splitlines()
        [libm]=[line.split()[2] for line in linked if "libm.so.6 =>" in line]
        proof["libm"]=binding(Path(libm).resolve())
    proof["tool_timings"]=TIMES
    proof["end_utc"]=utc()
    if args.out:
        args.out.write_text(json.dumps(proof,indent=2)+"\n")
    print(f"{TASK}: matched {len(output)} exact cases. {DOMAIN}")


if __name__=="__main__":
    main()
