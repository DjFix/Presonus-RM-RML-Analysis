# Боевой тест через граф: 10 одновременных сабагентов × 5 символов

Инструкция новому координатору. Пользователь разрешил один следующий тест в новом
чате, его подготовку, необходимую поддержку группового dispatch, реконструкцию,
приёмку, глобальную интеграцию и guarded admission. Повторного подтверждения не
нужно. После одной партии остановиться. Сейчас запускать ничего не требуется.

## Место и исходное состояние

Работай в `/home/rs/projects/opencs/ai-line-analysis` на VM101. Сначала прочитай
`AGENTS.md`, `docs/worker-handoff.md`, `dependency-graph/CONTEXT_SELECTION.md`
и `dependency-graph/DEDUPLICATION.md`. Сохрани все действующие validation gates.

VM101 обновлена, её основной диск перенесён пользователем на SSD/local-zfs.
Memgraph — отдельный PVE LXC125: `bolt://192.168.50.190:7687`,
Lab `http://192.168.50.190:3000/`. SQLite канонический для original identity,
readiness и proof links; Memgraph производный индекс. MySQL здесь нет.

Предыдущий тест:
`evidence/recovery/2026-11-01/dependency-graph/live-trial-03/REPORT.md`,
рядом `metrics.json`, `SEAL.json`, `snapshot/`.
Два новых простых метода, 7173 ARM-кейса, 326/326 CTest; ready1052/pending1057.
Обе unique-work claims завершены. Было0 broad dependency scans и0 запросов
недостающего кода; два административных запроса о tool environment.
Результат compiled-pending, оригинальные return/layout не установлены.

После партии исходники и CMake изменились. Новые пакеты должны пройти штатный
refresh; предыдущие пакеты нельзя использовать для нового dispatch.
Проверь актуальное состояние, не считай эти исторические цифры текущей истиной.
Не перезапускай живые jobs по observation timeout; сначала осмотри handles/claims.

## Параллелизм и состав

Нужны **10 одновременно работающих reconstruction workers**, каждому ровно
**5 исходных символов**: всего50. Координатор отдельно, всего11 агентов.
Не заменяй это3 workers, волнами или последовательным запуском десяти задач.
Не создавай цепочки вложенных агентов ради обхода runtime-лимита.

До дорогостоящей подготовки проверь доступную ёмкость среды. По официальной
справке Codex настройка пользовательского config.toml:

```toml
[agents]
max_concurrent_threads_per_session = 10
```

Она исключает primary thread; `max_threads` — legacy alias. В этом окружении
конфигурация VM101 находится в `/home/rs/.codex/config.toml`. Ссылка:
https://learn.chatgpt.com/docs/config-file/config-reference
Настройка не является доказательством фактически предоставленной ёмкости.
Если новому чату доступны меньше10 workers, явно сообщи blocker и не запускай
уменьшенную партию. Текущий старый чат объявлял всего4 concurrency slots.

Подбирай50 ещё не восстановленных original symbols с реальными зависимостями:
вызовы, данные/таблицы, состояние, provider bindings. Приоритет UC/DICE, затем
остальной Presonus. Не включай Core firmware recovery, flashing/hardware work.
Не набирай партию только getters/setters, arithmetic leaves, пустыми методами
или aliases одной реализации. Отдельно покажи число уникальных работ,
алгоритмов, aliases и covered original identities:50 символов не значит50
независимых реализаций. Не восстанавливай имеющийся canonical C++ повторно.

Пять символов worker должны образовывать связный небольшой scope с обоснованным
общим владением; между10 workers не должно быть write/read конфликтов.
Root сохраняет shared CMake/build files, registry, tracker и admission.

## Согласование группового запуска с существующим gate

Сейчас один packet покрывает один unique work item; batch-dispatch требует
уникальных task_id и проверяет зависимости. Нельзя просто положить пять
независимых работ в TASK и обойти это ограничение или склеить промпты вручную.

Сначала проверь, есть ли уже проверенный grouped dispatch для worker с несколькими
пакетами. Если нет, реализуй минимальную поддержку группы из5 sealed work packets
на одного worker с теми же exact identity, claim, snapshot, manifest и freshness
проверками. Каноническую readiness-схему не меняй. Проверка10 групп обязана до
первого worker edit проверять все50 work bindings, одинаковое поколение,
отсутствие дубликатов и межгрупповых write/read конфликтов. Внутригрупповые
зависимости выполняются одним владельцем в обоснованном порядке. Итоговый
DISPATCH должен формироваться проверенным оператором. Сохрани negative tests
на overlap, mixed generations, empty/stale context и duplicate work.

Это отдельная инфраструктурная фаза с собственными временем/токенами, входящими
в whole-cycle total. Заверши её и заморозь инфраструктуру до измеряемого запуска.
Не скрывай её стоимость внутри обычной реконструкции. Не ослабляй существующие
проверки ради требуемого числа workers. Если безопасная группировка невозможна,
сообщи конкретную причину вместо фиктивного запуска.

## Выполнение

1. С первого действия зафиксируй session ID, время и cumulative token baseline
   координатора. Проверки окружения и отбор входят в полную стоимость.
2. Проверь сервисы, live claims, readiness/unique-work и исходную ELF provenance.
   Обоснуй кандидатов конкретными call/data связями и отсутствием готового C++.
3. Подготовь все графовые пакеты и запечатай общий конфликтно проверенный batch
   до начала любых worker edits. Каждый target имеет реальное проверенное
   native/source/provider body. Не допускай empty packets/ignore-staleness.
4. Запусти10 свежих workers по5 символов из generated dispatch, `fork_turns=none`.
   Не передавай координаторскую историю или широкие proof bundles. Workers
   используют pinned CCL source для Core, без Core binary reconstruction.
5. Workers полностью выполняют native range verification, C++, независимый
   ARM/provider oracle, fixtures/replay, формат/compile/mangling и HANDOFF v1
   с явным результатом по каждому original. Источник oracle не новый C++ и
   не псевдокод. Недостающий код запрашивается через Root expand с seed/query/reason;
   для работающего задания baseline frozen generation, не текущие edited sources.
6. Root рецензирует handoffs/argv, выполняет accept_worker, затем общую Linux
   интеграцию, полный CTest, installed-role/compile-once, свежий active proof,
   guarded SQLite dry-run/admission, tracker/checkpoint и полный mirror audit.
   Не повышай readiness по aliases или наличию исходника. Неустановленные
   original declarations/layout остаются явно pending.
7. Закрой claims с evidence, сохрани resumable state и остановись после партии.
   Не выключай VM101. Не запускай следующую партию автоматически.

Используй `uc-library/.venv/bin/python`, CMake/CTest/clang-format из той же venv;
Unicorn2.1.4 был доступен там в предыдущем тесте. Актуальный успешный role auditor
предыдущей партии: `uc-library/tools/recovery/audit_role_build_basic_activity.py`.
Не используй устаревший `uc-library/tools/audit_role_build.py` без проверки его
соответствия текущим RTTI exceptions и SQLite. Не повторяй уже успешные проверки
после изменения только метаданных, если входы проверок не изменились.

## Раздельные замеры

Для Root и каждого из10 workers: фактический provider session ID, cumulative
baseline/end, input, cached input (часть input), noncached input и output;
UTC wall start/end, инструментальные durations и метод их получения.
Свежие worker counters начинаются с0. Для Root считай дельту от начала задачи.
Недоступные counters не подменяй оценкой. Не суммируй cached ещё раз с input.

Раздели этапы: окружение/отбор, инфраструктура, refresh графа, packet preparation
и dispatch, работа каждого worker/ожидание контекста, local acceptance,
общая интеграция/admission, отчётность. Покажи полный wall time и перекрытия;
сумма времен10 workers не является временем всей партии. Root tool timings
и worker tool timings сохраняй отдельно. Включи failures/retries и reporting;
обозначь точную границу последнего token snapshot и исключённый хвост.

Для каждого worker и символа запиши targets/native bodies/call/data/unresolved
relations/selected files, реально прочитанные и проверенные зависимости,
нерелевантные связи с причиной, запросы дополнительного контекста/ожидание,
широкие поиски вне пакета, пропущенные нужные зависимости и повторы проверок.
Отличай обязательные worker→acceptance→canonical validation gates от лишних
повторов неизменённых входов. Неиспользованная связь не автоматически лишняя:
раздели protective context, нерелевантное и неизвестное.

Исторические464 привязки относятся к другому кейсу: не заявляй464→N или причинное
ускорение без сопоставимого контроля на одинаковой задаче. Нужны практические
числа новой партии и явные границы вывода.

## Сохранение и ответ

Scratch только project `temp/`; evidence в новом датированном
`evidence/recovery/.../dependency-graph/` с REPORT.md, metrics.json, raw usage/tool
receipts, source/fixture/proof hashes, phase timeline, claims и resumable state.
Ничего не очищай окончательно из `.trashes/`.

Финальный ответ компактный: таблица Root +10 workers (5 symbols, wall time,
input/cached/noncached/output, outcome), общий wall time, отдельная стоимость
инфраструктуры/refresh/интеграции, число реально просмотренных связей, лишних
проверок и context requests; ссылки на полный отчёт. Сохрани текущую работу
пользователя и историческую provenance. Коммит/пуш этой будущей партии не
предполагается автоматически.
