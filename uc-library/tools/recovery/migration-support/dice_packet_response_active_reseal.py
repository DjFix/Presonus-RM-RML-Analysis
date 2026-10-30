#!/usr/bin/env python3
"""Guarded fixture-only reseal of completed packet/wait and header dependents."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
PIN = "e8cbdea4a4a20e15111f5a690798a259c0374b31"
HEADER = "include/presonus/dice/sysex.hpp"
FINAL_HEADER = "922790f2790af825e97c33f498b4a1abc92f2ef0ab6a3be82fb9b1062e9d5549"
INPUTS = {
    "packet": ("validation/dice-packet-candidate/runs/20261026T220418.737889Z/verification/20261026T222135.419433Z/candidate-validation.json", "92e72332a484573f3e6e4c5dcb9c2349c0ad501c593a14a692996dd0beb7226c"),
    "wait": ("validation/dice-response-candidate/seals/20261027T024529.685428Z/candidate-validation.json", "3d09163b65e506fbabc7a0ed6e34fdcdc8e5ddfc64a668c7d32a62418ffa6ef9"),
    "avb": ("validation/avb-lookup-active/runs/20261027T024718.933061Z/validation.json", "0e5982020daf9874e4ac836d69fcdaeba202dbe9a7c65a700e6069e690805317"),
    "dice": ("validation/dice-subsystem/runs/20261026T194021.475305Z-0a62b643/validation.json", "5e0f878d1d22ca315f3e78e8ce2eef9f424e88ee6e317a62e1672d944155a69b"),
    "vtables": ("validation/dice-packet-candidate/original-vtable-evidence.json", "449bdd868dee81e52aaeb1c3e2ff8fe54d90405be6daadc0e54d48198833cd93"),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True,
                        help="Configured root build; provenance only, never rebuilt or modified")
    parser.add_argument("--provider-proof", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    repo = args.repository.resolve()
    library = repo / "uc-library"
    if not library.is_dir():
        library = repo / "uc-library"
    def rooted(path):
        selected = (repo / path).resolve()
        assert selected.is_relative_to(repo), str(selected)
        return selected
    sdk, root_build, provider_path = map(rooted, (args.sdk, args.build, args.provider_proof))
    assert (root_build / "CMakeCache.txt").is_file()
    frozen = {}
    input_hashes = {}
    for group, (name, digest) in INPUTS.items():
        assert sha(library / name) == digest, name
        frozen[group] = json.loads((library / name).read_text())
        input_hashes[name] = digest
    packet, wait, avb, dice = (frozen[k] for k in ("packet", "wait", "avb", "dice"))
    packet_candidate = library / "validation/dice-packet-candidate"
    wait_candidate = library / "validation/dice-response-candidate"
    packet_manifest = json.loads((packet_candidate / "apply-manifest.json").read_text())
    wait_manifest = json.loads((wait_candidate / "apply-manifest.json").read_text())
    assert sha(packet_candidate / "apply-manifest.json") == wait_manifest["packet_prerequisite"]["manifest_sha256"]
    assert packet_manifest["candidate_proof_sha256"] == INPUTS["packet"][1]
    assert wait_manifest["proof_sha256"] == INPUTS["wait"][1]
    assert wait_manifest["shared_header_merge"]["candidate_header_sha256"] == FINAL_HEADER
    expected_active = {}
    for candidate, manifest in ((packet_candidate, packet_manifest), (wait_candidate, wait_manifest)):
        for item in manifest["files"]:
            assert sha(candidate / item["candidate"]) == item["sha256"]
            expected_active[item["target"]] = item["sha256"]
    assert len(expected_active) == 16
    expected_active[HEADER] = FINAL_HEADER
    assert sha(wait_candidate / HEADER) == FINAL_HEADER
    for name, digest in packet["unchanged_active_dependencies"].items():
        assert sha(library / name) == digest, name
    for name, digest in avb["sources"].items():
        if name != HEADER and not name.endswith("CMakeLists.txt"):
            assert sha(library / name) == digest, name
    provider = json.loads(provider_path.read_text())
    assert provider["passed"] and provider["source_commit"] == PIN
    assert provider["original_core_binary_reconstructed"] is False
    for name, digest in provider["provider_sdk_hashes"].items():
        assert sha(sdk / name) == digest, name
    upstream = repo / "third_party/ccl-framework"
    sdk_headers = {}
    for path in sorted((sdk / "include/presonus-core-5/core").rglob("*")):
        if path.is_file():
            relative = path.relative_to(sdk / "include/presonus-core-5")
            assert sha(path) == sha(upstream / relative)
            sdk_headers[str(relative)] = sha(path)
    assert set(sdk_headers) == {str(p.relative_to(upstream)) for p in (upstream / "core").rglob("*") if p.is_file() and p.suffix in (".h", ".hpp")}
    # Frozen packet metadata lacks role/hash; attach ONLY after actual manifest equality.
    manifest = json.loads((library / "recovered-all/client/manifest.json").read_text())
    assert manifest["sha256"] == packet["original_elf_sha256"] == dice["original_elf_sha256"]
    packet_rows = [dict(row, role="client", original_elf_sha256=manifest["sha256"], group="packet",
                        portable_ready="7receiveE" not in row["mangled"]) for row in packet["functions"]]
    assert len(packet_rows) == 7 and sum(r["portable_ready"] for r in packet_rows) == 5
    assert [r["mangled"] for r in packet_rows if "SysexPacketC" in r["mangled"]] == ["_ZN8Presonus4DICE11SysexPacketC1EPKhh"]
    original_dice = dice["original_symbols"]
    if isinstance(original_dice, dict):
        original_dice = list(original_dice.values())
    dice_rows = [dict(row, role="client", original_elf_sha256=manifest["sha256"], group="dice", portable_ready=True) for row in original_dice]
    wait_rows = [dict(row, group="wait") for row in wait["functions"]]
    avb_rows = [dict(row, group="avb-" + row["group"]) for row in avb["functions"]]
    rows = packet_rows + wait_rows + dice_rows + avb_rows
    assert len(dice_rows) == 2 and len(rows) == len({(r["role"], r["mangled"]) for r in rows}) == 25
    assert sum(r["portable_ready"] for r in rows) == 16
    fixtures = {}
    def retained(path, digest):
        assert sha(path) == digest, str(path)
        fixtures[str(path.relative_to(library))] = digest
        return path
    packet_oracle = retained(library / packet["oracle_path"], packet["oracle_sha256"])
    packet_vectors = {mode: retained(packet_oracle.parent / filename, packet["fixture_hashes"][filename])
                      for mode, filename in (("constructor", "constructors.txt"), ("commands", "commands.txt"), ("receivers", "receivers.txt"))}
    wait_replay = retained(library / wait["input_replay"]["path"], wait["input_replay"]["sha256"])
    wait_vectors = {}
    for role in ("client", "server"):
        retained(wait_replay.parent / (role + "-arm-oracle.json"), wait["oracle_sha256"][role])
        wait_vectors[role] = retained(wait_replay.parent / (role + "-response-vectors.txt.gz"), wait["fixtures"][role])
    dice_oracle_path = library / "validation/dice-subsystem/arm-oracle.json"
    assert sha(dice_oracle_path) == "ec7f7a9b888be42ef1c1c372b67e63decb1bdfbf7bf7411868d739292947e27c"
    dice_oracle = json.loads(dice_oracle_path.read_text())
    dice_vector = retained(dice_oracle_path.parent / "arm-vectors.txt", dice_oracle["vectors_sha256"])
    for name, digest in avb["existing_fixture_sha256"].items():
        retained(library / name, digest)
    lookup_replay = retained(library / avb["input_replay"]["path"], avb["input_replay"]["sha256"])
    lookup_vectors = {}
    for role in ("client", "server"):
        path = retained(lookup_replay.parent / (role + "-arm-oracle.json"), avb["oracle_sha256"][role])
        lookup_vectors[role] = retained(path.parent / (role + "-lookup-vectors.txt"), json.loads(path.read_text())["fixture_sha256"])
    statuses = {name: "matching" if (library / name).is_file() and sha(library / name) == digest else "missing-or-different"
                for name, digest in expected_active.items()}
    plan = dict(execute=args.execute, source_pin=PIN, sdk_headers_checked=len(sdk_headers),
                expected_final_header_sha256=FINAL_HEADER, active_products=statuses,
                rows=25, ready_entries=16, pending_entries=9, original_oracle_regenerated=False,
                root_build=str(root_build), root_build_modified=False, isolated_fresh_objects=True,
                baseline_ledger_expected={"ready": 407, "pending": 41})
    if not args.execute:
        print(json.dumps(plan, indent=2))
        return
    assert sys.platform.startswith("linux")
    assert all(value == "matching" for value in statuses.values()), "Atomic root apply incomplete"
    from avb_protocol_reseal import verify_originals, HELPER, LISTENER, TALKER
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    work = repo / "temp/dice-packet-response-active" / stamp
    output = library / "validation/dice-packet-response-active/runs" / stamp
    evidence = repo / "evidence/recovery/2026-10-27/dice-packet-response-active" / stamp
    for path in (work, output, evidence):
        path.mkdir(parents=True, exist_ok=False)
    (work / "tmp").mkdir()
    commands = []
    def run(name, argv):
        result = subprocess.run([str(a) for a in argv], cwd=repo,
            env=dict(os.environ, TMPDIR=str(work / "tmp")), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (evidence / (name + ".log")).write_text(result.stdout)
        commands.append(dict(name=name, argv=[str(a) for a in argv], exit_code=result.returncode))
        (evidence / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError(f"{name}: {result.stdout[-4000:]}")
        return result.stdout
    assert run("source-pin", ["git", "-C", upstream, "rev-parse", "HEAD"]).strip() == PIN
    assert not run("source-clean", ["git", "-C", upstream, "status", "--porcelain", "--untracked-files=all"]).strip()
    originals_checked = verify_originals(repo, library, [rows])
    # Original newly exposed virtual slots are verified from actual ELF data.
    from elftools.elf.elffile import ELFFile
    original_binary = repo / manifest["path"]
    assert sha(original_binary) == frozen["vtables"]["original_elf_sha256"]
    raw = original_binary.read_bytes()
    virtual_checks = []
    with original_binary.open("rb") as stream:
        elf = ELFFile(stream)
        for table in frozen["vtables"]["tables"]:
            section = elf.get_section(table["section"])
            assert section["sh_type"] != "SHT_NOBITS"
            assert section["sh_addr"] <= table["address"] and table["address"] + table["size"] <= section["sh_addr"] + section["sh_size"]
            offset = int(section["sh_offset"]) + table["address"] - int(section["sh_addr"])
            assert offset == table["file_offset"]
            data = raw[offset:offset + table["size"]]
            assert hashlib.sha256(data).hexdigest() == table["sha256"]
            assert data == (library / "recovered-all/client" / table["export_path"]).read_bytes()
            for slot in table["slots"]:
                assert struct.unpack_from("<I", data, slot["vptr_relative_offset"] + 8)[0] == slot["address"]
            virtual_checks.append(table)
    production = ["src/Presonus/DICE/" + name for name in ("SysexPacket.cpp", "Dice3Subsystem.cpp", "Codec.cpp", "SysexPacketConstruction.cpp", "Dice3SubsystemCommands.cpp", "SysexReceiver.cpp", "SysexReceiverWait.cpp")]
    production += ["src/portable/dice/ResponseWait.cpp", "src/portable/dice/CclResponseServices.cpp", "src/Presonus/NOAA/SysexReceiverWait.cpp"]
    production += ["src/Presonus/AVB/" + name for name in ("Protocol.cpp", "Streams.cpp", "AvbManagerReceive.cpp", "AvbManagerLookup.cpp")]
    gateway = "src/Presonus/DICE/PacketClockGateway.cpp"
    stub = packet_candidate / "tests/compatibility_clock_stub.cpp"
    targets = {
        "dice_packet_tests": (library / "tests/dice_packet_tests.cpp", None),
        "dice_response_tests": (library / "tests/dice_response_tests.cpp", stub),
        "dice_response_ccl_smoke": (library / "tests/dice_response_ccl_smoke.cpp", library / gateway),
        "dice_packet_clock_smoke": (packet_candidate / "tests/upstream_clock_smoke.cpp", library / gateway),
        "dice_subsystem_tests": (library / "tests/dice_subsystem_tests.cpp", stub),
        "avb_protocol_tests": (library / "tests/avb_protocol_tests.cpp", stub),
        "avb_streams_tests": (library / "tests/avb_streams_tests.cpp", stub),
        "avb_receive_tests": (library / "tests/avb_receive_tests.cpp", stub),
        "avb_lookup_tests": (library / "validation/avb-lookup-candidate/tests/lookup_tests.cpp", stub),
    }
    formatter_paths = [library / name for name in production + [gateway]] + [item[0] for item in targets.values()] + [stub]
    run("formatter-version", [library / ".venv/bin/clang-format", "--version"])
    run("formatter-check", [library / ".venv/bin/clang-format", "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", *formatter_paths, *[library / n for n in expected_active if n.endswith(".hpp")]])
    project = work / "project"
    project.mkdir()
    quote = lambda p: '[=[' + str(p) + ']=]'
    lines = ["cmake_minimum_required(VERSION 3.30)", "project(DicePacketResponseActive LANGUAGES CXX)", "find_package(PresonusCore 5.0.0 EXACT CONFIG REQUIRED)",
             "add_library(active_product STATIC " + " ".join(quote(library / n) for n in production) + ")",
             "target_include_directories(active_product PUBLIC " + quote(library / "include") + ")",
             "target_link_libraries(active_product PUBLIC PresonusCore::Provider)", "target_compile_features(active_product PUBLIC cxx_std_17)"]
    for target, (test, extra) in targets.items():
        lines += ["add_executable(" + target + " " + quote(test) + (" " + quote(extra) if extra else "") + ")", "target_link_libraries(" + target + " PRIVATE active_product)"]
        if target == "avb_receive_tests":
            lines.append("target_link_options(" + target + " PRIVATE " + " ".join(quote("-Wl,--wrap=" + name) for name in (HELPER, LISTENER, TALKER)) + ")")
    cmake_file = project / "CMakeLists.txt"
    cmake_file.write_text("\n".join(lines) + "\n")
    build = work / "fresh-build"
    deps = repo / "temp/core-upstream/external-dev/usr"
    cmake = library / ".venv/bin/cmake"
    run("compiler-version", ["c++", "--version"])
    run("configure", [cmake, "-S", project, "-B", build, "-DCMAKE_BUILD_TYPE=Release",
        f"-DPresonusCore_DIR={sdk}/lib/cmake/PresonusCore", f"-DCMAKE_PREFIX_PATH={sdk};{deps}",
        f"-DPNG_PNG_INCLUDE_DIR={deps}/include/libpng16", "-DPNG_LIBRARY_RELEASE=/usr/lib/x86_64-linux-gnu/libpng16.so.16",
        "-DZLIB_LIBRARY_RELEASE=/usr/lib/x86_64-linux-gnu/libz.so.1", f"-DCoreDNSSD_LIBRARY={deps}/lib/x86_64-linux-gnu/libdns_sd.so"])
    run("build", [cmake, "--build", build, "-j1"])
    results = {}
    for mode, fixture in packet_vectors.items():
        results["packet-" + mode] = run("packet-" + mode, [build / "dice_packet_tests", mode, fixture])
    for role, fixture in wait_vectors.items():
        results["wait-" + role] = run("wait-" + role, [build / "dice_response_tests", fixture, role])
    for name in ("dice_response_ccl_smoke", "dice_packet_clock_smoke"):
        results[name] = run(name, [build / name])
    results["dice"] = run("dice-subsystem", [build / "dice_subsystem_tests", dice_vector])
    avb_files = [library / n for n in avb["existing_fixture_sha256"]]
    for group in ("protocol", "streams", "receive"):
        selected = [p for p in avb_files if ("avb-" + group) in str(p)]
        if group == "protocol":
            selected.sort(key=lambda p: ("accept" not in p.name, "reverse" not in p.name))
        results["avb-" + group] = run("avb-" + group, [build / ("avb_" + group + "_tests"), *selected])
    for role, fixture in lookup_vectors.items():
        results["avb-lookup-" + role] = run("avb-lookup-" + role, [build / "avb_lookup_tests", fixture])
    assert all("PASS" in text for text in results.values())
    nm = run("nm", ["nm", "--defined-only", build / "libactive_product.a"])
    names = {line.split()[-1] for line in nm.splitlines() if line.split()}
    assert {r["mangled"] for r in rows} <= names
    # Compiler-selected source closure, with explicit app/repository anchors.
    closure = {}
    system_headers = {}
    for depfile in build.rglob("*.o.d"):
        if "active_product.dir" not in str(depfile):
            continue
        tokens = shlex.split(depfile.read_text().replace("\\\n", " ").split(":", 1)[1])
        paths = [Path(token).resolve() for token in tokens]
        source = next(p for p in paths if p.suffix == ".cpp")
        app_deps, core_deps = {}, {}
        for path in paths:
            if path.is_relative_to(library):
                app_deps[str(path.relative_to(library))] = sha(path)
            elif path.is_relative_to(sdk / "include/presonus-core-5"):
                relative = path.relative_to(sdk / "include/presonus-core-5")
                original = upstream / relative
                assert sha(path) == sha(original)
                core_deps[str(original.relative_to(repo))] = sha(original)
            else:
                system_headers[str(path)] = sha(path)
        closure[str(source.relative_to(library))] = dict(sources=app_deps, repository_sources=core_deps)
    # Gateway is built as a separate actual-source smoke object; capture its deps too.
    for path in build.rglob("*.o.d"):
        if "PacketClockGateway.cpp.o.d" in path.name:
            tokens = shlex.split(path.read_text().replace("\\\n", " ").split(":", 1)[1])
            app_deps, core_deps = {}, {}
            for token in tokens:
                dependency = Path(token).resolve()
                if dependency.is_relative_to(library):
                    app_deps[str(dependency.relative_to(library))] = sha(dependency)
                elif dependency.is_relative_to(sdk / "include/presonus-core-5"):
                    relative = dependency.relative_to(sdk / "include/presonus-core-5")
                    assert sha(dependency) == sha(upstream / relative)
                    core_deps[str((upstream / relative).relative_to(repo))] = sha(dependency)
            closure[gateway] = dict(sources=app_deps, repository_sources=core_deps)
    assert set(production + [gateway]) <= set(closure)
    packet_domain = "Active payload/metadata/state and ordered constructor clock/command post/wait boundaries from retained original ARM fixtures. Constructor excludes original padding and inactive byte255; portable tail remains initialized0. Enum underlying spelling/layout and full class hierarchy unresolved. Normal-return contracts only; no device backend or original ARM ABI claim."
    def domain(row):
        group = row["group"]
        if group == "packet":
            return packet_domain + (" Receive side effects only; original return declaration unresolved." if not row["portable_ready"] else " Raw observed command return values retained.")
        if group == "wait":
            return wait["role_domains"][row["role"]] + (" Original NOAA/SPI scope with observed one-shot forced pumping; no DICE alias assumption." if row["role"] == "server" else " Original DICE/UART scope.")
        if group == "dice":
            return dice["domain"]
        return avb["validation_domains"][group.removeprefix("avb-")]
    def implementations(row):
        name, group = row["mangled"], row["group"]
        if group == "packet":
            if "SysexPacketC" in name:
                return ["src/Presonus/DICE/SysexPacketConstruction.cpp", gateway]
            if "SysexReceiver7receive" in name:
                return ["src/Presonus/DICE/SysexReceiver.cpp"]
            return ["src/Presonus/DICE/Dice3SubsystemCommands.cpp", "src/Presonus/DICE/SysexPacketConstruction.cpp", "src/Presonus/DICE/Codec.cpp", gateway]
        if group == "wait":
            names = ["src/portable/dice/ResponseWait.cpp", "src/portable/dice/CclResponseServices.cpp"]
            names += ["src/Presonus/DICE/SysexReceiverWait.cpp", "src/Presonus/DICE/SysexReceiver.cpp"] if row["role"] == "client" else ["src/Presonus/NOAA/SysexReceiverWait.cpp"]
            return names
        if group == "dice":
            return ["src/Presonus/DICE/SysexPacket.cpp" if "getSysexCommandStr" in name else "src/Presonus/DICE/Dice3Subsystem.cpp"]
        if group == "avb-receive":
            return ["src/Presonus/AVB/AvbManagerReceive.cpp", "src/Presonus/AVB/Protocol.cpp", "src/Presonus/AVB/Streams.cpp"]
        return ["src/Presonus/AVB/AvbManagerLookup.cpp" if group == "avb-lookup" else "src/Presonus/AVB/Protocol.cpp"]
    build_config = {"isolated-CMakeLists.txt": sha(cmake_file), "root-CMakeLists.txt": sha(library / "CMakeLists.txt"), "root-CMakeCache.txt": sha(root_build / "CMakeCache.txt"), "provider-proof.json": sha(provider_path)}
    for original, filename in ((cmake_file, "isolated-CMakeLists.txt"), (library / "CMakeLists.txt", "root-CMakeLists.txt"), (root_build / "CMakeCache.txt", "root-CMakeCache.txt"), (provider_path, "provider-proof.json")):
        shutil.copy2(original, evidence / filename)
    artifacts = {}
    for artifact in sorted([*build.rglob("*.o"), build / "libactive_product.a", *[build / target for target in targets]]):
        relative = str(artifact.relative_to(build))
        artifacts[relative] = sha(artifact)
        destination = evidence / "artifacts" / relative.replace("/", "_")
        destination.parent.mkdir(exist_ok=True)
        shutil.copy2(artifact, destination)
    for path in sorted(build.rglob("*")):
        if path.is_file() and path.name in ("flags.make", "link.txt"):
            destination = evidence / "configuration" / str(path.relative_to(build)).replace("/", "_")
            destination.parent.mkdir(exist_ok=True)
            shutil.copy2(path, destination)
            build_config[str(destination.relative_to(evidence))] = sha(path)
    for path in sorted((sdk / "lib/cmake/PresonusCore").glob("*.cmake")):
        destination = evidence / "sdk-package" / path.name
        destination.parent.mkdir(exist_ok=True)
        shutil.copy2(path, destination)
        build_config[str(destination.relative_to(evidence))] = sha(path)
    common_inputs = {str(Path(__file__).relative_to(library)): sha(Path(__file__)), "tools/avb_protocol_reseal.py": sha(library / "tools/avb_protocol_reseal.py")}
    for path, digest in input_hashes.items():
        common_inputs[path] = digest
    records = []
    for row in rows:
        app_sources, repository_sources = dict(common_inputs), {}
        for name in implementations(row):
            app_sources.update(closure[name]["sources"])
            repository_sources.update(closure[name]["repository_sources"])
        # Retained tests/fixtures are explicit validation inputs, never global CMake.
        app_sources.update(fixtures)
        for test, extra in targets.values():
            app_sources[str(test.relative_to(library))] = sha(test)
            if extra and extra != library / gateway:
                app_sources[str(extra.relative_to(library))] = sha(extra)
        inherited = wait["unresolved"] if row["group"] == "wait" else avb.get("unresolved", []) if row["group"].startswith("avb-") else dice.get("limitations", []) if row["group"] == "dice" else [packet["constructor_alias_caveat"], "Original receive return declarations remain unresolved; no class layout/hierarchy or ARM ABI claim."]
        records.append(dict(role=row["role"], mangled=row["mangled"], original_elf_sha256=row["original_elf_sha256"],
            original_address=row["address"], original_size=row["size"], original_section=row["section"], original_bytes_sha256=row["sha256"],
            sources=app_sources, repository_sources=repository_sources, domain=domain(row),
            cpp_compiled=True, mangling_namespace_checked=True, portable_ready=row["portable_ready"],
            declaration_uncertainties=inherited, original_function_verified=False, hardware_verified=False))
    assert all(r["domain"].strip() for r in records)
    assert all(sha(library / name) == digest for name, digest in expected_active.items())
    proof = dict(passed=True, status="active-path completed packet/wait + dependent header fixture reseal",
        input_proofs=input_hashes, retained_fixtures=fixtures, current_provider_proof_sha256=sha(provider_path),
        sdk_files={str(path.relative_to(sdk)):sha(path) for path in sorted(sdk.rglob("*")) if path.is_file()}, sdk_headers=sdk_headers,
        final_header_sha256=FINAL_HEADER, active_products=expected_active, functions=rows, domains={str((r["role"], r["mangled"])):domain(r) for r in rows},
        native_results=results, byte_checks=originals_checked, original_virtual_slots=virtual_checks,
        compiler_semantic_closures=closure, compiler_system_headers=system_headers, build_configuration=build_config,
        fresh_artifacts=artifacts,
        original_oracle_regenerated=False, fresh_isolated_objects=True, root_build_modified=False,
        counts={"rows":25,"ready":16,"pending":9}, constructor_variant_policy="OriginalC1 only; extra emittedC2 never admitted",
        compiled_constructor_aliases=sorted(n for n in names if "SysexPacketC" in n),
        hardware_verified=False, original_arm_abi_verified=False)
    path = output / "validation.json"
    path.write_text(json.dumps(proof, indent=2) + "\n")
    for record in records:
        record.update(validation=str(path.relative_to(library)), validation_sha256=sha(path))
    for ready, filename in ((True, "ready-functions.fragment.json"), (False, "compiled-functions.fragment.json")):
        (output / filename).write_text(json.dumps({"functions":[r for r in records if r["portable_ready"] == ready]}, indent=2) + "\n")
    for source in output.iterdir():
        shutil.copy2(source, evidence / source.name)
    (evidence / "manifest.json").write_text(json.dumps({str(p.relative_to(evidence)):sha(p) for p in sorted(evidence.rglob("*")) if p.is_file()}, indent=2) + "\n")
    print(json.dumps(dict(proof=str(path), sha256=sha(path), ready_entries=16, pending_entries=9, evidence=str(evidence)), indent=2))


if __name__ == "__main__":
    main()
