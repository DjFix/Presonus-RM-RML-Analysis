# Задание: рейтинг функций, данных и инициализаторов → боевой тест 10×10

## Авторизация и результат

Работать в `/home/rs/projects/opencs/ai-line-analysis` на VM101. Пользователь
поручил разработать и внедрить рейтинг по графу, сначала проверить его на данных
проекта, затем выбрать следующую партию из самых простых допустимых узлов с
реальными зависимостями, **показать список и веса и продолжить реконструкцию без
дополнительного подтверждения**. Одна партия:10 одновременно работающих
сабагентов, по10 целевых исходных символов каждому, координатор отдельно.
После полного цикла остановиться; следующая партия не разрешена автоматически.

В этом задании «дешевле» означает меньше доказанной структурной сложности и
неопределённости, а не меньше денег, токенов или секунд. Не обучать рейтинг на
длительности/токенах; не включать их в признаки, веса и порядок отбора.
Фактические замеры цикла сохраняются независимо для оценки процесса.

Ожидаемый результат: действующий производный индекс рейтинга, объяснимый
воспроизводимый отбор, событийное обновление, проверка на реальных ELF и одна
завершённая партия. Документ — задание, не доказательство уже имеющихся полей
или возможностей операторов. Сначала прочитать их текущую реализацию.

## 1. Начальные проверки и границы

Прочитать `AGENTS.md`, `docs/worker-handoff.md`,
`dependency-graph/CONTEXT_SELECTION.md`, `dependency-graph/BATCH_CONTEXT.md`,
`dependency-graph/DEDUPLICATION.md`, `dependency-graph/NATIVE_GRAPH.md`,
`dependency-graph/SOURCE_IDENTITIES.md`, `uc-library/tools/registry/README.md`.
Проверить последние завершённые партии и infrastructure evidence; исходные
ориентиры — `evidence/recovery/2026-11-02/dependency-graph/live-trial-07-10x10/`
и `evidence/recovery/2026-11-02/dependency-graph/batch-context-01/`.
Не принимать их номера поколений и totals за актуальные без проверки.

Зафиксировать начало и provider-token baseline Root до обследования. Проверить
git changes, live agents/processes, context lock, незавершённые refresh/publication
и claims. Дождаться активных редакторов/публикаций до изменения общих producers;
не останавливать их, не освобождать claims по таймауту. Сохранить чужую работу.
Если предыдущая партия уже была начата другим координатором, не выдавать те же
работы повторно и не считать её «следующей» без проверки состояния.

SQLite остаётся каноническим registry; Memgraph — derived context graph.
Рейтинг реализовать отдельным производным слоем, без изменения canonical
readiness schema и без неявного обновления/импорта старых ready/pending JSON.
Существующие unique-work/claim, provider, freshness, nonempty и admission gates
сохранить. Core — pinned CCL source; Core binary reconstruction запрещена.
Без hardware, flashing/erase, Mac sync, выключения VM и permanent trash purge.

## 2. Единицы работ и отдельные состояния

Основной ключ рейтинга — уникальный work item, а не display name или файл.
Сохранять полный набор ELF SHA/version/role/mangled/anchor/range каждого original.
Число символов, physical ranges, implementation groups и уникальных работ
выводить отдельно. Alias не становится независимой реализацией.

Разделить work kinds и сравнивать их с учётом требуемого результата:

- `function_reconstruction`: переносимый C++ и независимая native/provider
  behavioral проверка в явном домене;
- `data_interpretation` / `data_binding`: установление представления и реальное
  использование данных восстановленным кодом;
- `initializer_reconstruction`: исполняемая инициализация, её зависимости,
  порядок и эффекты;
- `payload_extraction`, `extent_research`, `equivalence_research`,
  `provider_binding`: самостоятельные виды работ, не маскируемые под новые C++.

Извлечённый payload не означает установленный тип. Compiled-pending не означает
доказанный original interface/layout. Claim completed не означает dependency
satisfied. Признаки обеспеченности должны ссылаться на конкретное требование
потребителя и подтверждающее evidence, а не на единый флаг «готово».

## 3. Извлечение признаков функций из ELF

Переиспользовать проверенные native/dedup inputs и retained observations; не
перезапускать полный анализ без изменения его входов. Для каждого признака
хранить value, known/unknown/partial, scope, producer/version/hash и provenance.

Инструменты:

- `pyelftools`: ELF machine/flags, symbols, sections, relocations, mapping symbols,
  реальное VA→file offset, полные диапазоны и SHA; unknown extent не подменять0.
- Capstone ARM/Thumb detail: decode по подтверждённым диапазонам и mapping symbols
  `$a/$t/$d`, прямые вызовы/переходы, memory operands, literal loads, explicit
  indirect boundaries. Literal pools не считать инструкциями.
- CFG builder: basic blocks по entry/targets/terminators, conditional edges,
  back edges и SCC. Циклы и число blocks/branches считать только в заявленной
  области покрытия. Неразрешённый jump table/indirect jump делает CFG partial;
  полное декодирование байтов само по себе не доказывает полный CFG.
- Ограниченное отслеживание происхождения регистров для PC-relative адресов,
  this/state accesses и pointer flows. Сохранять основания и unknowns; один
  `[r0+offset]` не доказывает поле класса, `r0` может быть переопределён.
- `readelf`, `objdump`, `nm` — независимые сверки layout/символов. Проверить
  поддержку целевой архитектуры конкретной установленной версии инструментов.
- Unicorn — bounded native oracle при реконструкции/разборе спорного случая,
  не обязательный массовый запуск всех функций ради рейтинга. Static analysis
  не обозначать как наблюдавшееся исполнение. Декомпилятор — точечно, не новый
  обязательный whole-corpus export; pseudocode не доказательство поведения.

Признаки: byte/instruction count, CFG blocks/conditional branches/cyclic SCC,
direct callee count, unique proven data dependencies, unresolved indirect sites,
relocations, неполнота CFG/ranges, observed state reads/writes с шириной доступа,
требования к interface/layout и подтверждённый контекст класса.
Необоснованные pointer/address candidates не превращать в execution/data edges.
Повторные call sites и unique dependency count хранить раздельно.

## 4. Статические данные: признаки и реконструкция

Различать файловые `.rodata`/initial `.data`, zero-initialized `SHT_NOBITS`,
address tables (включая vtables/jump tables), strings, containers/firmware blobs.
Секция не определяет исходный C++ type/const; data pointers не execution edges.

Извлечение: проверить весь размер и ELF mapping, хранить content object один раз
по полному size+SHA, все occurrences отдельно. Никаких prefix/256-byte hashes
как доказательства полного совпадения. Overlap/aliases сохранять явно.
SHT_NOBITS не имеет file bytes и не получает фиктивный empty-content hash.
Unknown extent требует исследования; граница следующего символа — не автоматическое
доказательство. Уже извлечённые объекты не отправлять агенту извлекать повторно.

Статические признаки рейтинга:

1. Доказанность extent и наличие полных проверенных bytes/storage metadata.
2. Известность representation: opaque bytes, scalar/string, numeric array,
   structured records, address table, transformed container, unknown.
   Opaque bytes дёшевы только для raw extraction; для typed binding это unknown.
3. Доказанные width/count/alignment/endianness/encoding; неоднозначности сохранять.
4. Число pointer/relocation targets, известность их identities и binding scopes.
5. Трансформации: compressed/expanded содержимое отдельно, producer/hash/replay
   связи преобразования; неизвестный формат — блокер соответствующей работы.
6. Необходимая связь с readers/writers и unresolved interpretation requirements.

Реконструкция: независимо фиксировать `raw_verified`, `representation_verified`,
`consumer_binding_verified`, `initial_state_verified` или эквивалентные scoped
состояния. Не добавлять один универсальный data-ready флаг.

- Числовые таблицы: вывести представление из evidence; проверить полные значения
  и при необходимости сериализацию в исходные width/endianness. Выполнить
  behavioral replay потребителя, если заявляется его семантика.
- Strings: доказать encoding и границы, сохранить embedded NUL и фактическую длину;
  не считать произвольные bytes C string по наличию первого NUL.
- Pointer/vtable/jump tables: установить каждый target и slot/addend/representation;
  не переносить ARM VA в host C++ pointer. Отдельно original ABI и portable binding.
- `.data`: различать file initial image, relocations и изменяемое runtime state.
- `.bss`: проверить размеры/zero-init semantics, но не придумывать исходные поля.
- Blob/container: exact payload preservation не означает восстановление embedded
  firmware как C++, а decompression не устанавливает семантику содержимого.

Данные без original symbol могут быть обеспечивающей payload-работой, но не
выдуманным символом для выполнения квоты100.

## 5. Инициализаторы

Различать `.init` code, `.init_array`/`.preinit_array`/`.fini_array` entries,
доступные `DT_INIT`/`DT_INIT_ARRAY` metadata, constructors и compiler-generated
initialization routines. Наличие секции не доказывает полный startup порядок.
Старые форматы вроде `.ctors` учитывать, если они реально присутствуют.

Граф: initializer→called functions/providers, initializer→written objects,
table slot→target; хранить order provenance, guards, external calls, allocations,
registrations, cleanup и unresolved lifetime assumptions. Не выводить полный
межмодульный порядок из одного ELF-массива. Отсутствие relocations не означает
отсутствие адресных зависимостей в final-linked ELF.

Рейтинг: признаки функции плюс число и готовность write targets, известность
initial state, условность/повторяемость запуска, order/lifetime constraints,
callbacks/allocations и неразрешённые эффекты. Код, создаваемый данными, и initial
bytes не объединять одним completion marker. SCC initializer/object зависимостей
рассматривать как совместную работу либо явный блокер, не самоподтверждение.

Native validation офлайн: фактические ARM инструкции, начальные образы памяти,
записанные bytes, порядок и аргументы вызовов; stubs и исключения явно обозначить.
Восстановленный initializer должен replay те же наблюдения. Не запускать
целое приложение/реальный device initializer без необходимости и разрешения.

## 6. Рейтинг: воспроизводимые веса без псевдоточности

Сначала eligibility, затем lexicographic rank. Нельзя «компенсировать» отсутствие
тела или опасную неопределённость маленьким byte count/высоким fan-in.

Основные очереди: `reconstruction_eligible`, `research_required`, `provider_work`,
`claimed`, `completed`. Функция с неразрешёнными original declarations может
допускаться как bounded compiled-pending source port только при достаточном
контексте/явном uncertainty scope; это не автоматическая готовность её consumers.

Предлагаемый начальный rank vector (меньше лучше):

```text
(
  unmet_essential_requirements,
  material_uncertainty_grade,
  semantic_complexity_grade,
  context_complexity_grade,
  unique_required_dependency_count,
  -eligible_consumers_helped,
  stable_work_item_id
)
```

Eligibility и каждая grade имеют отдельные явные правила по work kind. Веса
здесь — компоненты rank vector, не время/токены/вероятность. Опубликовать policy
JSON с versions, ordered components, thresholds, units и unknown rules; thresholds
обосновать наблюдаемым распределением проекта. Unknown никогда не равно0.
Сначала сравнивать внутри совместимых видов работ; смешанный отбор описать
явной политикой, не сравнивать bytes data и function instructions как одну шкалу.
Пороговые grades не заменяют сырые counts — сохранять оба и причины.

`eligible_consumers_helped` считать по уникальным remaining work items и
конкретным требованиям, а не по call sites/aliases/всей транзитивной достижимости.
Отдельно вывести потенциально разблокируемых и тех, кому результата достаточно.
Занятые/готовые consumers не завышают приоритет. Стабильный tie-break обязателен.
Если иной вектор объективно лучше на наших данных, объяснить изменение, сохранить
исходную и выбранную policy и проверочные примеры до freeze.

Не формировать отдельные гарантированные numeric seconds/token/$ estimates.
Не скрывать экспертные grade rules как «измеренную сложность».

## 7. Производный индекс и обновление

Сохранить статические features отдельно от динамических requirement states,
rank evaluations, policy и истории. Каждая оценка binds native/source/dedup
generations, registry observation, feature/producer hashes и policy revision.
Никаких больших повторяющихся proof JSON в каждой member row.

Статические признаки переиспользуются при тех же ELF/analysis inputs. Динамика:

- claim/release меняет dispatch eligibility;
- scoped accepted result меняет только закрытые им requirements и их consumers;
- data interpretation/provider binding меняет соответствующие edges/requirements;
- native/code edges, extents и equivalence revisions инвалидируют затронутые
  features/groups/packets;
- policy version меняет все rank evaluations.

Обновлять затронутый reverse-dependency frontier, по SCC с фиксированной точкой,
распространять дальше только реально изменившийся статус. Не делать полного
пересчёта после каждого символа и не считать accepted/completed readiness.
Для общих feature normalizations, если они зависят от corpus, явно версионировать
такой вход; изменение распределения не должно тихо сдвигать старые grades.

Предпочесть идемпотентный derived event journal с receipt/cursor и reconciliation
по canonical observations перед planning. Canonical registry transaction не
должна зависеть от успешной записи производного рейтинга. При сбое сохранить
событие/состояние и восстановить до следующего назначения, не игнорировать staleness.
Полный rebuild — контроль корректности incremental update и аварийный путь.
Ранжирование само по себе не получает claim; final prepare повторно проверяет
доступность, generations и транзакционно резервирует выбранные работы.

## 8. Сначала проверка на данных проекта

Не начинать боевую реконструкцию до завершения этого этапа.

1. Read-only inventory всех текущих eligible функций/данных/initializers:
   known/unknown/partial, work kinds, зависимости, exclusions, распределения
   признаков, runtime/output размер расчёта. Original identities не потеряны.
2. Проверить реальные положительные и отрицательные примеры: arithmetic leaf,
   direct calls+table, stateful method, indirect/partial CFG, aliases/different
   versions, Core provider, known/unknown payload bounds, pointer table,
   NOBITS и initializer. Если типа нет в корпусе, так и указать; synthetic tests
   дополняют, но не заменяют real-data evidence.
3. Book и предыдущие принятые функции использовать как контроль маршрутизации
   existing result, а не как новые reconstruction candidates.
4. Детерминизм и idempotency, content corruption, неизвестные признаки,
   status-scope distinction, SCC/циклы, duplicate unique work, stale generation,
   busy claims, changing revision, provider exclusion и negative empty packet tests.
5. Проверить incremental events в изолированном индексе против fresh rebuild:
   completion, provider binding, demotion/revision и data interpretation.
   Сравнить все eligibility/rank fields, не только top10. Не изменять operational
   readiness или освобождать production claims ради тестов.
6. Обосновать порядок на выборке верхних/пограничных/blocked узлов. Сохранить
   features, rank vector, reasons и evidence. Не подгонять политику под заранее
   желаемые100 символов. Запустить подходящие существующие regression checks.

Операторские действия должны позволять build/update, explain item, list ranked,
plan batch и validate plan; точные имена выбрать по текущему CLI. Экспортировать
machine-readable JSON и читаемый Markdown. Обновить документацию рабочего пути.

## 9. Следующая партия: десять групп по десять

После успешной проверки заморозить infrastructure+ranking policy. Формировать
партию из самых простых eligible уникальных работ с **реальными доказанными
call/data/initialization зависимостями**. Name correspondence и одна stack access
не считаются содержательной зависимостью. Не добирать leaves только ради числа.

По умолчанию100 target original function/initializer symbols; необходимые
статические данные включаются в полноценные подзадачи их consumer group и
учитываются отдельно. Допустима смешанная партия с named data symbols, если
это actual unresolved interpretation/binding work с конкретным consumer replay,
а не повторное извлечение готовых bytes. Явно показать состав по типам до запуска.
Первую подходящую смесь не объявлять математически глобально минимальной.

Группы строить по class/namespace ownership и shared context. Учитывать реальную
суммарную уникальную зависимость группы, а не сумму повторённого context каждого
метода. Межгрупповые write/read conflicts запрещены; циклы не разрезать так,
чтобы workers одновременно изменяли читаемые друг другом inputs. Рейтинг помогает
отбору, но не отменяет групповой dependency gate. Для пропущенного более дешёвого
узла сохранить причину: занят, не независим, другой work kind, blocked и т.п.

Если100 подходящих целей или10 независимых групп нет, не изобретать symbols,
эквивалентность, evidence или безопасную независимость. Показать точный дефицит
и blocker; не запускать меньшую/волновую партию молча.

Контекст класса: цельная существующая декларация и необходимые типы/definitions,
ctors/dtors и mutators для инвариантов. Небольшие связанные class files давать
целиком; большие смешанные файлы — связанные scopes и explicit expansion.
Всё hash-bound к packet generation; не выдумывать original C++ layout из ELF.

Перед запуском **опубликовать в комментарии** компактную таблицу десяти групп
и ссылку на полный список100 targets. Полный `SELECTION.md` + `SELECTION.json`
обязаны для каждого item содержать:

```text
group / owner / execution order
work_item_id / kind / covered original identities
namespace / original mangled / ELF SHA / role / version / range
raw features + known/unknown/partial flags
rank vector + policy version + human reasons
required dependencies + satisfaction scope/evidence
unresolved requirements + declared limitations
owned files / inter-group conflicts checked
reason for skipping cheaper conflicting candidates
```

Список и веса показать **до spawn**, но не ставить новую approval-паузу:
пользователь уже разрешил продолжить. Рейтинг и final selected bindings должны
совпадать; при stale/claim конфликте пересчитать affected selection и показать
существенные изменения до запуска. Сохранить rejected plan revisions.

## 10. Реконструкция и обязательные gates

Использовать действующий `batch-prepare --jobs auto` с общим grouped manifest,
claims и final EX publication barrier. Все пакеты и конфликтные проверки до
первого worker edit. Только complete `BATCH_DISPATCH.json` разрешает spawn.
10 свежих workers одновременно, generated arguments, `fork_turns=none`.
Capacity check до дорогостоящей подготовки; требуется11 slots с Root.
Если runtime предоставляет меньше, сообщить blocker, не подменять волнами.

Workers выполняют полный bounded reconstruction cycle и HANDOFF по действующему
контракту, включая individual original checks, independent native/provider
observations, formatting, compile/mangling, replay и limitations. Для данных
сохранить distinct data work result и memory/consumer replay; при необходимости
добавить совместимую поддержку typed data handoff/acceptance в infrastructure
этапе и проверить её до freeze, не выдавать фиктивный function handoff.

Root рецензирует substance/argv, запускает accept_worker и все существующие
Linux/full CTest, installed-role/compile-once, fresh source/proof/Core/formatter,
guarded SQLite dry-run/admission, trackers/checkpoints/mirror audit. Не менять
proof oracle или ослаблять admission ради успеха партии. Исходные объявления,
ABI/layout и hardware claims строго по evidence. Claims завершать по действительным
результатам; failed work сохраняет resumable state и владельца до явного решения.

После принятых результатов обновить derived requirement/ranking state штатным
идемпотентным путём, проверить соответствие фактическому registry. Не запускать
ещё одну партию после изменения порядка очереди.

## 11. Замеры, evidence и завершение

Не связывать ranking score с токенами/временем, но измерить отдельно Root и10
workers: provider session IDs, cumulative baseline/end, input/cached subset/
noncached/output, wall timestamps, tool durations, context requests/ожидание,
лишние широкие чтения/повторы. Не оценивать недоступные counters на глаз.

Отделить infrastructure/ranking development и real-data verification от отбора,
refresh, batch prepare/dispatch, worker reconstruction, local acceptance,
global integration/admission, ranking update и отчётности. Полная стоимость
включает failures и reporting; parallel intervals не складывать в whole wall time.
Обязательные повторы validation отделить от avoidable repeats неизменённых входов.

Evidence — новый датированный `evidence/recovery/.../dependency-graph/`:
policy/schema/operator source hashes, inventory, test receipts, incremental-vs-full
checks, ranked candidate export, selection revisions, shown list timestamp,
packet/dispatch bindings, raw usage/tool events, HANDOFF/acceptance/admission,
final report/metrics/seal и live-job/claim state. Scratch только project temp/.

Критерий завершения: рейтинг всех трёх kinds реализован и проверен на реальных
данных; статическое и динамическое состояние разделены; scoped updates совпадают
с rebuild; до spawn опубликованы100 целей/веса/группы; одна партия10×10 завершена
с сохранением всех validation gates и честным per-symbol outcome. Возможный
blocked/failed outcome не маскировать readiness или успешным extraction-only.
В конце — короткий результат и ссылки на полный список/веса/отчёт. Коммит/push
дальнейших изменений этим заданием автоматически не предписываются.
