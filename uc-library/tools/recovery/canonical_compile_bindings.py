"""Read actual canonical CMake product/provider bindings. No compile or fallback proof."""
import hashlib
import json
from pathlib import Path
import shlex


def need(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def absolute(path, directory):
    path = Path(path)
    return (directory / path).resolve() if not path.is_absolute() else path.resolve()


def arguments(row):
    return row.get('arguments') or shlex.split(row['command'])


def output_path(argv, directory, explicit=None):
    if explicit is None:
        need(argv.count('-o') == 1, 'Unique actual -o output required')
        explicit = argv[argv.index('-o') + 1]
    return absolute(explicit, directory)


def make_dependencies(path, directory, obj):
    text = path.read_text().replace('\\\n', ' ')
    need(':' in text, 'Malformed canonical depfile')
    targets, body = text.split(':', 1)
    need(obj in {absolute(t, directory) for t in shlex.split(targets)}, 'Depfile target differs from supplied object')
    paths = {absolute(t, directory) for t in shlex.split(body)}
    need(paths and all(p.is_file() for p in paths), 'Missing or empty canonical dependency closure')
    return paths


def archive_contains(path, wanted, basename):
    """Require a unique named GNU/BSD ar member with exact object bytes."""
    data = path.read_bytes()
    need(data.startswith(b'!<arch>\n'), 'Unsupported/nonordinary canonical archive')
    pos = 8; longnames = b''; matches = []; names = 0
    while pos < len(data):
        header = data[pos:pos + 60]
        need(len(header) == 60 and header[58:] == b'`\n', 'Malformed archive header')
        size = int(header[48:58]); member = data[pos + 60:pos + 60 + size]
        need(len(member) == size, 'Truncated archive member')
        name = header[:16].decode().strip()
        if name == '//': longnames = member
        elif name.startswith('#1/'):
            length = int(name[3:]); name = member[:length].decode().rstrip('\0'); member = member[length:]
        elif name.startswith('/') and name[1:].isdigit():
            name = longnames[int(name[1:]):].split(b'/\n', 1)[0].decode()
        else: name = name.rstrip('/')
        if name == basename:
            names += 1; matches.append(hashlib.sha256(member).hexdigest() == wanted)
        pos += 60 + size + size % 2
    need(names <= 1, 'Ambiguous duplicate archive member basename: ' + basename)
    return matches == [True]


def bind(root, object_path, source, exe_path=None, required_provider_sources=(), required_archive_names=()):
    root = Path(root).resolve(); obj = Path(object_path).resolve(); source = (root / source).resolve()
    need(obj.is_file() and obj.is_relative_to(root / 'temp'), 'Actual project canonical object required')
    builds = [p for p in obj.parents if (p / 'compile_commands.json').is_file() and (p / 'CMakeCache.txt').is_file()]
    need(builds, 'Actual CMake compile commands/cache required; worker scratch is not canonical')
    build = builds[0]
    need(build == (root / 'temp/core-upstream/root-integration-01').resolve(), 'Reviewed actual canonical build root required')
    cache = build / 'CMakeCache.txt'; commands = build / 'compile_commands.json'
    cache_text = cache.read_text()
    need('CMAKE_HOME_DIRECTORY:INTERNAL=' + str(root / 'uc-library') in cache_text.splitlines(), 'CMake source root differs')
    need('CMAKE_BUILD_TYPE:STRING=Release' in cache_text.splitlines(), 'Actual canonical Release build required')
    seals = {cache: digest(cache), commands: digest(commands), obj: digest(obj)}
    rows = json.loads(commands.read_text()); files = {}; observed = []; installed_core_bindings = []

    def observe(unit, expected=None):
        hits = []
        for row in rows:
            directory = Path(row['directory']).resolve(); argv = arguments(row)
            if absolute(row['file'], directory) != unit:
                continue
            out = output_path(argv, directory, row.get('output'))
            if expected is None or out == expected:
                hits.append((row, directory, out))
        production_partition = None
        if expected is None:
            # Canonical production ownership, not an arbitrary first compile row.
            groups = root / 'uc-library/cmake/ProductionSourceGroups.cmake'
            need(groups.is_file() and unit.is_relative_to(root / 'uc-library'), 'Actual production source ownership required')
            seals[groups] = digest(groups)
            files[str(groups.relative_to(root))] = seals[groups]
            relative_unit = str(unit.relative_to(root / 'uc-library'))
            owners = []
            import re
            for role, body in re.findall(r'set\(PRESONUS_(common|cs18|rm)_SOURCES\s+(.*?)\)', groups.read_text(), re.S):
                entries = [line.split('#', 1)[0].strip().strip('"') for line in body.splitlines()]
                if relative_unit in entries: owners.append(role)
            need(len(owners) == 1, 'Exactly one declared production OBJECT partition required: ' + relative_unit)
            role = owners[0]
            expected_production = build / ('CMakeFiles/presonus_' + role + '_objects.dir') / (relative_unit + '.o')
            hits = [hit for hit in hits if hit[2] == expected_production]
            production_partition = {'name': role, 'manifest': str(groups.relative_to(root)), 'sha256': seals[groups], 'expected_object': str(expected_production.relative_to(root))}
        need(len(hits) == 1, 'Unique actual source/object compile entry required: ' + str(unit))
        row, directory, output = hits[0]
        need(output.is_file(), 'Canonical provider object absent')
        dep = output.with_name(output.name + '.d'); need(dep.is_file(), 'Actual canonical object depfile required; no empty fallback')
        seals[output] = digest(output); seals[dep] = digest(dep)
        paths = make_dependencies(dep, directory, output)
        need(unit in paths, 'Canonical dependency closure omits production unit')
        need(all(p.stat().st_mtime_ns <= output.stat().st_mtime_ns for p in paths), 'Canonical object older than dependency; build required')
        for p in paths:
            if p.is_relative_to(root): files[str(p.relative_to(root))] = digest(p)
            installed_core = build / 'upstream-core/sdk/include/presonus-core-5/core'
            if p.is_relative_to(installed_core):
                origin = root / 'third_party/ccl-framework/core' / p.relative_to(installed_core)
                need(origin.is_file(), 'Installed Core dependency has no pinned source origin: ' + str(p))
                actual_sha = digest(p); origin_sha = digest(origin)
                need(actual_sha == origin_sha, 'Installed Core dependency differs from pinned source: ' + str(p))
                files[str(origin.relative_to(root))] = origin_sha
                seals[p] = actual_sha; seals[origin] = origin_sha
                installed_core_bindings.append({'installed_path': str(p.relative_to(root)), 'source_path': str(origin.relative_to(root)), 'sha256': origin_sha, 'scope': 'Exact installed header bytes matched to pinned Core source; no layout or original ABI claim'})
        item = {'source': str(unit.relative_to(root)), 'object': {'path': str(output.relative_to(root)), 'sha256': seals[output]}, 'depfile': {'path': str(dep.relative_to(root)), 'sha256': seals[dep]}, 'compile_entry': row}
        if production_partition is not None:item['production_partition'] = production_partition
        observed.append(item)
        return output

    objects = [observe(source, obj)]; header_providers = []
    for value in required_provider_sources:
        unit = (root / value).resolve(); need(unit.is_relative_to(root), 'Provider source outside repository')
        if unit.suffix in ('.h', '.hpp', '.hxx'):
            need(str(unit.relative_to(root)) in files, 'Header-only provider absent from actual dependency closure')
            header_providers.append({'path': str(unit.relative_to(root)), 'sha256': files[str(unit.relative_to(root))]})
        else:
            objects.append(observe(unit))
    link = None
    if exe_path is not None:
        exe = Path(exe_path).resolve(); need(exe.is_file() and exe.is_relative_to(build), 'Actual supplied canonical executable required')
        seals[exe] = digest(exe); matches = []
        for path in (build / 'CMakeFiles').glob('*.dir/link.txt'):
            argv = shlex.split(path.read_text())
            if argv.count('-o') == 1 and output_path(argv, build) == exe: matches.append((path, argv))
        need(len(matches) == 1, 'Unique actual executable CMake link entry required')
        path, argv = matches[0]; seals[path] = digest(path)
        # Fail rather than silently omit response-file link dependencies.
        need(not any(t.startswith('@') for t in argv), 'Response-file link requires explicit supported expansion')
        archives = list(dict.fromkeys(absolute(t, build) for t in argv if t.endswith('.a')))
        need(all(p.is_file() for p in archives), 'Canonical link archive missing')
        for p in archives: seals[p] = digest(p)
        need(set(required_archive_names) <= {p.name for p in archives}, 'Required actual linked provider archive absent')
        need(all(sum(p.name == name for p in archives) == 1 for name in required_archive_names), 'Ambiguous actual linked provider archive basename')
        direct_objects = {absolute(t, build) for t in argv if t.endswith(('.o', '.obj'))}
        for output in objects:
            need(output in direct_objects or any(archive_contains(p, seals[output], output.name) for p in archives), 'Canonical linked objects/archives omit required production/provider object')
        link = {'executable': {'path': str(exe.relative_to(root)), 'sha256': seals[exe]}, 'link_file': {'path': str(path.relative_to(root)), 'sha256': seals[path]}, 'argv': argv, 'archives': [{'path': str(p.relative_to(root)) if p.is_relative_to(root) else str(p), 'sha256': seals[p]} for p in archives]}
    else:
        need(not required_provider_sources and not required_archive_names, 'Provider binding requires actual executable/link entry')
    need(all(digest(path) == value for path, value in seals.items()), 'Canonical artifacts changed during observation')
    need(all(digest(root / name) == value for name, value in files.items()), 'Canonical dependencies changed during observation')
    return {'installed_core_bindings': installed_core_bindings, 'files': files, 'build': str(build.relative_to(root)), 'cache': {'path': str(cache.relative_to(root)), 'sha256': seals[cache]}, 'compile_commands': {'path': str(commands.relative_to(root)), 'sha256': seals[commands]}, 'objects': observed, 'header_providers': header_providers, 'link': link, 'scope': 'Fresh actual canonical Release CMake source/object/depfile/link/archive binding; no worker proof reuse or original ABI/native behavior claim'}


def load_transition(root, explicit_repository_relative_path):
    """Root creates this only after applying archived, reviewed producer revisions."""
    root = Path(root).resolve()
    relative = Path(explicit_repository_relative_path)
    need(not relative.is_absolute() and relative.parts and '..' not in relative.parts, 'Explicit repository-relative transition path required')
    path = (root / relative).resolve()
    need(path.is_relative_to(root), 'Canonical transition outside repository')
    need(path.is_file(), 'Actual Root-applied canonical input transition required')
    value = json.loads(path.read_text())
    need(all(key in value for key in ('baseline_provider_manifest', 'accepted_root_bindings', 'receipts', 'current_sources')), 'Incomplete actual canonical transition')
    for key in ('baseline_provider_manifest', 'accepted_root_bindings'):
        ref = value[key]; need(digest(root / ref['path']) == ref['sha256'], 'Canonical transition input changed')
    return {'path': str(path.relative_to(root)), 'sha256': digest(path), 'record': value}
