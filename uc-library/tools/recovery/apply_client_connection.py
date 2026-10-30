"""Fixed Handler4/typed-event product application; admission is separate."""
import argparse
import hashlib
import json
from pathlib import Path
import re

repo = Path.cwd().resolve()
lib = repo / 'uc-library'
out = repo / 'evidence/recovery/2026-10-28/client-connection-batch'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())

def once(text, needle, replacement):
    assert text.count(needle) == 1, needle
    return text.replace(needle, replacement, 1)

def counts(text):
    return [len(re.search(r'set\(PRESONUS_' + g + r'_SOURCES\n(.*?)\n\)', text, re.S).group(1).split()) for g in ('common', 'cs18', 'rm')]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    pre = read(out / 'candidate-preflight-01/validation.json')
    assert pre['passed']
    for name, digest in {**pre['unchanged_state'], **pre['inputs']}.items():
        assert sha(lib / name) == digest, name
    expected = {'noaa-ucnet-handler': 'c2a241aa9ce9679df2f40e2087a906cd4b5c2576cd298e75250b96de6094f246', 'uc-client-connection-dispatch': '3cd07a5aaf21cfe647a0808b1d299d8218a3cf86e8ae9bc9c35200db080c9849'}
    products, previous, origins, mappings = {}, {}, {}, {}
    candidate_paths = []
    for candidate, digest in expected.items():
        own = lib / 'candidates' / candidate
        map_path = own / 'CONTROLLED-APPLY.json'
        assert sha(map_path) == digest
        mapping = mappings[candidate] = read(map_path)
        for row in mapping['products']:
            name = row.get('target', row.get('destination'))
            source = lib / row['source'] if row['source'].startswith('candidates/') else own / row['source']
            target = lib / name
            assert source.resolve().is_relative_to(lib) and target.resolve().is_relative_to(lib)
            assert sha(source) == row['sha256'] and not target.is_symlink() and name not in products
            old = row.get('previous_sha256', row.get('required_destination_sha256'))
            assert not target.exists() if old is None else sha(target) == old
            products[name], previous[name], origins[name] = source.read_bytes(), old, str(source.relative_to(lib))
            if source.suffix in ('.cpp', '.hpp', '.h'):
                candidate_paths.append(str(source.relative_to(lib)))
    mapping = mappings['noaa-ucnet-handler']
    bridge = mappings['uc-client-connection-dispatch']
    groups = (lib / 'cmake/ProductionSourceGroups.cmake').read_text()
    assert counts(groups) == [103, 46, 44]
    assert mapping['production_cpp_partition'] == {'src/Presonus/NOAA/TCardUCNetHandlerIO.cpp': 'rm'}
    assert bridge['production_cpp'] == ['src/Presonus/UC/ClientConnectionDispatch.cpp', 'src/Presonus/UC/ClientTypedOrigins.cpp'] and bridge['production_partition'] == 'common'
    assert sha(lib / 'candidates/uc-client-event-values/CONTROLLED-APPLY.json') == bridge['required_bridge_map_sha256']
    for group, cpp in [('rm', 'src/Presonus/NOAA/TCardUCNetHandlerIO.cpp')] + [('common', cpp) for cpp in bridge['production_cpp']]:
        assert cpp not in groups
        marker = 'set(PRESONUS_' + group + '_SOURCES\n'
        groups = once(groups, marker, marker + '  ' + cpp + '\n')
    assert counts(groups) == [105, 46, 45]
    headers = [name.removeprefix('include/') for name in mapping['new_public_headers'] + bridge['public_headers']]
    assert len(set(headers)) == 3 and all(name not in groups for name in headers)
    groups = once(groups, 'set(PRESONUS_PUBLIC_HEADERS\n', 'set(PRESONUS_PUBLIC_HEADERS\n' + ''.join('  ' + name + '\n' for name in headers))
    cmake = (lib / 'CMakeLists.txt').read_text()
    cmake = once(cmake, 'set(PRESONUS_UC_PUBLIC_HEADERS\n', 'set(PRESONUS_UC_PUBLIC_HEADERS\n' + ''.join('  ' + name + '\n' for name in headers))
    options = mapping['production_compile_options']['src/Presonus/NOAA/TCardUCNetHandlerIO.cpp']
    assert options == ['-fno-rtti', '-fno-lto']
    property_line = 'set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/Presonus/NOAA/TCardUCNetHandlerIO.cpp" APPEND PROPERTY COMPILE_OPTIONS ' + ' '.join(options) + ')'
    cmake = once(cmake, 'presonus_build_common_objects()', 'presonus_build_common_objects()\n' + property_line)
    block = []
    assert len(mapping['test_targets']) == 1
    for target in mapping['test_targets']:
        name = target['name']
        assert 'add_executable(' + name not in cmake
        assert '-UNDEBUG' in target['compile_options']
        block += ['  add_executable(' + name + ' ' + target['source'] + ')',
                  '  target_link_libraries(' + name + ' PRIVATE ' + target['link'] + ')',
                  '  target_compile_options(' + name + ' PRIVATE ' + ' '.join(target['compile_options']) + ')',
                  '  target_link_options(' + name + ' PRIVATE ' + ' '.join(target['link_options']) + ')',
                  '  add_test(NAME ' + name + ' COMMAND ' + name + ' ' + ' '.join(target['arguments']) + ')']
    own = lib / 'candidates/uc-client-connection-dispatch'
    assert sha(own / bridge['test_block']) == bridge['test_block_sha256']
    assert sha(own / bridge['source_block']) == bridge['source_block_sha256']
    assert 'add_executable(' + bridge['test_target'] not in cmake
    block.append((own / bridge['test_block']).read_text())
    marker = '  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)' 
    cmake = once(cmake, marker, '\n'.join(block) + '\n' + marker)
    for name, text in [('CMakeLists.txt', cmake), ('cmake/ProductionSourceGroups.cmake', groups)]:
        assert (out / 'before' / name).read_bytes() == (lib / name).read_bytes()
        products[name], previous[name], origins[name] = text.encode(), sha(lib / name), 'Fixed shared Client6/UCNet4 root recipe'
    changed = {name for name, old in previous.items() if old and hashlib.sha256(products[name]).hexdigest() != old}
    affected = {kind: [row for row in read(lib / 'validation' / filename)['functions'] if changed.intersection(row['sources'])]
                for kind, filename in [('ready', 'ready-functions.json'), ('pending', 'compiled-functions.json')]}
    assert (len(affected['ready']), len(affected['pending'])) == (6, 26)
    plan = dict(products=len(products), partitions=counts(groups), cpp=196, suites=213, headers=136,
                affected_ready=6, affected_pending=26)
    if not args.apply:
        (out / 'application-plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    else:
        assert not (out / 'application.json').exists() and read(out / 'application-plan.json') == plan
        for name, data in products.items():
            target = lib / name
            if target.exists():
                backup = out / 'before' / name
                backup.parent.mkdir(parents=True, exist_ok=True)
                if backup.exists():
                    assert backup.read_bytes() == target.read_bytes()
                else:
                    backup.write_bytes(target.read_bytes())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (out / 'application.json').write_text(json.dumps({name: dict(previous_sha256=previous[name], applied_sha256=sha(lib / name), source=origins[name]) for name in products}, indent=2) + '\n')
        (out / 'affected-source-closure.json').write_text(json.dumps(affected, indent=2) + '\n')
        paths = candidate_paths + [name for name in products if Path(name).suffix in ('.cpp', '.hpp', '.h')]
        (lib / 'validation/format-client-connection-paths.json').write_text(json.dumps(sorted(set(paths)), indent=2) + '\n')
        additions = sorted(set(products) | {'candidates/' + name + '/CONTROLLED-APPLY.json' for name in expected} | {str(Path(__file__).relative_to(lib))})
        (lib / 'validation/integration-client-connection-additions.json').write_text(json.dumps(additions, indent=2) + '\n')
    print(json.dumps(dict(plan, apply=args.apply)))

if __name__ == '__main__':
    main()
