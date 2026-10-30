#!/usr/bin/env python3
"""Seal bounded portable PreSonus mixer-state behavior and original names."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import subprocess


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("repository",type=Path);p.add_argument("oracle_run");a=p.parse_args()
    root=a.repository.resolve();lib=root/"uc-library";oracle_run=lib/a.oracle_run
    out=oracle_run/"verification"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True,exist_ok=False);commands=[]

    def run(argv,name):
        commands.append(argv);result=subprocess.run(argv,cwd=lib,text=True,capture_output=True)
        (out/name).write_text("$ "+shlex.join(argv)+"\n"+result.stdout+result.stderr)
        (out/"commands.json").write_text(json.dumps(commands,indent=2)+"\n")
        if result.returncode:raise RuntimeError(f"{out/name}: {result.stdout}{result.stderr}")
        return result.stdout

    sources=["src/mixer_state/MixerState.cpp","include/presonus/mixer_state/MixerState.hpp","tests/mixer_state_tests.cpp"]
    formatter=str(lib/".venv/bin/clang-format")
    version=run([formatter,"--version"],"formatter-version.log").strip()
    run([formatter,"--style=file","--fallback-style=LLVM","--dry-run","--Werror",*sources],"format-check.log")
    source_hashes={name:sha(lib/name) for name in sources}
    formatting=dict(formatter=version,configuration_sha256=sha(root/".clang-format"),format_check_passed=True,files=source_hashes)
    (out/"formatting.json").write_text(json.dumps(formatting,indent=2)+"\n")
    obj=str((out/"MixerState.o").relative_to(lib));exe=str((out/"tests").relative_to(lib))
    flags=["-std=c++17","-O2","-Wall","-Wextra","-Wpedantic","-Iinclude"]
    run(["g++",*flags,"-c",sources[0],"-o",obj],"build-source.log")
    run(["g++",*flags,sources[2],obj,"-o",exe],"build-tests.log")
    nm=run(["nm","--defined-only",obj],"compiled-symbols.log")
    defined={line.split()[-1] for line in nm.splitlines() if line.split()}
    records=[];pending=[];logs={}
    for role in ("client","server"):
        oracle_path=oracle_run/role/"arm-oracle.json";oracle=json.loads(oracle_path.read_text())
        fixtures=oracle_run/role/"arm-vectors.txt"
        assert sha(fixtures)==oracle["fixture_sha256"]
        logs[role]=run([exe,str(fixtures.relative_to(lib))],role+"-differential-tests.log")
        expected="PASS:"+"".join(f' {op}={oracle["cases"][op]}' for op in sorted(oracle["cases"]))
        assert logs[role].startswith(expected)
        for op,symbol in oracle["functions"].items():
            item=dict(symbol,role=role,original_elf_sha256=oracle["original_elf_sha256"])
            if op in ("P","Q"):
                item.update(status="declaration-pending; raw ARM return words tested only",portable_ready=False,
                            unresolved="Return pointer/pointee identity is not established by mangling or a field load. No C++ declaration or implementation emitted.")
                pending.append(item)
            else:
                assert symbol["mangled"] in defined,symbol["mangled"]
                records.append(item)
        records_for_role=[x for x in records if x["role"]==role]
        for item in records_for_role:
            item["oracle_path"]=str(oracle_path.relative_to(lib));item["oracle_sha256"]=sha(oracle_path)
            item["fixture_path"]=str(fixtures.relative_to(lib));item["fixture_sha256"]=sha(fixtures)
        assert not any(x["demangled"].startswith("Core::") for x in oracle["functions"].values())
    assert source_hashes=={name:sha(lib/name) for name in sources}
    domain=("Portable state corresponding to originalmaster/slaveword tests and optionalconfigurationcountword; validnonoverlapping originalmemory. "
            "Fiveinteger/predicate methods on bothELFs; channel0..65535 plus5edge+4096randomwords; counts15edge+1024randomwords in null/non-nullconfiguration; "
            "originalvirtual getNumGeqs dispatch and explicitoverride returnwordcontract, onecall/originalthis; modulo2^32 subtraction; cascade7x7links+1024randompairs. "
            "Exactreturnwords, untouched original0x688-byte object/config and portable state, overridecallcounts checked. No Core code, floating helpers, hardware or originalobject/vtableABI claim.")
    proof=dict(namespace="Presonus",classes=["MixerClientComponentBase","MixerClientComponent"],functions=records,pending_functions=pending,
        domain=domain,sources=source_hashes,cpp_differential_passed=True,compiled_original_mangled_names_matched=True,
        return_declaration_choices={"predicates":"portable bool for observed0/1 returns; originalreturnspelling not encoded",
            "getNumGeqs/getNumMixGeqs":"portable int32 return preservingall32bits; originalsignedness/spelling unresolved",
            "getCascadeState":"portable uint32 for observed0/1/2codes; originalenum/type spelling unresolved"},
        original_scope_and_qualifiers="Original case-sensitive namespace/class/member/const/ChannelType identity preserved. Positivevtable evidence for threeBase virtualmethods; no inheritance or completevtable fidelity claimed.",
        compiler=run(["g++","--version"],"compiler-version.log").splitlines()[0],compiler_flags=flags,object_sha256=sha(lib/obj),
        formatting={"path":str((out/"formatting.json").relative_to(lib)),"sha256":sha(out/"formatting.json")},test_output=logs,
        tools={name:sha(lib/name) for name in ("tools/mixer_state_inspect.py","tools/metering_inspect.py","tools/mixer_state_oracle.py","tools/mixer_state_verify.py")},
        original_arm_abi_compatible=False,hardware_verified=False,central_ledger_modified=False)
    path=out/"validation.json";path.write_text(json.dumps(proof,indent=2)+"\n")
    fragment={"functions":[dict(role=s["role"],mangled=s["mangled"],original_elf_sha256=s["original_elf_sha256"],
        validation=str(path.relative_to(lib)),validation_sha256=sha(path),sources=source_hashes,portable_ready=True,domain=domain) for s in records]}
    (out/"ready-functions.fragment.json").write_text(json.dumps(fragment,indent=2)+"\n")
    (out/"declaration-pending.json").write_text(json.dumps(pending,indent=2)+"\n")
    print("".join(role+": "+text for role,text in logs.items()),end="")
    print("PROOF",path,sha(path))


if __name__=="__main__":main()
