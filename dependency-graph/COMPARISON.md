# SQLite, Neo4j и Memgraph: критерии dev-эксперимента

Проверено по официальным материалам 31 октября 2026 года. Это сравнение
возможностей; результаты исполнения хранятся отдельно в `runs/` и evidence.
Скорость движков нельзя выводить из рекламных описаний.

| Для нашего проекта | SQLite | Neo4j Community | Memgraph Community/MAGE |
| --- | --- | --- | --- |
| Модель графа | Таблицы вершин/связей, recursive CTE | Property graph, Cypher | Property graph, Cypher с собственными расширениями |
| Текущий реестр | Уже действующий источник | Отдельная проекция | Отдельная проекция |
| Хранение | Файл БД | Дисковое хранилище и page cache | По умолчанию in-memory transactional, WAL и snapshots |
| Аналитика/обходы | SQL или прикладной обход | Cypher; расширения APOC/GDS проверяются отдельно | В MAGE-образе алгоритмы уже включены |
| Dev-запуск | Существующий Python/SQLite | Один Docker service; Java внутри образа | Один Docker service; Lab — отдельный необязательный service |
| GUI | В этом эксперименте отсутствует | Browser через HTTP | Memgraph Lab отдельным контейнером |
| Драйвер | Python standard library | Bolt driver | Совместимость с Bolt позволяет проверить тот же driver |
| Переносимость запросов | Другой язык | Не считать Cypher всех версий идентичным | Есть отличия Cypher, индексов, constraints и процедур |

Neo4j поддерживает готовые Community-образы, persistent `/data` и
переменные конфигурации: [официальная Docker-инструкция](https://neo4j.com/docs/operations-manual/current/docker/introduction/).
APOC подключается отдельной настройкой образа; GDS имеет собственные условия
доступности: [Docker plugins](https://neo4j.com/docs/operations-manual/current/docker/plugins/).
В baseline сначала проверяем обход без этих расширений, затем можно измерить
специализированный серверный обход отдельно.

Memgraph предлагает готовые `memgraph-mage` и отдельный Lab:
[Docker Compose](https://memgraph.com/docs/getting-started/install-memgraph/docker-compose),
[установка MAGE](https://memgraph.com/docs/advanced-algorithms/install-mage).
Для разработки это удобно, если действительно нужны встроенные алгоритмы и GUI.
Различать in-memory transactional, analytical без тех же ACID-гарантий и
on-disk transactional обязательно:
[режимы хранения](https://memgraph.com/docs/fundamentals/storage-memory-usage).
Первый тест использует transactional; ускорять импорт переключением в analytical
и затем сравнивать его с обычной транзакционной загрузкой было бы некорректно.

Совместимость Cypher не означает полной взаимозаменяемости. В частности,
constraint в Memgraph не заменяет явное создание индекса:
[различия Cypher](https://memgraph.com/blog/cypher-differences-between-neo4j-and-memgraph).
В импортёре поэтому есть отдельная инициализация схемы каждого движка.

Маркетинговое слово «open source» не заменяет условия выбранного релиза:
страница [Memgraph Legal](https://memgraph.com/legal) указывает Business Source
License для Community. Для итогового выбора следует сохранить LICENSE именно
скачанного образа; коммерческие возможности и лицензирование не являются
результатом нашего performance benchmark.

## Стадии решения

1. **Развёрнутые bindings.** Один снимок реестра, один CSV-граф для всех движков.
   Измеряем стоимость извлечения отдельно от импорта. Сравниваем одинаковые
   транзакционные online imports, индексы, точное множество достижимых ID,
   повторные обходы, память контейнеров и размер persistent storage.
2. **Нормализованные source sets.** Отдельный следующий вариант, сохраняющий
   общие manifest sets. Сравниваем тождественность затронутых оригинальных
   символов с развёрнутым вариантом, а затем цену хранения и запросов.
3. **Реальные code dependencies.** Compiler/build evidence уже отдельно от
   proof bindings. Calls/type/virtual-dispatch и неопределённость требуют
   отдельного извлечения и ручной проверки полноты. Ни один backend не создаёт
   этих знаний сам.
4. **Dev-удобство.** Проверяем воспроизводимый запуск, restart с сохранением
   данных, повторное подключение, журналы и стоимость обновления образа.
   Сохраняем digest, версию, конфигурацию и команды; `latest` не используем.

Первый переносимый тест использует BFS с глобальным visited set на клиенте.
SQLite выполняет closure внутри процесса; Bolt добавляет сетевые roundtrips.
Это измерение прикладного пути, а не изолированного ядра движка. Нативные BFS/APOC
нужно измерять отдельным вариантом с теми же reachable IDs. Перечисление всех
возможных путей не эквивалентно reachability и может искусственно ухудшить результат.

Оба graph service ограничены двумя CPU и 6 GiB; Neo4j heap/page cache по 2 GiB,
Memgraph memory limit 4096 MiB. Эти настройки не означают одинаковое использование
RAM. Контейнерные memory/disk receipts обязательны, а конкурирующие импорты и
извлечение должны завершиться до сравнительных query timings.

До согласования новой модели доказательств production admission, полный Linux
replay и freshness checks остаются прежними. Граф даёт рекомендации и объяснения.
