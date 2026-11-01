# Чаты OpenCS18: работа на VM101, управление с Mac

Проверено 28 октября 2026 года. Канонический проект: `/home/rs/projects/opencs/ai-line-analysis`; хост: `remote-ssh-discovered:vm101`, SSH `rs@192.168.50.238`. Текущий desktop remote project — **ai**, ID `e9a2021b-f9ea-43fc-99ad-c67413dc2922`. Прежние ID сохранённых remote projects больше не использовать.

## Что уже подтверждено

Файлы перенесены и проверены: preservation audit охватил 245 925 исходных файлов, 50 801 добавленный файл и шесть фотографий. Linux configure/build/ctest/seal/install прошли; 132 теста успешны. Библиотека находится в `uc-library/` в корне. Старый `temp/uc-recovery/` расформирован: его исходное дерево сохранено в `evidence/recovery/2026-10-28/vm-migration/legacy-uc-recovery`, 168 файлов инструментов — в `uc-library/tools/recovery`, четыре входных файла — в validation. `AGENTS.md` и документация обновлены. Пять прежних версий runtime сохранены в `state.tar`. Архивы обеих машин и исходная копия Mac сохранены.

На VM без перезаписи существующих файлов сохранены **53 исходных native rollout JSONL**, включая дочерние сессии. Одиннадцать исходных основных чатов восстановлены через нативный `thread/resume(path,cwd,excludeTurns:true)`. Их полная логическая история, включая `history_base`, проверена по всем turn IDs и item IDs. Исходные Mac-чаты архивированы штатным API; они не удалены.

Для рабочего продолжения созданы **11 native forks с новыми ID**. У всех сверены полные множества turn IDs и item IDs; исследовательские turns при создании не запускались. Receipt с соответствиями и результатами — `/home/rs/projects/opencs/ai-line-analysis/temp/vm-migration-20261028/remote-continuations.json`.

Пилот Decode и продолжение Extract UC уже открыты в desktop по ссылкам с явным hostId и подтверждены в remote project ai: VM101, canonical cwd, idle. Назначение Extract через `move_thread_to_project` после такой регистрации прошло успешно. Регистрация остальных девяти выполняется управляющим агентом; полное завершение нужно подтвердить итоговым API-readback. **Пауза Extract UC сохраняется**: показ чата в приложении не разрешает возобновлять реконструкцию.

## Рабочая последовательность переноса

1. Сохранить исходные native JSONL и проверить транзитивную цепочку `history_base`. Переносить также реальные дочерние rollout, если требуется сохранить их собственные истории. Сообщения, уже доставленные родителю, находятся в его JSONL, но это не копия всей внутренней истории дочернего агента.
2. Через установленный app-server 0.165 восстановить исходный чат с `path`, canonical `cwd` и `excludeTurns:true`, без `turn/start`. `path` — экспериментальное поле, требующее `initialize.capabilities.experimentalApi:true`. Не копировать живые SQLite-базы или credentials с Mac.
3. Создать native `thread/fork` с canonical cwd, `excludeTurns:true` и `deferGoal:true`. Точные параметры брать из схемы установленной версии. Fork получает новый ID; исходный чат остаётся неизменным. Не переносить активный goal автоматически и не отправлять пользовательское сообщение для «пробуждения».
4. Прочитать **все** страницы `thread/turns/list` с `itemsView:full`; проверить полное совпадение turn IDs и item IDs с исходной логической историей. Одного успешного `resume`, общего счётчика или последней страницы недостаточно.
5. Сохранить исходный title через штатный `thread/name/set`.
6. Зарегистрировать новое продолжение в desktop, открыв **точный deep link с `hostId`**. На этом Mac рабочий способ — явный выбор приложения:

   ```sh
   open -a /Applications/ChatGPT.app 'codex://threads/01a17fc6-3e44-7dd1-beb3-319f5d4d97a0?hostId=remote-ssh-discovered%3Avm101'
   ```

   Эта команда открывает Extract UC на VM101. Не вводить и не отправлять сообщение. Bare `open URL` на этой машине не нашёл обработчик; вариант с `-a` сработал без перезапуска приложения.
7. При необходимости вызвать `move_thread_to_project` с **новым ID**, `hostId=remote-ssh-discovered:vm101` и desktop project ID `e9a2021b-f9ea-43fc-99ad-c67413dc2922`. Затем проверить `list_threads` и `read_thread` с явным hostId: projectId, host, cwd, история, idle, отсутствие нового turn. Повторить по одному для остальных чатов.

Официальная документация разделяет `thread/resume`, `thread/fork` и `turn/start`; для paginated history предусмотрены `thread/turns/list` и `thread/items/list`. Создание fork означает новый ID, а не сохранение ID рабочего продолжения. [OpenAI Docs: App Server](https://learn.chatgpt.com/docs/app-server).

## Рабочие продолжения

Ссылки ниже содержат обязательный hostId VM101. Открытие ссылки само по себе не является разрешением запускать исследование.

| Чат | Исходный ID | Продолжение на VM101 | Turns / items |
|---|---|---|---|
| Decode FPGA AVB NIH bitstream | `01a17e03-d528-7102-af84-2a680a143ee3` | [Открыть](codex://threads/01a17fbf-6884-7892-a777-26ac027064ab?hostId=remote-ssh-discovered%3Avm101) | 8 / 929 |
| Extract UC client and server sources | `01a17910-caf1-7012-934c-607ed1db6a6f` | [Открыть](codex://threads/01a17fc6-3e44-7dd1-beb3-319f5d4d97a0?hostId=remote-ssh-discovered%3Avm101) | 47 / 8159 |
| Reconstruct STM32 firmware in mixer | `01a17eec-c2fa-7a62-8956-7071dd1c9347` | [Открыть](codex://threads/01a17fc6-4577-75f3-9b75-4f75543e94a9?hostId=remote-ssh-discovered%3Avm101) | 4 / 301 |
| Find STM32 firmware in mixer | `01a17d6e-a435-7ab2-b63a-3357972ff315` | [Открыть](codex://threads/01a17fc6-4166-7461-81c3-5037569e288b?hostId=remote-ssh-discovered%3Avm101) | 2 / 103 |
| Find open XMOS VHDL definitions | `01a17e19-2a73-76d3-a074-7e44f4789145` | [Открыть](codex://threads/01a17fc6-44bc-7c21-a697-a16f74528bb7?hostId=remote-ssh-discovered%3Avm101) | 3 / 29 |
| Locate main sound processing | `01a17dd9-8fc7-7e33-bdb9-6acdcdee2927` | [Открыть](codex://threads/01a17fc6-43e1-7102-85f9-31adcf7cfa89?hostId=remote-ssh-discovered%3Avm101) | 3 / 216 |
| Locate the TCAT DICE SDK source | `01a17acd-1548-72e3-89cb-1a9f079f1592` | [Открыть](codex://threads/01a17fc6-3fec-7a61-b72a-f80e28c7b4c4?hostId=remote-ssh-discovered%3Avm101) | 9 / 420 |
| Extract fader board firmware | `01a17d87-cefd-72e2-987f-34a7a1e4a7e7` | [Открыть](codex://threads/01a17fc6-427e-7f71-80a7-13bccbc35f26?hostId=remote-ssh-discovered%3Avm101) | 6 / 249 |
| Locate LPC1317F firmware binaries | `01a17da1-1cce-7161-b2d6-2c52cf97ccab` | [Открыть](codex://threads/01a17fc6-437b-7ff2-851d-5b132b724244?hostId=remote-ssh-discovered%3Avm101) | 1 / 62 |
| Investigate EFM32 fader bootloader update… | `01a17d9b-50b1-7122-9f8f-5f96f1282d17` | [Открыть](codex://threads/01a17fc6-4307-7870-a328-73f6617d0486?hostId=remote-ssh-discovered%3Avm101) | 1 / 350 |
| Assess FPGA bitstream structure | `01a17d5f-8d7d-7c22-b839-ce6290870e7b` | [Открыть](codex://threads/01a17fc6-4082-7772-9608-60d346582686?hostId=remote-ssh-discovered%3Avm101) | 2 / 84 |

## Почему использован native fork и deep link

Штатный cross-host Hand off в установленном desktop категорически отклоняет `historyMode=paginated`; полная загрузка страниц этот guard не снимает. Поэтому для этих чатов применён нативный перенос rollout и fork с полной историей, а не краткий пересказ. Патч приложения и переписывание SQLite не использовались.

Импорт с сохранением исходных ID выявил коллизию desktop sidebar с Mac-копиями. Архивирование Mac-копий сняло первый отказ, но desktop membership всё ещё ссылался на старый local OpenCS18. Flow перемещения отклонял переход local-project → remote-project по сравнению папок. Новые ID продолжений устранили эту коллизию.

Нативные forks без собственного пользовательского сообщения могут иметь пустой preview. Серверный обычный `thread/list` в 0.165 добавляет `threads.preview <> ''`. Это не отсутствие истории. Desktop background hydration также не добавляет чат в recent автоматически. Открытие точного host-specific deep link запускает штатную desktop-регистрацию и добавляет продолжение в recent без исследовательского turn; рабочий путь подтверждён пилотом и Extract UC.

Deep link проверен в установленном `/Applications/ChatGPT.app/Contents/Resources/app.asar`: `app-initial-feb30b196d11.js`, функция `uZ`, принимает `codex://threads/<ID>` и один query key `hostId`; route parser читает именно его. Не заменять на `host=` и не добавлять непроверенные параметры. Native metadata update не предоставляет полей preview/has_user_event; вручную редактировать их не нужно.

## История и архивные зависимости

`history_base.thread_id` обозначает immutable rollout ID, а не обязательно текущий thread ID. Код 0.165 `rollout/src/list.rs`, `find_rollout_path_by_rollout_id`, ищет его и в `sessions`, и в `archived_sessions`. `thread-store/src/local/rollout_lineage.rs` рекурсивно собирает bounded prefixes; `model_context.rs` использует ту же lineage при восстановлении модельного контекста.

Поэтому архивный родитель технически поддерживается. Однако штатный `thread/archive` может архивировать и spawned descendants. До архивирования импортированных VM-оригиналов нужно проверить, что рабочие новые продолжения не входят в эту parent-thread цепочку, сохранить receipt и повторить чтение всей истории после операции. Пока исходные rollout на VM оставлены как immutable dependencies. Их нельзя удалять, переименовывать или менять байты; очередной исходный turn тоже нарушил бы смысл замороженной миграционной копии.

Полная история просмотра и model-visible контекст — разные слои. Нативный resume восстанавливает контекст последней исходной компакции и более новый suffix; это исходное поведение Codex. Предыдущие turns при этом сохранены и доступны через history pagination. Внешние фотографии/файлы, skills, MCP, окружение и фоновые процессы проверяются отдельно от JSONL.

## Прежний сбой Git origins

На обеих машинах ровно один `origin`, fetch/push: `git@github.com:DjFix/Presonus-RM-RML-Analysis.git`. Git 2.43 на VM возвращал пустой origin при команде Codex из `.git` с `-c safe.bareRepository=explicit`. Этот случай исправлен в [Git 2.44](https://raw.githubusercontent.com/git/git/v2.44.0/Documentation/RelNotes/2.44.0.txt), а аналогичный запуск внутри managed worktrees — в [Git 2.45](https://raw.githubusercontent.com/git/git/v2.45.0/Documentation/RelNotes/2.45.0.txt).

После обновления Git и перезапуска Mac-приложения для очистки 24-часового worker cache matching заработал. Popup `ai-line-analysis` был fallback на basename при пустом originUrl; GitLab remote не возвращался. Следующий отказ Hand off оказался отдельным ограничением paginated history. Промежуточная ошибка pending composer также не доказывала наличие черновика: поле было пустым, и этот gate позднее прошёл без отправки сообщения.

## Автономная работа VM при закрытом Mac

Доступность чатов в sidebar ещё не доказывает автономность работающих агентов. Нужен один проверенный долгоживущий app-server на VM, к которому подключаются клиенты Mac и в котором реально находятся запущенные задачи.

На последней read-only проверке default control socket ответил версией 0.165.0, но `thread/loaded/list` вернул 0. Отдельный SSH stdio-server может иметь иное состояние. `app-server proxy` — raw byte relay; для control socket нужен HTTP Upgrade и masked WebSocket framing, а не NDJSON напрямую. Диагностический helper на Mac: `/Users/romansavrulin/stefania/temp/probe_vm_codex_ws.py`.

Linux `app-server daemon bootstrap` устанавливает detached PID backend с `setsid()` и закрытыми stdin/stdout. Это не systemd unit и не гарантия автозапуска после reboot. `daemon stop` не захватывает unmanaged сервер. Bootstrap требует полный CLI-пакет, а не один бинарь: официальный installer хранит его в пользовательском `CODEX_HOME/packages/standalone`. Подготовка полного пакета сейчас выполняется отдельно; до её проверки работающий сервер не останавливать. [CLI installation](https://learn.chatgpt.com/docs/codex/cli), [App Server transports](https://learn.chatgpt.com/docs/app-server).

После согласованного перехода на managed server нужно проверить actual PID/exe, версию, WS-протокол, загрузку нужных чатов и сохранение работы при отключении Mac/SSH. Запуск исследования для этой проверки отдельно согласуется; пауза Extract UC сохраняется. Перезапуск VM и автозапуск после reboot — отдельная проверка, пока не выполненная.

## Критерий завершения

Все 11 новых продолжений видны с Mac в remote project ai; их host и cwd подтверждены API; полный history ledger совпадает; исходники, родительские и дочерние rollout сохранены; ни одного неожиданного turn или активного goal не появилось. Для автономности дополнительно подтверждены единый VM runtime и работа после отключения Mac. До этих проверок сохраняются архивы и исходная Mac-копия.
