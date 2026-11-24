#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 6 ]]; then
  echo 'usage: run_cycle_final.sh REPO CONFIG MILESTONES VERIFIED_GRAPH_AGGREGATE AS_OF_UTC OUTPUT_PREFIX' >&2
  exit 2
fi
support="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(realpath "$1")"
config="$(realpath "$2")"
milestones="$(realpath "$3")"
graph="$(realpath "$4")"
as_of="$5"
prefix="$(realpath -m "$6")"
cd "$repo"
python=uc-library/.venv/bin/python
reporter=uc-library/tools/recovery/report_cycle_timing.py
actual_end="$("$python" - "$milestones" <<'PY'
from datetime import datetime
from hashlib import file_digest
import json
from pathlib import Path
import sys

gates = json.loads(Path(sys.argv[1]).read_bytes())["gates"]
required = {"admission", "closing_graph", "pinned_codec", "historical_reseal"}
if len(gates) != len(required) or {item["kind"] for item in gates} != required:
    raise ValueError("Exactly one receipt is required for each closing gate")
for gate in gates:
    if not gate["receipts"]:
        raise ValueError(f"Missing evidence for {gate['kind']}")
    for proof in gate["receipts"]:
        with Path(proof["path"]).open("rb") as stream:
            if file_digest(stream, "sha256").hexdigest() != proof["sha256"]:
                raise ValueError(f"Terminal receipt changed: {proof['path']}")
print(max(datetime.fromisoformat(gate["verified_utc"]) for gate in gates).isoformat())
PY
)"
previous="$("$python" -c 'import json,sys; print(json.load(open(sys.argv[1]))["previous"])' "$config")"
bash "$support/run_cycle_report.sh" "$repo" "$config" --as-of "$as_of" --operational-end "$actual_end" --out "$prefix-timing.json"
"$python" "$reporter" compare --current "$prefix-timing.json" --previous "$previous" --graph "$graph" --out "$prefix-comparison.json"
(set -o noclobber; "$python" "$support/check_primary_receipts.py" "$prefix-timing.json" > "$prefix-primary-audit.json")
"$python" "$support/render_final_cycle.py" --timing "$prefix-timing.json" --comparison "$prefix-comparison.json" --primary-audit "$prefix-primary-audit.json" --milestones "$milestones" --out "$prefix.md"
