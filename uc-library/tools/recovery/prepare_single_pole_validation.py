"""Prepare fixed-phase validation operators from retained prior operators."""
import ast,hashlib,json
from pathlib import Path
repo=Path('/home/rs/projects/opencs/ai-line-analysis');lib=repo/'uc-library';phase=repo/'evidence/recovery/2026-10-27/single-pole-root'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=repo/'uc-library/tools/recovery/admit_pot_fader.py';target=repo/'uc-library/tools/recovery/admit_single_pole.py';assert not target.exists()
t=base.read_text().replace('pot-fader-root','single-pole-root').replace('noaa-spi-service-pot-fader','noaa-spi-service-single-pole')
start=t.index('audits=list(');end=t.index('raw=read(',start)
t=t[:start]+'''single=read(lib/'validation/dsp-single-pole/pending-validation.json')
assert single['cpp_differential_passed'] and single['original_ranges_rechecked_separately']
assert not single['portable_ready'] and not single['original_oracles_regenerated']
'''+t[end:]
old="inputs={'--fragment':[active+'ready.fragment.json',spi+'ready-functions.fragment.json'],'--pending':[active+'pending.fragment.json',spi+'pending-functions.fragment.json']}"
new="inputs={'--fragment':[spi+'ready-functions.fragment.json'],'--pending':['validation/dsp-single-pole/pending-functions.fragment.json',spi+'pending-functions.fragment.json']}"
assert t.count(old)==1;t=t.replace(old,new)
t=t.replace("canonical_ctest_count']==126","canonical_ctest_count']==127").replace("headers['headers']==84","headers['headers']==85")
t=t.replace('==(638,342,392)','==(638,342,393)').replace('ready=638,mangles=342,pending=392','ready=638,mangles=342,pending=393').replace('==(622,378)','==(638,392)').replace('keys(oldready)<=keys(ready)','keys(oldready)==keys(ready)')
ast.parse(t);target.write_text(t)
rawbase=lib/'candidates/efm-fader-control-dispatch/tools/seal_raw_root_pot_fader.py';rawtarget=rawbase.with_name('seal_raw_root_single_pole.py');assert not rawtarget.exists()
r=rawbase.read_text().replace('pot-fader-root','single-pole-root').replace('==126','==127').replace('canonical_ctest_count=126','canonical_ctest_count=127')
ast.parse(r);rawtarget.write_text(r)
(phase/'validation-operator-derivation.json').write_text(json.dumps(dict(admission=dict(source=str(base.relative_to(repo)),source_sha256=sha(base),derived=str(target.relative_to(repo)),derived_sha256=sha(target)),raw=dict(source=str(rawbase.relative_to(lib)),source_sha256=sha(rawbase),derived=str(rawtarget.relative_to(lib)),derived_sha256=sha(rawtarget)),scope='Fixed phase inputs/counts only; unchanged merger, raw ranges and validation gates'),indent=2)+'\n')
manifest=dict(phase='single-pole-validation-operators',transfers=[dict(direction='push',area='library',paths=[str(rawtarget.relative_to(lib))]),dict(direction='push',area='operators',paths=['admit_single_pole.py']),dict(direction='push',area='evidence',paths=['2026-10-27/single-pole-root/validation-operator-derivation.json'])])
(repo/'temp/recovery-work/sync-single-pole-validation.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(admission_sha256=sha(target),raw_sha256=sha(rawtarget))))
