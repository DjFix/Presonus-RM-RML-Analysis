"""Bind fresh RM-only ARM observations to current shared root native objects."""
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

assert sys.platform.startswith("linux")
repo=Path.cwd().resolve();lib=repo/"uc-library";build=repo/"temp/core-upstream/root-integration-01"
phase=repo/"evidence/recovery/2026-10-27/spi-avb-helpers-root"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
fresh=repo/"temp/recovery-work/avb-rm-helpers/fresh-01"
original=read(fresh/"validation.json")
assert original["counts"]==dict(R=6146,U=2440)
assert original["tool_sha256"]==sha(repo/"uc-library/tools/recovery/verify_avb_rm_helpers.py")
names={r["mangled"] for r in original["functions"]}
ready=read(lib/"validation/ready-functions.json")["functions"]
prior=[r for r in ready if r["mangled"] in names]
assert len(prior)==2 and len({r["original_elf_sha256"] for r in prior})==1
assert all(r["original_elf_sha256"].startswith("304c6cd1") for r in prior)
sources={n:h for r in prior for n,h in r["sources"].items()}
for name,digest in sources.items():assert sha(lib/name)==digest,name
target=lib/"validation/avb-rm-helpers/active-01";target.mkdir(parents=True,exist_ok=False)
for path in fresh.iterdir():
    if path.is_file():shutil.copyfile(path,target/path.name)
tool=target/"original_verify_tool.py";shutil.copyfile(repo/"uc-library/tools/recovery/verify_avb_rm_helpers.py",tool)
for path in target.iterdir():
    if path.is_file():sources[str(path.relative_to(lib))]=sha(path)
formatter=lib/".venv/bin/clang-format"
def run(label,argv):
    result=subprocess.run(list(map(str,argv)),capture_output=True,text=True,cwd=repo)
    (target/(label+".log")).write_text(repr(list(map(str,argv)))+"\n"+result.stdout+result.stderr)
    assert result.returncode==0,(label,result.stderr[-3000:])
    return result.stdout
cpp=[lib/name for name in sources if Path(name).suffix in (".cpp",".hpp",".h")]
version=run("formatter-version",[formatter,"--version"]).strip()
run("strict-format",[formatter,"--style=file","--fallback-style=LLVM","--dry-run","--Werror",*cpp])
formatting=read(lib/"validation/formatting.json")
for path in cpp:assert formatting["files"].get(str(path.relative_to(lib)))==sha(path)
integration=read(lib/"validation/integration.json");assert integration["ctest_passed"] and integration["test_suites"]==116
for name,digest in integration["files"].items():assert sha(lib/name)==digest,name
rows=[r for r in read(build/"compile_commands.json") if Path(r["file"]).resolve()==lib/"src/Presonus/AVB/Protocol.cpp"]
assert len(rows)==1
argv=rows[0].get("arguments") or shlex.split(rows[0]["command"])
obj=Path(argv[argv.index("-o")+1]);obj=obj if obj.is_absolute() else Path(rows[0]["directory"])/obj
assert obj.is_relative_to(build) and obj.is_file()
symbols=run("object-symbols",["nm","--defined-only",obj]);assert names<={line.split()[-1] for line in symbols.splitlines() if line.split()}
archive=build/"libpresonus_rm_components.a"
members=run("rm-members",["ar","t",archive]).splitlines();assert members.count(obj.name)==1
symbols=run("rm-symbols",["nm","--defined-only",archive]);assert names<={line.split()[-1] for line in symbols.splitlines() if line.split()}
fixtures=lib/"validation/avb-protocol/runs/20261026T235518.530958Z"
native=run("current-root-native",[build/"avb_protocol_tests",*[fixtures/n for n in ("accept-vectors.txt","reverse-vectors.txt","memory-vectors.bin.gz")]])
assert "PASS 65536 accepts, 6146 reverse, 73932 exact-memory ARM fixtures" in native
sources["tests/avb_protocol_tests.cpp"]=sha(lib/"tests/avb_protocol_tests.cpp")
proof=dict(status="fresh RM ARM helpers and current common source port",cpp_differential_passed=True,compiled_mangled_names_matched=True,portable_ready=True,functions=original["functions"],mangled_names=sorted(names),sources=sources,domain="Fresh RM original ARM reverseEndian:6146 cases, all256 values ineach8byte position,4096 random and2 boundaries. unpackAvbSpiMsg:2440 cases, lengths-16..64,10 overlap/disjoint placements,3 patterns,5 positive rejected lengths including nulls on rejection. Full512byte RAM arenas and observed return values compared. Current root native fixture executable replayed; same shared production CPP and mangles present once in RM archive. Valid padded ordinary RAM; no huge extents/addresswrap/volatile/MMIO/hardware/full-manager-layout or ARMABI claim.",formatter=version,canonical_integration_sha256=sha(lib/"validation/integration.json"),current_native_executable_sha256=sha(build/"avb_protocol_tests"),compile_entry=rows[0],production_object=dict(path=str(obj.relative_to(repo)),sha256=sha(obj)),rm_archive_sha256=sha(archive),fresh_arm_proof_sha256=sha(target/"validation.json"),fresh_arm_regenerated_for_rm=True,original_function_verified=False,hardware_verified=False,original_arm_abi_verified=False,declaration_uncertainties=["Uses the same existing reviewed portable declarations as the client; no complete original class layout or ARM calling-ABI compatibility claimed."],tool_sha256=sha(Path(__file__)))
proofpath=target/"active-validation.json";proofpath.write_text(json.dumps(proof,indent=2)+"\n")
entries=[dict(role="server",mangled=r["mangled"],original_elf_sha256=r["original_elf_sha256"],original_address=r["address"],validation=str(proofpath.relative_to(lib)),validation_sha256=sha(proofpath),sources=sources,portable_ready=True,cpp_compiled=True,mangling_namespace_checked=True,domain=proof["domain"]) for r in original["functions"]]
(target/"ready-functions.fragment.json").write_text(json.dumps(dict(functions=entries),indent=2)+"\n")
evidence=phase/"avb-active-01";shutil.copytree(target,evidence)
print(json.dumps(dict(ready=2,new_unique_names=0,proof_sha256=sha(proofpath),fragment=str((target/"ready-functions.fragment.json").relative_to(lib)))))
