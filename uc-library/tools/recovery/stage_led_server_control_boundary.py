"""Describe explicit stable-boundary sync and scoped formatting inputs."""
import json
from pathlib import Path

repo=Path('/home/rs/projects/opencs/ai-line-analysis')
lib=repo/"uc-library"
phase=repo/"evidence/recovery/2026-10-27/led-server-control-root"
applied=json.loads((phase/"apply-01/applied.json").read_text())
paths=sorted(applied)
cpp=[p for p in paths if Path(p).suffix in (".cpp",".hpp",".h")]
format_list="validation/format-led-server-control-paths.json"
integration_list="validation/integration-led-server-control-additions.json"
producers=["candidates/noaa-spi-refresh-led-server-control/tools/produce_existing.py","candidates/panel-led-control-lifecycle/active_reseal_led_server_control.py"]
for name,payload in ((format_list,cpp),(integration_list,sorted(set(paths+producers)))):
    target=lib/name
    assert not target.exists()
    target.write_text(json.dumps(payload,indent=2)+"\n")
manifest=dict(phase="led-server-control-application",transfers=[
    dict(direction="push",area="library",paths=sorted(set(paths+producers+[format_list,integration_list]))),
    dict(direction="push",area="evidence",paths=["2026-10-27/led-server-control-root/apply-01","2026-10-27/led-server-control-root/producer-derivatives.json"]),
    dict(direction="push",area="operators",paths=["apply_led_server_control.py","prepare_led_server_control_producers.py","stage_led_server_control_boundary.py"]),
])
target=repo/"temp/recovery-work/sync-led-server-control-application.json"
assert not target.exists()
target.write_text(json.dumps(manifest,indent=2)+"\n")
print(json.dumps(dict(cpp_paths=len(cpp),integration_inputs=len(set(paths+producers)),manifest=str(target))))
