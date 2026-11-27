#!/usr/bin/env python3
"""Finite LPC installed-role successor; no production changes or readiness admission.

Preserves the R4 producer and failure manifest and replaces its conflicting map
options with exactly one output-specific map. Uses reviewed provider requirements.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

from canonical_compile_bindings import bind, make_dependencies
import canonical_compile_bindings as bindings

ROOT = Path(__file__).resolve().parents[3]
BUILD = ROOT / 'temp/core-upstream/root-integration-01'
HISTORY = ROOT / 'temp/recovery-work/rolling-c001-20261124/integration-support/current104-proof-prep-sol61'


def sha(path):
    return hashlib.file_digest(Path(path).open('rb'), 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    path = Path(path).resolve()
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha(path)}


def put(path, data):
    with Path(path).open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


def run(argv, cwd, log):
    put(log.with_suffix('.argv.json'), {'argv': argv, 'cwd': str(cwd)})
    with log.open('xb') as stream:
        subprocess.run(argv, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, check=True)


def exact_member(archive, wanted, basename):
    """Duplicate names are allowed only with exactly one matching byte identity."""
    data = archive.read_bytes()
    assert data.startswith(b'!<arch>\n')
    pos, longnames, matches = 8, b'', []
    while pos < len(data):
        header = data[pos:pos+60]
        assert len(header) == 60 and header[58:] == b'`\n'
        size = int(header[48:58]); member = data[pos+60:pos+60+size]
        assert len(member) == size
        name = header[:16].decode().strip()
        if name == '//':
            longnames = member
        elif name.startswith('#1/'):
            length = int(name[3:]); name = member[:length].decode().rstrip('\0'); member = member[length:]
        elif name.startswith('/') and name[1:].isdigit():
            name = longnames[int(name[1:]):].split(b'/\n', 1)[0].decode()
        else:
            name = name.rstrip('/')
        if name == basename:
            matches.append(hashlib.sha256(member).hexdigest())
        pos += 60 + size + size % 2
    assert pos == len(data) and matches.count(wanted) <= 1
    return matches.count(wanted) == 1


def strict_receipt(command):
    """Same original R4 strict-wrapper contract, bound to the new role executable."""
    assert command[command.index('--profile')+1] == 'lpc'
    exe = Path(command[command.index('--exe')+1]).resolve(strict=True)
    wrapper = Path(command[1]).resolve(strict=True)
    mapper = wrapper.parent / 'prepare_local_symbol_map.py'
    st = exe.stat()
    tag = hashlib.sha256(json.dumps(dict(binary=str(exe), sha256=sha(exe), stat=[st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns], mapper=sha(mapper)), sort_keys=True).encode()).hexdigest()
    directory = ROOT / 'temp/test-work/current104-static' / ('lpc-'+tag)
    mapping = directory / 'MAP.json'; data = read(mapping)
    assert data['binary'] == str(exe) and data['sha256'] == sha(exe)
    receipts = [(p, read(p)) for p in directory.glob('PASS-*.json') if read(p)['binary_hashes'] == {str(exe): sha(exe)}]
    assert len(receipts) == 1
    receipt, row = receipts[0]
    assert row['passed'] and not row['inherited_PRESONUS_variables_used'] and row['before_and_after_each_subprocess_verified'] and row['replays'] and not row['fixture_or_oracle_changes']
    assert row['map'] == str(mapping) and row['map_sha256'] == sha(mapping) and row['mapper_sha256'] == sha(mapper)
    return dict(wrapper=ref(wrapper), map=ref(mapping), receipt=ref(receipt), exe=ref(exe))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve(); assert out.is_relative_to(ROOT / 'evidence/recovery')
    out.mkdir(parents=True, exist_ok=False)
    archive = out / 'historical-producer'; archive.mkdir()
    originals = [HISTORY/'seal_current104_r4.py', HISTORY/'updater_role104_r2.py', ROOT/'evidence/recovery/2026-11-24/rolling-c001/sqlite-cycle02-wave16-eligible77-proofs01/PARKED-27-METHODS.json']
    preserved = []
    for source in originals:
        target = archive / source.name; shutil.copyfile(source, target); assert sha(source) == sha(target)
        preserved.append({'original': ref(source), 'preserved': ref(target)})
    planpath = HISTORY/'PROOF-PLAN-R3.json'; policypath = HISTORY/'PROVIDER-POLICY-CANDIDATE03-R3.json'
    plan, policy = read(planpath), read(policypath)
    regs = [r for r in plan['registrations'] if r['group'] == 'lpc']
    assert len(regs) == 16
    manifest = BUILD/'install_manifest.txt'
    paths = [Path(p) for p in manifest.read_text().splitlines()]
    compilers = read(BUILD/'compile_commands.json')
    bindings.archive_contains = exact_member
    proofs = []
    for reg in regs:
        task = reg['task']; location = out/task; location.mkdir()
        assert ref(ROOT/reg['handoff']['path']) == reg['handoff']
        assert ref(ROOT/reg['context']['path']) == reg['context']
        source = 'uc-library/'+reg['source']; obj = BUILD/reg['object']
        command = reg['ctest']
        exe = Path(reg['executable']); roles = {}
        for role in ['client', 'server']:
            folder = location/role; folder.mkdir()
            requirement = policy['tasks'][task]['roles'][role]
            required = requirement['required_runtime_providers']; assert not requirement['compiled_evidence_only']
            observed = bind(ROOT, obj, source, exe, required_provider_sources=tuple(required), required_archive_names=('libcorelib.a','libpresonus_core_allocator.a','libpresonus_png.a','libpresonus_zlib.a'))
            archive_name = 'libpresonus_'+{'client':'cs18','server':'rm'}[role]+'_components.a'
            installed, = [p for p in paths if p.name == archive_name]
            assert sha(installed) == sha(BUILD/archive_name)
            original_link = observed['link']['argv']
            # R4 inserted its map before the canonical map, so ld selected the latter.
            removed = [a for a in original_link if a.startswith('-Wl,-Map,') or a.startswith('-Wl,--dependency-file=')]
            assert sum(a.startswith('-Wl,-Map,') for a in removed) == 1
            link = [a for a in original_link if a not in removed]
            slots = [i for i,a in enumerate(link) if Path(a).name in ('libpresonus_uc.a','libpresonus_cs18_components.a','libpresonus_rm_components.a')]
            slot, = slots; link[slot] = str(installed)
            roleexe, mapping = folder/'replay', folder/'role-link.map'
            link[link.index('-o')+1] = str(roleexe); link.append('-Wl,-Map,'+str(mapping))
            assert sum(a.startswith('-Wl,-Map,') for a in link) == 1
            run(link, BUILD, folder/'link.log'); maptext = mapping.read_text()
            for item in observed['objects']:
                objectref = item['object']; basename = Path(objectref['path']).name
                assert exact_member(installed, objectref['sha256'], basename)
                assert f'{installed}({basename})' in maptext
            assert 'libpresonus_uc.a(' not in maptext
            opposite = 'libpresonus_'+{'client':'rm','server':'cs18'}[role]+'_components.a('
            assert opposite not in maptext
            names = [line.split()[-1] for line in subprocess.check_output(['nm','--defined-only',str(roleexe)], text=True).splitlines() if line.split()]
            for original in reg['exact_originals']:
                if original['role'] == role: assert names.count(original['mangled']) == 1
            replay = [str(roleexe) if a == str(exe) else a for a in command]
            assert replay != command
            if '--out' in replay: replay[replay.index('--out')+1] = str(folder/'observations.json')
            run(replay, ROOT, folder/'replay.log')
            strict = strict_receipt(replay)
            linkfile = ROOT/observed['link']['link_file']['path']; target = linkfile.parent.name.removesuffix('.dir')
            units = []
            for unit in compilers:
                if not unit['output'].startswith('CMakeFiles/'+target+'.dir/'): continue
                testobj = Path(unit['directory'])/unit['output']; dep = testobj.with_name(testobj.name+'.d')
                deps = make_dependencies(dep, Path(unit['directory']), testobj)
                assert Path(unit['file']) in deps and all(p.stat().st_mtime_ns <= testobj.stat().st_mtime_ns for p in deps)
                units.append(dict(object=ref(testobj), depfile=ref(dep), files={str(p.relative_to(ROOT)):sha(p) for p in deps if p.is_relative_to(ROOT)}))
            assert units
            roles[role] = dict(archive=ref(installed), map=ref(mapping), exe=ref(roleexe), link_argv=link, removed_flags=removed, replay_argv=replay, stdout=ref(folder/'replay.log'), strict_runtime=strict, compile_and_link=observed, test_units=units, requirement=requirement)
        proof = dict(passed=True, task=task, handoff=reg['handoff'], context=reg['context'], originals=reg['exact_originals'], roles=roles, scope='Installed role link/runtime replay and fresh source/object/archive ownership only; no native replay, declaration resolution, full-suite completion or readiness admission.')
        put(location/'PROOF.json', proof); proofs.append(ref(location/'PROOF.json'))
    put(out/'COMPLETED.json', dict(passed=True, producer=ref(Path(__file__)), historical=preserved, plan=ref(planpath), provider_policy=ref(policypath), installed_manifest=ref(manifest), proofs=proofs, tasks=len(proofs)))


if __name__ == '__main__':
    main()
