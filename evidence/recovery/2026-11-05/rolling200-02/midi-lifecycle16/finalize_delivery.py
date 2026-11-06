"""Add bounded scope remarks after Root clarification; preserve proof unchanged.
No product/source/check changes. Hash-bound delivery amendment only.
"""
import datetime,hashlib,json,pathlib,runpy
ROOT=pathlib.Path.cwd();EVIDENCE=pathlib.Path('evidence/recovery/2026-11-05/rolling200-02/midi-lifecycle16')
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
remark='Owned local tags0/4/5 retain actual CCL Component controller behavior; this destructor-only adapter does not automatically route their notifications to MidiMixerHandler. The operational bridge forwards real borrowed normal tag0xa007 notifications and its removal is covered. Existing paramChanged tag0/4/5 explicit-call behavior passes unchanged historical1102-case replay. Original constructor/controller topology is not claimed; additional automatic wiring requires separately scoped native/source evidence.'
counts='Historical342-case consolidated replay includes192 Midi updateMapping,6 getParamFocusInfo and16 connect/control cases plus128 Scene/FX cases. Historical18 helper/idle cases and865 dispatch cases are separate; these are regressions, not new original reconstruction targets.'
records=[]
for n in [5,6,7]:
 path=pathlib.Path(f'uc-library/candidates/rolling200_02_midi_lifecycle16_{n:02}/HANDOFF.json');j=json.loads(path.read_text());o=j['originals'][0];records.append({'date':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original_elf_sha256':o['elf_sha256'],'mangled':o['mangled'],'owner':'rolling200_02_midi_lifecycle16','status':'bounded worker-local destructor reconstruction complete; global admission pending','remark':remark,'regression_scope':counts,'proof':str(EVIDENCE/'proof.json'),'retry_condition':'New assignment/evidence for original constructor and local controller topology; no extra original constructor or automatic local callback credit in this handoff.'})
supplement=EVIDENCE/'SCOPE_REMARKS.json';(ROOT/supplement).write_text(json.dumps(records,indent=2)+'\n')
producer=EVIDENCE/'finalize_delivery.py'
for n in [5,6,7]:
 path=pathlib.Path(f'uc-library/candidates/rolling200_02_midi_lifecycle16_{n:02}/HANDOFF.json');j=json.loads(path.read_text());j['limitations'].append(remark);j['validation_domain']+=' '+counts
 for p in [supplement,producer]:j['artifacts'].append({'kind':'dependency','path':str(p),'sha256':sha(p)})
 j['scope_amendment']={'producer':str(producer),'remarks':str(supplement),'reason':'Root clarified destructor-only notification scope after final checks; no source or check changed; original proof preserved byte-for-byte.'}
 path.write_text(json.dumps(j,indent=2)+'\n')
# Read-only admission structure check only; no ledger or acceptance subprocess.
m=runpy.run_path(str(ROOT/'uc-library/tools/recovery/accept_worker.py'))
results=[]
for n in [5,6,7]:
 p=pathlib.Path(f'uc-library/candidates/rolling200_02_midi_lifecycle16_{n:02}/HANDOFF.json');j=json.loads(p.read_text());m['validate'](j);results.append({'handoff':str(p),'sha256':sha(p),'validated':True,'artifact_count':len(j['artifacts'])})
proof=json.loads((ROOT/EVIDENCE/'proof.json').read_text())
for p,digest in proof['source_sha256'].items():assert sha(p)==digest,p
(ROOT/EVIDENCE/'final-bind-audit.json').write_text(json.dumps({'date':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'read-only HANDOFF v1 structure and all artifact/source hashes; no execution/admission claim','results':results,'all_proof_bound_inputs_current':True},indent=2)+'\n')
print('PASS three HANDOFF schemas, all bound artifacts and final proof source inputs; no global admission')
