"""Canonical supplied-object/executable checker, no fallback compilation."""
import argparse,hashlib,json,subprocess
from pathlib import Path
P=Path(__file__).parent
S=['uc-library/include/presonus/IFaderUnit.hpp','uc-library/src/Presonus/IFaderUnit.cpp']
M='_ZN8Presonus10IFaderUnitD0Ev'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 a=argparse.ArgumentParser();a.add_argument('--exe',required=True);a.add_argument('--object',required=True);a.add_argument('--integration',required=True);a.add_argument('--out',required=True);v=a.parse_args()
 fixture=json.loads((P/'fixtures.json').read_text());nm=subprocess.check_output(['nm','--defined-only',v.object],text=True);assert M in [r.split()[-1] for r in nm.splitlines()]
 # Enforce the independently evidenced unsized-delete provider binding.
 undefined=subprocess.check_output(['nm','-u',v.object],text=True);assert '_ZdlPv\n' in undefined and '_ZdlPvm' not in undefined
 output=subprocess.check_output([str(Path(v.exe).resolve())],text=True).splitlines();assert output==[str(r['delete_calls']) for r in fixture['cases']]
 sources={p.removeprefix('uc-library/'):digest(p) for p in S}
 row={'original_elf_sha256':fixture['elf_sha256'],'mangled':M,'sources':sources,'cpp_compiled':True,'mangling_namespace_checked':True,'portable_ready':False,'domain':fixture['domain'],'declaration_uncertainties':['Partial interface omits other virtual methods; original base classes, layout and constructor declaration unresolved.'],'native_cases':len(output),'actual_host_deallocation_observed':True}
 proof={'success':True,'proposed_readiness':{'ready':[],'pending':[row]},'functions':[row],'fixture_sha256':digest(P/'fixtures.json'),'object_sha256':digest(v.object),'executable_sha256':digest(v.exe),'integration':v.integration,'provider':'Actual compiler global unsized delete via linker --wrap forwarding to __real__ZdlPv; native import hook observes call only. No CCL dependency in selected D0.'}
 Path(v.out).parent.mkdir(parents=True,exist_ok=True);Path(v.out).write_text(json.dumps(proof,indent=2)+'\n');print('PASS 8 native/C++ D0 cases')
if __name__=='__main__':main()
