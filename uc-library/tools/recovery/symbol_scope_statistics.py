"""Recursive scope views of the same canonical SQLite function statistics.

Scope syntax does not establish whether a component is a namespace or a class.
Unknown demangling is kept in an explicit bucket, never silently dropped.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path

from symbol_statistics import ROOT, resolve_db, load_facts, aggregate

GLOBAL = '[global / C]'
UNKNOWN = '[unresolved scope]'


def scope_parts(demangled, mangled):
    if not demangled or (demangled == mangled and mangled.startswith('_Z')):
        return (UNKNOWN,)
    # Identify top-level separators, ignoring parameters and template arguments.
    # Return types precede the qualified function name in some demangler output.
    text = demangled
    for prefix in ('non-virtual thunk to ', 'virtual thunk to ', 'covariant return thunk to '):
        if text.startswith(prefix):
            text = text[len(prefix):]
    text = text.replace('(anonymous namespace)', '{anonymous namespace}')
    angle = 0
    separators = []
    start = 0
    i = 0
    while i < len(text):
        ch = text[i]
        # Once the terminal operator name begins, its type/signature is not scope.
        if angle == 0 and text.startswith('operator', i):
            break
        if ch == '<':
            angle += 1
        elif ch == '>':
            angle -= 1
            if angle < 0:
                return (UNKNOWN,)
        elif angle == 0:
            if ch == '(':
                break
            if text.startswith('::', i):
                separators.append(i)
                i += 1
            elif ch.isspace() and not text[max(0,i-10):i].endswith('{anonymous'):
                # A top-level return type has ended; discard its qualifications.
                start = i + 1
                separators = []
        i += 1
    if angle:
        return (UNKNOWN,)
    if not separators:
        return (GLOBAL,) if not mangled.startswith('_ZN') else (UNKNOWN,)
    parts = []
    for end in separators:
        part = text[start:end].strip().replace('{anonymous namespace}', '(anonymous namespace)')
        if not part:
            return (UNKNOWN,)
        parts.append(part)
        start = end + 2
    return tuple(parts)


def memberships(scope_rows):
    paths = defaultdict(set)
    for name, demangled in scope_rows:
        paths[name].add(scope_parts(demangled, name))
    result = {}
    for name, candidates in paths.items():
        parts = next(iter(candidates)) if len(candidates) == 1 else (UNKNOWN,)
        # Tuple parts avoid splitting the :: inside template argument types.
        result[name] = ['::'.join(parts[:i]) for i in range(1, len(parts)+1)]
    return result


def markdown(report):
    lines = ['# Статистика функций по областям имён', '',
             'SQLite; те же статусы и библиотечная классификация, что в symbol_statistics.py.',
             'Родитель включает всех потомков: строки разных уровней нельзя суммировать.',
             'Компоненты C++ scope не размечены как namespace/class без отдельного доказательства.',
             'Уникальность — исходное mangled-имя; для общих имён учитываются все ELF.',
             'Глобальные C-функции и неразобранные имена показаны отдельно.', '']
    for tree in report['scope_trees']:
        lines += ['## '+tree['title'], '',
                  '| Scope (включая вложенные) | Всего | Готово | Уточнить объявления | Core | libpng | zlib | Осталось | Частично |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for row in tree['rows']:
            name = row['scope'].replace('|', r'\|').replace('<','&lt;').replace('>','&gt;')
            lines.append('| '+name+' | '+' | '.join(str(row[k]) for k in
                ('total','ready','pending','core','libpng','zlib','remaining','partial'))+' |')
        lines.append('')
    return '\n'.join(lines)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry-db', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    database = resolve_db(ROOT/'uc-library', args.registry_db)
    rows,vendors,provenance,names = load_facts(database, include_scopes=True)
    scopes = memberships(names)
    report = aggregate(rows,vendors,scopes)
    report.update(registry=str(database), provider_provenance=provenance,
                  scope_semantics='Recursive lexical C++ scope; namespace/class kind unresolved')
    args.output_dir.mkdir(parents=True,exist_ok=True)
    for name,body in (('scopes.json',json.dumps(report,indent=2,ensure_ascii=False)+'\n'),
                      ('scopes.md',markdown(report))):
        with (args.output_dir/name).open('x') as stream:
            stream.write(body)
    print(json.dumps({'output':str(args.output_dir),'trees':[
        {'title':tree['title'],'rows':len(tree['rows'])} for tree in report['scope_trees']]}))


if __name__ == '__main__':
    main()
