"""Compare real role-archive state outputs; never claim unavailable call traces."""
import argparse,collections,hashlib,json,subprocess,shlex
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);p.add_argument('--fixture-sha256',required=True);p.add_argument('--inputs',required=True);p.add_argument('--inputs-sha256',required=True);args=p.parse_args()
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert sha(args.fixtures)==args.fixture_sha256,'native fixture hash mismatch'
assert sha(args.inputs)==args.inputs_sha256,'input fixture hash mismatch'
native=json.loads(Path(args.fixtures).read_text());text=Path(args.inputs).read_text();assert text==''.join(' '.join(map(str,c['input']))+'\n' for c in native['cases'])
result=subprocess.run([str(Path(args.executable).resolve())],input=text,text=True,capture_output=True);assert result.returncode==0,(result.returncode,result.stderr)
lines=result.stdout.splitlines();assert len(lines)==len(native['cases']),(len(lines),len(native['cases']))
state_checked=collections.Counter();trace_only=collections.Counter()
for index,(line,c) in enumerate(zip(lines,native['cases'])):
 actual=shlex.split(line);observed=shlex.split(c['output']);event_count=int(observed[0]);assert actual and actual[0]=='0',(index,'canonical trace prefix must remain unavailable')
 # Native method-entry events are intentionally absent from canonical archives.
 expected_state=observed[1+event_count:];actual_state=actual[1:]
 if c['input'][0]!=4:expected_state=list(map(float,expected_state));actual_state=list(map(float,actual_state))
 assert actual_state==expected_state,(index,c['input'],expected_state,actual_state)
 if expected_state:state_checked[str(c['input'][0])]+=1
 else:trace_only[str(c['input'][0])]+=1
print(json.dumps(dict(input_cases=len(lines),state_validated_cases=sum(state_checked.values()),per_method_state_cases=dict(state_checked),local_instrumentation_only_cases=dict(trace_only),compared=['selectGroup final selection for stable configured providers equals recorded original pre-doselect selection','own-controller paramChanged tag1009 result','onObserveredParamChange group tag603/mapping tag6 values','addGroup names and bit-exact numeric tag603/646 outcomes'],unavailable_scope=['Original direct-call ordering is preserved only by immutable local instrumented proof.','Cases with no recorded state fields are explicitly local-instrumentation-only, not canonical behavior coverage.','No claim about additional state fields absent from original native fixture, original return declarations, layout, ARM ABI or hardware.'],fixture_sha256=args.fixture_sha256,inputs_sha256=args.inputs_sha256,executable_sha256=sha(args.executable)),sort_keys=True))
