# Batch context prepare/dispatch: результат

Реализованы `batch-prepare`, ограниченные параллельные builders, общая batch validation и атомарная публикация dispatch. Readiness-схема и admission не менялись. Новая firmware-реконструкция не запускалась.

## Условие начала

До изменения инфраструктуры проверены завершение trial07, процессы и evidence. Все 100 claims фактически имели состояние completed в активном derived SQLite. Приёмка, Linux integration и guarded admission предыдущей партии завершены. Проверка сохранена в `start-condition.json`.

## Изменения

- EX setup фиксирует задачи, актуальное поколение, claims, инструменты и инструкции; builders держат собственные SH locks и отдельные output-каталоги.
- Persistent runner/analysis containers используют pinned image IDs и независимые, hash-verified source/native snapshots. Пинованный read-only receipt позволяет stat fastpath только для actual copied inode (`samefile`, nlink1, matching digest/fingerprint). Live-host freshness не обходится.
- Final EX barrier свежо проверяет generation, inventory, source/tool/instruction hashes, selected registry records, claims, packets и конфликты. Только complete `BATCH_DISPATCH.json` разрешает запуск. Per-packet batch membership не содержит spawn arguments.
- Grouped 10×5/10×10 и single CLI сохранены. Общая validation использует один контейнер/driver/session и scoped immutable-input verification, текущие claims проверяются заново.
- `--jobs auto` учитывает affinity/cgroup CPU, память, число задач и Memgraph cap; selection/validation и AST имеют отдельные лимиты. Неизвестные ресурсы дают один builder; memory estimates настраиваемы.
- Сохраняются handles, attempts, argv, phase timings и evidence; claims автоматически не освобождаются. Resume проверяет live containers и точные task/claim bindings.

Оператор и примеры: `dependency-graph/BATCH_CONTEXT.md`. Maintained tests находятся под `tests/`.

## Измерение

Восемь одинаковых существующих identities, два повтора каждого режима, одинаковые host resources. Последовательный baseline — контейнер на этап; это не точное воспроизведение старых CLI cgroup defaults. Все task/claim/registry stores изолированы. Production graph только читался.

Медиана total pipeline включает snapshot, environment startup, selection, slicing, finalize, validation и реальный shutdown. Исключены test-store isolation и отдельная optional telemetry. Host claim/enrich, refresh, dispatch publication и admission не входят: коэффициент не является ускорением всего операционного цикла.

| Запрошено | Фактически builders | Медиана total, с | Legacy / new |
|---|---:|---:|---:|
| legacy | 1 | 137.482 | 1.000× |
| 1 | 1 | 223.551 | 0.615× |
| 4 | 3 | 112.580 | 1.221× |
| 8 | 3 | 112.003 | 1.227× |
| auto | 3 | 110.602 | 1.243× |

`auto`: **1.243× total**, на 19.55% меньше wall time; kernel без snapshot/shutdown — 1.556×. Raw auto 110.279/110.925с; legacy 137.430/137.533с. VM affinity позволяет 3 CPUs, поэтому запрошенные 4/8 тоже ограничены 3 builders.

Все 80 пакетов прошли обязательную полную content/artifact equivalence; 340 команд — без required failures и без optional telemetry failures. Нормализация ограничена run-local путями, точными claim fields и явно неупорядоченными `unknowns`, `inclusion_reasons`, `slice_translation_units` с сохранением кратности; в Markdown — только rendered Unknowns JSON. Тела, identities, hashes, значения и порядок остальных списков сохранены.

На двух заданиях total вырос 33.778→55.846 с; snapshot стоит примерно 20 с. Новый serial `jobs 1` также медленнее. Практическая рекомендация: `--jobs auto` для измеренного batch workload; одиночный путь остаётся полезен для малых объёмов. Нельзя экстраполировать8-task время на 100 symbols.

Финальная capacity-проверка 100 заданий: 337 mounts; максимум 102718 bytes в shell argument против 131072. Это проверка конкретного100-task набора/путей, не универсальная оценка любых packet sizes.

Cold означает новый Python process/container. OS/server caches не сбрасывались; raw first/repeat значения приведены отдельно. Два повтора не задают статистическое распределение. Docker CPU/memory samples могут пропускать пики; host snapshot-copy CPU и remote graph CPU не измерены. `SHOW STORAGE INFO` start/end memory/storage и query counts/time сохранены.

## Проверки и invariance

- 81 maintained infrastructure tests, включая реальные Docker snapshot/lock/import tests и негативные receipt checks.
- 73 существующих graph identity/hash/freshness/nonempty/conflict tests.
- 367 Linux CTest, все успешно; production C++/headers не изменялись. Formatter execution для них N/A; обнаружен clang-format 23.1.3.
- Production claims, append-only claim history, registry guard и все readiness records имеют те же logical hashes до/после benchmark (`production-before-benchmark.json`, `production-after-benchmark.json`).
- Все frozen benchmark producer hashes соответствуют финальному исходному коду. Source archive и hashes: `SOURCES.json`, `source-snapshot/`.

Maintained dispatch readers обновлены. Дополнительный audit runtime scripts
сохранён в `DISPATCH-CONSUMER-AUDIT.json`: исторические post-PVE validators
ожидают старый per-packet файл и для нового batch fail closed; они не запускают
агентов и не переписаны как новые producers. Historical group acceptors читают
общий `packet_manifests` seal.

## История ошибок и ограничения

Сохранены failed smoke runs: duplicate benchmark mount, исправленный actual runpy sibling-import failure, comparator-only set-order differences. До изменения producers сохранены их точные bytes/hashes; retrospective comparisons отмечены отдельно и не превращают старый failed runner в новый successful execution.

Первый refresh выполнил compiler observations, но publisher invocation имел лишний interpreter token. Producer guard затем корректно заблокировал изменённый coordinator. Продолжение использовало точный captured producer snapshot в read-only overlay под EX lock; original plan не переписывался, compiler replay не повторялся. Все попытки и argv сохранены в root evidence и исходном refresh output. Refresh не оптимизировался и не входит в speedup.

Остаются: per-packet selection reconnect, отсутствие AST cache, фиксированная snapshot стоимость и manual inspection для malformed/partial selection. Cooperative filesystem guard не является защитой от hostile privileged writer. Source context и эти проверки не доказывают original binary behavior, ARM ABI, symbol readiness или hardware interoperability.

## Evidence

- `VALIDATION.json`, `HANDOFF.json`, `SOURCES.json`: top-level evidence.
- `benchmark/full-8x2/full/PERFORMANCE-SUMMARY.json`: матрица timings/resources и границы.
- `benchmark/full-8x2/COMMAND-AUDIT.json`, `MANIFEST.json`: команды/hashes.
- Raw complete output: `temp/recovery-work/context-benchmark-full-1793636324568919849/`.
- Многогигабайтные immutable snapshots оставлены на исходных local temp paths; evidence manifest связывает их exact hashes.

Git commit/push не выполнялись. Firmware flashing, erase, hardware tests и Mac synchronization не выполнялись.
