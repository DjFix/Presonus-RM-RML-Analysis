# ТЗ: отдельный Memgraph в LXC на PVE

Сделать рабочий сервис, не ограничиваться планом. Пользователь разрешил отдельный
контейнер на PVE, минимум 16 GiB памяти для Memgraph и доступ к графам из всей
локалки. Установка, сеть, доступы, перенос данных и проверка входят в задачу.
Не запускать реконструкцию C++ или сабагентов реконструкции.

## Контекст и границы

Клиент и канонический проект остаются на VM101:
`/home/rs/projects/opencs/ai-line-analysis`, пользователь `rs`.
Текущий адрес VM101: **192.168.50.238/24**, gateway **192.168.50.1**;
интерфейс `enp6s18`, hostname `fs-rs`. Эти значения проверены 2026-10-31.
PVE node, storage, bridge, свободный CTID и адрес нового CT определить из реальной
конфигурации PVE/IPAM. Их нельзя угадывать или занимать адрес по одному ping.
Нужен статический адрес/резервация в **192.168.50.0/24**, hostname `memgraph-uc`.
Если hostname уже занят — выбрать уникальный и зафиксировать.

Сначала прочитать проектный AGENTS.md. Сохранить оригинальные ELF, старые БД,
Docker volumes, контейнеры, snapshots, логи и proofs. Canonical SQLite readiness,
firmware и исходники не переносить в CT и не менять. Memgraph — производный индекс.
Не редактировать рабочие selector/registry/build-файлы параллельно Root; для смены
endpoint вернуть точные параметры и проверенный адрес Root.

## Ресурсы — конкретная конфигурация

| Ресурс | Значение |
| --- | --- |
| PVE guest | Отдельный unprivileged LXC, x86_64 |
| CPU | 4 vCPU |
| RAM LXC | **20 GiB** |
| Swap LXC | 2 GiB, не замена RAM |
| Внутренний Memgraph memory-limit | **16384 MiB = 16 GiB** |
| Docker memory limit для Memgraph | **18 GiB** |
| Memgraph Lab | До 1 GiB RAM |
| Root filesystem CT | **32 GiB** |
| Отдельный постоянный data mount | **64 GiB**, `/srv/memgraph` |
| Всего диска | **96 GiB**, root + data |

20 GiB для CT нужны, чтобы Memgraph действительно получил 16 GiB, а не делил
общий лимит 16 GiB с ОС, Docker и Lab. Проверить реальные свободные ресурсы PVE;
не уменьшать память других гостей и не делать скрытый overcommit ради выполнения.
Если 20 GiB невозможно выделить, вернуть фактическую доступность и конкретный
блокер; не запускать конфигурацию с лимитом Memgraph ниже 16 GiB.

Текущий volume Memgraph занимает **6 479 602 531 байт (~6.03 GiB)**; текущий MAGE
image — **2 403 462 285 байт**. Data 64 GiB предусматривает snapshots, WAL,
транзакционное обновление полного графа и рост; root 32 GiB — ОС, образы и обновления.
Большие данные/логи не должны незаметно заполнять root. Зафиксировать mountpoint,
реальный размер и свободное место. Не резервировать лишь 4 GiB диска: прежняя
ошибка относилась к RAM.

## Установка и эксплуатация

- Поддерживаемая Debian/Ubuntu LXC template. Docker Engine + Compose plugin
  внутри CT; не устанавливать Docker или зависимости Memgraph на сам PVE host.
- Для unprivileged LXC включить необходимые `nesting`/`keyctl` в соответствии
  с установленной версией PVE. Проверить Docker/cgroup limits. Не превращать CT
  в privileged и не отключать AppArmor целиком как способ скрыть ошибку запуска.
- Memgraph: **`memgraph/memgraph-mage:3.13.0`**, как текущий экземпляр. Записать
  image digest. Не совмещать перенос с апгрейдом формата БД.
- Memgraph Lab отдельным Docker service, совместимый release с конкретным
  tag/digest в итоговой конфигурации; не оставлять `latest` единственной фиксацией.
- Compose/config под `/opt/memgraph/`; data `/srv/memgraph/data` →
  `/var/lib/memgraph`, persistent logs `/srv/memgraph/log` → `/var/log/memgraph`.
  Проверить фактический UID/GID image и доступ на запись из unprivileged CT.
- `--memory-limit=16384`, `--storage-mode=IN_MEMORY_TRANSACTIONAL`.
  Не переключать storage mode ради обхода транзакционных гарантий.
- Services стартуют после reboot CT, `restart: unless-stopped` или эквивалентная
  воспроизводимая systemd/Compose конфигурация. Проверить настоящий запрос
  `RETURN 1`, а не только наличие процесса/открытого TCP-порта.
- Сохранить recovery snapshots/WAL; описать backup/restore и сделать исходный
  backup после установки. Дисковый backup не должен быть единственной копией
  внутри того же data volume. Существующие исходные backups не удалять.
- Не включать TRACE по умолчанию и не создавать неограниченно растущие Docker logs;
  настроить bounded log rotation и показать конфигурацию.

## Сеть: доступ из ВСЕЙ локалки

Это не сервис только для VM101. Пользователь должен открыть браузер на своём
компьютере в LAN и увидеть настоящий граф.

| TCP порт CT | Кто может обращаться | Назначение |
| --- | --- | --- |
| 22 | `192.168.50.0/24`, SSH по ключам | Обслуживание |
| 7687 | `192.168.50.0/24` | Bolt, скрипты VM101 и LAN-клиенты |
| 3000 | `192.168.50.0/24` | Memgraph Lab в браузере |
| 7444 | `192.168.50.0/24` | Поддерживаемый интерфейс логов/monitoring для Lab |

Не bind-ить эти ports только к 127.0.0.1. Привязать опубликованные порты к
LAN IP CT и проверить реальную доступность. **Не делать WAN port forwarding**;
вход снаружи LAN не нужен. Firewall PVE/CT должен учитывать Docker forwarding:
одного правила UFW, которое Docker обходит, недостаточно. Не менять глобальные
firewall rules PVE так, чтобы затронуть остальные VM/CT или доступ к самому PVE.
DNS, NTP и исходящий доступ для установки/registry должны работать.

Сохранить текущий dev-режим Bolt **без auth**, доступный в доверенной локалке;
существующие Python-клиенты используют `auth=None`. Не вводить обязательную
Enterprise/RBAC-лицензию или произвольный пароль, который сломает эти клиенты.
SSH — только по ключам, password login и root SSH отключить.

Lab:
- URL **`http://<CT_LAN_IP>:3000`**.
- Bolt для внешних клиентов **`bolt://<CT_LAN_IP>:7687`**.
- В Compose установить `QUICK_CONNECT_MG_HOST` в имя Memgraph service,
  `QUICK_CONNECT_MG_PORT=7687`; проверить подключение именно браузером.
- Сохранённое/автоматически восстановленное соединение `UC dependency graph`.
- Не грузить demo dataset: в Lab должны быть наши source/native индексы.
- Проверить и прямой доступ с VM101, и доступ из Docker runner на VM101
  (`dependency-graph-experiment` network). Host `/etc/hosts` сам по себе
  не меняет DNS внутри Docker. Старое имя `dependency-graph-memgraph` сейчас
  используется скриптами; не делать вид, что оно автоматически указывает на CT.
  Передать Root endpoint для централизованного переключения клиентов.

## SSH: точный ключ для обслуживания с VM101

Создан отдельный Ed25519-ключ для этого сервиса. Приватный ключ остаётся ТОЛЬКО на
VM101: `/home/rs/.ssh/id_ed25519_memgraph_pve`, mode 0600. Не читать/не копировать
его в чат, проект, PVE или CT. Старый личный RSA/GitLab-ключ не переиспользовать.

Публичный ключ (одна строка, без переноса):

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGU8V7LrvFnIt+B3QhfGNk2UzQ5rRXEJVQ1or8vEOHhe rs@vm101 memgraph-pve maintenance 2026-10-31
```

Fingerprint:

```text
SHA256:kLhCKfztI2IUIWlT3YG25EV9f2BoEHRw8FckFufiYHM
```

Копия: `dependency-graph/ops/keys/vm101-memgraph-pve.pub` на VM101.
Создать в CT пользователя **`rs`** с обычным shell и home. Установить эту строку
в `/home/rs/.ssh/authorized_keys` с владельцем rs, directory 0700, file 0600.
Для данной ключевой строки допустимы source restriction и запрет forwarding:

```text
from="192.168.50.238",no-agent-forwarding,no-X11-forwarding,no-port-forwarding ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGU8V7LrvFnIt+B3QhfGNk2UzQ5rRXEJVQ1or8vEOHhe rs@vm101 memgraph-pve maintenance 2026-10-31
```

Доступ Lab/Bolt из остальной локалки этим не ограничивать: это только SSH-ключ
автоматического обслуживания VM101. Если у владельца уже задан его личный public
key — сохранить/добавить его отдельно; не требовать его для работы браузерного Lab.
Адрес VM101 должен оставаться стабильным; не менять его сеть без необходимости.

`rs` обслуживает сервис через root-owned `/usr/local/sbin/memgraphctl` с фиксированными
действиями status/logs/start/stop/restart/health/snapshot и неизменяемым rs Compose.
Sudoers разрешает NOPASSWD только для этих действий wrapper. Не выдавать
NOPASSWD:ALL, членство в Docker group или произвольный root shell. Это не доступ
к PVE host; maintenance-ключ CT не устанавливать в PVE root authorized_keys.
Проверить с VM101:

```sh
ssh -i /home/rs/.ssh/id_ed25519_memgraph_pve -o IdentitiesOnly=yes -o BatchMode=yes rs@<CT_LAN_IP> 'hostname; sudo -n /usr/local/sbin/memgraphctl status'
```

Получить ED25519 host-key fingerprint CT через доверенный канал PVE `pct exec`,
вернуть его в handoff и сверить перед добавлением в VM101 known_hosts.
Не использовать `StrictHostKeyChecking=no` как постоянное решение.

## Данные и текущее незавершённое обновление

На VM101 уже есть наш граф, не начинать с пустой БД без миграции.
Текущий Docker container: `dependency-graph-memgraph`, image 3.13.0,
**8 GiB effective Memgraph / 10 GiB Docker**, license memory limit unlimited.
Volume: `dependency-graph-memgraph-data` → `/var/lib/memgraph`.
Сохранён старый остановленный container
`dependency-graph-memgraph-retained-20261031-4g`; его не удалять.

Последний snapshot, проверенный при восстановлении нового local container:
`/var/lib/memgraph/snapshots/20261031160047672476_timestamp_24528`.
После восстановления были **551 198 `Artifact`** и **204 204 `NativeArtifact`**.
Это контрольные числа сохранённого состояния, не гарантия будущего числа после
новых публикаций. Перед реальным переносом снять свежие counts по labels/types,
индексы и generation markers, создать новый consistency snapshot.

В source refresh есть **незавершённая публикация**, а не незавершённая компиляция:
`temp/recovery-work/dependency-graph/refresh/1793460399608072116`.
`dependency-graph/state/refresh-index.sqlite` хранит durable `pending` journal.
Delta и compiler observations уже собраны; последний apply откатился по лимиту
RAM 4 GiB. Root повторно компилировал только 10 не прошедших TU и переиспользовал
620 завершённых наблюдений с проверкой хешей.

**Не выставлять `ContextGeneration.state=ready` вручную.** Перенос инфраструктуры
не доказывает, что граф соответствует последним исходникам. Root должен
возобновить sealed delta после переключения endpoint, без нового полного
пересчёта. Готовый dedup index находится на VM101:
`temp/recovery-work/dependency-graph/dedup-10/dedup.sqlite`,
указатель `dependency-graph/DEDUP_ACTIVE.json`; его не переносить в Memgraph CT.

Порядок переноса:
1. Сначала поднять новый CT, Docker, сеть, ключи и Lab, не трогая старый сервис.
2. Проверить живые jobs и общий lock
   `dependency-graph/state/context.lock` на VM101. Не прерывать работающий producer
   или retry из-за ожидания. Фактическое состояние может измениться после этого ТЗ.
3. При согласованном idle-write окне создать snapshot и сохранить counts/markers.
   Перенести совместимый snapshot/WAL штатным recovery-путём той же версии,
   либо консистентную копию остановленного volume. Не копировать live volume как
   будто он атомарен. Старые данные остаются на VM101 для rollback.
4. На CT восстановить graph, проверить counts/edge types/markers и реальные
   запросы. Перенос не должен потерять native/source projections и индексы.
5. Передать Root точный endpoint, SSH host fingerprint, manifests и команды.
   Root переключает project clients и возобновляет pending publication.
6. После проверенного cutover старый локальный instance можно оставить
   остановленным. Не удалять старые containers/volumes/snapshots.

## Приёмка и результат агента

Сохранить reproducible bootstrap/Compose, точные версии/digests, ресурсы CT,
network/firewall config, migration manifest с hashes и логи проверок. Проверить:

- `pct config <CTID>`: unprivileged, CPU, RAM, swap, root/data mounts, bridge/IP.
- `SHOW STORAGE INFO`: effective **memory_limit >= 16 GiB**, записать также
  license_memory_limit, а не только число в Docker command.
- SSH BatchMode с новым ключом от VM101 и `sudo -n` без пароля.
- Bolt-запрос с VM101 **и из Docker runner VM101** по новому endpoint.
- HTTP Lab с LAN, реальный запрос и отображение графа; одного HTTP 200 недостаточно.
- Reboot CT, повторная доступность SSH/Bolt/Lab и неизменность graph counts.
- После restore сохранить source/native generation states как в snapshot;
  publication-ready проверяет Root, не инфраструктурный агент.

Нужные запросы для Lab и контрольных counts:

```cypher
MATCH (n:Artifact) RETURN count(n) AS source_nodes;
MATCH (n:NativeArtifact) RETURN count(n) AS native_nodes;
MATCH (:Artifact)-[r]->(:Artifact) RETURN type(r), count(r);
MATCH (:NativeArtifact)-[r]->(:NativeArtifact) RETURN type(r), count(r);
MATCH (g:ContextGeneration) RETURN g.id, g.state, g.digest;
MATCH (g:NativeGeneration) RETURN g.id, g.state, g.digest;
MATCH (n:NativeArtifact)
WHERE n.label CONTAINS 'Book::isValidPos'
OPTIONAL MATCH (n)-[r]-(m:NativeArtifact)
RETURN n,r,m LIMIT 100;
```

В финальном handoff выдать коротко:
**PVE node/CTID, IP/hostname, Lab URL, Bolt URI, SSH command и host fingerprint,
фактические RAM/disk limits, Compose location, backup/restore, counts/markers,
что готово к cutover и что должен выполнить Root с pending journal.**
Только реально проведённые проверки отмечать успешными. Если доступа к PVE нет,
не выдумывать CTID/адрес: завершить доступную подготовку и назвать точный blocker.

## Официальные справочные страницы

- Memgraph memory-limit — RAM, MiB и effective/license limit:
  https://memgraph.com/docs/fundamentals/storage-memory-usage
- Docker Compose и Memgraph Lab ports/Quick Connect:
  https://memgraph.com/docs/getting-started/install-memgraph/docker-compose
- Lab remote connections:
  https://memgraph.com/docs/memgraph-lab/getting-started/connection-types
- PVE LXC: https://pve.proxmox.com/wiki/Linux_Container
  (страница недоступна из VM101 с HTTP 403; версию/доступные options проверить на PVE).
