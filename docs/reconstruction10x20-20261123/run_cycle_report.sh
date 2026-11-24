#!/usr/bin/env bash
set -euo pipefail
export PYTHONHASHSEED=0
if [[ $# -lt 3 ]]; then
  echo 'usage: run_cycle_report.sh REPO CONFIG REPORT_ARGUMENTS...' >&2
  exit 2
fi
repo="$(realpath "$1")"
config="$(realpath "$2")"
shift 2
cd "$repo"
uc-library/.venv/bin/python - "$config" "$@" <<'PY'
import json
from pathlib import Path
import subprocess
import sys

config = json.loads(Path(sys.argv[1]).read_bytes())
command = [sys.executable, "uc-library/tools/recovery/report_cycle_timing.py", "report"]
for key in ("cycle", "evidence", "previous", "coverage"):
    command.extend(("--" + key, config[key]))
for key, flag in (("replacement_plans", "--replacement-plan"),
                  ("historical_task_plans", "--historical-task-plan")):
    for path in config[key]:
        command.extend((flag, path))
subprocess.run(command + sys.argv[2:], check=True)
PY
