#!/usr/bin/env python3
"""Seal original manager routing logic within an explicit callback domain."""
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
    oracle_path=oracle_run/"arm-oracle.json";oracle=json.loads(oracle_path.read_text())
    fixtures=oracle_run/"arm-vectors.txt";assert sha(fixtures)==oracle["fixture_sha256"]
    out=oracle_run/"verification"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True,exist_ok=False);commands=[]

    def run(argv,name):
        commands.append(argv);result=subprocess.run(argv,cwd=lib,text=True,capture_output=True)
        (out/name).write_text("$ "+shlex.join(argv)+"\n"+result.stdout+result.stderr)
        (out/"commands.json").write_text(json.dumps(commands,indent=2)+"\n")
        if result.returncode:raise RuntimeError(f"{out/name}: {result.stdout}{result.stderr}")
        return result.stdout

    sources=["src/Presonus/DICE/Dice3Manager.cpp","include/presonus/dice/manager.hpp","tests/dice_routing_tests.cpp"]
    formatter=str(lib/".venv/bin/clang-format")
    version=run([formatter,"--version"],"formatter-version.log").strip()
    run([formatter,"--style=file","--fallback-style=LLVM","--dry-run","--Werror",*sources],"format-check.log")
    source_hashes={name:sha(lib/name) for name in sources}
    formatting=dict(formatter=version,configuration_sha256=sha(root/".clang-format"),format_check_passed=True,files=source_hashes)
    (out/"formatting.json").write_text(json.dumps(formatting,indent=2)+"\n")
    obj=str((out/"Dice3Manager.o").relative_to(lib));exe=str((out/"tests").relative_to(lib))
    flags=["-std=c++17","-O2","-Wall","-Wextra","-Wpedantic","-Iinclude"]
    run(["g++",*flags,"-c",sources[0],"-o",obj],"build-source.log")
    run(["g++",*flags,sources[2],obj,"-o",exe],"build-tests.log")
    nm=run(["nm","--defined-only",obj],"compiled-symbols.log")
    defined={line.split()[-1] for line in nm.splitlines() if line.split()}
    expected={s["mangled"] for s in oracle["functions"].values()};assert expected<=defined,expected-defined
    output=run([exe,str(fixtures.relative_to(lib))],"differential-tests.log")
    prefix="PASS:"+"".join(f' {op}={oracle["cases"][op]}' for op in sorted(oracle["cases"]))
    assert output.startswith(prefix)
    assert source_hashes=={name:sha(lib/name) for name in sources}
    domain=(oracle["domain"]+" Only surface13840 has theseManager methods. Thetransportboundary is independentpresonus::dice::RouteSink representingtheoriginalsetRoutecall, not a recoveredsubsystemimplementation. "
            "Portableexplicitsetupconstructor andstorage do not recoveroriginalzeroargconstructor, inheritance, ownership orARMobjectABI. Originalroutingprofileenumidentity retained withportableintunderlyingtype; originalenumerators/returntypedefspelling unresolved.")
    functions=[dict(s,role="client",original_elf_sha256=oracle["original_elf_sha256"]) for s in oracle["functions"].values()]
    proof=dict(original_elf_sha256=oracle["original_elf_sha256"],role="client",namespace="Presonus::DICE",class_name="Dice3Manager",
        functions=functions,mangled_names=sorted(expected),sources=source_hashes,domain=domain,
        cpp_differential_passed=True,compiled_mangled_names_matched=True,portable_ready=True,
        exact_ordered_callback_traces_compared=True,case_counts=oracle["cases"],callback_events=oracle["callback_events"],test_output=output,
        oracle_path=str(oracle_path.relative_to(lib)),oracle_sha256=sha(oracle_path),fixture_path=str(fixtures.relative_to(lib)),fixture_sha256=sha(fixtures),
        callback_contract=oracle["callback_contract"],state_checks=oracle["state_checks"],
        dependency_boundary=dict(oracle["callback_symbol"],body_executed=False,implementation_recovered=False),
        return_declaration_choice="Portableint32 preservesoriginalexplicitR0zeroonallpaths, includingnegativecallbackresults; exactoriginaltypedefspelling notencoded.",
        compiler=run(["g++","--version"],"compiler-version.log").splitlines()[0],compiler_flags=flags,object_sha256=sha(lib/obj),
        formatting={"path":str((out/"formatting.json").relative_to(lib)),"sha256":sha(out/"formatting.json")},
        tools={name:sha(lib/name) for name in ("tools/dice_routing_inspect.py","tools/metering_inspect.py","tools/dice_routing_oracle.py","tools/dice_routing_verify.py")},
        original_arm_abi_compatible=False,hardware_verified=False,central_ledger_modified=False)
    path=out/"validation.json";path.write_text(json.dumps(proof,indent=2)+"\n")
    fragment={"functions":[dict(role="client",mangled=s["mangled"],original_elf_sha256=oracle["original_elf_sha256"],
        validation=str(path.relative_to(lib)),validation_sha256=sha(path),sources=source_hashes,portable_ready=True,domain=domain) for s in functions]}
    (out/"ready-functions.fragment.json").write_text(json.dumps(fragment,indent=2)+"\n")
    print(output,end="");print("PROOF",path,sha(path))


if __name__=="__main__":main()
