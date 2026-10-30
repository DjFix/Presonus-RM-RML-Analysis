#!/usr/bin/env python3
"""Audit actual source Core linkage/header identity after completed wait replay."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex

from avb_protocol_reseal import command, sha

REPLAY = "validation/dice-response-candidate/runs/20261027T023858.579945Z/candidate-validation.json"
REPLAY_SHA = "9a819c81b5a5935d6eee59a53d43399e731dd64c370a973df5a273704b3d8e94"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository",type=Path)
    args=parser.parse_args()
    repository=args.repository.resolve()
    library=repository/"uc-library"
    path=library/REPLAY
    assert sha(path)==REPLAY_SHA
    replay=json.loads(path.read_text())
    for n,h in replay["sources"].items():
        assert sha(library/n)==h,n
    provider=replay["provider_proof"]
    assert sha(library/provider["path"])==provider["sha256"]
    for n,r in json.loads((library/provider["path"]).read_text())["files"].items():
        assert sha(repository/n)==r["sha256"]
    output=library/"validation/dice-response-candidate/seals"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output.mkdir(parents=True,exist_ok=False)
    candidate=library/"validation/dice-response-candidate"
    frozen=library/"validation/dice-packet-candidate"
    sdk=repository/"temp/core-upstream/provider-integration-02/build/upstream-core/sdk/include/presonus-core-5"
    vendor=repository/"third_party/ccl-framework"
    source=candidate/"src/CclResponseServices.cpp"
    text=command(["g++","-std=c++17","-Ulinux","-DNDEBUG=1","-DCORE_USE_OPENSSL=1","-DPRESONUS_HAS_UPSTREAM_CORE=1","-I"+str(candidate/"include"),"-I"+str(frozen/"include"),"-I"+str(sdk),"-M","-MT","closure",str(source)],output/"dependencies.log")
    headers={}
    for name in shlex.split(text.replace("\\\n"," ").split(":",1)[1]):
        p=Path(name)
        if not p.is_relative_to(sdk):
            continue
        rel=p.relative_to(sdk)
        assert sha(p)==sha(vendor/rel),str(rel)
        blob=command(["git","-C",str(vendor),"rev-parse",replay["upstream_commit"]+":"+str(rel)],output/("blob-"+str(rel).replace("/","-")+".log")).strip()
        actual=command(["git","-C",str(vendor),"hash-object",str(vendor/rel)],output/("hash-"+str(rel).replace("/","-")+".log")).strip()
        assert blob==actual
        headers[str(p.relative_to(repository))]=dict(sha256=sha(p),upstream_path=str(rel),pinned_git_blob=blob)
    # Public CurrentThread::sleep is a source-inline forwarding API; its actual
    # out-of-line provider body is Platform::CurrentThread::sleep.
    source_core_names=["_ZN4Core8Platform13CurrentThread5sleepEj","_ZN4Core11DebugPrintfEPKcz"]
    nm=command(["nm","--defined-only",str(path.parent/"real-core-tests")],output/"real-core-nm.log")
    assert set(source_core_names)<={line.split()[-1] for line in nm.splitlines() if line.split()}
    command([str(library/".venv/bin/clang-format"),"--style=file","--fallback-style=LLVM","--dry-run","--Werror",*[str(library/n) for n in replay["sources"]]],output/"formatter-check.log")
    role_oracles={role:json.loads((path.parent/f"{role}-arm-oracle.json").read_text()) for role in ("client","server")}
    for role,oracle in role_oracles.items():
        assert sha(path.parent/f"{role}-arm-oracle.json")==replay["oracle_sha256"][role]
        assert sha(path.parent/f"{role}-response-vectors.txt.gz")==oracle["fixture_sha256"]
    proof=dict(replay,input_replay=dict(path=REPLAY,sha256=REPLAY_SHA),actual_sdk_dependencies=headers,
               source_provider_compiled_symbols=source_core_names,source_provider_headers_git_checked=True,
               role_domains={role:o["domain"] for role,o in role_oracles.items()},counts={role:o["counts"] for role,o in role_oracles.items()},
               source_binding="Actual pinned CCL SystemClock::getTime (header-inline POSIX nanoseconds), CurrentThread::sleep(uint32 milliseconds), DebugPrintf source body. No legacy Core symbol definitions or Core binary bodies.",
               noaa_specific="Separate original NOAA methods; TCardSPI::onIdle(false), then one forced onIdle(true) after strict elapsed>60ms(ack) or>23ms(response), only before timeout. Forced pump remains after timing even if normal pump set response.",
               domain=replay["domain"]+" Server is original NOAA/SPI scope with separately observed one-shot forced pumping, not an assumed DICE alias.",
               seal_tool_sha256=sha(Path(__file__)),validation_replayed=False,
               sealing_note="Completed original app/native replay unchanged; added source provider exact modern symbols and all compiler-selected SDK-header/pinned-Git identities.")
    result=output/"candidate-validation.json"
    result.write_text(json.dumps(proof,indent=2)+"\n")
    records=[dict(role=r["role"],mangled=r["mangled"],original_elf_sha256=r["original_elf_sha256"],validation=str(result.relative_to(library)),validation_sha256=sha(result),sources=proof["sources"],cpp_compiled=True,mangling_namespace_checked=True,portable_ready=True,domain=proof["domain"]) for r in proof["functions"]]
    (output/"candidate-ready-functions.fragment.json").write_text(json.dumps(dict(functions=records),indent=2)+"\n")
    print("SEALED",result,sha(result),"SDK HEADERS",len(headers),"READY CANDIDATE ENTRIES",len(records))


if __name__=="__main__":
    main()
