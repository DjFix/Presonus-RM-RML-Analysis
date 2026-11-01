# Прозрачная структура и смысл запросов

Это экспериментальная проекция; production schema не менялась.

## Что есть в данных

| Сущность | Где хранится | Идентичность |
| --- | --- | --- |
| Исходный символ | SQLite `nodes(kind=symbol)` / graph `OriginalSymbol` | Полный ELF SHA-256 + исходное mangled name |
| Файл | SQLite `nodes(kind=file)` / graph `Artifact` | Нормализованный путь в конкретном снимке |
| Единица компиляции | SQLite ownership `objects` / graph `TranslationUnit` | Путь object в конкретной конфигурации; свойство `source` указывает CPP |
| Определение символа | SQLite `definitions` / graph `DEFINES` | Наблюдение `nm --defined-only`; SHA-256 object проверен до/после |
| Привязка proof | `proof_binding`, `validation_binding` | Историческая hash-bound привязка; не означает владение реализацией |

Низкоуровневый baseline имеет всего две таблицы `nodes` и `edges`, плюс `inputs`
с хешами источников наблюдений. В SQLite-варианте с integer keys меняются только
внутренние ключи связей, логические идентичности сохранены. В графовых движках
семантический overlay добавляет два понятных label и `DEFINES`, сохраняя baseline.

| Связь | Точное значение | Источник |
| --- | --- | --- |
| `compiles` | object компилируется из CPP | compile_commands.json |
| `compiler_input` | файл входит в compiler dependency closure object | GCC depfile; это не только прямой include |
| `link_input` | явный object/archive operand команды линковки | CMake link.txt |
| `DEFINES` | TU определяет символ с таким точным mangled name | host object nm + original-key lookup |
| `proof_binding` | manifest символа содержит source binding | read-only SQLite snapshot |
| `validation_binding` | запись указывает на validation document | read-only SQLite snapshot |

Сборочные входы, владение кодом и доказательства различаются по типу связи.
Достижимость через архив не используется для автоматического расширения
первого пакета чтения агенту.

## Один и тот же вопрос в трёх движках

«Какие production CPP и какие оригинальные символы читать при изменении файла?»

Фактически проверенный запрос Neo4j **и** Memgraph, без отличий:

```cypher
MATCH (tu:TranslationUnit)-[:compiler_input|compiles]->(:Artifact {id: $input_id})
WITH DISTINCT tu
OPTIONAL MATCH (tu)-[:DEFINES]->(symbol:OriginalSymbol)
RETURN tu.source AS source, symbol.id AS original_id, symbol.mangled AS mangled
ORDER BY source, original_id
```

SQLite с именованным представлением:

```sql
SELECT source, original_id, mangled
FROM affected_original_symbols
WHERE input_id = ?
ORDER BY source, original_id;
```

Полные определения двух TEMP VIEW открыто приведены в `case_last_cycle.py`:
первое связывает compilation inputs с production TU, второе добавляет точные
определения оригинальных символов. Индексы и joins не спрятаны в непрозрачном ORM.
Сам запрос чтения прост, но поддержку views тоже учитываем при сравнении.

## Где различается удобство

- Для текущего вопроса SQLite views и Cypher одинаково дают понятный интерфейс.
  У SQLite меньше компонентов и уже есть общая транзакционная идентичность реестра.
- Для новых произвольных вопросов по нескольким типам путей Cypher позволяет
  выразить шаблон непосредственно. SQLite требует нового join/CTE или view.
  Это преимущество выразительности, а не доказанное ускорение реконструкции.
- Neo4j и Memgraph выполнили этот Cypher без изменений. Отличия инициализации
  индексов/constraints явно находятся в импортёре, а не просачиваются в вопрос.
- Оба graph engine являются проекциями. Их полнота и свежесть зависят от
  extractor/index и generation binding. Изменение движка не восстановит
  отсутствующие call/type/virtual-dispatch связи.

Для следующей стадии полезнее добавить несколько реальных вопросов агента и
проверить пропуски контекста, чем расширять синтетическую нагрузку. В частности:
«кто вызывает метод?», «какие типы затронет изменение декларации?» и «какие
fixtures объясняют эту ветку?». Сейчас данных для честного ответа на эти вопросы
недостаточно; они не подменяются широкими manifest bindings.
