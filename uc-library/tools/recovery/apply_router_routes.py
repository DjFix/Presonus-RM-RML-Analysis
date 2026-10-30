"""Fixed Router6 product application; ledger admission is a separate gate."""
import argparse
import hashlib
import json
from pathlib import Path
import re

repo = Path.cwd().resolve()
lib = repo / 'uc-library'
out = repo / 'evidence/recovery/2026-10-28/router-routes-batch'
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
    map_path = lib / 'candidates/noaa-router-routes/CONTROLLED-APPLY.json'
    assert sha(map_path) == 'fffa5bb7098e708381b5a604718ae9dfcd4a06378ef8c2ed43b9cd3f704ac0b4'
    mapping = read(map_path)
    products, previous, origins = {}, {}, {}
    candidate_paths = []
    for row in mapping['products']:
        name = row['target']
        source, target = lib / row['source'], lib / name
        assert source.resolve().is_relative_to(lib) and target.resolve().is_relative_to(lib)
        assert sha(source) == row['sha256'] and not target.is_symlink()
        old = row['previous_sha256']
        assert not target.exists() if old is None else sha(target) == old
        products[name], previous[name], origins[name] = source.read_bytes(), old, row['source']
        if source.suffix in ('.cpp', '.hpp', '.h'):
            candidate_paths.append(row['source'])
    groups = (lib / 'cmake/ProductionSourceGroups.cmake').read_text()
    assert counts(groups) == [102, 46, 42]
    assert mapping['production_cpp_partition'] == {'src/Presonus/NOAA/TCardRouterRoutes.cpp': 'rm'}
    cpp = 'src/Presonus/NOAA/TCardRouterRoutes.cpp'
    assert cpp not in groups and not mapping['new_public_headers']
    groups = once(groups, 'set(PRESONUS_rm_SOURCES\n', 'set(PRESONUS_rm_SOURCES\n  ' + cpp + '\n')
    assert counts(groups) == [102, 46, 43]
    cmake = (lib / 'CMakeLists.txt').read_text()
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
    marker = '  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)'
    cmake = once(cmake, marker, '\n'.join(block) + '\n' + marker)
    for name, text in [('CMakeLists.txt', cmake), ('cmake/ProductionSourceGroups.cmake', groups)]:
        assert (out / 'before' / name).read_bytes() == (lib / name).read_bytes()
        products[name], previous[name], origins[name] = text.encode(), sha(lib / name), 'Fixed Router-only root recipe'
    changed = {name for name, old in previous.items() if old and hashlib.sha256(products[name]).hexdigest() != old}
    affected = {kind: [row for row in read(lib / 'validation' / filename)['functions'] if changed.intersection(row['sources'])]
                for kind, filename in [('ready', 'ready-functions.json'), ('pending', 'compiled-functions.json')]}
    assert (len(affected['ready']), len(affected['pending'])) == (6, 24)
    plan = dict(products=len(products), partitions=counts(groups), cpp=191, suites=209, headers=130,
                affected_ready=6, affected_pending=24)
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
        (lib / 'validation/format-router-routes-paths.json').write_text(json.dumps(sorted(set(paths)), indent=2) + '\n')
        additions = sorted(set(products) | {'candidates/noaa-router-routes/CONTROLLED-APPLY.json', str(Path(__file__).relative_to(lib))})
        (lib / 'validation/integration-router-routes-additions.json').write_text(json.dumps(additions, indent=2) + '\n')
    print(json.dumps(dict(plan, apply=args.apply)))

if __name__ == '__main__':
    main()
