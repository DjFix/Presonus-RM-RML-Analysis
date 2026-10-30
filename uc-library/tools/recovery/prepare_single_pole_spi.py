"""Derive the next fixed SPI CMake refresh; retain all existing proof gates."""
import ast,hashlib,json,subprocess,sys
from pathlib import Path
repo=Path('/home/rs/projects/opencs/ai-line-analysis')
base=repo/'uc-library/tools/recovery/prepare_pot_fader_spi.py'
target=repo/'uc-library/tools/recovery/prepare_single_pole_spi_snapshot.py'
assert not target.exists()
text=base.read_text().replace('noaa-spi-service-refresh-pot-fader','noaa-spi-service-refresh-single-pole').replace("phase='pot-fader-root'","phase='single-pole-root'")
# Replacement strings in the template, not the previous phase's source files.
text=text.replace("replace('dispatch-transfers-root','pot-fader-root')","replace('dispatch-transfers-root','single-pole-root')").replace("replace('noaa-spi-service-dispatch-transfers','noaa-spi-service-pot-fader')","replace('noaa-spi-service-dispatch-transfers','noaa-spi-service-single-pole')")
ast.parse(text);target.write_text(text)
subprocess.run([sys.executable,str(target)],check=True)
phase=repo/'evidence/recovery/2026-10-27/single-pole-root';phase.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(phase/'spi-operator-derivation.json').write_text(json.dumps(dict(source=str(base.relative_to(repo)),source_sha256=sha(base),derived=str(target.relative_to(repo)),derived_sha256=sha(target),changes='Only fixed output phase names; current snapshot hash generated from admitted ledgers'),indent=2)+'\n')
