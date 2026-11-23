"""Compile the local replay or check a supplied canonical object and executable."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import shlex
from pathlib import Path
import subprocess
import sys

from native import capture, FX, RADIO


ROOT = Path(__file__).resolve().parents[4]
TEST = Path(__file__).with_name("Replay.cpp").relative_to(ROOT)
SOURCE_ROOT = Path("uc-library/src/Presonus")
HDR_ROOT = Path("uc-library/include/presonus/surface")
MAPPING = SOURCE_ROOT / "Surface/MappingComponent.cpp"
RECEIPT = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/"
               "control10x20-after-4fed70d11/workspaces/actual04-scoped01-cycle20_g01/"
               "DAW-MAPPING-TYPED-PROVIDER-READ01.json")
RECEIPT_SHA = "ace020119cc8fb0059cc17bb3b4997bda4f6d6eee250969386f430874629dd0c"
DAW_FX = SOURCE_ROOT / "Surface/DawFxPageComponent.cpp"
DAW_FX_SHA = "37ffef0afc5aaade5ff69ddb891607f4263b19bcf08ef2b1049ac2aacce11baf"
SNAPSHOT = RECEIPT.parents[2] / "packeting/actual04-next-batch01/snapshot"
SUPPLEMENTAL_HEADERS = {
    Path("uc-library/include/presonus/PageComponent.hpp"): "54200b8d2ccb7d3568566c0703587e258f4f440045f126a5388a4000fd5b1bbb",
    Path("uc-library/include/presonus/surface/PresetsPageComponent.hpp"): "d5e7f8d5d3784dd3129c0b9303b30dcecadf47b3c7066aca8f2fdf52c603001c",
}
SOURCE = SOURCE_ROOT / "Surface/DAWMixerHandler.cpp"
HEADER = HDR_ROOT / "DAWMixerHandler.hpp"
SYMBOL = "_ZN8Presonus7Surface15DAWMixerHandler13setControllerEPNS_18IMappingControllerE"
SOURCES = [SOURCE_ROOT / ("Surface/" + name + ".cpp") for name in (
    "DAWMixerHandler", "DawFxPageComponent", "DawFxPageMapping",
    "MappingComponent", "MappingInputRoutes", "MappingRadioRoutes",
    "MappingMeterRouting", "MappingRadioValidation", "MappingControllerParameters",
    "MappingMainMixLock",
)] + [SOURCE_ROOT / "DelayTimer.cpp", SOURCE_ROOT / "DICE/PacketClockGateway.cpp"]
HEADERS = [HDR_ROOT / name for name in (
    "DAWMixerHandler.hpp", "DawFxPageComponent.hpp", "MappingComponent.hpp",
    "sl_mixer_encoder.hpp", "mapping_input_routes.hpp",
)]
CORE = [Path("third_party/ccl-framework/core") / name for name in (
    "portable/corecomponent.cpp", "portable/corecomponent.h",
    "portable/coreparams.cpp", "portable/coreparams.h", "portable/coreparaminfo.h",
    "portable/coretypeinfo.h", "public/corevector.h",
)]
FORMAT = ["uc-library/.venv/bin/clang-format", "--style=file",
          "--fallback-style=LLVM", "--dry-run", "--Werror"]
DOMAIN = (
    "Six original ARM executions with a stable roster of zero, one or three real "
    "DawFx page thunks and setters, incoming null or replacement controller. Capture "
    "handler/page writes, exact MappingComponent dispatch/args and four native Core "
    "lookups with the controlled missing-parameter boundary. Six Linux executions "
    "observe the same ordered page writes and exact radio call, exercise genuine "
    "DawFx and MappingRadioRoutes bodies and verify real CCL tag values and unchanged "
    "outside-group/previous controller values."
)
UNCERTAINTIES = [
    "The native return type is unencoded and not independently established. "
    "The portable method has a void side-effect contract.",
]
LIMITS = UNCERTAINTIES + [
    "Portable roster is initialized, ordered and unchanged throughout dispatch. "
    "ARM object layout, reentrant roster invalidation, other native derived page "
    "types and hardware are outside the observed domain.",
    "ARM Core lookups return no parameter at a controlled boundary. Present-parameter "
    "behavior is observed separately in the pinned Linux CCL provider.",
]


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(args, temp=None):
    env = {"TMPDIR": str(temp.resolve())} if temp else {}
    result = subprocess.run([str(x) for x in args], cwd=ROOT, env=os.environ | env,
                            text=True, capture_output=True, timeout=100)
    if result.returncode:
        raise RuntimeError(f"{args!r}: {result.stdout}\n{result.stderr}")
    return result.stdout


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def frozen_mapping():
    assert sha(RECEIPT) == RECEIPT_SHA
    binding = json.loads(RECEIPT.read_text())["files"][str(MAPPING)]
    source = Path(binding["frozen_read_path"])
    assert sha(source) == binding["sha256"]
    return source


def frozen_providers():
    pages = SNAPSHOT / DAW_FX
    assert sha(pages) == DAW_FX_SHA
    return {MAPPING: frozen_mapping(), DAW_FX: pages}


def build(dest, provider):
    dest.mkdir(parents=True, exist_ok=True)
    # Overlay the sealed header subset while keeping the owned edited header.
    include_root = Path("uc-library/include")
    overlay = dest / "frozen-headers"
    frozen_headers = {}
    for path in sorted((SNAPSHOT / include_root).rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(SNAPSHOT / include_root)
        if include_root / relative == HEADER:
            continue
        link = overlay / relative
        link.parent.mkdir(parents=True, exist_ok=True)
        if not link.is_symlink():
            link.symlink_to(path)
        assert link.resolve() == path.resolve()
        logical = include_root / relative
        if logical in SUPPLEMENTAL_HEADERS:
            assert sha(path) == SUPPLEMENTAL_HEADERS[logical]
        frozen_headers[str(link)] = {"path": str(path), "sha256": sha(path)}
    flags = [
        "-std=c++20", "-O3", "-DNDEBUG=1", "-DCORE_USE_OPENSSL=1",
        "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-pthread", "-Ulinux", "-fno-sized-deallocation",
        "-ffunction-sections", "-fdata-sections", "-I" + str(overlay), "-Iuc-library/include",
        "-isystem", "third_party/ccl-framework",
    ]
    archives = [provider / n for n in ("libcorelib.a", "libpresonus_core_allocator.a")]
    hashes = [sha(p) for p in archives]
    assert hashes == [
        "3c4f0825acb529fda135587b7ff5cb92ca0100bb417a20c034d3fdef80a93e0c",
        "69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d",
    ]
    commands = []
    objects = []
    closure = {}
    providers = frozen_providers()
    for source in [*SOURCES, TEST]:
        obj = dest / (source.stem + ".o")
        actual_source = providers.get(source, source)
        depfile = Path(str(obj) + ".d")
        command = ["c++", *flags, "-MD", "-MF", str(depfile), "-c",
                   str(actual_source), "-o", str(obj)]
        run(command, dest)
        dependencies = shlex.split(
            depfile.read_text().replace(chr(92) + chr(10), " ").split(":", 1)[1]
        )
        input_hashes = {p: sha(p) for p in sorted(set(dependencies))}
        frozen_matches = {}
        for path, digest in input_hashes.items():
            if path in frozen_headers:
                assert digest == frozen_headers[path]["sha256"]
                frozen_matches[path] = digest
                continue
            relative = Path(path)
            if relative.is_absolute() or relative in (SOURCE, HEADER, TEST):
                continue
            frozen = SNAPSHOT / relative
            if frozen.is_file():
                assert sha(frozen) == digest, f"Frozen dependency mismatch: {path}"
                frozen_matches[path] = digest
        closure[str(source)] = {"depfile_sha256": sha(depfile),
                                "inputs": input_hashes, "snapshot_matches": frozen_matches}
        commands.append(command)
        objects.append(obj)
    command = ["c++", "-pthread", *map(str, objects), *map(str, archives),
               "-Wl,--gc-sections", f"-Wl,--wrap={FX}", "-ldl",
               "-o", str(dest / "Replay")]
    run(command, dest)
    commands.append(command)
    write(dest / "commands.json", {
        "compiler_depfile_closure": closure, "frozen_header_overlay": frozen_headers,
        "exact_commands": commands, "TMPDIR": str(dest.resolve()),
        "provider_load": {str(p): h for p, h in zip(archives, hashes)},
        "provider_receipt_sha256": sha(provider / "archive-receipt"),
    })


def symbols(obj):
    names = {row.split()[-1] for row in run(["nm", "--defined-only", obj]).splitlines()
             if len(row.split()) == 3}
    assert SYMBOL in names
    assert FX in run(["nm", "--undefined-only", obj])
    return SYMBOL


def replay(args):
    started = datetime.now(timezone.utc)
    run([*FORMAT, HEADER, SOURCE, TEST])
    fixture = json.loads(args.fixture.read_text())
    assert capture(args.elf, args.contract) == fixture
    symbol = symbols(args.object)
    names = {row.split()[-1] for row in run(["nm", "--defined-only", args.exe]).splitlines()
             if len(row.split()) == 3}
    assert {FX, RADIO, "__wrap_" + FX, "_ZN4Core8Portable9ParamListD1Ev"} <= names
    expected = []
    for case in fixture["cases"]:
        expected.append(f"case {case['page_count']} {int(case['enabled'])}")
        expected.extend(" ".join(map(str, event)) for event in case["trace"]
                        if event[0] in ("page", "radio"))
    stdout = run([args.exe.resolve()]).splitlines()
    assert stdout == expected, (stdout, expected)
    commands = args.object.parent / "commands.json"
    local_build = commands.is_file()
    frozen_inputs = frozen_providers()
    actual_inputs = frozen_inputs if local_build else {p: p for p in frozen_inputs}
    for logical, actual in actual_inputs.items():
        assert sha(actual) == sha(frozen_inputs[logical])
    frozen_headers = {p: SNAPSHOT / p if local_build else p
                      for p in SUPPLEMENTAL_HEADERS}
    for logical, source in frozen_headers.items():
        previous = SUPPLEMENTAL_HEADERS[logical]
        expected = previous
        if not local_build and logical == Path("uc-library/include/presonus/PageComponent.hpp"):
            assert sha(SNAPSHOT / logical) == previous
            expected = "4564d19e2cc2b8c13d38697c89943c41947aa1af5f399b0e8079f919ae83e608"
        assert sha(source) == expected
    sources = {str(path.relative_to("uc-library")): sha(path)
               for path in (*SOURCES, *HEADERS, TEST, *(() if local_build else SUPPLEMENTAL_HEADERS))
               if path not in frozen_inputs or not local_build}
    providers = {str(path): sha(path) for path in CORE}
    function = {
        "original_elf_sha256": fixture["elf_sha256"], "mangled": symbol,
        "cpp_compiled": True, "mangling_namespace_checked": True,
        "portable_ready": False, "declaration_uncertainties": UNCERTAINTIES,
        "sources": sources, "validation_domain": DOMAIN,
        "repository_sources": providers,
    }
    write(args.out, {
        "success": True, "cpp_differential_passed": True,
        "compiled_mangled_names_matched": True, "portable_ready": False,
        "mangled_names": [symbol], "original_elf_sha256": fixture["elf_sha256"],
        "domain": DOMAIN, "validation_domain": DOMAIN, "limitations": LIMITS,
        "functions": [function], "proposed_readiness": {"ready": [], "pending": [function]},
        "format_check_passed": True, "formatted_paths": {str(p): sha(p) for p in
                                                         (HEADER, SOURCE, TEST)},
        "format_version": run([FORMAT[0], "--version"]).strip(),
        "replay_argv": sys.argv, "native": fixture, "host_trace": stdout,
        "native_case_count": len(fixture["cases"]), "host_case_count": len(fixture["cases"]),
        "original_vtable_thunks_and_implementations_verified": True,
        "fixture_sha256": sha(args.fixture), "integration_sha256": sha(args.integration),
        "replay_producer_sha256": sha(__file__),
        "native_producer_sha256": sha(Path(__file__).with_name("native.py")),
        "compiled_object_sha256": sha(args.object), "replay_exe_sha256": sha(args.exe),
        "core_commit": "e8cbdea4a4a20e15111f5a690798a259c0374b31",
        "repository_sources": providers, "sources": sources,
        "frozen_provider_inputs": {str(p): {"path": str(actual), "sha256": sha(actual)}
                                   for p, actual in actual_inputs.items()},
        "frozen_additional_headers": {str(p): {"path": str(actual), "sha256": sha(actual)}
                                      for p, actual in frozen_headers.items()},
        "mapping_lifetime_provider": {"path": str(actual_inputs[MAPPING]),
                                      "sha256": sha(actual_inputs[MAPPING]),
                                      "receipt_sha256": RECEIPT_SHA},
        "local_compile": json.loads(commands.read_text()) if commands.is_file() else None,
        "replay_start_utc": started.isoformat(),
        "replay_end_utc": datetime.now(timezone.utc).isoformat(),
    })
    print(f"{symbol}: six original and six Linux controller-routing cases passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", action="store_true")
    for option in ("exe", "object", "integration", "out", "elf", "contract",
                   "fixture", "build", "provider"):
        parser.add_argument("--" + option, type=Path)
    args = parser.parse_args()
    if args.build:
        build(args.build, args.provider)
    elif args.symbols:
        print(symbols(args.object))
    else:
        replay(args)


if __name__ == "__main__":
    main()
