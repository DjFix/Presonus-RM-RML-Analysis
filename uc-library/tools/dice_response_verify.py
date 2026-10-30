#!/usr/bin/env python3
"""Bounded original DICE app wait differential + actual-source CCL binding."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import platform
import random
import shutil
import struct

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import arm_const as arm

from avb_protocol_reseal import command, sha, verify_originals

MANGLES = ["_ZN8Presonus4DICE13SysexReceiver7waitAckEx",
           "_ZN8Presonus4DICE13SysexReceiver15waitResponseSetERjx"]
ROLE_MANGLES = {"client": MANGLES, "server": [name.replace("4DICE", "4NOAA") for name in MANGLES]}
MASK = (1 << 64) - 1
PIN = "e8cbdea4a4a20e15111f5a690798a259c0374b31"
PROVIDER_SHA = "cf13e63b689bcf3ef1b8a63f6dfb5e2bbecd4fa3c41b45b7725c44b27e52b408"


def signed(bits):
    return (bits ^ (1 << 63)) - (1 << 63)


def generate(repository, library, output, role):
    directory = library / "recovered-all" / role
    manifest = json.loads((directory / "manifest.json").read_text())
    binary = repository / manifest["path"]
    assert sha(binary) == manifest["sha256"]
    rows = json.loads((directory / "symbols.json").read_text())
    names = {r["mangled"]:r for r in rows}
    functions = [dict(names[n], role=role, original_elf_sha256=manifest["sha256"]) for n in ROLE_MANGLES[role]]
    verify_originals(repository, library, [functions])
    targets = {}
    for label, prefix in (("clock", "Core::GetAbsoluteTime()"), ("sleep", "Core::Threads::sleep(unsigned int)"),
                          ("debug", "Core::DebugPrintf("), ("divide", "__aeabi_ldivmod"),
                          ("pump", "Presonus::DICE::Dice3Uart::onIdle()" if role == "client" else "Presonus::NOAA::TCardSPI::onIdle(bool)")):
        row = next(r for r in rows if r["kind"] == "STT_FUNC" and r["demangled"].startswith(prefix))
        targets[row["address"]] = label
    uc = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    pages = set()
    with binary.open("rb") as stream:
        for segment in ELFFile(stream).iter_segments():
            if segment["p_type"] != "PT_LOAD":
                continue
            start, end = segment["p_vaddr"], segment["p_vaddr"] + segment["p_memsz"]
            for page in range(start & ~4095, (end + 4095) & ~4095, 4096):
                if page not in pages:
                    uc.mem_map(page, 4096)
                    pages.add(page)
            uc.mem_write(start, segment.data())
    code = [(directory / r["export_path"]).read_bytes() for r in functions]
    singleton = struct.unpack_from("<I", code[0], len(code[0]) - 12)[0]
    assert singleton == struct.unpack_from("<I", code[1], len(code[1]) - 16)[0]
    assert struct.unpack_from("<I", code[0], len(code[0]) - 16)[0] == 1000000
    assert struct.unpack_from("<I", code[1], len(code[1]) - 12)[0] == 1000000
    obj, response, uart, stack, stop = 0x10000000, 0x10000100, 0x10002000, 0x20000000, 0x30000000
    uc.mem_map(obj, 16384)
    uc.mem_map(stack, 65536)
    uc.mem_map(stop, 4096)
    uc.mem_write(singleton, struct.pack("<I", uart))
    state = {}
    counts = Counter()

    def reg(index):
        return uc.reg_read(getattr(arm, f"UC_ARM_REG_R{index}"))

    def word():
        return struct.unpack("<I", uc.mem_read(response, 4))[0]

    def set64(first, value):
        bits = value & MASK
        uc.reg_write(getattr(arm, f"UC_ARM_REG_R{first}"), bits & 0xffffffff)
        uc.reg_write(getattr(arm, f"UC_ARM_REG_R{first+1}"), bits >> 32)

    def event(kind, ticks=0, first=0, second=0):
        index = len(state["events"])
        assert index < 40
        before_ack = uc.mem_read(obj + 4, 1)[0]
        before_word = word()
        if index == state["mutate_at"]:
            if state["new_ack"] < 256:
                uc.mem_write(obj + 4, bytes([state["new_ack"]]))
            if state["new_word"] < 0x100000000:
                uc.mem_write(response, struct.pack("<I", state["new_word"]))
        if index == 31:
            uc.mem_write(obj + 4, b"\x11")
            uc.mem_write(response, struct.pack("<I", 0x80000000))
        state["events"].append([kind, ticks & MASK, first, second, before_ack, before_word, uc.mem_read(obj + 4, 1)[0], word()])

    def hook(machine, address, size, user):
        label = targets.get(address)
        if label is None:
            row = functions[state["mode"]]
            assert row["address"] <= address < row["address"] + row["size"], f"unapproved execution {address:#x}"
            return
        if label == "clock":
            ticks = state["ticks"][state["clocks"]]
            state["clocks"] += 1
            event('C', ticks)
            set64(0, ticks)
        elif label == "divide":
            numerator = signed(reg(0) | reg(1) << 32)
            divisor = signed(reg(2) | reg(3) << 32)
            assert divisor == 1000000
            quotient = abs(numerator) // divisor * (-1 if numerator < 0 else 1)
            set64(0, quotient)
            set64(2, numerator - quotient * divisor)
            state["divisions"] += 1
        elif label == "pump":
            assert reg(0) == uart
            force = reg(1) if role == "server" else 0
            assert force in (0, 1)
            event('P', first=force)
            uc.reg_write(arm.UC_ARM_REG_R0, 0xa5a5a5a5)
        elif label == "sleep":
            assert reg(0) == 1
            event('S', first=reg(0))
            uc.reg_write(arm.UC_ARM_REG_R0, 0x5a5a5a5a)
        else:
            address = reg(0)
            text = bytes(uc.mem_read(address, 64)).split(b"\0", 1)[0]
            if state["mode"] == 0:
                assert text == b"ack timeout\n"
                event('A')
            else:
                assert text == b"waitResponseSet timeout:%d %d\n"
                event('R', first=reg(1), second=reg(2))
            uc.reg_write(arm.UC_ARM_REG_R0, 0xdeadbeef)
        uc.reg_write(arm.UC_ARM_REG_PC, uc.reg_read(arm.UC_ARM_REG_LR))

    def writes(machine, access, address, size, value, user):
        if address == response and size == 4:
            assert state["mode"] == 1 and not state["events"] and value == 0
            state["resets"] += 1
        else:
            assert stack <= address and address + size <= stack + 65536

    uc.hook_add(unicorn.UC_HOOK_CODE, hook)
    uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, writes)
    rng = random.Random(0x4449434557414954)
    fixture = output / f"{role}-response-vectors.txt.gz"
    with fixture.open("wb") as compressed:
        with gzip.GzipFile(filename="", fileobj=compressed, mode="wb", mtime=0) as stream:
            def emit(mode, timeout, initial_ack=0, initial_word=0xdeadbeef, mutate_at=-1,
                     new_ack=256, new_word=0x100000000, ticks=None):
                if ticks is None:
                    ticks = [0] * 40
                initial = bytearray([0xa5] * 16384)
                initial[4] = initial_ack
                struct.pack_into("<I", initial, response - obj, initial_word)
                uc.mem_write(obj, bytes(initial))
                state.update(mode=mode, ticks=ticks, clocks=0, divisions=0, events=[], resets=0,
                             mutate_at=mutate_at, new_ack=new_ack, new_word=new_word)
                uc.reg_write(arm.UC_ARM_REG_CPSR, 0x10)
                for register in range(13):
                    uc.reg_write(getattr(arm, f"UC_ARM_REG_R{register}"), 0x55555555)
                uc.reg_write(arm.UC_ARM_REG_R0, obj)
                uc.reg_write(arm.UC_ARM_REG_R1, response)
                set64(2, timeout)
                uc.reg_write(arm.UC_ARM_REG_SP, stack + 0xff00)
                uc.reg_write(arm.UC_ARM_REG_LR, stop)
                uc.emu_start(functions[mode]["address"], stop, count=20000)
                assert uc.reg_read(arm.UC_ARM_REG_PC) == stop and uc.reg_read(arm.UC_ARM_REG_SP) == stack + 0xff00
                assert state["clocks"] == state["divisions"]
                assert state["resets"] == mode
                forced_calls = sum(e[0] == 'P' and e[2] == 1 for e in state["events"])
                assert forced_calls <= (1 if role == "server" else 0)
                expected = bytearray(initial)
                expected[4] = uc.mem_read(obj + 4, 1)[0]
                struct.pack_into("<I", expected, response - obj, word())
                assert bytes(uc.mem_read(obj, 16384)) == expected
                assert struct.unpack("<I", uc.mem_read(singleton, 4))[0] == uart
                result = reg(0)
                assert result == (expected[4] if mode == 0 else int(word() != 0))
                values = [mode, timeout & MASK, initial_ack, initial_word, mutate_at, new_ack, new_word,
                          result, expected[4], word(), len(state["events"])]
                values += [v for row in state["events"] for v in row]
                stream.write((" ".join(map(str, values)) + "\n").encode())
                counts["ack" if mode == 0 else "response"] += 1
                counts["clock_calls"] += state["clocks"]
                counts["idle_calls"] += sum(e[0] == 'P' for e in state["events"])
                counts["timeout_notices"] += sum(e[0] in ('A','R') for e in state["events"])
                counts["forced_idle_calls"] += forced_calls

            for ack in range(256):
                emit(0, 0, initial_ack=ack, ticks=[0,1000000] + [0] * 38)
                for phase in range(5):
                    emit(0, -1, mutate_at=phase, new_ack=ack)
            timeouts = [-(1 << 63), -1, 0, 1, 0x7fffffff, 0xffffffff, 0x100000000, (1 << 63)-1]
            raw_edges = [-(1 << 63), -1000001, -1000000, -999999, -1, 0, 1, 999999, 1000000, (1 << 63)-1]
            for mode in (0,1):
                if role == "server":
                    for milliseconds in (0,22,23,24,59,60,61,100,1000):
                        for timeout in (20,23,24,60,61,1000):
                            for phase in (-1,1,3,4,7):
                                emit(mode,timeout,mutate_at=phase,new_ack=255,new_word=0x80000000,
                                     ticks=[0]+[milliseconds*1000000]*39)
                for timeout in timeouts:
                    for phase in range(13):
                        for value in (0, 1, 127, 128, 255):
                            tick = raw_edges[(phase + value) % len(raw_edges)]
                            emit(mode, timeout, initial_word=rng.getrandbits(32), mutate_at=phase,
                                 new_ack=value, new_word=[0,1,0x80000000,0xffffffff][value % 4], ticks=[tick] * 40)
                for timeout in range(-2,4):
                    for elapsed in (timeout-1, timeout, timeout+1):
                        for raw_start in raw_edges:
                            end = signed((raw_start + elapsed * 1000000) & MASK)
                            emit(mode, timeout, ticks=[raw_start] + [end]*39)
                for _ in range(4096):
                    emit(mode, rng.choice(timeouts + [rng.randrange(-100,101)]), initial_ack=rng.randrange(256) if rng.randrange(4)==0 else 0,
                         initial_word=rng.getrandbits(32), mutate_at=rng.randrange(-1,16), new_ack=rng.randrange(257),
                         new_word=rng.choice([0,1,0xffffffff,0x100000000,rng.getrandbits(32)]),
                         ticks=[signed(rng.getrandbits(64)) for _ in range(40)])
    oracle = dict(role=role, functions=functions, counts=dict(counts), fixture_sha256=sha(fixture),
                  intercepted_targets={hex(a):n for a,n in targets.items()}, singleton_slot=singleton,
                  execution="Only two original Presonus app wait bodies in role's actual DICE/NOAA namespace. Core clock/sleep/debug and compiler signed-division contracts intercepted; no Core body, UART/SPI device, singleton allocation or hardware execution.",
                  domain="Preinitialized borrowed UART; distinct responseword. Exact ordered boundary/state traces, raw command returns, reset-before-clock, signed64 nanosecond division/truncation, timeout equality/negative/highword, backward/extreme rawtimes. Deterministic cooperative mutation; fallback event31 terminates otherwise unbounded cases.")
    (output / f"{role}-arm-oracle.json").write_text(json.dumps(oracle,indent=2) + "\n")
    return oracle


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository",type=Path)
    parser.add_argument("--reuse-client-oracle",type=Path)
    args=parser.parse_args()
    assert platform.system()=="Linux"
    repository=args.repository.resolve()
    library=repository/"uc-library"
    candidate=library/"validation/dice-response-candidate"
    frozen=library/"validation/dice-packet-candidate"
    output=candidate/"runs"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output.mkdir(parents=True,exist_ok=False)
    provider_path=library/"validation/core-upstream/provider-integration-02-validation.json"
    assert sha(provider_path)==PROVIDER_SHA
    provider=json.loads(provider_path.read_text())
    assert provider["source_commit"]==PIN
    for name,entry in provider["files"].items():
        assert sha(repository/name)==entry["sha256"]
    sdk=repository/"temp/core-upstream/provider-integration-02/build/upstream-core/sdk"
    vendor=repository/"third_party/ccl-framework"
    assert command(["git","-C",str(vendor),"rev-parse","HEAD"],output/"upstream-pin.log").strip()==PIN
    owned=sorted([*candidate.glob("include/presonus/**/*.hpp"),*candidate.glob("src/*.cpp"),*candidate.glob("tests/*.cpp")])
    formatter=library/".venv/bin/clang-format"
    version=command([str(formatter),"--version"],output/"formatter-version.log").strip()
    command([str(formatter),"--style=file","--fallback-style=LLVM","-i",*map(str,owned)],output/"formatter-apply.log")
    command([str(formatter),"--style=file","--fallback-style=LLVM","--dry-run","--Werror",*map(str,owned)],output/"formatter-check.log")
    closure=owned+[frozen/"include/presonus/dice/packet_services.hpp",frozen/"src/SysexReceiver.cpp"]
    before={str(p.relative_to(library)):sha(p) for p in closure}
    oracles={}
    reused=None
    if args.reuse_client_oracle:
        source=library/args.reuse_client_oracle
        oracle=json.loads(source.read_text())
        assert [r["mangled"] for r in oracle["functions"]]==ROLE_MANGLES["client"]
        verify_originals(repository,library,[oracle["functions"]])
        fixture=source.parent/"client-response-vectors.txt.gz"
        assert sha(fixture)==oracle["fixture_sha256"]
        shutil.copy2(source,output/"client-arm-oracle.json")
        shutil.copy2(fixture,output/fixture.name)
        oracles["client"]=oracle
        reused=dict(path=str(source.relative_to(library)),sha256=sha(source),initial_generator_sha256=sha(candidate/"history/initial-oracle-generator.py"))
    else:
        oracles["client"]=generate(repository,library,output,"client")
    oracles["server"]=generate(repository,library,output,"server")
    build=["g++","-std=c++17","-O2","-Ulinux","-DNDEBUG=1","-DCORE_USE_OPENSSL=1","-DPRESONUS_HAS_UPSTREAM_CORE=1","-I"+str(candidate/"include"),"-I"+str(frozen/"include"),"-I"+str(sdk/"include/presonus-core-5"),*[str(p) for p in sorted((candidate/"src").glob("*.cpp"))],str(frozen/"src/SysexReceiver.cpp")]
    archives=[sdk/"lib/libcorelib.a",sdk/"lib/libpresonus_core_allocator.a"]
    results={}
    names=set()
    for label,test in (("response",candidate/"tests/response_tests.cpp"),("real-core",candidate/"tests/ccl_response_smoke.cpp")):
        executable=output/(label+"-tests")
        command([*build,str(test),*map(str,archives),"-lz","-pthread","-ldl","-lm","-o",str(executable)],output/(label+"-compile.log"))
        if label=="response":
            results[label]=[command([str(executable),str(output/f"{role}-response-vectors.txt.gz"),role],output/(role+"-replay.log")).strip() for role in oracles]
        else:
            results[label]=command([str(executable)],output/"real-core-smoke.log").strip()
        names|={line.split()[-1] for line in command(["nm","--defined-only",str(executable)],output/(label+"-nm.log")).splitlines() if line.split()}
    expected_names={n for ns in ROLE_MANGLES.values() for n in ns}
    assert expected_names<=names
    assert before=={str(p.relative_to(library)):sha(p) for p in closure}
    proof=dict(status="isolated DICE/NOAA response wait/source CCL binding candidate",cpp_differential_passed=True,compiled_mangled_names_matched=True,mangled_names=sorted(expected_names),reused_client_oracle=reused,
               functions=[dict(r,portable_ready=True) for o in oracles.values() for r in o["functions"]],sources=before,formatter=version,native_results=results,
               oracle_sha256={role:sha(output/f"{role}-arm-oracle.json") for role in oracles},fixtures={role:oracles[role]["fixture_sha256"] for role in oracles},
               provider_proof=dict(path=str(provider_path.relative_to(library)),sha256=PROVIDER_SHA,files_checked=len(provider["files"])),upstream_commit=PIN,
               provider_archives={str(p.relative_to(repository)):sha(p) for p in archives},tool_sha256=sha(Path(__file__)),
               domain=oracles["client"]["domain"],
               unresolved=["Original return spelling/typedef unencoded; waitAck unsigned char and waitResponseSet bool are portable numeric choices matching full observed R0.","UART must already be initialized; original lazy singleton allocation/registration branch excluded. Borrowed idle pump remains an explicit application dependency, not a device backend.","Cooperative state updates at service boundaries only; concurrent unsynchronized access, aliasing responseword with receiver/global memory and unbounded waits are outside proof.","Legacy GetAbsoluteTime/global Threads::sleep differ from actual source SystemClock/CurrentThread APIs: intentional Linux POSIX nanosecond/millisecond adapters, no old Core ABI or body recovery.","No full original class layout/inheritance, ARM ABI or hardware interoperability claim."])
    path=output/"candidate-validation.json"
    path.write_text(json.dumps(proof,indent=2)+"\n")
    records=[dict(role=r["role"],mangled=r["mangled"],original_elf_sha256=r["original_elf_sha256"],validation=str(path.relative_to(library)),validation_sha256=sha(path),sources=before,cpp_compiled=True,mangling_namespace_checked=True,portable_ready=True,domain=proof["domain"]) for r in proof["functions"]]
    (output/"candidate-ready-functions.fragment.json").write_text(json.dumps(dict(functions=records),indent=2)+"\n")
    print("RESULTS",results,flush=True)
    print("PROOF",path,sha(path),flush=True)


if __name__=="__main__":
    main()
