"""Publish bounded case results, readable queries and a compact agent packet."""
import hashlib
import inspect
import json
import pathlib
import sqlite3

from full_queries import QUERIES, graph_closure, sql_closure

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT/'dependency-graph'
RUN = BASE/'runs/full-01'
CORE = BASE/'runs/core-source-01'


def sha(path):
    return hashlib.file_digest(path.open('rb'),'sha256').hexdigest()


def main():
    assert not (BASE/'FULL_REPORT.md').exists()
    checks = {b:json.loads((RUN/(b+'-full-check.json')).read_text()) for b in ('neo4j','memgraph')}
    assert checks['neo4j']['identity_set_sha256']==checks['memgraph']['identity_set_sha256']
    for b in checks:
        assert json.loads((CORE/(b+'-full-load.json')).read_text())['exact_counts_match']
    proof = checks['neo4j']
    stats = json.loads((CORE/'full-graph-qualified.json').read_text())
    times = json.loads((RUN/'full-query-timings.json').read_text())['results']
    excerpts = json.loads((RUN/'case-source-excerpts.json').read_text())['functions']
    registry = sqlite3.connect((BASE/'runs/baseline-01/registry-snapshot.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
    original = [json.loads(r[0]) for r in registry.execute('SELECT metadata FROM records WHERE mangled IN (?,?)',
                ('_ZNK8Presonus5Panel16ControlRegistrar5countEv','_ZNK8Presonus5Panel16ControlRegistrar2atEi'))]
    grouped = {}
    for label in proof['required_source_files']:
        grouped.setdefault(sha(ROOT/label),[]).append(label)
    reading = []
    aliases = {}
    for digest,paths in grouped.items():
        path = next((p for p in paths if p.startswith('third_party/')),paths[0])
        reading.append(path)
        aliases[path] = {'sha256':digest,'observed_paths':paths}
    packet = ['# Context for the two ControlRegistrar getters','',
              'Current source-port reconstruction; original return declarations remain unresolved.',
              'Do not reconstruct Core: use the pinned official CCL implementation.','',
              '## Existing implementations: five functions, 24 source lines','']
    for name,item in excerpts.items():
        packet += ['### '+name,'',f"`{item['path']}:{item['first_line']}`",'',
                   '```cpp',item['excerpt'].rstrip(),'```','']
    packet += ['## State, caller and source context','',*['- `'+p+'`' for p in sorted(reading)],'',
               '## Test and explicit fixture','',*['- `'+p+'`' for p in proof['selected_tests']],
               *['- `'+p.removeprefix('file:')+'`' for p in proof['fixture_ids']],
               '', '## Original identities and dedicated behavior proof','']
    for item in original:
        packet += ['- `'+item['original_elf_sha256']+'` / `'+item['mangled']+'`; '+
                   item['firmware_version']+'; address '+str(item['original_address'])+
                   '; size '+str(item['original_size'])+'.']
    behavior = sorted({item['behavior_validation'] for item in original})
    packet += ['',*['- `uc-library/'+p+'`' for p in behavior], '',
               'Merged fragments remain provenance; resolve the four original keys rather than reading all 464 records.',
               'Scope: indexed current source/configurations. Runtime pointer aliasing and unreconstructed firmware callers are not proven complete.']
    (RUN/'agent-context.md').write_text('\n'.join(packet)+'\n')
    (RUN/'agent-context.json').write_text(json.dumps({'source_aliases':aliases,'original_records':original,
          'call_functions':proof['call_closure_functions'],'context_nodes':proof['context_nodes'],
          'source_files':sorted(reading),'fixtures':proof['fixture_ids'],
          'unresolved':proof['unresolved_in_target_context']},indent=2)+'\n')
    catalog = {name:{'question':q.question,'sql':q.sql,'cypher':q.cypher,
                     'sql_joins':q.sql.upper().count(' JOIN ')} for name,q in QUERIES.items()}
    (RUN/'query-catalog.json').write_text(json.dumps({'queries':catalog,
         'sqlite_recursive_helper':inspect.getsource(sql_closure),
         'portable_graph_recursive_helper':inspect.getsource(graph_closure)},indent=2)+'\n')
    table = ['| Вопрос / метод | SQLite, ms | Neo4j, ms | Memgraph, ms |',
             '| --- | ---: | ---: | ---: |']
    for row in times:
        method = 'count' if '5countEv' in row['seed'] else 'at'
        table.append('| '+row['query']+' / '+method+' | '+' | '.join(
            f"{row['median_ms'][b]:.3f}" for b in ('sqlite','neo4j','memgraph'))+' |')
    report = '''# Полный доступный source/build graph: результат

Во все три БД загружен один полный корпус выбранной Linux-конфигурации:

- **551 185 узлов, 6 651 932 ребра**; счётчики каждого типа совпали.
- **625 TU**: 574 app/test и 51 реальной source-сборки CCL.
- **51 137 original catalog anchors**, включая разные адреса/диапазоны одинаковых
  имён; 119 групп ELF+name имеют несколько anchors. Они не схлопнуты.
- 322 CTest-команды, их явные file arguments, code/type/data references,
  compiler aliases и validation links. Original ready/pending registry не менялся.

Это весь извлечённый корпус доступной активной сборки, а не искусственная выборка.
Это **не полный runtime-граф всех функций исходной прошивки**. Каталог
невосстановленных symbols не содержит автоматически восстановленных вызовов.
Отсутствие source mapping означает неизвестность, не независимость.

GCC source replay прошёл для всех625 TU. Clang: 623 clean + 2 явно отмеченных
recovery AST для GCC-валидной singleton specialization. CCL извлечён из pinned
официального source; Core binary decompilation не применялась. Косвенные и
виртуальные dispatch boundaries сохранены отдельно. Pointer/alias analysis не
выполнялся. Native GCC graph дополнительно покрывает implicit ctor/dtor calls,
которые нельзя считать полными по одним явным CALL_EXPR.

## Последний кейс: достаточны ли 15 записей

**15 — не полный пакет контекста.** Это production-TU impact заголовка:
12 app-методов / 15 per-ELF записей. Для двух выбранных getter-ов проверен другой
вопрос: непосредственные вызовы, их замыкание, типы/данные, вызывающий код и fixture.

| Необходимая часть | Результат |
| --- | ---: |
| Целевые методы / original records | 2 / 4 |
| Прямые связи вызовов из них | 4 |
| Уникальные вызываемые CCL methods | 3 |
| Функции в исходящем замыкании, включая цели | **5** |
| Типы / элементы данных в reading context | **6 / 6** |
| Всего узлов call/type/data context | **17** |
| Прямой caller и все обнаруженные ссылки на цели | **один test main** |
| Связанный тест / fixture | **1 / 1** |
| Source paths / уникальные по bytes source files | **7 / 6** |
| Неразрешённые calls в выбранном контексте | **0** |

17 узлов — функции, типы и данные, а не 17 записей firmware registry; сравнивать их
с 464 per-ELF записями как одну метрику нельзя. Дополнительных app-callees за
пределами прежних15 не найдено, но были нужны Core vector source, state adapter,
ControlGroup declaration, test source и fixture. Adapter уже был в старом
read-on-demand, поэтому не все эти paths являются вновь обнаруженными.

Clang и GCC независимо дали одинаковые четыре target call edges. Проверка всех
574 готовых app/test объектов через nm обнаружила references только из
panel_registrar_access_tests.cpp; расширенный source/compiler graph всех625 TU
не добавил другого caller/address reference. SQLite, Neo4j и Memgraph вернули
одинаковые точные IDs для всех проверенных запросов. Существующий Linux CTest
panel_registrar_access прошёл на2048 fixture cases.

```mermaid
flowchart LR
  T[panel_registrar_access test] --> C[ControlRegistrar::count]
  T --> A[ControlRegistrar::at]
  C --> VC[Core::ConstVector::count]
  A --> VC
  A --> VA[Core::ConstVector::at]
  A --> E[Core::ConstVector::getError]
```

Новый handoff: `runs/full-01/agent-context.md`. Пять нужных function bodies дают
**24 строки существующего source**, с полными original identities, ссылками на
state/caller/fixture и dedicated behavior proof. Это начальный пакет для чтения,
не разрешение убрать validation gates и не измеренное ускорение полного цикла.

## Скорость: короткий справочный замер

Три чередующихся повтора, медианы; Bolt roundtrips включены, disk-cold/high-load
не заявляются. Все результаты совпали. Миллисекунды не определяют выбор.

'''+ '\n'.join(table)+'''

## Сложность запросов и поддержки

| Задача | SQLite | Neo4j / Memgraph |
| --- | --- | --- |
| Callees, callers, references, source files | Простой SELECT по typed edges | Простой typed path; читается непосредственно |
| Test → TU → caller → target | Три alias таблицы edges, два JOIN | Три явные связи в Cypher; понятнее для исследования |
| Рекурсивный обход с циклами | Один recursive CTE с UNION | Переносимый node-global BFS в Python + batched Cypher шаг |
| Новая code relation | Обновить общую policy tuple и тест | Та же policy, Cypher строится тем же factory |
| Индексы/constraints | Уже используем SQLite, нет второго сервиса | У Memgraph constraint требует отдельного индекса; init различается |
| Версии/импорт/свежесть | Один файл-проекция и существующий registry | Docker service + projection/import state, version/digest и parity checks |

**Cypher не всегда уменьшает весь поддерживаемый код:** безопасная переносимая
рекурсия здесь использует дополнительный BFS helper. Перечисление всех путей
не подменяет reachability. Native APOC/BFS может сократить запрос, но добавит
backend-specific код и тесты. Он в этих измерениях не использовался.

Весь рабочий query catalog находится в `full_queries.py` и
`runs/full-01/query-catalog.json`, включая оба recursive helpers. На этих вопросах
Cypher для Neo4j и Memgraph **одинаковый**. Доказанного различия стоимости
поддержки запросов между ними пока нет.

Практический выбор: SQLite проще эксплуатировать рядом с действующим реестром;
Cypher удобнее для новых исследовательских multi-hop вопросов. При текущей
скорости выбирать по latency оснований нет. Главная стоимость поддержки —
корректный extractor, compile-context identities, source freshness и явная
неопределённость, а не синтаксис СУБД.

Не следует пересобирать весь корпус на каждую маленькую задачу. Эксперимент
сохраняет его как индекс. Дизайн incremental refresh/active generations остаётся
следующим отдельным решением; production schema/process и admission не изменены.
'''
    (BASE/'FULL_REPORT.md').write_text(report)
    schema = '''# Full graph data contract

Current source/compiler observations are separate from original ELF identities.
Source Function/Type/Data declarations describe the current port and pinned CCL,
not original firmware layout/return types or ARM ABI compatibility.

## Nodes

'''
    schema += '| Kind | Count |\n| --- | ---: |\n'+'\n'.join(
        f'| {k} | {v} |' for k,v in stats['node_kinds'].items())
    schema += '''

`CatalogSymbol` is keyed by the original catalog anchor: duplicate ELF/name ranges
remain separate. `symbol` is the original readiness key ELF SHA+mangled name.
`Function` includes source methods, template specializations and compiler ABI
variants; its count is not a count of independent algorithms. Local compiler
IDs have build-group scope; test main/definitions are qualified by source TU.
`TranslationUnit` carries the exact compile command/configuration. File roles
are also expressed by relations; one path can be both source and test input.

## Relations

'''
    schema += '| Kind | Count |\n| --- | ---: |\n'+'\n'.join(
        f'| {k} | {v} |' for k,v in stats['edge_kinds'].items())
    schema += '''

CALLS = source-resolved call; GCC_CALLS = compiler pre-optimization call.
ALIAS_OF retains compiler variants. VIRTUAL_CALL/INDIRECT_CALL/GCC_UNRESOLVED
retain uncertainty; OVERRIDES gives candidates, not proven runtime receivers.
USES_DATA/GCC_REFERENCES do not claim complete memory alias or write analysis.
USES_TYPE/HAS_TYPE/MEMBER_OF/INHERITS retain source declarations.
FUNCTION_REFERENCE includes address/other source references, not only execution.
CREATES_LAMBDA does not assert invocation. DECLARED_IN/IMPLEMENTED_IN locate source.
HAS_TEST_TU/RUNS/USES_FIXTURE come from explicit CMake/CTest evidence.
ENCODED_NAME_MATCH/CATALOG_CANDIDATE are identity candidates, not ABI proof.
proof_binding/validation_binding/VALIDATED_BY are provenance, not code ownership.

Query seed resolution must distinguish an indexed Function from a catalog-only
symbol. An unmapped original symbol must be reported unknown rather than treated
as an independent leaf. Current case checker explicitly verifies its source seeds.

Reading-context policy is explicitly in full_queries.py. It does not silently
cross all whole-archive/proof bindings or solve runtime pointer aliasing. Preserve
unknown boundaries and escalate instead of presenting this as full firmware
semantic independence. Both graph services preserve the same input CSV hashes;
type counts and queried exact-ID sets were checked against SQLite.
'''
    (BASE/'FULL_SCHEMA.md').write_text(schema)
    print(json.dumps({'nodes':sum(stats['node_kinds'].values()),'edges':sum(stats['edge_kinds'].values()),
                      'source_files_unique':len(reading),'source_excerpt_lines':24,
                      'report':str(BASE/'FULL_REPORT.md')}))


if __name__=='__main__':main()
