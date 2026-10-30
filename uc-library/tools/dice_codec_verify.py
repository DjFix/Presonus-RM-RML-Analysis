#!/usr/bin/env python3
"""Seal numeric unpack ports and keep output-only packers declaration-pending."""
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

    sources=["src/Presonus/DICE/Codec.cpp","include/presonus/dice/codec.hpp","tests/dice_codec_tests.cpp"]
    formatter=str(lib/".venv/bin/clang-format")
    version=run([formatter,"--version"],"formatter-version.log").strip()
    run([formatter,"--style=file","--fallback-style=LLVM","--dry-run","--Werror",*sources],"format-check.log")
    source_hashes={name:sha(lib/name) for name in sources}
    formatting=dict(formatter=version,configuration_sha256=sha(root/".clang-format"),format_check_passed=True,files=source_hashes)
    (out/"formatting.json").write_text(json.dumps(formatting,indent=2)+"\n")
    obj=str((out/"Codec.o").relative_to(lib));exe=str((out/"tests").relative_to(lib))
    flags=["-std=c++17","-O2","-Wall","-Wextra","-Wpedantic","-Iinclude"]
    run(["g++",*flags,"-c",sources[0],"-o",obj],"build-source.log")
    run(["g++",*flags,sources[2],obj,"-o",exe],"build-tests.log")
    nm=run(["nm","--defined-only",obj],"compiled-symbols.log")
    defined={line.split()[-1] for line in nm.splitlines() if line.split()}
    ready=[];pending=[];logs={};oracles=[]
    for role in ("client","server"):
        oracle_path=oracle_run/role/"arm-oracle.json";oracle=json.loads(oracle_path.read_text())
        fixtures=oracle_run/role/"arm-vectors.txt";assert sha(fixtures)==oracle["fixture_sha256"]
        logs[role]=run([exe,str(fixtures.relative_to(lib))],role+"-differential-tests.log")
        expected="PASS:"+"".join(f' {op}={oracle["cases"][op]}' for op in sorted(oracle["cases"]))
        assert logs[role].startswith(expected)
        oracles.append(dict(role=role,path=str(oracle_path.relative_to(lib)),sha256=sha(oracle_path),fixture=str(fixtures.relative_to(lib)),fixture_sha256=sha(fixtures)))
        for op,symbol in oracle["functions"].items():
            assert symbol["mangled"] in defined,symbol["mangled"]
            record=dict(symbol,role=role,original_elf_sha256=oracle["original_elf_sha256"],case_count=oracle["cases"][op])
            if op in ("P","p"):
                record.update(portable_ready=False,status="compiled; output-only ARM differential passed; original declaration pending",
                    unresolved="Original void-versus-observable-value return declaration unresolved. Portablevoidchoice is not an originaldeclarationclaim; ARM storeordering is evidence only, not portablevolatile/MMIO ordering.")
                pending.append(record)
            else:
                record.update(portable_ready=True,status="bounded numeric/buffer semantic port validated")
                ready.append(record)
    assert source_hashes=={name:sha(lib/name) for name in sources}
    domain=("Original global scope and parameteridentity retained; portableunsigned32/unsigned16 unpackreturnchoices match observedzero-extendednumericwords. "
            "Noncanonicalhighbits deliberatelyunmasked in nonfinalbytes; exactnumericunpackreturns andcomplete32byteguardedbuffers compared over documentedoraclecases, offsets1..7. "
            "Packerreturns excluded;packersdeclarationpending. OrdinaryRAM only; no volatile/MMIOordering, pointerownership, hardware or originalARMABI claim.")
    proof=dict(original_scope="global",sources=source_hashes,functions=ready,pending_functions=pending,oracles=oracles,
        domain=domain,cpp_differential_passed=True,compiled_original_mangled_names_matched=True,
        return_declaration_caveat="Unpackreturntypes are explicitportableunsignednumericchoices; exactoriginalspelling notencoded. Packervoid-vs-value unresolved andexcludedfromreadiness.",
        compiler=run(["g++","--version"],"compiler-version.log").splitlines()[0],compiler_flags=flags,object_sha256=sha(lib/obj),
        formatting={"path":str((out/"formatting.json").relative_to(lib)),"sha256":sha(out/"formatting.json")},test_output=logs,
        tools={name:sha(lib/name) for name in ("tools/dice_codec_inspect.py","tools/metering_inspect.py","tools/dice_codec_oracle.py","tools/dice_codec_verify.py")},
        original_arm_abi_compatible=False,hardware_verified=False,central_ledger_modified=False)
    path=out/"validation.json";path.write_text(json.dumps(proof,indent=2)+"\n")
    fragment={"functions":[dict(role=s["role"],mangled=s["mangled"],original_elf_sha256=s["original_elf_sha256"],
        validation=str(path.relative_to(lib)),validation_sha256=sha(path),sources=source_hashes,portable_ready=True,domain=domain) for s in ready]}
    (out/"ready-functions.fragment.json").write_text(json.dumps(fragment,indent=2)+"\n")
    (out/"declaration-pending.json").write_text(json.dumps(pending,indent=2)+"\n")
    print("".join(role+": "+text for role,text in logs.items()),end="")
    print("PROOF",path,sha(path))


if __name__=="__main__":main()
