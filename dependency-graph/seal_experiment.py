"""Preserve experiment receipts without changing readiness or operational DB."""
import hashlib
import json
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / 'dependency-graph'
RUN = BASE / 'runs/baseline-01'
OUT = ROOT / 'evidence/recovery/2026-10-31/dependency-graph/stage-01'
OUT.mkdir(parents=True, exist_ok=False)


def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


tests = subprocess.run([str(ROOT / 'uc-library/.venv/bin/python'), '-m', 'unittest',
                        'discover', '-s', str(BASE), '-v'], capture_output=True, text=True)
(OUT / 'unit-tests.log').write_text(tests.stdout + tests.stderr)
assert tests.returncode == 0
assert subprocess.run(['git', 'diff', '--check'], cwd=ROOT, capture_output=True).returncode == 0
active = json.loads((ROOT / 'uc-library/validation/registry-sqlite/ACTIVE.json').read_text())
assert sha(ROOT / active['database']['path']) == active['database']['sha256']
cases = {name: json.loads((RUN / ('case-last-cycle-' + name + '.json')).read_text())
         for name in ('neo4j', 'memgraph')}
assert cases['neo4j']['exact_original_ids'] == cases['memgraph']['exact_original_ids']
for case in cases.values():
    assert case['exact_backend_parity'] and case['new_original_records_retained'] == 4
    assert case['selected_original_records'] == 15
source_files = [p for p in BASE.iterdir() if p.is_file()]
for category, paths in [('sources', source_files),
                        ('results', [p for p in RUN.iterdir() if p.suffix in ('.json', '.md')]),
                        ('docker-operations', list((BASE / 'runs/docker-operations').iterdir()))]:
    directory = OUT / category
    directory.mkdir()
    for path in paths:
        shutil.copy2(path, directory / path.name)
inventory = {str(p.relative_to(ROOT)): {'bytes': p.stat().st_size, 'sha256': sha(p)}
             for p in sorted(RUN.iterdir()) if p.is_file()}
manifest = {'checkout_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'operational_db_unchanged': True, 'operational_db_sha256': active['database']['sha256'],
            'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in source_files},
            'artifacts': inventory, 'unit_tests_passed': True,
            'neo4j_memgraph_sqlite_last_case_parity': True,
            'production_process_or_schema_changed': False,
            'scope': 'Initial agent code-reading context; no end-to-end token/time speedup claim'}
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
timings = {k: v['median_seconds'] for k, v in cases.items()}
report = f'''# Последний кейс: размер контекста агента

Два целевых метода: `ControlRegistrar::count()` и `at(int)`.

| Показатель | Результат |
| --- | ---: |
| Исходный входящий пакет | 464 per-ELF записи |
| Привязки изменённого заголовка | 131 запись (127 прежних + 4 новые) |
| Начальный пакет через граф | **15 per-ELF записей** |
| Независимые методы в пакете | **12: 2 целевых + 10 связанных** |
| Прежние записи в пакете | 11 |
| Новые записи сохранены | 4 из 4 |
| Production CPP для чтения | 5 |
| Сокращение относительно 464 | **30.9 раза** |
| Совпадение SQLite / Neo4j / Memgraph | точные original IDs совпали |

Это сравнение размера первоначального чтения, не доказанный выигрыш полного
цикла реконструкции. 464 — измеренный входящий пакет из аудита, не измеренное
число фактически прочитанных агентом связей. Manifest-only записи сохранены в
приложении; их отсутствие в первом пакете не доказывает семантическую независимость.
Calls/types/virtual dispatch ещё не извлечены.

## Короткий замер

Пять повторов одного семантического запроса; SQLite views и одинаковый Cypher
на обоих graph engines. Медианы: SQLite 0.11–0.20 ms, Neo4j 3.04 ms,
Memgraph 1.00 ms. Bolt включает сетевой вызов. Для нашего workflow все достаточно
быстры; нагрузочных, memory и restart серий не проводили.

Полные значения: `{json.dumps(timings, sort_keys=True)}`.

## Практическое решение

Основной выигрыш дал переход от широких proof bindings к compiler dependencies
и фактическому определению символов в TU. Одинаковый Cypher с понятными
TranslationUnit / OriginalSymbol / DEFINES выполнился в Neo4j и Memgraph без
изменений. SQLite даёт тот же результат через две открытые именованные view.
По этим измерениям скорость не определяет выбор backend; важнее поддержка
реальных вопросов и отсутствие пропусков в пакете чтения.

Эксперимент в `dependency-graph/`; production SQLite, схема и admission не менялись.
Локальные Java/Neo4j зависимости перемещены в `.trashes/` с проверенными хешами;
окончательного удаления не было. Docker services и named volumes сохранены.
'''
(OUT / 'REPORT.md').write_text(report)
(BASE / 'REPORT.md').write_text(report)
print(str(OUT / 'REPORT.md'))
