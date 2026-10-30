"""Derive the next fixed SPI source-closure refresh with unchanged proof gates."""
import ast,hashlib,json,subprocess,sys
from pathlib import Path
repo=Path('/home/rs/projects/opencs/ai-line-analysis')
base=repo/'uc-library/tools/recovery/prepare_pot_fader_spi.py';target=repo/'uc-library/tools/recovery/prepare_network_biquad_spi_snapshot.py'
assert not target.exists()
t=base.read_text().replace('noaa-spi-service-refresh-pot-fader','noaa-spi-service-refresh-network-biquad').replace("phase='pot-fader-root'","phase='network-biquad-root'")
t=t.replace("replace('dispatch-transfers-root','pot-fader-root')","replace('dispatch-transfers-root','network-biquad-root')").replace("replace('noaa-spi-service-dispatch-transfers','noaa-spi-service-pot-fader')","replace('noaa-spi-service-dispatch-transfers','noaa-spi-service-network-biquad')")
ast.parse(t);target.write_text(t);subprocess.run([sys.executable,str(target)],check=True)
phase=repo/'evidence/recovery/2026-10-27/network-biquad-root';phase.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(phase/'spi-operator-derivation.json').write_text(json.dumps(dict(source=str(base.relative_to(repo)),source_sha256=sha(base),derived=str(target.relative_to(repo)),derived_sha256=sha(target),changes='Only phase paths; snapshot generated from current admitted SPI identities'),indent=2)+'\n')
