#!/usr/bin/env python3
"""Exercise accepted proof schemas and rejection of mismatched original scopes."""
import argparse
import copy
import json
from pathlib import Path
from merge_readiness import proof_covers


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    entry=dict(mangled='_Z_TEST_FIXTURE_ONLY',original_elf_sha256='test-elf-a')
    canonical=dict(cpp_differential_passed=True,compiled_mangled_names_matched=True,mangled_names=[entry['mangled']])
    detailed=dict(cpp_differential_passed=True,compiled_original_mangled_names_matched=True,functions=[entry])
    single=dict(arm_differential_passed=True,mangling_namespace_checked=True,mangled=entry['mangled'],portable_ready=True)
    cases=[('canonical',canonical,entry,True),('detailed',detailed,entry,True),('single',single,entry,True)]
    for key in ('cpp_differential_passed','compiled_mangled_names_matched','portable_ready'):
        changed=copy.deepcopy(canonical);changed[key]=False
        cases.append(('reject-'+key,changed,entry,False))
    cases.append(('reject-wrong-mangle',canonical,dict(entry,mangled='_Z_OTHER_TEST_ONLY'),False))
    cases.append(('reject-wrong-elf',detailed,dict(entry,original_elf_sha256='test-elf-b'),False))
    cases.append(('reject-name-and-elf-from-different-records',dict(detailed,functions=[dict(entry,original_elf_sha256='test-elf-b'),dict(entry,mangled='_Z_OTHER_TEST_ONLY')]),entry,False))
    results=[]
    for name,proof,target,expected in cases:
        actual=proof_covers(proof,target)
        assert actual is expected,name
        results.append(dict(name=name,expected=expected,actual=actual,passed=True))
    args.output.write_text(json.dumps(dict(cases=results,passed=True),indent=2)+'\n')
    print(json.dumps(dict(tests=len(results),passed=True)))


if __name__=='__main__':main()
