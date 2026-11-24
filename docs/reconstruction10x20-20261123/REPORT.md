# Контрольная реконструкция 10×20

Канонически закрыто **200 из 200** первичных слотов. Принято **372** отдельных ELF-идентичностей, из них 112 готовы в проверенной области и у 260 остаются открытыми декларации.

| Единица учёта | Итог |
| --- | ---: |
| Первичные слоты | 200 |
| Канонически принятые задания | 205 |
| ELF-идентичности из отдельно учтённых прежних заданий | 5 |
| Уникальные mangled имена | 231 |
| Группы callable по деманглированному имени | 200 |
| ELF среди ABI-вариантов | 139 |
| Принятые / утверждённые замены | 23 / 25 |

Независимая сверка соединила точные ELF-идентичности из предложений с хешированными примечаниями канонической приёмки. Каждое задание должно закрыть все свои ELF. Замена наследует один первичный слот, прежние задания учитываются отдельно. Группы callable и ABI-варианты показывают разные разрезы числа ELF.

## Конечные отметки UTC

- Запрос — 2026-11-21T09:58:45.311Z.
- Завершение канонической приёмки — 2026-11-23T08:53:22.746682464+00:00. 200 primary, 372 exact ELF (112 ready/260 pending), terminal SQLite claims, notes, tracker and mirror. Время по записи локальной квитанции, проверено относительно live, mirror и коммита 852b93fb71ae. [POSTADMISSION-CYCLE-READBACK.json](../../evidence/recovery/2026-11-21/control10x20-after-4fed70d11/actual08-final10-admission/POSTADMISSION-CYCLE-READBACK.json), [POSTADMISSION-VERIFIED.json](../../evidence/recovery/2026-11-21/control10x20-after-4fed70d11/actual08-final10-admission/POSTADMISSION-VERIFIED.json), [LIVE_COMMAND.json](../../evidence/recovery/2026-11-21/control10x20-after-4fed70d11/actual08-final10-admission/LIVE_COMMAND.json), [mirror-audit.json](../../evidence/recovery/2026-11-21/control10x20-after-4fed70d11/actual08-final10-admission/mirror-audit.json), [COMPLETED.json](../../evidence/recovery/2026-11-21/control10x20-after-4fed70d11/linux-actual08-final10-01/COMPLETED.json)
- Завершающая регистрация графа — 2026-11-24T01:11:54.471542+00:00. Первый публикатор завершился из-за OOM, следующий отказал по проверяемому бюджету. Неудачные команды сохранены с фактической длительностью 5439.843, 2055.474, 3506.005, 39684.864, 1.290 с. Завершающая команда прошла за 3047.482 с; регистрация и отсутствие незавершённых изменений проверены. [COMPLETED.json](../../temp/recovery-work/control10x20-after-4fed70d11/graph/actual09/COMPLETED.json), [COMPLETED.json](../../temp/recovery-work/control10x20-after-4fed70d11/graph/actual09-recovery01/COMPLETED.json), [COMPLETED.json](../../temp/recovery-work/control10x20-after-4fed70d11/graph/actual09-recovery02/COMPLETED.json), [COMPLETED.json](../../temp/recovery-work/control10x20-after-4fed70d11/graph/actual09-recovery03/COMPLETED.json), [COMPLETED.json](../../temp/recovery-work/control10x20-after-4fed70d11/graph/actual09-resume01/COMPLETED.json), [PUBLISHER_OOM_ROLLBACK.json](../../temp/recovery-work/control10x20-after-4fed70d11/graph/actual09/PUBLISHER_OOM_ROLLBACK.json), [TERMINAL_BUDGET_REFUSAL.json](../../temp/recovery-work/control10x20-after-4fed70d11/graph/actual09-recovery01/TERMINAL_BUDGET_REFUSAL.json), [TERMINAL_GUARD_REFUSAL.json](../../temp/recovery-work/control10x20-after-4fed70d11/graph/actual09-recovery02/TERMINAL_GUARD_REFUSAL.json), [COMPLETED.json](../../temp/recovery-work/control10x20-after-4fed70d11/graph/actual09-resume02/COMPLETED.json), [VERIFIED.json](../../temp/recovery-work/control10x20-after-4fed70d11/graph/actual09-resume02/VERIFIED.json), [AGGREGATE-final.json](../../temp/recovery-work/control10x20-after-4fed70d11/graph/AGGREGATE-final.json), [MEASURED_RESUME_AND_PUBLICATION.json](../../temp/recovery-work/control10x20-after-4fed70d11/graph/actual09-resume02/MEASURED_RESUME_AND_PUBLICATION.json), [REGISTERED_INPUT_COMPARISON.json](../../temp/recovery-work/control10x20-after-4fed70d11/graph/actual09-resume02/REGISTERED_INPUT_COMPARISON.json), [CLOSING_RECOVERY03_RESUME02_SOURCE_NATIVE_FINAL01.json](../../temp/recovery-work/control10x20-after-4fed70d11/timing/CLOSING_RECOVERY03_RESUME02_SOURCE_NATIVE_FINAL01.json)
- Каноническая проверка закреплённых кодеков — 2026-11-23T09:22:04.476568+00:00. 1101/1101 в каноническом Linux и 3/3 после переноса Core, CS18AI и RM. Первая попытка завершилась с 12 ошибками CTest, 403.77 с команды тестов; повтор после 13 точечных исправлений проверок прошёл, 372.25 с CTest и 372.38 с команды тестов. [POST-SWITCH.json](../../temp/recovery-work/libpng-zlib-lineage/integration/reproducible-audit/operator-switch-20261123T085431.198592380Z/POST-SWITCH.json), [timing.tsv](../../temp/recovery-work/libpng-zlib-lineage/integration/reproducible-audit/operator-switch-20261123T085431.198592380Z/timing.tsv), [COMPLETED.json](../../evidence/recovery/2026-11-23/pinned-codecs-20261123T085431.198592380Z/retry01/COMPLETED.json), [commands.json](../../evidence/recovery/2026-11-23/pinned-codecs-20261123T085431.198592380Z/retry01/commands.json), [installed-audit.json](../../evidence/recovery/2026-11-23/pinned-codecs-20261123T085431.198592380Z/retry01/installed-audit.json), [validation.json](../../uc-library/validation/role-build-audit/runs/20261123T092002.309115Z/validation.json), [POSTADMISSION-TUPLE-READBACK.json](../../evidence/recovery/2026-11-21/control10x20-after-4fed70d11/actual08-final10-admission/POSTADMISSION-TUPLE-READBACK.json)
- Повторная привязка прежних доказательств — 2026-11-23T10:34:15.147576+00:00. Строгая проверка 3931 записи, 3913 без изменений, 18 деклараций ожидают подтверждения и получили обновлённую привязку к доказательствам, без новых ELF или повышения статуса. Tracker, checkpoint и mirror прошли. [INDEPENDENT-POSTSWITCH-FINAL-READBACK.json](../../evidence/recovery/2026-11-23/pinned-codecs-20261123T085431.198592380Z/retry01/INDEPENDENT-POSTSWITCH-FINAL-READBACK.json), [COMPAT-ADMISSION-VERIFIED.json](../../evidence/recovery/2026-11-23/pinned-codecs-20261123T085431.198592380Z/provider-guard-compatibility-scope/COMPAT-ADMISSION-VERIFIED.json), [COMPAT-LIVE-COMMAND.json](../../evidence/recovery/2026-11-23/pinned-codecs-20261123T085431.198592380Z/provider-guard-compatibility-scope/COMPAT-LIVE-COMMAND.json)

Исходный слой графа подтвердил 12,892,035 строк в 12,898 пакетах. От первого до последнего подтверждённого пакета прошло 35 146.003 с. Затем native-транзакция превысила лимит времени. Интервал от последнего исходного пакета до выхода команды составил 783.630 с и включает промежуточные проверки. Возобновление заняло 3 047.482 с. Оно передало 0 исходных строк и 2,218,508,472 байт в native-фазе и проверках регистрации. Лимит таймаута восстановлен до 600 с. Внутренние фазы входят во время команд.

- Коммит переключения кодеков — `6ba52df979958c1a3be6114d7dad68b856ed31ee`, время коммитера 2026-11-23T09:22:33+00:00.
- Коммит реконструкции — `852b93fb71ae7b6b33a138126617df1c587d025f`, время коммитера 2026-11-23T08:53:51+00:00.
- Полная операционная длительность — 227 589.161 с.
- Окно от начала запуска канонической проверки кодеков до итоговой квитанции — 1 653.091 с. Его пересечение с объединением попыток завершающего графа — 1 557.479 с.

Архивы и заголовки закреплённых libpng и zlib, роли Core, CS18AI и RM, и исполняемые пользовательские пробы проверялись отдельным этапом. Upstream-реализации не входят в зачёт ELF реконструкции.

## Накладные затраты и перекрытия

| Измерение | 10×20 | 10×10 |
| --- | ---: | ---: |
| Операционное календарное время, с | 227 589.161 | 30 814.245 |
| Принято первичных слотов | 200 | 100 |
| Принято ELF-идентичностей | 372 | 100 |
| Проверенные регистрации графа | 9 | 4 |
| Сумма команд графа, с | 79 896.312 | 13 648.102 |
| Команды графа на принятый слот, с | 399.482 | 136.481 |
| Команды графа на принятый ELF, с | 214.775 | 136.481 |
| Канонические Linux-команды на принятый ELF, с | 18.684 | 30.828 |

Пересечение графа с объединением измеренных фаз — 9 623.565 с. Категории отслеживаются отдельно, в календарное время повторно не складываются. Канонический codec-аудит учитывается отдельно от Linux-команд реконструкции. Объём и состав задач двух циклов различаются.

Наблюдаемый перерыв координатора по квоте — 99 983.129 с, включён в полное время. Измеренное пересечение процесса с этим интервалом — 0.000 с. Календарное время при вычитании наблюдаемого перерыва — 127 606.032 с. Эти значения не описывают CPU, биллинг или полную недоступность провайдера.

| Фаза неудачной команды | Попытки | Объединённое время, с |
| --- | ---: | ---: |
| packet_launcher_attempt | 3 | 2 079.995 |
| canonical_linux | 6 | 2 049.658 |
| graph_postflight | 2 | 9.202 |
| sqlite_admission | 0 | 0.000 |
| live_graph | 5 | 50 687.465 |

Для actual07 union65 первая попытка завершилась с ошибкой CTest. Вторая прошла 1091/1091 за 372.88 с и была отклонена проверкой изменения снимка. Третья прошла весь канонический путь, 1091/1091 за 378.59 с. Эти запуски сохранены отдельно, включая отказ после успешных тестов. Список CTest-попыток и командных отказов частично пересекается.

Перед последней полной проверкой целевой прогон завершил 35 из 37 тестов. Повтор с точной архивной привязкой прежней LCD-проверки прошёл 37/37 за 9.71 с. Учитываем этот целевой прогон отдельно от полноразмерных Linux-команд.

Аудит параметров компиляции сверил 65 реальных handoff и 22 единицы с обязательными локальными параметрами. Для каждой установлена единственность команды и наличие параметров. Прошли восемь тестов аудитора и отрицательная проверка на реальных данных. Доступного доисправительного снимка команд нет, сохранился его хеш. Проверка обнаружения утечки с целым baseline воспроизведена синтетическим тестом.

## Воспроизведение

Агрегатор `uc-library/tools/recovery/report_cycle_timing.py` читает квитанции и сохраняет отдельный результат. В scratch сохранены команды воспроизведения, сравнения и независимой сверки. Снятие счётчиков затрат запускается отдельно через `uc-library/tools/recovery/collect_cycle_cost.py cutoff` после фактической отсечки. Время подготовки отчёта и коммита фиксируется отдельной квитанцией.
