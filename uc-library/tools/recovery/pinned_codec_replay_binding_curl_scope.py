"""Bind current canonical replay archives without rewriting historical inputs."""

import hashlib
import json
import re
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


def read_canonical_codec_link(root, executable, transitive_provider=None):
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
    codec_runtime = [line for line in runtime.splitlines()
                     if line.lstrip().startswith(("libz.so", "libpng"))]
    dynamic_codec_provider = None
    if codec_runtime:
        assert transitive_provider is not None, executable
        dynamic_codec_provider = validate_transitive_curl_codec(
            root, executable, link, argv, codec_runtime, transitive_provider)
    assert digest(root / TRANSITION["path"]) == TRANSITION["sha256"]
    return {
        "archives": archives, "link_file": str(link.relative_to(root)),
        "link_file_sha256": digest(link), "executable_sha256": digest(executable),
        "transition": TRANSITION, "dynamic_codec_provider": dynamic_codec_provider,
    }


def validate_transitive_curl_codec(root, executable, link, argv, codec_runtime, binding):
    """Permit one hash-bound curl dependency; all other codec rules stay strict."""
    binding_path = (root / binding["path"]).resolve(strict=True)
    assert binding_path.is_relative_to(root) and digest(binding_path) == binding["sha256"]
    contract = json.loads(binding_path.read_text())
    assert contract["version"] == 1 and executable.name == contract["target"]
    assert digest(executable) == contract["executable_sha256"]
    assert str(link.relative_to(root)) == contract["link"]["path"]
    assert digest(link) == contract["link"]["sha256"]
    provider_ref = contract["curl_provider"]
    provider_path = (root / provider_ref["path"]).resolve(strict=True)
    assert provider_path.is_relative_to(root) and digest(provider_path) == provider_ref["sha256"]
    provider = json.loads(provider_path.read_text())
    curl = Path(provider["runtime"]["path"]).resolve(strict=True)
    assert digest(curl) == provider["runtime"]["sha256"]
    assert [Path(item).resolve() for item in argv if Path(item).name.startswith("libcurl.so")] == [curl]
    def needed(path):
        text = subprocess.check_output(["/usr/bin/readelf", "-d", str(path)], text=True)
        return re.findall(r"NEEDED.*\[(.*?)\]", text)
    direct = needed(executable)
    assert "libcurl.so.4" in direct
    assert not any(name.startswith(("libz.so", "libpng")) for name in direct)
    assert "libz.so.1" in needed(curl)
    closure = {}
    for item in provider["runtime_dependency_closure"]:
        path = Path(item["path"]).resolve(strict=True)
        assert digest(path) == item["sha256"]
        closure[path] = item["sha256"]
    observed = []
    for line in codec_runtime:
        fields = line.split()
        assert fields[0] == "libz.so.1" and fields[1] == "=>"
        path = Path(fields[2]).resolve(strict=True)
        assert path in closure and digest(path) == closure[path]
        observed.append({"path": str(path), "sha256": closure[path]})
    assert len(observed) == 1
    return {"binding": binding, "provider": provider_ref, "loaded_transitive_codec": observed,
            "scope": "Dependency closure only; not exclusive runtime symbol resolution or original ABI."}


def validate_archives(root, executable, integration, historical, *, transitive_provider=None):
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

    link = read_canonical_codec_link(root, executable, transitive_provider)
    for path, expected in historical.items():
        original = (root / path).resolve()
        actual = link["archives"][str(original)]
        if original.name == "libcorelib.a":
            assert expected == HISTORICAL_CORE_SHA256, original
        else:
            assert actual == expected, original
    link["historical"] = historical
    return link
