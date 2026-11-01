# Монитор публикации

На VM101 установлен user timer `opencs-publication-monitor.timer`, каждые пять
минут. User lingering включён: проверки продолжаются после закрытия чата/SSH.
Service запускает только `monitor_publication.py`: читает `/proc`, pending SQLite
journal и endpoint config; после cutover проверяет TCP reachability, не подменяя
это проверкой Cypher. Не запускает, не останавливает и не повторяет producers,
не пересчитывает граф и не создаёт сабагентов.

Состояние: `evidence/recovery/2026-10-31/dependency-graph/publication-monitor/status.json`.
Читаемая версия: `STATUS.md` рядом; meaningful changes дописываются в `events.jsonl`.
Автоматической доставки в чат нет: native Codex automation tool в сессии отсутствует.

```sh
systemctl --user list-timers opencs-publication-monitor.timer
systemctl --user status opencs-publication-monitor.service
journalctl --user -u opencs-publication-monitor.service
```

Адрес всех текущих source/native операторов задаётся в
`dependency-graph/state/memgraph-endpoint.json`. `status=migration_pending` блокирует
публикацию/подготовку ещё до получения work claim. После проверки восстановленной
PVE-копии Root ставит `status=ready` и verified Bolt URI. Старые baseline benchmark
scripts с явным --host сохраняют историческую конфигурацию.
