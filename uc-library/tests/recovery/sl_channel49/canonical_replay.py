"""Attributed canonical provenance successor; original SL/native/fixtures unchanged.
Only explicit replay CLI executes; this scratch delivery was statically checked only.
"""
import argparse,datetime,hashlib,importlib.util,json,pathlib,shlex,subprocess,sys
from link_provenance import prove_link,sha as snapshot_sha,verify_snapshot
ROOT=pathlib.Path.cwd()
HERE=pathlib.Path(__file__).resolve().parent

def digest(p):return snapshot_sha(p)
def bind(p):return {'path':str(p),'sha256':digest(p)}
def inside(p):
    p=p.resolve();assert p.is_relative_to(ROOT),p;return p
def main():
    for producer_input in [pathlib.Path(__file__).resolve(),HERE/'link_provenance.py',HERE/'RUNTIME-ALIASES.json',HERE/'SOURCE-GENERATION.json']:snapshot_sha(producer_input)
    ap=argparse.ArgumentParser();ap.add_argument('--exe',type=pathlib.Path,required=True);ap.add_argument('--build',type=pathlib.Path,default=pathlib.Path('temp/core-upstream/root-integration-01'));ap.add_argument('--out',type=pathlib.Path,required=True);ap.add_argument('--link-maps',type=pathlib.Path,required=True);ap.add_argument('--original-checker',type=pathlib.Path,default=pathlib.Path('uc-library/tests/recovery/sl_channel49/run_all.py'));a=ap.parse_args()
    exe=inside(a.exe);build=inside(a.build);out=inside(a.out);map_contract_path=inside(a.link_maps);map_contract_before=bind(map_contract_path);map_contract=json.loads(map_contract_path.read_text());assert not out.exists();assert exe.is_file();aliases=json.loads((HERE/'RUNTIME-ALIASES.json').read_text());before=[]
    for x in aliases['runtime']:
        p=inside(ROOT/x['path']);assert p.is_file() and digest(p)==x['sha256'],('runtime alias missing/stale',x['path']);before.append(bind(p))
    generation=json.loads((HERE/'SOURCE-GENERATION.json').read_text())
    for path,expected_hash in generation.items():
        actual=inside(ROOT/path);assert digest(actual)==expected_hash,('source generation rebind required',path);before.append(bind(actual))
    checker=inside(a.original_checker);expected=next(x['sha256'] for x in aliases['runtime'] if x['path']=='uc-library/tests/recovery/sl_channel49/run_all.py');assert digest(checker)==expected
    # Import only at explicit future execution. ROOT rebound to canonical checkout;
    # native subprocesses retain original producer bytes and canonical immutable aliases.
    spec=importlib.util.spec_from_file_location('unchanged_sl49_family',checker);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.ROOT=ROOT
    commands=build/'compile_commands.json';commands_before=bind(commands);rows=json.loads(commands.read_text());records=[];inputs={};symbols=set();production_symbols={}
    def command(argv):return m.run(argv)
    for source in [*m.SOURCES,m.TEST/'Shared.cpp']:
        matches=[x for x in rows if pathlib.Path(x['file']).resolve()==ROOT/source];row,=matches;obj=inside(pathlib.Path(row['directory'])/row['output']);assert obj.is_file();dep=pathlib.Path(str(obj)+'.d');assert dep.is_file(),dep
        parts=shlex.split(row['command'])
        if source==m.TEST/'Shared.cpp':
            assert '-std=gnu++20' in parts or '-std=c++20' in parts
            defs=[p for p in parts if p.startswith(('-DNDEBUG','-UNDEBUG'))];assert defs and defs[-1]=='-UNDEBUG',('assert activation',defs)
            assert '-Ulinux' in parts and '-fno-sized-deallocation' in parts
        raw=dep.read_text().replace('\\\n',' ');paths=shlex.split(raw.split(':',1)[1])
        for name in paths:
            p=pathlib.Path(name);p=p if p.is_absolute() else pathlib.Path(row['directory'])/p;p=p.resolve();assert p.is_file(),p;inputs[str(p)]=bind(p)
        record={'source':bind(ROOT/source),'object':bind(obj),'depfile':bind(dep),'compile_entry':row};records.append(record)
        if source!=m.TEST/'Shared.cpp':
            observed=command(['nm','--defined-only',obj]);production_symbols[str(source)]=observed;symbols.update(line.split()[-1] for line in observed.splitlines() if line.split())
    contexts=sorted((ROOT/m.PACKETS).glob('*/CONTEXT.json'));assert len(contexts)==78
    originals=[x['original'] for p in contexts for x in json.loads(p.read_text())['originals']]
    unresolved=[x for x in originals if x['mangled'].startswith('_ZTh')];assert len(unresolved)==6 and all(x['mangled'].startswith('_ZThn4_') for x in unresolved)
    # Match exactly the six accepted pending identities; no universal thunk skip.
    accepted_pending=[]
    for x in aliases['runtime']:
        if '/packet-r4/tasks/' in x['path'] and x['path'].endswith('/CONTEXT.json'):
            frozen=json.loads((ROOT/x['path']).read_text());accepted_pending.extend(y['original'] for y in frozen['originals'] if y['original']['mangled'].startswith('_ZTh'))
    assert {(x['elf'],x['mangled']) for x in unresolved}=={(x['elf'],x['mangled']) for x in accepted_pending}
    ordinary=[x for x in originals if x not in unresolved];assert all(x['mangled'] in symbols for x in ordinary)
    assert '_ZN8Presonus24MixerClientComponentBase15channelSelectedEPNS_13SLChannelBaseE' in symbols
    thunks=sorted(n for n in symbols if n.startswith('_ZTh') and 'paramChanged' in n and any(c in n for c in ['13SLChannelBase','15ClientComponent','9SLChannel']));assert all(n.startswith('_ZThn8_') for n in thunks)
    driver=records[-1];link=pathlib.Path(driver['compile_entry']['directory'])/pathlib.Path(driver['compile_entry']['output']).parts[0]/pathlib.Path(driver['compile_entry']['output']).parts[1]/'link.txt';assert link.is_file();linktext=link.read_text()
    for flag in ['--wrap=_ZdlPv','--wrap=_ZN8presonus4dice19packetClockRawTicksEv','--wrap=_ZN8Presonus24MixerClientComponentBase15channelSelectedEPNS_13SLChannelBaseE']:assert flag in linktext,flag
    linkparts=shlex.split(linktext);output=pathlib.Path(linkparts[linkparts.index('-o')+1]);output=output if output.is_absolute() else build/output;assert output.resolve()==exe,('actual executable/link binding',output,exe)
    archives=[inside(p) for p in m.ARCHIVES];link_before=bind(link);archive_records=[bind(p) for p in archives];archive_members={str(p):command(['ar','t',p]).splitlines() for p in archives};
    driver_actual={**driver,'actual_compile_entry':driver['compile_entry']}
    link_proof=prove_link(ROOT,build,exe,driver_actual,rows,map_contract,command,{x['mangled'] for x in ordinary}|{'_ZN8Presonus24MixerClientComponentBase15channelSelectedEPNS_13SLChannelBaseE'}|set(thunks),archives+[build/'upstream-core/sdk/lib/libpresonus_png.a',build/'upstream-core/sdk/lib/libpresonus_zlib.a',build/'private-glibc29-provider/libpresonus_private_glibc29.a'])
    start=datetime.datetime.now(datetime.timezone.utc).isoformat();exe_before=bind(exe)
    # Original formatter and native observations retained; no fixture rewrite.
    command(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*m.HEADERS,*m.FORMAT_SOURCES])
    fixture=json.loads((ROOT/m.FIXTURE).read_text());fresh=m.native();assert fresh==fixture
    selector=json.loads((ROOT/m.SELECTOR_FIXTURE).read_text());assert json.loads(command([sys.executable,'-B','uc-library/tests/recovery/sqlite_sl49_channel_selected01/native.py']))==selector
    outputs,counts=m.compare(fresh,selector,exe)
    hash_snapshot=verify_snapshot()
    for x in before:assert digest(pathlib.Path(x['path']))==x['sha256']
    for x in records:
        for kind in ['source','object','depfile']:assert digest(pathlib.Path(x[kind]['path']))==x[kind]['sha256']
    for x in inputs.values():assert digest(pathlib.Path(x['path']))==x['sha256']
    for x in link_proof['bound_inputs']+[link_proof['map'],link_proof['link_file']]:assert digest(pathlib.Path(x['path']))==x['sha256']
    assert bind(map_contract_path)==map_contract_before
    assert bind(commands)==commands_before and bind(link)==link_before
    assert [bind(p) for p in archives]==archive_records and bind(exe)==exe_before
    proof={'version':1,'hash_snapshot':hash_snapshot,'attribution':'Root-authorized SL49 canonical --exe provenance successor; original worker producers immutable','started_utc':start,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'executable':exe_before,'adapter':bind(pathlib.Path(__file__).resolve()),'original_checker':bind(checker),'canonical_compile_table':bind(commands),'canonical_compile_records':records,'actual_driver_link':bind(link),'compiler_inputs':list(inputs.values()),'actual_link_proof':link_proof,'link_map_contract':map_contract_before,'current_archives':archive_records,'current_archive_member_names':archive_members,'original_native_fixture':bind(ROOT/m.FIXTURE),'selector_fixture':bind(ROOT/m.SELECTOR_FIXTURE),'native_producer':bind(ROOT/m.TEST/'native_common.py'),'selector_native_producer':bind(ROOT/'uc-library/tests/recovery/sqlite_sl49_channel_selected01/native.py'),'runtime_bindings':before,'ordinary_symbols_matched':len(ordinary),'canonical_production_symbols':production_symbols,'exact_six_pending_native_thunks':unresolved,'host_thunks':thunks,'counts':counts,'cpp_outputs':outputs,'commands':m.TIMES,'historical_LAST_COMPILE_used':False,'shared_execution_count':1,'typed_references':72,'credit':'45 remaining original49 methods, prior4 zero duplicate; extraSelector1 outside171; six originalthunks0','limitations':['Portable source/native-boundary scope unchanged; no ARM ABI/hardware claim.','Installed-role/compile-once archive audit, maintained formatting metadata, full Linux, current derived/Clipboard/incumbent source reproof and guarded admission remain separate mandatory gates.']}
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
if __name__=='__main__':main()
