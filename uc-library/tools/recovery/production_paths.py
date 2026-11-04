"""Reject new scheduling-named production paths and scratch dependencies.

Existing debt is exact and reviewed, not a pattern exemption. This check is
structural only; it does not replace compile, behavior, role or readiness gates.
"""
import json
from pathlib import Path
import re


class ProductionPathError(ValueError):
    pass


SCHEDULING = re.compile(
    r'(?:frontier\d|reconstruction\d|rank\d|trial\d|cycle\d|_w\d|batch\d|large\d)',
    re.IGNORECASE)
SUFFIXES = {'.cpp', '.hpp', '.h', '.cc', '.cxx', '.inc', '.c'}
FORBIDDEN = {'candidates', 'temp', 'scratch', '.trashes'}


def check(library):
    library = Path(library).resolve()
    manifest = library / 'cmake/ProductionPathMigration.json'
    debt = {}
    if manifest.exists():
        document = json.loads(manifest.read_text())
        if document.get('version') != 1:
            raise ProductionPathError('Unsupported production migration inventory')
        for entry in document.get('entries', []):
            name = entry.get('path', '')
            path = library / name
            destinations = entry.get('destinations', [])
            if (name in debt or not name.startswith(('include/', 'src/'))
                    or not SCHEDULING.search(name) or not path.is_file()
                    or not path.resolve().is_relative_to(library)
                    or not entry.get('owner') or not entry.get('reason')
                    or not destinations or not entry.get('baseline_sha256')):
                raise ProductionPathError('Invalid or stale migration entry: ' + name)
            for destination in destinations:
                if (not destination.startswith(('include/', 'src/'))
                        or SCHEDULING.search(destination)
                        or not (library / destination).resolve().is_relative_to(library)):
                    raise ProductionPathError('Noncanonical migration destination: ' + destination)
            debt[name] = entry
    paths = sorted(p for directory in ('include', 'src')
                   for p in (library / directory).rglob('*')
                   if p.is_file() and p.suffix in SUFFIXES)
    includes = 0
    for path in paths:
        name = str(path.relative_to(library))
        if SCHEDULING.search(name) and name not in debt:
            raise ProductionPathError('New noncanonical production path: ' + name)
        if not path.resolve().is_relative_to(library):
            raise ProductionPathError('Production source escapes library: ' + name)
        # Scan every production header as well as TUs: a canonical intermediary
        # cannot conceal a transitive candidate/scratch include.
        text = re.sub(r'/\*.*?\*/|//[^\n]*', '', path.read_text(), flags=re.S)
        for line in text.splitlines():
            match = re.match(r'^\s*#\s*include\s+(.+)', line)
            if not match:
                continue
            literal = re.fullmatch(r'[<"]([^>"\n]+)[>"]\s*', match[1])
            if not literal:
                raise ProductionPathError('Unresolved production include: ' + name + ': ' + line)
            include = literal[1]
            includes += 1
            if FORBIDDEN.intersection(Path(include).parts):
                raise ProductionPathError('Production dependency on scratch/candidates: ' + name + ': ' + include)
            for candidate in (path.parent / include, library / 'include' / include,
                              library / include):
                if candidate.exists():
                    resolved = candidate.resolve()
                    parts = (resolved.relative_to(library).parts
                             if resolved.is_relative_to(library) else resolved.parts)
                    if FORBIDDEN.intersection(parts):
                        raise ProductionPathError('Production dependency resolves to scratch/candidates: ' + name)
                    break
    return {'passed': True, 'production_files': len(paths),
            'reviewed_existing_path_exceptions': len(debt),
            'literal_include_edges_checked': includes,
            'scope': 'Structural source/include check; no behavior or readiness credit'}
