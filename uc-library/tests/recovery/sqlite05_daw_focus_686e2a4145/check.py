"""Build and compare the DAWFocusChannel provider, ARM and portable replays."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

import native

ROOT = Path(__file__).resolve().parents[4]
TEST = Path(__file__).resolve().parent.relative_to(ROOT)
SRC = Path("uc-library/src/Presonus/DAWFocusChannel.cpp")
HDR = Path("uc-library/include/presonus/DAWFocusChannel.hpp")
CLIENT = Path("uc-library/src/Presonus/UC/ClientComponent.cpp")
REPLAY = TEST / "Replay.cpp"
CHECK = TEST / "check.py"
NATIVE = TEST / "native.py"
PYTHON = "uc-library/.venv/bin/python"
FORMATTER = "uc-library/.venv/bin/clang-format"
PROJECT = Path("/home/rs/projects/opencs/ai-line-analysis")
SDK = PROJECT / "temp/core-upstream/root-integration-01/upstream-core/sdk"
LIBRARIES = [SDK / "lib" / name for name in (
    "libcorelib.a", "libpresonus_core_allocator.a", "libpresonus_zlib.a"
)]
PROVENANCE = SDK / "share/presonus-core-5/provenance.json"
FORMAT = [FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run",
          "--Werror", SRC, HDR, REPLAY]
CXX = ["/usr/bin/c++", "-std=c++20", "-Wall", "-Wextra", "-fno-rtti",
       "-Wno-multichar", "-Iuc-library/include", "-isystem", "third_party/ccl-framework",
       "-Ulinux"]
CCL_COMMIT = "e8cbdea4a4a20e15111f5a690798a259c0374b31"
LINK = ["-Wl,--wrap=_ZdlPv", "-pthread", "-ldl", "-lm"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def binding(path):
    return dict(path=str(path), sha256=sha(path))


def run(argv, **options):
    args = list(map(str, argv))
    print(json.dumps(args), flush=True)
    completed = subprocess.run(args, check=True, cwd=ROOT, text=True,
                               stdout=subprocess.PIPE, **options)
    return completed.stdout


def build(scratch):
    scratch.mkdir(parents=True, exist_ok=True)
    provenance = json.loads(PROVENANCE.read_text())
    assert provenance["upstream_commit"] == CCL_COMMIT
    assert run(["/usr/bin/git", "-C", "third_party/ccl-framework", "rev-parse", "HEAD"]).strip() == CCL_COMMIT
    archives_before = [binding(p) for p in LIBRARIES]
    records = []
    for source, key, flags in ((SRC, "focus", []), (CLIENT, "client", []),
                               (REPLAY, "replay", []),
                               (REPLAY, "provider-main", ["-DDAW_FOCUS_PROVIDER_ONLY"])):
        obj = scratch / (key + ".o")
        deps = scratch / (key + ".d")
        argv = [*CXX, *flags, "-MD", "-MF", deps, "-c", source, "-o", obj]
        run(argv)
        headers = shlex.split(deps.read_text().replace("\\\n", " ").split(":", 1)[1])
        records.append(dict(argv=list(map(str, argv)), result=0, object=binding(obj),
                            dependencies=[binding(p) for p in headers if not Path(p).is_absolute()]))
    for key, objs in (("provider", ["provider-main", "client"]),
                      ("replay", ["replay", "focus", "client"])):
        binary = scratch / key
        link_map = scratch / (key + ".map")
        argv = [CXX[0], *(scratch / (x + ".o") for x in objs), *LIBRARIES,
                *LINK, "-Wl,-Map," + str(link_map), "-o", binary]
        run(argv)
        records.append(dict(argv=list(map(str, argv)), result=0, executable=binding(binary),
                            link_map=binding(link_map)))
    assert [binding(p) for p in LIBRARIES] == archives_before
    return records


def symbol_rows(obj, binary, provider, exact):
    all_names = {native.FOCUS + suffix for suffix in native.METHODS}
    results = []
    for path in (obj, binary):
        lines = run(["/usr/bin/nm", "--defined-only", path]).splitlines()
        rows = [row for row in lines if row.split() and row.split()[-1] in all_names]
        assert all_names == {row.split()[-1] for row in rows}
        assert all(row.split()[-2] == "T" for row in rows)
        results.append(dict(binary=str(path), exact=exact, rows=rows))
    defined_by_provider = run(["/usr/bin/nm", "--defined-only", provider])
    assert native.FOCUS not in defined_by_provider
    assert native.CLIENT + "C2EPKc" in defined_by_provider
    assert native.COMPONENT_D2 in defined_by_provider
    return results


def portable(executable, fixture):
    data = json.loads(Path(fixture).read_text())
    count = 0
    for entry in data["entries"]:
        for case in entry["cases"]:
            items = case["input"]
            if entry["mode"] == "init":
                arguments = "".join(" ".join(map(str, step)) + "\n" for step in items)
            else:
                arguments = (" ".join(map(str, items)) if isinstance(items, list)
                             else str(items)) + "\n"
            output = run([executable, entry["mode"]], input=arguments)
            actual = [list(map(int, row.split())) for row in output.splitlines()]
            assert actual == case["expected"], (entry["mode"], items, actual, case["expected"])
            count += 1
    print(f"{count} native to portable comparisons passed")
    return count


def original_id(original):
    return dict(elf_sha256=original["elf"], **{key: original[key] for key in
                ("firmware", "role", "mangled", "address", "size", "section")})


def checks_for(task, packet):
    scratch = Path("temp/recovery-work/daw-focus-build") / task
    args = [PYTHON, CHECK]
    return [
        ("format", FORMAT),
        ("compile", [*args, "compile", scratch]),
        ("symbols", [*args, "symbols", scratch, packet]),
        ("replay", [*args, "replay", scratch, packet, fixture_for(task)]),
    ]


def fixture_for(task):
    return TEST.parent / task / "fixtures.json"


def verify_native(scratch, packet, fixture):
    argv = [PYTHON, NATIVE, packet, scratch / "provider"]
    observed = json.loads(run(argv))
    assert observed == json.loads(fixture.read_text())
    return observed, list(map(str, argv))


def seal(packet):
    data = json.loads(packet.read_text())
    task = data["task"]["id"]
    scratch = Path("temp/recovery-work/daw-focus-build") / task
    fixture = fixture_for(task)
    proof_path = Path("uc-library/candidates") / task / "worker-proof.json"
    handoff_path = proof_path.with_name("HANDOFF.json")
    originals = [item["original"] for item in data["originals"]]
    mode = native.METHODS[originals[0]["mangled"].removeprefix(native.FOCUS)][0]
    review = data["task"]["review"]
    domain = review["domain"] + " " + review["oracle_plan"]
    limitations = [
        "ARM executes exact application entries. Outbound calls use verified target identities "
        "with separately linked pinned CCL and ClientComponent provider boundaries. "
        "Firmware allocator instructions and original Core instructions remain outside replay.",
        "Native D0 reaches the verified _ZdlPv PLT relocation, frees the live provider allocation "
        "and unmaps the guest receiver. Native D1 preserves the receiver. Linux D0 performs real "
        "virtual deletion through Component and forwards an unsized delete.",
        "Portable C1/C2 execute the exact emitted Linux symbols on aligned storage. Original "
        "addresses differ in each firmware; Linux aliases are permitted and recorded separately.",
        "Only portable class behavior is claimed. ARM layouts, complete virtual interface, "
        "getFocusChannel, paramChanged, allocation failures and hardware remain outside scope.",
        "Original return spelling is unresolved for castTo and init. Portable declarations "
        "use the established CCL virtual interface for castTo and the state-only contract for init.",
    ]
    run(FORMAT)
    compile_records = build(scratch)
    rows = symbol_rows(scratch / "focus.o", scratch / "replay", scratch / "provider",
                       originals[0]["mangled"])
    observed, native_argv = verify_native(scratch, packet, fixture)
    case_count = portable(scratch / "replay", fixture)
    repository_sources = {entry["path"]: entry["sha256"] for entry in review["providers"]}
    functions = [
        dict(original_elf_sha256=item["elf"], mangled=item["mangled"],
             sources={str(p.relative_to("uc-library")): sha(p) for p in (HDR, SRC)},
             repository_sources=repository_sources, domain=domain,
             portable_ready=mode not in ("cast", "init"), cpp_compiled=True,
             mangling_namespace_checked=True,
             declaration_uncertainties=limitations[-1:] if mode in ("cast", "init") else [])
        for item in originals
    ]
    proof = dict(
        version=1, task_id=task, validation_domain=domain, limitations=limitations,
        originals=list(map(original_id, originals)), functions=functions,
        source_hashes={str(p): sha(p) for p in (HDR, SRC)}, provider_source_bindings=repository_sources,
        native_engine=observed["unicorn"], native_argv=native_argv,
        native_comparison_passed=True, behavior_comparison_passed=True,
        compiled_mangled_names_matched=True, cpp_compiled=True,
        native_ranges=[entry["original"] for entry in observed["entries"]],
        formatter_version=run([FORMATTER, "--version"]).strip(),
        compiler_version=run([CXX[0], "--version"]).splitlines()[0],
        formatter=dict(argv=list(map(str, FORMAT)), result=0),
        compilation=compile_records, compiled_symbols=rows,
        provider_archives=[binding(p) for p in LIBRARIES],
        provider_provenance=binding(PROVENANCE),
        producer_inputs=[binding(p) for p in [packet, CHECK, NATIVE, REPLAY, fixture]],
        case_count=case_count, native_step_count=sum(
            max(1, len(case["init_steps"])) for entry in observed["entries"]
            for case in entry["cases"]),
        canonical_integration_pending=True,
    )
    proof_path.write_text(json.dumps(proof, indent=2) + "\n")
    artifacts = [
        ("source", SRC), ("source", HDR), ("test", REPLAY), ("fixture", fixture),
        ("replay", CHECK), ("native-oracle", NATIVE), ("proof", proof_path),
        ("packet", packet),
        *(("provider", Path(p)) for p in repository_sources),
    ]
    handoff = dict(
        version=1, task_id=task, namespace=data["task"]["namespace"],
        packet_manifest=str(packet), originals=list(map(original_id, originals)),
        artifacts=[dict(kind=kind, **binding(p)) for kind, p in artifacts],
        checks=[dict(kind=kind, argv=list(map(str, argv)), timeout_seconds=120)
                for kind, argv in checks_for(task, packet)],
        validation_domain=domain, limitations=limitations,
        build_integration=dict(
            production_partition="common", sources=[str(SRC)], public_headers=[str(HDR)],
            test_targets=["DAWFocusChannelReplay"], test_source=str(REPLAY),
            test_compile_options=["-fno-rtti"], test_link_options=["-Wl,--wrap=_ZdlPv"],
            test_link_libraries=["presonus::rm_components"],
            ctest_argv=[PYTHON, str(CHECK), "portable", "$<TARGET_FILE:DAWFocusChannelReplay>",
                        str(fixture)], working_directory="repository_root", fixture=binding(fixture),
        ),
    )
    handoff_path.write_text(json.dumps(handoff, indent=2) + "\n")
    print(str(handoff_path), sha(handoff_path))


if __name__ == "__main__":
    action, *args = sys.argv[1:]
    if action == "compile":
        build(Path(args[0]))
    elif action == "symbols":
        scratch, packet = map(Path, args)
        exact = json.loads(packet.read_text())["originals"][0]["original"]["mangled"]
        print(json.dumps(symbol_rows(scratch / "focus.o", scratch / "replay",
                                     scratch / "provider", exact), indent=2))
    elif action == "replay":
        scratch, packet, fixture = map(Path, args)
        verify_native(scratch, packet, fixture)
        portable(scratch / "replay", fixture)
    elif action == "portable":
        portable(*args)
    elif action == "seal":
        seal(Path(args[0]))
    else:
        raise SystemExit(f"unknown action: {action}")
