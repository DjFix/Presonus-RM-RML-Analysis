"""Derive fixed batch operators; keep the actual merger and validation gates."""
import ast,hashlib,json
from pathlib import Path
repo=Path('/home/rs/projects/opencs/ai-line-analysis');lib=repo/'uc-library';phase=repo/'evidence/recovery/2026-10-27/network-biquad-root'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=repo/'uc-library/tools/recovery/admit_pot_fader.py';target=repo/'uc-library/tools/recovery/admit_network_biquad.py';assert not target.exists()
t=base.read_text().replace('pot-fader-root','network-biquad-root').replace('noaa-spi-service-pot-fader','noaa-spi-service-network-biquad')
start=t.index('audits=list(');end=t.index('raw=read(',start)
t=t[:start]+'''ctor='candidates/dsp-biquad-calc/validation/constructor-active-01/'
network='validation/uc-network-manager-services/active-01/'
assert read(lib/ctor/'validation.json')['active_source_gate']['passed']
assert read(lib/network/'audit.json')['active_source_replay_passed']
'''+t[end:]
old="inputs={'--fragment':[active+'ready.fragment.json',spi+'ready-functions.fragment.json'],'--pending':[active+'pending.fragment.json',spi+'pending-functions.fragment.json']}"
new="inputs={'--fragment':[ctor+'ready.fragment.json',spi+'ready-functions.fragment.json'],'--pending':[network+'pending-fragment.json',spi+'pending-functions.fragment.json']}"
assert t.count(old)==1;t=t.replace(old,new)
t=t.replace("canonical_ctest_count']==126","canonical_ctest_count']==132").replace("headers['headers']==84","headers['headers']==87")
t=t.replace('==(638,342,392)','==(639,343,403)').replace('ready=638,mangles=342,pending=392','ready=639,mangles=343,pending=403').replace('==(622,378)','==(638,393)')
ast.parse(t);target.write_text(t)
rawbase=lib/'candidates/efm-fader-control-dispatch/tools/seal_raw_root_pot_fader.py';rawtarget=rawbase.with_name('seal_raw_root_network_biquad.py');assert not rawtarget.exists()
r=rawbase.read_text().replace('pot-fader-root','network-biquad-root').replace('==126','==132').replace('canonical_ctest_count=126','canonical_ctest_count=132');ast.parse(r);rawtarget.write_text(r)
(phase/'validation-operator-derivation.json').write_text(json.dumps(dict(admission=dict(source=str(base.relative_to(repo)),source_sha256=sha(base),derived=str(target.relative_to(repo)),derived_sha256=sha(target)),raw=dict(source=str(rawbase.relative_to(lib)),source_sha256=sha(rawbase),derived=str(rawtarget.relative_to(lib)),derived_sha256=sha(rawtarget)),scope='Fixed phase inputs/counts only; unchanged actual merger and all original range/source/native gates'),indent=2)+'\n')
manifest=dict(phase='network-biquad-validation-operators',transfers=[dict(direction='push',area='library',paths=[str(rawtarget.relative_to(lib))]),dict(direction='push',area='operators',paths=['admit_network_biquad.py']),dict(direction='push',area='evidence',paths=['2026-10-27/network-biquad-root/validation-operator-derivation.json'])])
(repo/'temp/recovery-work/sync-network-biquad-validation.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(admission_sha256=sha(target),raw_sha256=sha(rawtarget))))
