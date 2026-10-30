"""Fixed Manager-batch retained Panel UART replay; no ledger mutation."""
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

from elftools.elf.elffile import ELFFile

REPO = Path(__file__).resolve().parents[3]
LIB = REPO / "uc-library"
OWN = LIB / "candidates/dice-manager-lifecycle"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tag = sys.argv[1]
    assert re.fullmatch(r"[A-Za-z0-9_-]+", tag)
    active = "--active" in sys.argv[2:]
    phase = REPO / "evidence/recovery/2026-10-28/manager-discovery-batch"
    out = phase / ("panel-uart-" + tag)
    out.mkdir(exist_ok=False)
    scratch = REPO / "temp/recovery-work/manager-panel-uart" / tag
    scratch.mkdir(parents=True, exist_ok=False)
    temp = scratch / "tmp"
    temp.mkdir()
    env = dict(os.environ, TMPDIR=str(temp), TMP=str(temp), TEMP=str(temp), PYTHONDONTWRITEBYTECODE="1")
    sync = OWN / "validation/receiver-sync-03/validation.json"
    proof = json.loads(sync.read_text())
    assert proof["passed"] and proof["source_snapshots_unchanged"]
    for name, digest in proof["source_hashes"].items():
        assert sha(LIB / name) == digest, name
    overlay = REPO / "temp/recovery-work/dice-manager-lifecycle/receiver-sync/receiver-sync-03/source"
    source_root = LIB if active else overlay
    header = source_root / "include/presonus/panel/uart_comm.hpp"
    assert sha(header) == sha(OWN / "include/presonus/panel/uart_comm.hpp")
    files = [source_root / "src/Presonus/Panel/UARTComm.cpp", LIB / "tests/panel_uart_comm_tests.cpp", LIB / "src/Presonus/Panel/protocol_comm.cpp", LIB / "src/Presonus/Panel/uart_protocol.cpp", LIB / "src/Presonus/DICE/PacketClockGateway.cpp", source_root / "src/portable/dice/OwnedUartServices.cpp"]
    assert all(path.is_file() for path in files)
    old = LIB / "candidates/panel-uart-comm/validation/compare-01/validation.json"
    original = json.loads(old.read_text())
    assert original["passed"] and original["cases_per_role"] == 2405 and original["original_core_bodies_loaded"] is False
    fixture = old.parent / "fixtures.txt"
    assert sha(fixture) == original["fixture_sha256"]
    for role, row in original["roles"].items():
        assert sha(old.parent / (role + "-arm-output.txt")) == row["arm_output_sha256"]
    for name, digest in original["tools"].items():
        assert sha(LIB / "candidates/panel-uart-comm/tools" / name) == digest
    commands = []

    def run(label, args, stdin=None):
        args = list(map(str, args))
        result = subprocess.run(args, cwd=REPO, env=env, input=stdin, text=True, capture_output=True)
        (out / (label + ".stdout.log")).write_text(result.stdout)
        (out / (label + ".stderr.log")).write_text(result.stderr)
        commands.append({"label": label, "command": args, "returncode": result.returncode})
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        assert result.returncode == 0, (label, result.stderr[-5000:])
        return result.stdout

    formatter = LIB / ".venv/bin/clang-format"
    version = run("formatter-version", [formatter, "--version"]).strip()
    assert "23.1.3" in version
    run("format-check", [formatter, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", header, *files])
    sdk = REPO / "temp/core-upstream/root-integration-01/upstream-core/sdk"
    core = sdk / "lib/libcorelib.a"
    upstream = REPO / "third_party/ccl-framework"
    assert run("core-pin", ["git", "-C", upstream, "rev-parse", "HEAD"]).strip() == "e8cbdea4a4a20e15111f5a690798a259c0374b31"
    assert not run("core-clean", ["git", "-C", upstream, "status", "--porcelain"])
    source_hashes = {str(path.relative_to(REPO)): sha(path) for path in [header, *files, old, fixture, sync, Path(__file__)]}
    dependencies = {}
    modes = {}
    original_rows = []
    for role, item in original["roles"].items():
        manifest = item["original_elf"]
        binary = REPO / manifest["path"]
        assert sha(binary) == manifest["sha256"]
        with binary.open("rb") as stream:
            elf = ELFFile(stream)
            for mode, row in item["originals"].items():
                section = elf.get_section(row["section"])
                offset = row["address"] - section["sh_addr"]
                assert 0 <= offset and offset + row["size"] <= section["sh_size"]
                data = section.data()[offset:offset + row["size"]]
                assert hashlib.sha256(data).hexdigest() == row["sha256"]
                original_rows.append({"role": role, "mode": mode, "original_elf_sha256": manifest["sha256"], **row})
    assert len(original_rows) == 22
    for mode, options in (("release", ["-O2"]), ("sanitizers", ["-O1", "-g", "-fsanitize=address,undefined", "-fno-sanitize=vptr", "-fno-sanitize-recover=all", "-fno-omit-frame-pointer"])):
        objects = []
        for index, source in enumerate(files):
            obj = scratch / f"{mode}-{index}.o"
            run(f"{mode}-compile-{index}", ["/usr/bin/c++", "-std=c++17", "-DCORE_USE_OPENSSL=1", "-Ulinux", "-frtti", "-fno-devirtualize", "-fno-devirtualize-speculatively", "-pthread", *options, "-I", source_root / "include", "-I", LIB / "include", "-isystem", sdk / "include/presonus-core-5", "-MMD", "-c", source, "-o", obj])
            objects.append(obj)
        exe = scratch / ("uart-" + mode)
        run(mode + "-link", ["/usr/bin/c++", *options, *objects, core, "-pthread", "-ldl", "-lm", "-Wl,--wrap=_ZN4Core11DebugPrintfEPKcz", "-Wl,--wrap=_ZdlPv", "-Wl,--wrap=_ZdlPvm", "-o", exe])
        output = run(mode + "-replay", [exe], fixture.read_text())
        assert len(output.splitlines()) == 2405
        for role in ("client", "server"):
            assert output == (old.parent / (role + "-arm-output.txt")).read_text(), (mode, role)
        symbols = run(mode + "-symbols", ["nm", "--defined-only", exe])
        names = {line.split()[-1] for line in symbols.splitlines() if line.split()}
        assert all(row["mangled"] in names for row in original_rows)
        modes[mode] = {"passed": True, "cases_per_role": 2405, "output_sha256": hashlib.sha256(output.encode()).hexdigest(), "executable_sha256": sha(exe), "object_hashes": {str(path.relative_to(REPO)): sha(path) for path in objects}}
        for depfile in scratch.glob(mode + "-*.d"):
            for token in shlex.split(depfile.read_text().replace("\\\n", " ").split(":", 1)[1]):
                path = Path(token).resolve()
                if path.is_relative_to(REPO) and path.is_file():
                    dependencies[str(path.relative_to(REPO))] = sha(path)
    for name, digest in {**source_hashes, **dependencies}.items():
        assert sha(REPO / name) == digest, name
    result = {"passed": True, "source_mode": "active" if active else "matched immutable candidate snapshot", "modes": modes, "original_ranges": original_rows, "source_hashes": source_hashes, "compiler_dependencies": dependencies, "original_oracle_regenerated": False, "core_binary_loaded": False, "device_io_executed": False, "formatter_version": version, "actual_core_archive_sha256": sha(core), "old_ready_records_preserved": 10, "old_pending_records_preserved": 12, "portable_ready": False, "scope": "Fresh full unchanged Panel UART 2405-case-per-role replay in Release/ASan/applicable UBSan against grown shared-provider header and real pinned CCL. Original ranges, current compiled original names, descriptor/state/ordered calls/buffers and actual deleting-destructor forwarding retained. New provider ownership is separately tested by Manager lifecycle. No original layout/Core equivalence, exceptions, unbounded polling, vptr sanitizer, ARM ABI or hardware proof; not a readiness fragment/admission."}
    (out / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": True, "cases_per_role_per_mode": 2405, "modes": 2, "ready_refresh_records": 10, "pending_refresh_records": 12}))


if __name__ == "__main__":
    main()
