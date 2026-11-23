"""Bind current canonical replay archives without rewriting historical inputs."""

import hashlib
from pathlib import Path
import shlex
import subprocess


HISTORICAL_CORE_SHA256 = "3c4f0825acb529fda135587b7ff5cb92ca0100bb417a20c034d3fdef80a93e0c"
CURRENT_ARCHIVES = {
    "libcorelib.a": "5a2c8bbb20d8d194ff4f5047118696afa918a046b01739c4257416044e83f5f3",
    "libpresonus_core_allocator.a": "69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d",
    "libpresonus_png.a": "99514af041c29b5aa782c14718794453b13841f99b7de584db3f3f89bf68ecc1",
    "libpresonus_zlib.a": "9095c54154b7617d8f283d7858ae45218cad1ba92e54e04f983dc0a7151c6c93",
}
TRANSITION = {
    "path": "evidence/recovery/2026-11-23/pinned-codecs-20261123T085431.198592380Z/CORE-ARCHIVE-TRANSITION.json",
    "sha256": "a00f61dc5c4dda34ce70fff1ee9733a86c71ff1e6bbb0066ff8670f6334bf04d",
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical_build(root):
    return root / "temp/core-upstream/root-integration-01"


def read_canonical_codec_link(root, executable):
    build = canonical_build(root)
    executable = Path(executable).resolve(strict=True)
    assert executable.parent == build, executable
    link = build / "CMakeFiles" / (executable.name + ".dir") / "link.txt"
    target_dirs = (build / "CMakeFiles/TargetDirectories.txt").read_text().splitlines()
    assert str(link.parent) in target_dirs, link
    argv = shlex.split(link.read_text())
    assert argv[argv.index("-o") + 1] == executable.name, link
    linked = [(build / item).resolve() for item in argv if item.endswith(".a")]
    sdk = build / "upstream-core/sdk/lib"
    archives = {}
    for name, expected in CURRENT_ARCHIVES.items():
        archive = sdk / name
        assert [item for item in linked if item.name == name] == [archive], (link, name)
        assert digest(archive) == expected, archive
        archives[str(archive)] = expected

    runtime = subprocess.check_output(["/usr/bin/ldd", executable], text=True)
    assert not any(line.lstrip().startswith(("libz.so", "libpng"))
                   for line in runtime.splitlines()), executable
    assert digest(root / TRANSITION["path"]) == TRANSITION["sha256"]
    return {
        "archives": archives, "link_file": str(link.relative_to(root)),
        "link_file_sha256": digest(link), "executable_sha256": digest(executable),
        "transition": TRANSITION,
    }


def validate_archives(root, executable, integration, historical):
    root = Path(root).resolve()
    historical = dict(historical)
    canonical_integration = integration and Path(integration).resolve() == (
        root / "uc-library/validation/integration.json")
    canonical_executable = executable and Path(executable).resolve().parent == canonical_build(root)
    canonical = canonical_integration or canonical_executable
    if not canonical:
        for path, expected in historical.items():
            assert digest(root / path) == expected, path
        return {"archives": historical, "historical": historical, "transition": None}

    link = read_canonical_codec_link(root, executable)
    for path, expected in historical.items():
        original = (root / path).resolve()
        actual = link["archives"][str(original)]
        if original.name == "libcorelib.a":
            assert expected == HISTORICAL_CORE_SHA256, original
        else:
            assert actual == expected, original
    link["historical"] = historical
    return link
