# Партии до конца реконструкции

Срез операционного каталога от 23 ноября 2026 года. В таблицах TSV одна строка соответствует появлению символа в конкретном бинаре. Для C, P и R единица планирования — уникальный work_item_id, для D — пара ELF SHA и mangled name.

## Кандидаты на реализацию

До десяти исполнителей и десяти работ каждому. Стартовый отбор пройден. Для выдачи необходимы проверенные контракты, свободные файлы и актуальные зависимости.

| Партия | Заданий | ELF-строк | Полный манифест на VM101 |
|---|---:|---:|---|
| [C001](C001.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/candidate-batches03/BATCH_001.json) |
| [C002](C002.tsv) | 100 | 101 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/candidate-batches03/BATCH_002.json) |
| [C003](C003.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/candidate-batches03/BATCH_003.json) |
| [C004](C004.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/candidate-batches03/BATCH_004.json) |
| [C005](C005.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/candidate-batches03/BATCH_005.json) |
| [C006](C006.tsv) | 98 | 98 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/candidate-batches03/BATCH_006.json) |
| [C007](C007.tsv) | 3 | 3 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/candidate-batches03/BATCH_007.json) |

## Дополнительный отбор

Открытые задания для пополнения C. Проверить тело, происхождение, историю, занятость и класс-владелец. Совпадение имени с upstream требует проверки.

| Партия | Заданий | ELF-строк | Полный манифест на VM101 |
|---|---:|---:|---|
| [P001](P001.tsv) | 100 | 104 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/preflight/PREFLIGHT_001.json) |
| [P002](P002.tsv) | 100 | 104 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/preflight/PREFLIGHT_002.json) |
| [P003](P003.tsv) | 94 | 97 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/preflight/PREFLIGHT_003.json) |

## Разблокировка и сверка

Обрабатывать по причине в колонке status. Для занятой задачи сначала установить состояние владельца. После подтверждения эквивалентности или существующей реализации закрыть дубликат; оставшиеся доступные реализации поставить в C.

| Партия | Заданий | ELF-строк | Полный манифест на VM101 |
|---|---:|---:|---|
| [R001](R001.tsv) | 100 | 103 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_001.json) |
| [R002](R002.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_002.json) |
| [R003](R003.tsv) | 100 | 195 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_003.json) |
| [R004](R004.tsv) | 100 | 208 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_004.json) |
| [R005](R005.tsv) | 100 | 224 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_005.json) |
| [R006](R006.tsv) | 100 | 213 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_006.json) |
| [R007](R007.tsv) | 100 | 213 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_007.json) |
| [R008](R008.tsv) | 100 | 232 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_008.json) |
| [R009](R009.tsv) | 100 | 222 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_009.json) |
| [R010](R010.tsv) | 100 | 309 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_010.json) |
| [R011](R011.tsv) | 100 | 220 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_011.json) |
| [R012](R012.tsv) | 100 | 220 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_012.json) |
| [R013](R013.tsv) | 100 | 355 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_013.json) |
| [R014](R014.tsv) | 100 | 204 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_014.json) |
| [R015](R015.tsv) | 100 | 211 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_015.json) |
| [R016](R016.tsv) | 100 | 210 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_016.json) |
| [R017](R017.tsv) | 100 | 305 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_017.json) |
| [R018](R018.tsv) | 100 | 205 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_018.json) |
| [R019](R019.tsv) | 100 | 230 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_019.json) |
| [R020](R020.tsv) | 100 | 489 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_020.json) |
| [R021](R021.tsv) | 100 | 323 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_021.json) |
| [R022](R022.tsv) | 100 | 190 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_022.json) |
| [R023](R023.tsv) | 100 | 190 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_023.json) |
| [R024](R024.tsv) | 100 | 125 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_024.json) |
| [R025](R025.tsv) | 100 | 102 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_025.json) |
| [R026](R026.tsv) | 100 | 104 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_026.json) |
| [R027](R027.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_027.json) |
| [R028](R028.tsv) | 100 | 106 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_028.json) |
| [R029](R029.tsv) | 100 | 165 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_029.json) |
| [R030](R030.tsv) | 19 | 19 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/research/RESEARCH_030.json) |

## Уточнение объявлений

Уже принятые реализации. Продвигать статус по независимому доказательству объявления. Дополнительного кредита за реконструкцию тела нет.

| Партия | Заданий | ELF-строк | Полный манифест на VM101 |
|---|---:|---:|---|
| [D001](D001.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_001.json) |
| [D002](D002.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_002.json) |
| [D003](D003.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_003.json) |
| [D004](D004.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_004.json) |
| [D005](D005.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_005.json) |
| [D006](D006.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_006.json) |
| [D007](D007.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_007.json) |
| [D008](D008.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_008.json) |
| [D009](D009.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_009.json) |
| [D010](D010.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_010.json) |
| [D011](D011.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_011.json) |
| [D012](D012.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_012.json) |
| [D013](D013.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_013.json) |
| [D014](D014.tsv) | 100 | 101 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_014.json) |
| [D015](D015.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_015.json) |
| [D016](D016.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_016.json) |
| [D017](D017.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_017.json) |
| [D018](D018.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_018.json) |
| [D019](D019.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_019.json) |
| [D020](D020.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_020.json) |
| [D021](D021.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_021.json) |
| [D022](D022.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_022.json) |
| [D023](D023.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_023.json) |
| [D024](D024.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_024.json) |
| [D025](D025.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_025.json) |
| [D026](D026.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_026.json) |
| [D027](D027.tsv) | 100 | 100 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_027.json) |
| [D028](D028.tsv) | 39 | 39 | [JSON](../../temp/recovery-work/control10x20-after-4fed70d11/selection/rolling10x10-to-finish/followup-tracks02/declaration/DECLARATION_028.json) |
