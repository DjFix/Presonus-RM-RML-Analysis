import argparse
import hashlib
import json
from pathlib import Path

def read(p):
    return json.loads(Path(p).read_bytes())

def ref(p):
    with Path(p).open("rb") as handle:
        return {"path": str(p), "sha256": hashlib.file_digest(handle, "sha256").hexdigest()}

parser=argparse.ArgumentParser()
for flag in ("admission","codec","historical","verified-graph","aggregate","out"):
    parser.add_argument("--"+flag, type=Path, required=True)
parser.add_argument("--source-publication", type=Path, required=True)
parser.add_argument("--failed-graph", type=Path, action="append", required=True)
args=parser.parse_args()
failed=args.failed_graph
restored=args.verified_graph
failed_commands=[read(run/"COMPLETED.json") for run in failed]
restored_command=read(restored/"COMPLETED.json")
proof=read(restored/"VERIFIED.json")
aggregate=read(args.aggregate)
assert all(command["returncode"] != 0 for command in failed_commands) and restored_command["returncode"] == 0
assert aggregate["verified_generations"] == 9
assert not proof["pending_or_unregistered"]
references=[ref(run/"COMPLETED.json") for run in failed]
references.extend(ref(run/name) for run in failed
                  for name in ("PUBLISHER_OOM_ROLLBACK.json", "TERMINAL_BUDGET_REFUSAL.json", "TERMINAL_GUARD_REFUSAL.json")
                  if (run/name).is_file())
references.extend(ref(p) for p in (restored/"COMPLETED.json",restored/"VERIFIED.json",args.aggregate))
p=restored/"RECOVERY_PROVENANCE.json"
if p.is_file():
    references.append(ref(p))
for name in ("MEASURED_RESUME_AND_PUBLICATION.json", "REGISTERED_INPUT_COMPARISON.json"):
    measured=restored/name
    if measured.is_file():
        references.append(ref(measured))
failed_durations=", ".join(f"{cmd['wall_seconds']:.3f}" for cmd in failed_commands)
publication=read(args.source_publication)
assert publication["resume"]["additional_transferred_source_rows"] == 0
references.append(ref(args.source_publication))
graph={
    "source_publication":publication,
    "kind":"closing_graph","verified_utc":proof["verified_utc"],
    "phase_windows":[{k:r[k] for k in ("start_utc","end_utc")} for r in (*failed_commands,restored_command)],
    "summary":f"Первый публикатор завершился из-за OOM, следующий отказал по проверяемому бюджету. Неудачные команды сохранены с фактической длительностью {failed_durations} с. Завершающая команда прошла за {restored_command['wall_seconds']:.3f} с; регистрация и отсутствие незавершённых изменений проверены.",
    "receipts":references,
}
gates=[read(p) for p in (args.admission,args.codec,args.historical)]+[graph]
with args.out.open("x") as handle:
    json.dump({"gates":gates},handle,indent=2)
    handle.write("\n")
