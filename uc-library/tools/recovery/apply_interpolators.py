"""Guarded application of the frozen shared interpolator packet."""
from pathlib import Path
import argparse, hashlib, json, re, shutil

p = argparse.ArgumentParser()
p.add_argument('--apply', action='store_true')
a = p.parse_args()
repo = Path.cwd().resolve()
lib = repo / 'uc-library'
out = repo / 'evidence/recovery/2026-10-28/interpolators-batch'
own = lib / 'candidates/dsp-ratio-exp-skew'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
assert sha(own / 'CONTROLLED-APPLY.json') == '5acb927df381e0d158f927769558ab1b783c980fc944978877b61b85564f61a8'
m = read(own / 'CONTROLLED-APPLY.json')
products, old, origins = {}, {}, {}
for row in m['products'] + [dict(m['fixture'], previous_sha256=None)]:
    source = (lib / row['source']).resolve()
    dest = (lib / row['target']).resolve()
    assert source.is_relative_to(lib) and dest.is_relative_to(lib)
    assert not dest.exists() and not dest.is_symlink()
    assert row['previous_sha256'] is None and sha(source) == row['sha256']
    products[row['target']] = source.read_bytes()
    old[row['target']] = None
    origins[row['target']] = row['source']

def once(text, needle, replacement):
    assert text.count(needle) == 1, needle
    return text.replace(needle, replacement, 1)

groups = (lib / 'cmake/ProductionSourceGroups.cmake').read_text()
counts = lambda t: [len(re.search(r'set\(PRESONUS_' + g + r'_SOURCES\n(.*?)\n\)', t, re.S).group(1).split()) for g in ('common', 'cs18', 'rm')]
assert counts(groups) == [83, 35, 11]
groups = once(groups, 'set(PRESONUS_common_SOURCES\n', 'set(PRESONUS_common_SOURCES\n' + ''.join('  ' + name + '\n' for name in m['production_common_cpp']))
groups = once(groups, 'set(PRESONUS_PUBLIC_HEADERS\n', 'set(PRESONUS_PUBLIC_HEADERS\n  presonus/mixer_dsp/Interpolators.hpp\n')
cmake = (lib / 'CMakeLists.txt').read_text()
properties = []
for name in m['production_common_cpp']:
    flags = m['strict_compile_options'] + (['-fno-rtti'] if name in m['no_rtti_sources'] else [])
    properties.append('set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/' + name + '" APPEND PROPERTY COMPILE_OPTIONS ' + ' '.join(flags) + ')')
cmake = once(cmake, 'presonus_build_common_objects()', 'presonus_build_common_objects()\n' + '\n'.join(properties))
cmake = once(cmake, 'foreach(_math_role presonus_uc presonus_rm_components)', 'foreach(_math_role presonus_uc presonus_cs18_components presonus_rm_components)')
cmake = once(cmake, 'set(PRESONUS_UC_PUBLIC_HEADERS\n', 'set(PRESONUS_UC_PUBLIC_HEADERS\n  presonus/mixer_dsp/Interpolators.hpp\n')
block = '''  add_executable(dsp_interpolators_tests tests/dsp_interpolators_tests.cpp)
  target_link_libraries(dsp_interpolators_tests PRIVATE presonus_uc)
  target_compile_options(dsp_interpolators_tests PRIVATE -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
  file(MAKE_DIRECTORY "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/dsp-interpolators")
  add_test(NAME dsp_interpolators_retained COMMAND dsp_interpolators_tests
    "${CMAKE_CURRENT_SOURCE_DIR}/validation/dsp-interpolators/fixtures.txt"
    "${PRESONUS_REPOSITORY_ROOT}/temp/test-work/dsp-interpolators/differences.txt")
'''
cmake = once(cmake, '  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)', block + '  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
for name, text in [('CMakeLists.txt', cmake), ('cmake/ProductionSourceGroups.cmake', groups)]:
    assert (out / 'before' / name).read_bytes() == (lib / name).read_bytes()
    products[name] = text.encode()
    old[name] = sha(lib / name)
    origins[name] = 'Root-reviewed shared interpolation recipe'
affected = {kind: [row for row in read(lib / 'validation' / name)['functions'] if {'CMakeLists.txt', 'cmake/ProductionSourceGroups.cmake'}.intersection(row['sources'])] for kind, name in [('ready', 'ready-functions.json'), ('pending', 'compiled-functions.json')]}
assert (len(affected['ready']), len(affected['pending'])) == (6, 10)
print(json.dumps(dict(apply=a.apply, products=len(products), groups=counts(groups), suites=152, headers=94, affected_ready=6, affected_pending=10)))
if not a.apply:
    raise SystemExit(0)
assert not (out / 'application.json').exists()
for name, data in products.items():
    dest = lib / name
    if dest.exists():
        backup = out / 'before' / name
        backup.parent.mkdir(parents=True, exist_ok=True)
        if backup.exists():
            assert backup.read_bytes() == dest.read_bytes()
        else:
            shutil.copyfile(dest, backup)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
(out / 'affected-source-closure.json').write_text(json.dumps(affected, indent=2) + '\n')
(out / 'application.json').write_text(json.dumps(dict(products={name: dict(previous_sha256=old[name], applied_sha256=sha(lib / name), source=origins[name]) for name in products}), indent=2) + '\n')
cpp = [name for name in products if Path(name).suffix in ('.cpp', '.hpp', '.h')]
paths = sorted(set(cpp + [origins[name] for name in cpp] + m['canonical_extra_formatter_paths']))
(lib / 'validation/format-interpolators-paths.json').write_text(json.dumps(paths, indent=2) + '\n')
(lib / 'validation/integration-interpolators-additions.json').write_text(json.dumps(sorted(products), indent=2) + '\n')
