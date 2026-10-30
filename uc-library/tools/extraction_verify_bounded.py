#!/usr/bin/env python3
"""Source-bound pseudocode exporter with bounded batches and soft memory guards."""
import argparse
from datetime import datetime,timezone
import fcntl
import gc
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import signal
import time

def digest(data):return hashlib.sha256(data).hexdigest()

def owning_namespace(mangled):
    """Return the original Itanium name's outermost scope, including thunk targets.

    Deliberately inspect the owning name, never parameter/return-type spellings.
    Handles nested names, cv/ref qualifiers, local encodings and both adjusting
    and covariant-return thunks. Unscoped/non-Itanium names return None.
    """
    if not mangled.startswith('_Z'):return None
    tail=mangled[2:]
    def offset(value):
        match=re.match(r'(?:hn?\d+_|vn?\d+_n?\d+_)',value)
        return value[match.end():] if match else None
    if tail.startswith('Tc'):
        tail=offset(tail[2:])
        tail=offset(tail) if tail is not None else None
    elif tail.startswith(('Th','Tv')):tail=offset(tail[1:])
    if tail is None:return None
    if tail.startswith('Z'):tail=tail[1:]
    if not tail.startswith('N'):return None
    tail=tail[1:].lstrip('rVKRO')
    length=re.match(r'\d+',tail)
    if not length:return None
    n=int(length.group());start=length.end()
    return tail[start:start+n] if n and len(tail)>=start+n else None

def atomic_bytes(path,data):
    temporary=path.with_name(path.name+f'.{os.getpid()}.new')
    with temporary.open('wb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    temporary.replace(path)

def atomic_json(path,value):atomic_bytes(path,(json.dumps(value,indent=2)+'\n').encode())

def memory():
    def fields(path):
        return {line.split(':',1)[0]:line.split(':',1)[1].strip() for line in path.read_text().splitlines() if ':' in line}
    if not Path('/proc/self/status').exists():return {'rss_mb':None,'available_mb':None}
    own=fields(Path('/proc/self/status'));system=fields(Path('/proc/meminfo'))
    return {'rss_mb':round(int(own['VmRSS'].split()[0])/1024,1),
            'available_mb':round(int(system['MemAvailable'].split()[0])/1024,1)}

def live_workers(repository,recovery,role):
    found=[]
    if not Path('/proc').exists():return found
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
        try:
            args=[a.decode() for a in (proc/'cmdline').read_bytes().split(b'\0') if a]
            if not any(Path(a).name in ('decompile_uc.py','extraction_verify_bounded.py') for a in args):continue
            if not any(candidate in args for candidate in ('client','server')) or '--recovery' not in args:continue
            actual=((proc/'cwd').resolve()/args[args.index('--recovery')+1]).resolve()
            if actual==(repository/recovery).resolve():found.append({'pid':int(proc.name),'command':args})
        except (FileNotFoundError,PermissionError,IndexError):pass
    return found

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('repository',type=Path);p.add_argument('role',choices=['client','server'])
    p.add_argument('--pattern',default='.*');p.add_argument('--timeout',type=int,default=20)
    p.add_argument('--recovery',type=Path,default=Path('uc-library/recovered'))
    p.add_argument('--reuse-from',type=Path,action='append',default=[])
    p.add_argument('--priority',choices=['uc','dice','application'],default='uc')
    p.add_argument('--batch-size',type=int,default=250,help='New attempts per process; 0 disables.')
    p.add_argument('--max-rss-mb',type=int,default=2048,help='Soft between-function current-RSS guard; 0 disables.')
    p.add_argument('--min-available-mb',type=int,default=1024,help='Soft between-function available-memory guard; 0 disables.')
    p.add_argument('--retry-failed',action='store_true')
    p.add_argument('--plan-only',action='store_true',help='Inspect cache without importing angr or changing recovery state.')
    p.add_argument('--quarantine-untrusted',action='store_true')
    p.add_argument('--stop-file',type=Path,help='Cooperative pause marker checked before/after CFG and between functions.')
    p.add_argument('--defer-namespace',action='append',default=[],
        help='Defer functions owned by this exact outermost original namespace; repeatable. Does not match parameter types.')
    a=p.parse_args()
    if min(a.batch_size,a.max_rss_mb,a.min_available_mb)<0 or a.timeout<=0:p.error('nonnegative limits and positive timeout required')
    a.repository=a.repository.resolve();root=a.repository/a.recovery/a.role
    if a.stop_file is not None:
        a.stop_file=(a.repository/a.stop_file).resolve()
        assert a.stop_file.is_relative_to(a.repository),'stop marker must stay inside project'
    manifest=json.loads((root/'manifest.json').read_text());binary=a.repository/manifest['path']
    assert digest(binary.read_bytes())==manifest['sha256'],'source ELF changed'
    functions={};aliases={}
    for s in json.loads((root/'symbols.json').read_text()):
        if s['kind']=='STT_FUNC' and s['size'] and isinstance(s['section'],int):
            addr=s['address'];aliases.setdefault(addr,[]).append(s['mangled'])
            if addr not in functions or s['size']>functions[addr]['size']:functions[addr]=s
    output=root/'pseudocode';state_file=root/'decompilation.json';index_file=root/'trusted-exports.json'
    old_entries=json.loads(state_file.read_text()) if state_file.exists() else []
    old={e['address']:e for e in old_entries if e['address'] in functions}
    input_file=root/'analysis-input.json'
    if input_file.exists():assert json.loads(input_file.read_text())['sha256']==manifest['sha256'],'cache source mismatch'
    legacy_source_bound=input_file.exists()
    old_index=json.loads(index_file.read_text()) if index_file.exists() else {'source_sha256':manifest['sha256'],'exports':{}}
    assert old_index['source_sha256']==manifest['sha256'],'index source mismatch'
    previous={}
    for scope in a.reuse_from:
        directory=a.repository/scope/a.role
        assert json.loads((directory/'manifest.json').read_text())['sha256']==manifest['sha256'],'prior scope uses another ELF'
        audit_path=directory.parent/'audit.json'
        assert audit_path.is_file(),'prior-scope reuse requires its independent byte audit'
        assert json.loads(audit_path.read_text())['roles'][a.role]['sha256']==manifest['sha256'],'prior scope audit source mismatch'
        for entry in json.loads((directory/'decompilation.json').read_text()):
            addr=entry['address'];source=directory/'pseudocode'/f'{addr:08x}.cpp.txt'
            if addr in functions and entry['status']=='exported' and source.is_file():
                data=source.read_bytes();assert data.startswith(b'// UNVALIDATED') and len(data)>100
                previous.setdefault(addr,[]).append((digest(data),source,data))
    trusted={};suspect=[];reuse={}
    for addr,sym in functions.items():
        path=output/f'{addr:08x}.cpp.txt'
        if path.exists():
            data=path.read_bytes();fingerprint=digest(data);indexed=old_index['exports'].get(str(addr))
            if indexed is not None:assert indexed['sha256']==fingerprint,'sealed cache file changed'
            recorded=legacy_source_bound and addr in old and old[addr]['status']=='exported'
            matches=[str(source) for value,source,_ in previous.get(addr,[]) if value==fingerprint]
            if indexed is not None or recorded or matches:
                assert data.startswith(b'// UNVALIDATED') and len(data)>100,'malformed trusted export'
                trusted[addr]={'sha256':fingerprint,'bytes':len(data),'provenance':'sealed-index' if indexed else ('recorded-checkpoint' if recorded else 'exact-prior-scope-copy')}
            else:suspect.append(path)
        elif addr in old and old[addr]['status']=='exported':raise ValueError(f'recorded output missing: {path}')
        if addr not in trusted and addr in previous:reuse[addr]=previous[addr][0]
    status={}
    for addr,sym in functions.items():
        if addr in trusted or addr in reuse:
            status[addr]=dict(address=addr,mangled=sym['mangled'],demangled=sym['demangled'],aliases=aliases[addr],status='exported')
            if addr in reuse:status[addr]['reused_from']=str(reuse[addr][1])
        elif addr in old and old[addr]['status']=='failed' and not a.retry_failed:status[addr]=old[addr]
    priorities={'uc':r'BufferReader|BufferWriter|EventFactory|EventClass::|Connection::(read|write)|Discovery',
        'dice':r'Presonus::DICE::|::Dice[A-Z0-9]|::initDice|::Shelby|^dice[0-9_]|^tcat_|^shelby',
        'application':r'Presonus::(?:DICE|Mixer|Surface|Panel|NOAA|AVB|Dsp)::'}
    ordered=sorted(functions,key=lambda addr:(not bool(re.search(priorities[a.priority],functions[addr]['demangled'])),addr))
    deferred={addr for addr,names in aliases.items() if any(owning_namespace(name) in a.defer_namespace for name in names)}
    deferred_pending={addr for addr in deferred if addr not in trusted and addr not in reuse}
    core_ranges=sorted((addr&~1,(addr&~1)+functions[addr]['size']) for addr in deferred)
    overlapping=[addr for addr,sym in functions.items() if addr not in deferred and
        any(start<(addr&~1)+sym['size'] and end>(addr&~1) for start,end in core_ranges)]
    # A past failure stays preserved, but deferral is neither success nor failure.
    for addr in deferred:
        if addr not in trusted and addr not in reuse:status.pop(addr,None)
    pending=[addr for addr in ordered if addr not in status and addr not in deferred and re.search(a.pattern,functions[addr]['demangled'])]
    plan=dict(role=a.role,source_sha256=manifest['sha256'],function_entries=sum(map(len,aliases.values())),
        unique_functions=len(functions),trusted_existing=len(trusted),reusable_prior=len(reuse),
        untrusted_files=[str(path) for path in suspect],pending_attempts=len(pending),batch_size=a.batch_size,
        previous_failures=sum(e['status']=='failed' for e in status.values()),memory=memory())
    plan.update(deferred_namespaces=a.defer_namespace,deferred_unique=len(deferred),
        deferred_pending_unique=len(deferred_pending),eligible_unique=len(functions)-len(deferred),
        eligible_exports=sum(addr not in deferred for addr in trusted),
        eligible_deferred_range_overlaps=overlapping,
        scope_complete=all(addr in trusted or addr in reuse for addr in functions if addr not in deferred))
    print(json.dumps(plan),flush=True)
    if a.plan_only:return
    if overlapping:raise ValueError('eligible ranges overlap deferred namespace code; requires explicit review')
    existing=live_workers(a.repository,a.recovery,a.role)
    if existing:raise RuntimeError(f'existing worker owns this recovery scope: {existing}')
    lock=(root/'decompiler.lock').open('a+')
    fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    global_lock_path=a.repository/'temp/extraction-verification/decompiler.global.lock'
    global_lock_path.parent.mkdir(parents=True,exist_ok=True)
    global_lock=global_lock_path.open('a+')
    try:fcntl.flock(global_lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError as error:raise RuntimeError('another bounded decompiler owns the project-wide heavy-analysis lock') from error
    output.mkdir(exist_ok=True)
    atomic_json(root/'deferred-scope.json',dict(source_sha256=manifest['sha256'],namespaces=a.defer_namespace,
        classification='original Itanium owning namespace; defer entire address if any alias is owned by a deferred namespace',
        entries=[dict(address=addr,aliases=aliases[addr],status='deferred-by-user' if addr in deferred_pending else 'previously-exported-scope-now-deferred') for addr in sorted(deferred)],
        ready=False,workload_complete=False))
    quarantine=a.repository/'temp/extraction-verification/quarantine'/a.role/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+f'-{os.getpid()}')
    moved=[]
    def quarantine_file(path):
        if path.exists():
            quarantine.mkdir(parents=True,exist_ok=True);destination=quarantine/path.name;path.replace(destination)
            moved.append({'original':str(path),'preserved':str(destination)})
    if a.quarantine_untrusted:
        for path in suspect:quarantine_file(path)
    for addr,(fingerprint,source,data) in reuse.items():
        path=output/f'{addr:08x}.cpp.txt'
        if path.exists():quarantine_file(path)
        atomic_bytes(path,data)
        trusted[addr]={'sha256':fingerprint,'bytes':len(data),'provenance':'copied-prior-recorded-scope'}
    stopping={'requested':False,'reason':None}
    attempts=0
    def request_stop(signum,frame):stopping.update(requested=True,reason=f'signal-{signum}')
    signal.signal(signal.SIGTERM,request_stop);signal.signal(signal.SIGINT,request_stop)
    def checkpoint(state,reason=None):
        atomic_json(index_file,dict(source_sha256=manifest['sha256'],exports={str(addr):entry for addr,entry in trusted.items()}))
        atomic_json(state_file,[status[addr] for addr in sorted(status)])
        summary=dict(state=state,reason=reason,pid=os.getpid(),source_sha256=manifest['sha256'],
            expected_unique=len(functions),processed=len(status),exports=sum(e['status']=='exported' for e in status.values()),
            failed=sum(e['status']=='failed' for e in status.values()),memory=memory(),quarantined=moved,
            pending_unique=len(functions)-len(trusted),unattempted_unique=len(functions)-len(status),
            new_attempts=attempts,workload_processed_complete=len(status)==len(functions),
            all_exports_present=len(trusted)==len(functions),stop_file=str(a.stop_file) if a.stop_file else None,
            updated_utc=datetime.now(timezone.utc).isoformat(),pseudocode_validated=False)
        summary.update(deferred_namespaces=a.defer_namespace,deferred_unique=len(deferred),
            deferred_pending_unique=sum(addr not in trusted for addr in deferred),
            eligible_unique=len(functions)-len(deferred),eligible_exports=sum(addr not in deferred for addr in trusted),
            eligible_pending_unique=sum(addr not in deferred and addr not in trusted for addr in functions),
            scope_complete=all(addr in trusted for addr in functions if addr not in deferred))
        atomic_json(root/'run-state.json',summary)
        return summary
    def finish(state,reason=None):
        summary=checkpoint(state,reason)
        print(json.dumps(dict(event='run-summary',**summary)),flush=True)
    def stop_reason():
        if stopping['requested']:return stopping['reason']
        if a.stop_file is not None and a.stop_file.exists():return 'stop-file'
        return None
    def final_state(complete,reason):
        return 'stopped' if reason=='stop-file' or reason and reason.startswith('signal-') else ('complete' if complete else 'partial')
    def limit_reason():
        values=memory()
        if a.max_rss_mb and values['rss_mb'] is not None and values['rss_mb']>=a.max_rss_mb:return 'soft-rss-limit'
        if a.min_available_mb and values['available_mb'] is not None and values['available_mb']<a.min_available_mb:return 'low-available-memory'
        return None
    checkpoint('prepared')
    reason=stop_reason()
    if reason:finish('stopped',reason);return
    if not pending:
        complete=len(status)==len(functions)
        scope_complete=all(addr in trusted for addr in functions if addr not in deferred)
        finish('complete' if complete else ('scope-complete' if scope_complete else 'partial'),'no-selected-pending-functions')
        print(f'{a.role}: {"DONE" if complete else "CHECKPOINT"} {len(status)}/{len(functions)} recorded',flush=True);return
    reason=limit_reason()
    if reason:
        finish('partial',reason);print(f'{a.role}: CHECKPOINT {reason}; no CFG started',flush=True);return
    scratch=a.repository/'temp/extraction-verification/runtime'/a.role/str(os.getpid())
    scratch.mkdir(parents=True,exist_ok=True);os.environ['TMPDIR']=str(scratch)
    import tempfile
    tempfile.tempdir=str(scratch)
    import angr
    logging.getLogger('angr').setLevel(logging.ERROR);logging.getLogger('cle').setLevel(logging.ERROR)
    atomic_json(input_file,dict(sha256=manifest['sha256'],angr=angr.__version__,bounded_exporter=True))
    project=angr.Project(str(binary),auto_load_libs=False);regions=[]
    analysis_functions={addr:sym for addr,sym in functions.items() if addr not in deferred}
    for addr,sym in sorted(analysis_functions.items()):
        start,end=addr&~1,(addr&~1)+sym['size']
        if regions and start<=regions[-1][1]:regions[-1]=(regions[-1][0],max(end,regions[-1][1]))
        else:regions.append((start,end))
    reason=stop_reason() or limit_reason()
    if reason:finish(final_state(False,reason),reason);return
    print(f'{a.role}: recovering CFG; pending={len(pending)}; memory={memory()}',flush=True);checkpoint('cfg')
    cfg=project.analyses.CFGFast(normalize=True,regions=regions,function_starts=list(analysis_functions),
        start_at_entry=False,symbols=False,force_complete_scan=False,resolve_indirect_jumps=True,data_references=True)
    print(f'{a.role}: CFG ready; memory={memory()}',flush=True)
    reason=stop_reason() or limit_reason()
    if reason:finish(final_state(False,reason),reason);return
    def timeout(signum,frame):raise TimeoutError('per-function decompilation deadline')
    signal.signal(signal.SIGALRM,timeout);reason=None
    for addr in pending:
        reason=stop_reason() or limit_reason()
        if reason:break
        if a.batch_size and attempts>=a.batch_size:reason='batch-limit';break
        sym=functions[addr];path=output/f'{addr:08x}.cpp.txt'
        if path.exists() and addr not in trusted:quarantine_file(path)
        entry=dict(address=addr,mangled=sym['mangled'],demangled=sym['demangled'],aliases=aliases[addr]);start=time.monotonic();result=None
        try:
            signal.alarm(a.timeout);function=cfg.kb.functions.get(addr)
            if function is None:raise ValueError('function missing from CFG')
            result=project.analyses.Decompiler(function,cfg=cfg.model,use_cache=False,update_cache=False)
            if result.codegen is None:raise ValueError('decompiler produced no code')
            text=f'// UNVALIDATED DECOMPILER OUTPUT. Not buildable C++ or an ABI declaration.\n// {sym["demangled"]}\n// Symbol {sym["mangled"]} address=0x{addr:x}\n'+result.codegen.text+'\n'
            data=text.encode();atomic_bytes(path,data)
            trusted[addr]={'sha256':digest(data),'bytes':len(data),'provenance':'atomic-no-cache-decompiler-export'}
            entry['status']='exported'
        except Exception as error:entry.update(status='failed',error=f'{type(error).__name__}: {error}')
        finally:
            signal.alarm(0);result=None;project.kb.decompilations.discard((addr,'pseudocode'));gc.collect()
        entry['seconds']=round(time.monotonic()-start,3);status[addr]=entry;attempts+=1;checkpoint('running')
        if attempts%25==0:print(f'{a.role}: {attempts} new attempts; {len(status)}/{len(functions)} recorded; memory={memory()}',flush=True)
    reason=reason or stop_reason()
    complete=len(status)==len(functions)
    scope_complete=all(addr in trusted for addr in functions if addr not in deferred)
    terminal=final_state(complete,reason)
    if terminal=='partial' and scope_complete:terminal='scope-complete'
    finish(terminal,reason)
    print(f'{a.role}: {"DONE" if complete else "CHECKPOINT"} {len(status)}/{len(functions)} recorded; new_attempts={attempts}; reason={reason}; memory={memory()}',flush=True)

if __name__=='__main__':main()
