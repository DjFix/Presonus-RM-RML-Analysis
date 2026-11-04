"""Early integration checks; final Linux, installed-role and readiness gates remain required."""
import hashlib
import json
from pathlib import Path
import re


class PreflightError(ValueError):
    pass


CODE_SUFFIXES = {'.cpp', '.hpp', '.h', '.c', '.cc', '.cxx', '.inc', '.cmake',
                 '.py', '.json', '.txt', '.sh'}


def source_inputs(library):
    paths = {library / 'CMakeLists.txt'}
    for name in ('src', 'include', 'tests', 'cmake', 'tools'):
        paths.update(p for p in (library / name).rglob('*')
                     if p.is_file() and p.suffix in CODE_SUFFIXES
                     and '__pycache__' not in p.parts)
    for path in paths:
        if not path.resolve().is_relative_to(library.resolve()):
            raise PreflightError('Integration input escapes library: ' + str(path))
    return paths


def snapshot(library):
    return {str(p.relative_to(library)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(source_inputs(library))}


def verify_snapshot(library, frozen):
    current = snapshot(library)
    changed = sorted(p for p in set(frozen) | set(current)
                     if frozen.get(p) != current.get(p))
    if changed:
        raise PreflightError('Inputs changed during integration: ' + ', '.join(changed))


def installed_headers(library, build):
    """Read CMake's configured install plan, never guess private/public headers."""
    script = build / 'cmake_install.cmake'
    if not script.is_file():
        raise PreflightError('Configure must produce ' + str(script))
    headers = set()
    for body in re.findall(r'file\(INSTALL\b(.*?)\)', script.read_text(), re.S):
        if not re.search(r'\bTYPE FILE\b', body):
            continue
        destination = re.search(r'DESTINATION\s+"([^"]+)"', body)
        for value in re.findall(r'"([^"]+)"', body):
            path = Path(value)
            if not path.is_absolute() or not path.is_relative_to(library / 'include'):
                continue
            name = str(path.relative_to(library))
            if not path.is_file():
                raise PreflightError('Missing installed header source: ' + name)
            expected = '${CMAKE_INSTALL_PREFIX}/' + str(Path(name).parent)
            if destination is None or destination[1] != expected:
                raise PreflightError('Unexpected install destination for ' + name)
            if name in headers:
                raise PreflightError('Duplicate installed header: ' + name)
            headers.add(name)
    if not headers:
        raise PreflightError('No application headers found in configured install plan')
    return headers


def production_groups(library):
    text = (library / 'cmake/ProductionSourceGroups.cmake').read_text()
    groups = {}
    for role, body in re.findall(
            r'set\(PRESONUS_(common|cs18|rm)_SOURCES\s*\n(.*?)\n\)', text, re.S):
        names = body.split()
        if role in groups or not names or len(names) != len(set(names)):
            raise PreflightError('Duplicate or empty production partition: ' + role)
        if any(not n.startswith('src/') or not n.endswith('.cpp') for n in names):
            raise PreflightError('Unsupported production path in ' + role)
        groups[role] = set(names)
    if set(groups) != {'common', 'cs18', 'rm'}:
        raise PreflightError('All three production partitions are required')
    all_sources = set().union(*groups.values())
    actual = {str(p.relative_to(library)) for p in (library / 'src').rglob('*.cpp')}
    if sum(map(len, groups.values())) != len(all_sources) or all_sources != actual:
        raise PreflightError('Unclassified/duplicated production CPPs: ' +
                             repr(sorted(all_sources ^ actual)))
    return groups


def automatic_inputs(library, build):
    from production_paths import check as check_production_paths
    check_production_paths(library)
    groups = production_groups(library)
    headers = installed_headers(library, build)
    paths = set().union(*groups.values()) | headers
    for directory in ('tests', 'cmake', 'tools'):
        paths.update(str(p.relative_to(library))
                     for p in (library / directory).rglob('*')
                     if p.is_file() and p.suffix in CODE_SUFFIXES
                     and '__pycache__' not in p.parts)
    paths.add('CMakeLists.txt')
    return paths, groups, headers


def inspect_configuration(library, build, frozen, extra):
    verify_snapshot(library, frozen)
    paths, groups, headers = automatic_inputs(library, build)
    paths.update(extra)
    for name in paths:
        path = library / name
        if not path.resolve().is_relative_to(library.resolve()) or not path.is_file():
            raise PreflightError('Invalid integration input: ' + name)
    # Use exactly the same strict contracts as the final role audit.
    from audit_role_build_basic_activity import check_production_compile_contracts
    check_production_compile_contracts(library, build, groups)
    return {'passed': True, 'production_cpp': sum(map(len, groups.values())),
            'installed_application_headers': len(headers),
            'additional_inputs': sorted(paths), 'frozen_sources': frozen,
            'scope': 'Early configuration/input checks only; no build, behavior, '
                     'installed-role, integration or readiness gate is waived.'}
