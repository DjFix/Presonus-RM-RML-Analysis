"""Read-only SQL counts of original function identities and exact-name unions.

Provider imports use the registry ORM and its explicit Alembic migration.
See symbol_statistics.md for counting semantics and commands.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'uc-library/tools/registry'))
from adapter import resolve_db
import orm
import schema


def import_providers(manifest, expected_sha256, database):
    data = Path(manifest).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha256:
        raise ValueError('Provider manifest SHA256 mismatch')
    document = json.loads(data)
    known_elfs = {item['sha256'] for item in document['elfs']}
    definitions = {}
    for item in document['definitions']:
        key = (item['elf_sha256'], item['original_mangled'], item['original_address'])
        library = item['vendor']
        if library not in ('libpng', 'zlib') or key[0] not in known_elfs:
            raise ValueError('Unsupported provider or ELF identity')
        value = (library, int(item['original_size']), int(item['section_index']))
        if key in definitions and definitions[key] != value:
            raise ValueError('Conflicting provider identity')
        definitions[key] = value
    unit = orm.Unit(database, write=True)
    try:
        schema.require_current(unit.raw)
        existing = unit.session.get(orm.ProviderImport, digest)
        if existing:
            if existing.document != data.decode():
                raise ValueError('Existing provider provenance mismatch')
            return {'already_imported': True, 'sha256': digest}
        # Validate every exact original range, including objects, before any write.
        for (elf, name, address), (library,size,section) in definitions.items():
            if not unit.raw.execute('SELECT 1 FROM catalog_symbols WHERE elf=? '
                                    'AND mangled=? AND address=? AND size=? AND section_json=?',
                                    (elf,name,address,size,str(section))).fetchone():
                raise ValueError(f'Provider identity absent from original catalog: {name}')
            if unit.session.get(orm.ProviderDefinition, (elf,name,address)):
                raise ValueError('Existing provider binding; explicit reconciliation required')
        unit.session.add(orm.ProviderImport(sha256=digest, path=str(Path(manifest).resolve()),
            imported_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            document=data.decode()))
        unit.session.flush()
        unit.session.add_all([orm.ProviderDefinition(elf=e,mangled=n,address=a,
            library=library,size=size,section=section,import_sha256=digest)
            for (e,n,a),(library,size,section) in definitions.items()])
        unit.commit()
        return {'database': str(database), 'definitions': len(definitions), 'sha256': digest}
    finally:
        unit.close()


def load_facts(registry, include_scopes=False):
    """One short ORM read transaction; no proof hashing or implicit migration."""
    unit = orm.Unit(registry)
    try:
        schema.require_current(unit.raw)
        provenance = [dict(sha256=r.sha256, path=r.path, imported_at=r.imported_at)
                      for r in unit.session.query(orm.ProviderImport).all()]
        if not provenance:
            raise ValueError('Provider manifest not imported; refusing incomplete library counts')
        vendor_rows = [tuple(r) for r in unit.session.query(orm.ProviderDefinition.elf,
            orm.ProviderDefinition.mangled, orm.ProviderDefinition.address,
            orm.ProviderDefinition.library).all()]
        scope_rows = unit.raw.execute(
            "SELECT mangled,demangled FROM catalog_symbols WHERE kind='STT_FUNC'"
        ).fetchall() if include_scopes else None
        rows = unit.raw.execute("""
            SELECT c.elf,c.role,c.firmware,c.mangled,c.address,c.size,c.policy,r.status
            FROM catalog_symbols c LEFT JOIN records r
              ON r.elf=c.elf AND r.mangled=c.mangled
            WHERE c.kind='STT_FUNC'
        """).fetchall()
        orphan_records = unit.raw.execute("""SELECT count(*) FROM records r WHERE NOT EXISTS
            (SELECT 1 FROM catalog_symbols c WHERE c.elf=r.elf AND c.mangled=r.mangled
             AND c.kind='STT_FUNC')""").fetchone()[0]
    finally:
        unit.close()
    if orphan_records:
        raise ValueError(f'{orphan_records} admitted records have no catalog function')
    return (rows, vendor_rows, provenance, scope_rows) if include_scopes else (rows, vendor_rows, provenance)


def aggregate(rows, vendor_rows, scopes=None):
    c = sqlite3.connect(':memory:')
    c.row_factory = sqlite3.Row
    try:
        c.executescript('''
            CREATE TABLE catalog(elf,role,firmware,mangled,address,size,policy,status);
            CREATE TABLE providers(elf,mangled,address,library,
                                   PRIMARY KEY(elf,mangled,address));
        ''')
        c.executemany('INSERT INTO catalog VALUES(?,?,?,?,?,?,?,?)', rows)
        c.executemany('INSERT INTO providers VALUES(?,?,?,?)', vendor_rows)
        c.executescript('''
            CREATE TEMP TABLE classified AS
            SELECT c.*, CASE WHEN c.policy IN ('core-deferred','core-source-provided')
                        THEN 'Core' ELSE coalesce(p.library,'application') END AS library
            FROM catalog c LEFT JOIN providers p
              ON p.elf=c.elf AND p.mangled=c.mangled AND p.address=c.address;
        ''')
        if c.execute("SELECT count(*) FROM classified WHERE status IS NOT NULL "
                     "AND status NOT IN ('ready','pending')").fetchone()[0]:
            raise ValueError('Unknown readiness status')
        conflicts = c.execute('''SELECT elf,mangled FROM classified GROUP BY elf,mangled
            HAVING count(DISTINCT library)>1 OR count(DISTINCT role)>1
                OR count(DISTINCT firmware)>1''').fetchall()
        if conflicts:
            raise ValueError(f'Conflicting catalog identity metadata: {list(map(tuple, conflicts))}')
        c.executescript('''
            CREATE TEMP TABLE identities AS
            SELECT elf,role,firmware,mangled,library,status,min(size) AS size
            FROM classified GROUP BY elf,mangled;
        ''')
        if c.execute("SELECT count(*) FROM identities WHERE library!='application' "
                     "AND status IS NOT NULL").fetchone()[0]:
            raise ValueError('Library and admitted reconstruction overlap; cannot subtract twice')
        # A same-name app/library collision cannot silently be called one function.
        conflicts = c.execute('''SELECT mangled FROM identities GROUP BY mangled
            HAVING count(DISTINCT library)>1''').fetchall()
        if conflicts:
            raise ValueError(f'Exact-name library conflicts: {[r[0] for r in conflicts]}')

        def count(where='', params=(), unique=False):
            group = 'mangled' if unique else 'elf,mangled'
            sql = f'''WITH units AS (
                SELECT library, min(status='ready') AS ready,
                       min(CASE WHEN status IN ('ready','pending') THEN 1 ELSE 0 END) AS admitted,
                       max(CASE WHEN status IN ('ready','pending') THEN 1 ELSE 0 END) AS any_admitted
                FROM identities {where} GROUP BY {group}
            ) SELECT count(*) AS total,
                coalesce(sum(library='application' AND admitted=1 AND ready=1),0) AS ready,
                coalesce(sum(library='application' AND admitted=1 AND ready=0),0) AS pending,
                coalesce(sum(library='application' AND admitted=1),0) AS reconstructed,
                coalesce(sum(library='Core'),0) AS core,
                coalesce(sum(library='libpng'),0) AS libpng,
                coalesce(sum(library='zlib'),0) AS zlib,
                coalesce(sum(library='application' AND admitted=0),0) AS remaining,
                coalesce(sum(library='application' AND admitted=0 AND any_admitted=1),0) AS partial
                FROM units'''
            result = dict(c.execute(sql, params).fetchone())
            assert result['total'] == sum(result[k] for k in
                ('reconstructed', 'core', 'libpng', 'zlib', 'remaining'))
            assert result['ready'] + result['pending'] == result['reconstructed']
            return result

        binaries = [dict(r) for r in c.execute(
            'SELECT DISTINCT elf,role,firmware FROM identities ORDER BY role,elf')]
        c.execute('''CREATE TEMP TABLE membership AS
            SELECT mangled,count(DISTINCT elf) AS binaries
            FROM identities GROUP BY mangled''')
        exclusive = [dict(b, firmware=b['firmware'] + ' (только в этом бинаре)',
                          **count('WHERE elf=? AND mangled IN '
                                  '(SELECT mangled FROM membership WHERE binaries=1)',
                                  (b['elf'],), True)) for b in binaries]
        common = dict(firmware='Общие символы', **count(
            'WHERE mangled IN (SELECT mangled FROM membership WHERE binaries>1)', unique=True))
        union = dict(firmware='Итого уникальных имён', **count(unique=True))
        for field in ('total','ready','pending','reconstructed','core','libpng','zlib','remaining','partial'):
            assert sum(r[field] for r in exclusive + [common]) == union[field]
        result = {
            'elf_symbols': [{**b, **count('WHERE elf=?', (b['elf'],))} for b in binaries]
                           + [{'firmware': 'Итого (сумма бинарей)', **count()}],
            'unique_names': exclusive + [common, union],
            'catalog_function_rows': len(rows),
            'zero_size_identities': c.execute('SELECT count(*) FROM identities WHERE size=0').fetchone()[0],
        }
        if scopes is not None:
            c.execute('CREATE TABLE scope_members(scope TEXT, mangled TEXT, PRIMARY KEY(scope,mangled))')
            c.executemany('INSERT INTO scope_members VALUES(?,?)',
                          ((scope,name) for name,paths in scopes.items() for scope in paths))
            c.execute('CREATE INDEX identity_name ON identities(mangled)')
            trees = []
            selections = [(b['firmware'], 'elf=? AND ', (b['elf'],), False) for b in binaries]
            selections += [(b['firmware']+' (только в этом бинаре)',
                            'elf=? AND mangled IN (SELECT mangled FROM membership WHERE binaries=1) AND ',
                            (b['elf'],), True) for b in binaries]
            selections += [('Общие символы',
                            'mangled IN (SELECT mangled FROM membership WHERE binaries>1) AND ', (), True),
                           ('Итого уникальных имён', '', (), True)]
            roots = {paths[0] for paths in scopes.values()}
            if set(scopes) != {r[0] for r in c.execute('SELECT DISTINCT mangled FROM identities')}:
                raise ValueError('Scope coverage differs from catalog identities')
            for title, prefix, params, unique in selections:
                entries = []
                for (scope,) in c.execute('SELECT DISTINCT scope FROM scope_members ORDER BY scope').fetchall():
                    values = count('WHERE '+prefix+'mangled IN '
                                   '(SELECT mangled FROM scope_members WHERE scope=?)',
                                   (*params,scope), unique)
                    if values['total']:
                        entries.append(dict(scope=scope, **values))
                expected = count('WHERE '+prefix.removesuffix(' AND ') if prefix else '', params, unique)
                for field in ('total','ready','pending','core','libpng','zlib','remaining','partial'):
                    if sum(r[field] for r in entries if r['scope'] in roots) != expected[field]:
                        raise ValueError('Scope roots do not partition the canonical statistics')
                trees.append(dict(title=title, rows=entries))
            result['scope_trees'] = trees
        return result
    finally:
        c.close()


def markdown(report):
    lines = []
    for key, title in [('elf_symbols', 'ELF-символы функций'),
                       ('unique_names', 'Непересекающиеся группы исходных mangled-имён')]:
        lines += [f'## {title}', '',
                  '| Бинарь | Всего | Готовы | Объявления уточняются | Восстановлено | Core | libpng | zlib | Осталось без библиотек | Из них частично |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for r in report[key]:
            values = [r['firmware']] + [str(r[k]) for k in ('total','ready','pending',
                'reconstructed','core','libpng','zlib','remaining','partial')]
            lines.append('| ' + ' | '.join(values) + ' |')
        lines.append('')
    lines += ['Уникальность — точное исходное mangled-имя, не эквивалентность реализаций. '
              'ABI-варианты и разные имена алиасов не склеиваются. В объединении имя '
              'восстановлено только при принятии всех его ELF-идентичностей; частично '
              'принятые входят в остаток. Строки второй таблицы разделены на имена '
              'только одного бинаря и общие имена; каждое имя входит ровно в одну группу.', '',
              'Core — все записи библиотечной политики, включая ещё не связанные с '
              'upstream интерфейсы. Другие не классифицированные библиотеки остаются '
              'в остатке. Нулевые размеры включены. Это учёт статусов, не новая проверка доказательств.']
    if 'declaration_statuses' in report:
        lines += ['', '## Причины незавершённых объявлений (SQLite)', '',
                  '| Статус | ELF-идентичностей | Уникальных имён с этой отметкой |',
                  '|---|---:|---:|']
        for row in report['declaration_statuses']:
            lines.append(f"| {row['declaration_status']} | {row['identities']} | {row['names']} |")
        lines += ['', 'Это детализация pending, не дополнительный объём. Одно имя может иметь разные отметки в разных ELF. return_type_unresolved означает недостаток доступных доказательств исходного возвращаемого типа; прочие ограничения сохраняются.']
    return '\n'.join(lines) + '\n'


def build_report(database):
    rows, vendors, provenance = load_facts(database)
    result = aggregate(rows, vendors)
    from declaration_status import summary
    result['declaration_statuses'] = summary(database)
    result.update(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  registry=str(database), provider_provenance=provenance,
                  freshness_checked=False,
                  unique_key='exact original mangled name; all ELF identities required')
    return result


def update_symbols_document(document, report):
    start, end = '## Coverage\n', '## Partial portable C++ evidence\n'
    if document.count(start) != 1 or document.count(end) != 1:
        raise ValueError('Expected one bounded SYMBOLS.md coverage section')
    left, rest = document.split(start, 1)
    _, right = rest.split(end, 1)
    section = (start + '\n<!-- Generated by tools/recovery/symbol_statistics.py; SQLite is authoritative. -->\n'
               'Current counts come exclusively from the operational SQLite registry. '
               'Markdown and coverage JSON are derived reports, not live state.\n\n'
               + markdown(report).replace('## ', '### ')
               + '\nDetailed original-range evidence: [CS18AI functions](tracking/client-functions.md), '
               '[RM/RML functions](tracking/server-functions.md), '
               '[CS18AI data](tracking/client-data.md), [RM/RML data](tracking/server-data.md).\n\n')
    return left + section + end + right


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    imp = commands.add_parser('import-providers')
    imp.add_argument('--manifest', type=Path, required=True)
    imp.add_argument('--sha256', required=True)
    imp.add_argument('--registry-db', type=Path)
    report = commands.add_parser('report')
    report.add_argument('--registry-db', type=Path)
    report.add_argument('--json-out', type=Path)
    report.add_argument('--update-symbols', type=Path, nargs='?',
                        const=ROOT / 'uc-library/SYMBOLS.md',
                        help='Update only the generated coverage section of SYMBOLS.md')
    args = parser.parse_args()
    database = resolve_db(ROOT / 'uc-library', args.registry_db)
    if args.command == 'import-providers':
        print(json.dumps(import_providers(args.manifest, args.sha256, database), indent=2))
        return
    result = build_report(database)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with args.json_out.open('x') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            f.write('\n')
    if args.update_symbols:
        previous = args.update_symbols.read_text()
        updated = update_symbols_document(previous, result)
        if previous != updated:
            args.update_symbols.write_text(updated)
    print(markdown(result))


if __name__ == '__main__':
    main()
