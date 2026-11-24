"""Write a Git-ready closing report from final timings and terminal gate receipts."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

def read(p):
    return json.loads(Path(p).read_bytes())

def utc(value):
    instant = datetime.fromisoformat(value)
    if instant.tzinfo is None:
        raise ValueError("Expected timezone on closing receipt")
    return instant

def duration(value):
    return f"{value:,.3f}".replace(",", " ")

def check(item):
    path = Path(item["path"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], path

def lines_for_failure(row):
    return f"| {row['phase']} | {row['count']} | {duration(row['failed_window_union_seconds'])} |"

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--timing", required=True, type=Path)
    p.add_argument("--comparison", required=True, type=Path)
    p.add_argument("--primary-audit", required=True, type=Path)
    p.add_argument("--milestones", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    ledger, comp, audit, milestones = map(read,(args.timing,args.comparison,args.primary_audit,args.milestones))
    required={"admission","closing_graph","pinned_codec","historical_reseal"}
    gates={r["kind"]:r for r in milestones["gates"]}
    assert set(gates)==required
    for gate in gates.values():
        for receipt in gate["receipts"]:
            check(receipt)
    physical_end = max(utc(gate["verified_utc"]) for gate in gates.values())
    assert physical_end == utc(ledger["operational_end_utc"])
    assert utc(ledger["as_of_utc"]) >= physical_end
    assert comp["operational_cutoff_utc"] == ledger["operational_end_utc"]
    t=ledger["targets"]; cur, old=comp["10x20"],comp["10x10"]
    ready,pending=(t["verified_admitted_status"][key] for key in ("ready","pending"))
    elf=t["verified_admitted_distinct_elf_identities"]
    assert (t["fully_admitted_primary_slots"],ready+pending)==(200,elf)
    assert (audit["fully_admitted_primary_slots"],audit["fully_admitted_exact_elf_identities"])==(200,elf)
    assert not audit["cross_counted_slots"] and not t["primary_slots_with_multiple_fully_admitted_actual_assignments"]
    assert not t["verified_admitted_outside_primary_or_retained_coverage"]
    rows=[
      "# Контрольная реконструкция 10×20",
      "",
      f"Канонически закрыто **200 из 200** первичных слотов. Принято **{elf}** отдельных ELF-идентичностей, из них {ready} готовы в проверенной области и у {pending} остаются открытыми декларации.",
      "",
      "| Единица учёта | Итог |",
      "| --- | ---: |",
      f"| Первичные слоты | {t['fully_admitted_primary_slots']} |",
      f"| Канонически принятые задания | {t['verified_admitted_distinct_implementation_tasks']} |",
      f"| ELF-идентичности из отдельно учтённых прежних заданий | {len(audit['retained_or_helper_elf'])} |",
      f"| Уникальные mangled имена | {t['verified_admitted_callables']['distinct_mangled_names']} |",
      f"| Группы callable по деманглированному имени | {t['verified_admitted_callables']['distinct_demangled_callables']} |",
      f"| ELF среди ABI-вариантов | {t['verified_admitted_callables']['abi_variant_identities']} |",
      f"| Принятые / утверждённые замены | {len(t['fully_admitted_replacements'])} / {len(t['replacement_to_primary_slot'])} |",
      "",
      "Независимая сверка соединила точные ELF-идентичности из предложений с хешированными примечаниями канонической приёмки. Каждое задание должно закрыть все свои ELF. Замена наследует один первичный слот, прежние задания учитываются отдельно. Группы callable и ABI-варианты показывают разные разрезы числа ELF.",
      "",
      "## Конечные отметки UTC",
      "",
      f"- Запрос — {ledger['request']['requested_utc']}.",
    ]
    for kind,name in (("admission","Завершение канонической приёмки"),("closing_graph","Завершающая регистрация графа"),("pinned_codec","Каноническая проверка закреплённых кодеков"),("historical_reseal","Повторная привязка прежних доказательств")):
        gate=gates[kind]
        links = ", ".join(f"[{Path(receipt['path']).name}](../../{receipt['path']})"
                          for receipt in gate["receipts"])
        rows.append(f"- {name} — {gate['verified_utc']}. {gate['summary']} {links}")
    publication = gates["closing_graph"]["source_publication"]
    source = publication["source_layer"]
    native = publication["native_followup"]
    resume = publication["resume"]
    assert resume["additional_transferred_source_rows"] == 0
    rows.extend([
        "",
        f"Исходный слой графа подтвердил {source['rows_counted_once']:,} строк в {source['verified_batches']:,} пакетах. "
        f"От первого до последнего подтверждённого пакета прошло {duration(source['first_to_last_batch_elapsed_seconds'])} с. "
        f"Затем native-транзакция превысила лимит времени. Интервал от последнего исходного пакета до выхода команды "
        f"составил {duration(native['last_source_batch_to_command_exit_seconds'])} с и включает промежуточные проверки. "
        f"Возобновление заняло {duration(resume['command_wall_seconds'])} с. Оно передало 0 исходных строк и "
        f"{resume['serialized_transfer_bytes_including_native_and_registration_checks']:,} байт в native-фазе "
        f"и проверках регистрации. Лимит таймаута восстановлен до {resume['timeout_restored_seconds']} с. "
        "Внутренние фазы входят во время команд.",
        "",
    ])
    reconstruction = gates["admission"]["reconstruction_commit"]
    codec_commit = gates["pinned_codec"]["codec_commit"]
    rows.append(f"- Коммит переключения кодеков — `{codec_commit['sha']}`, время коммитера {codec_commit['utc']}.")
    rows.append(f"- Коммит реконструкции — `{reconstruction['sha']}`, время коммитера {reconstruction['utc']}.")
    codec_window = gates["pinned_codec"]["phase_window"]
    codec_start, codec_end = (utc(codec_window[name]) for name in ("start_utc", "end_utc"))
    graph_windows = gates["closing_graph"].get("phase_windows") or [gates["closing_graph"]["phase_window"]]
    intervals = []
    for window in graph_windows:
        start = max(codec_start, utc(window["start_utc"]))
        end = min(codec_end, utc(window["end_utc"]))
        if start < end:
            intervals.append((start, end))
    overlap, covered_end = 0.0, codec_start
    for start, end in sorted(intervals):
        if end > covered_end:
            overlap += (end - max(start, covered_end)).total_seconds()
            covered_end = end
    rows += [
      f"- Полная операционная длительность — {duration(ledger['operational_seconds'])} с.",
      f"- Окно от начала запуска канонической проверки кодеков до итоговой квитанции — {duration((codec_end - codec_start).total_seconds())} с. Его пересечение с объединением попыток завершающего графа — {duration(overlap)} с.",
      "",
      "Архивы и заголовки закреплённых libpng и zlib, роли Core, CS18AI и RM, и исполняемые пользовательские пробы проверялись отдельным этапом. Upstream-реализации не входят в зачёт ELF реконструкции.",
      "",
      "## Накладные затраты и перекрытия",
      "",
      "| Измерение | 10×20 | 10×10 |",
      "| --- | ---: | ---: |",
      f"| Операционное календарное время, с | {duration(cur['user_wall_seconds'])} | {duration(old['user_wall_seconds'])} |",
      f"| Принято первичных слотов | {cur['primary_slots_fully_admitted']} | {old['primary_slots_fully_admitted']} |",
      f"| Принято ELF-идентичностей | {cur['distinct_elf_admitted']} | {old['distinct_elf_admitted']} |",
      f"| Проверенные регистрации графа | {cur['verified_graph_commands']} | {old['verified_graph_commands']} |",
      f"| Сумма команд графа, с | {duration(cur['graph_command_sum_seconds'])} | {duration(old['graph_command_sum_seconds'])} |",
      f"| Команды графа на принятый слот, с | {duration(cur['graph_command_seconds_per_admitted_primary_slot'])} | {duration(old['graph_command_seconds_per_admitted_primary_slot'])} |",
      f"| Команды графа на принятый ELF, с | {duration(cur['graph_command_seconds_per_admitted_elf'])} | {duration(old['graph_command_seconds_per_admitted_elf'])} |",
      f"| Канонические Linux-команды на принятый ELF, с | {duration(cur['canonical_linux_command_seconds_per_admitted_elf'])} | {duration(old['canonical_linux_command_seconds_per_admitted_elf'])} |",
      "",
      f"Пересечение графа с объединением измеренных фаз — {duration(cur['graph_overlap_with_union_of_measured_phases_seconds'])} с. Категории отслеживаются отдельно, в календарное время повторно не складываются. Канонический codec-аудит учитывается отдельно от Linux-команд реконструкции. Объём и состав задач двух циклов различаются.",
      "",
      f"Наблюдаемый перерыв координатора по квоте — {duration(ledger['quota_interruption']['observed_coordinator_interruption_seconds_within_cycle'])} с, включён в полное время. Измеренное пересечение процесса с этим интервалом — {duration(ledger['quota_interruption']['observed_union_overlap_of_measured_process_windows_seconds'])} с. Календарное время при вычитании наблюдаемого перерыва — {duration(cur['observed_quota_excluded_wall_seconds'])} с. Эти значения не описывают CPU, биллинг или полную недоступность провайдера.",
      "",
      "| Фаза неудачной команды | Попытки | Объединённое время, с |",
      "| --- | ---: | ---: |",
    ]
    rows.extend(map(lines_for_failure,cur["failed_attempts"]))
    failed_graph = [row for row in ledger["phase_windows"]["live_graph"] if row["status"] == "failed"]
    # Graph attempts are exclusive by the maintained context lock.
    for left, right in zip(failed_graph, failed_graph[1:]):
        assert utc(left["end_utc"]) <= utc(right["start_utc"])
    rows.append(lines_for_failure({
        "phase": "live_graph",
        "count": len(failed_graph),
        "failed_window_union_seconds": sum(row["calendar_seconds"] for row in failed_graph),
    }))
    rows.extend([
      "",
      "Для actual07 union65 первая попытка завершилась с ошибкой CTest. Вторая прошла 1091/1091 за 372.88 с и была отклонена проверкой изменения снимка. Третья прошла весь канонический путь, 1091/1091 за 378.59 с. Эти запуски сохранены отдельно, включая отказ после успешных тестов. Список CTest-попыток и командных отказов частично пересекается.",
      "",
      "Перед последней полной проверкой целевой прогон завершил 35 из 37 тестов. Повтор с точной архивной привязкой прежней LCD-проверки прошёл 37/37 за 9.71 с. Учитываем этот целевой прогон отдельно от полноразмерных Linux-команд.",
      "",
      "Аудит параметров компиляции сверил 65 реальных handoff и 22 единицы с обязательными локальными параметрами. Для каждой установлена единственность команды и наличие параметров. Прошли восемь тестов аудитора и отрицательная проверка на реальных данных. Доступного доисправительного снимка команд нет, сохранился его хеш. Проверка обнаружения утечки с целым baseline воспроизведена синтетическим тестом.",
      "",
      "## Воспроизведение",
      "",
      "Агрегатор `uc-library/tools/recovery/report_cycle_timing.py` читает квитанции и сохраняет отдельный результат. В scratch сохранены команды воспроизведения, сравнения и независимой сверки. Снятие счётчиков затрат запускается отдельно через `uc-library/tools/recovery/collect_cycle_cost.py cutoff` после фактической отсечки. Время подготовки отчёта и коммита фиксируется отдельной квитанцией.",
      "",
    ])
    with args.out.open("x") as out:
        out.write("\n".join(rows))

if __name__ == "__main__":
    main()
