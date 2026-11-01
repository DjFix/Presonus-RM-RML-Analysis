"""Read-only recurring observation; never starts/stops/retries any producer."""
import fcntl
import datetime
import json
import os
import pathlib
import socket
import sqlite3
from urllib.parse import urlsplit

ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'evidence/recovery/2026-10-31/dependency-graph/publication-monitor'


def read_json(path):
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return None


def processes():
    found=[]
    for folder in pathlib.Path('/proc').iterdir():
        if not folder.name.isdigit():continue
        try:
            args=(folder/'cmdline').read_bytes().decode(errors='replace').split('\0')
            if pathlib.Path(args[0]).name not in ('python','python3','python3.12','python3.13'):continue
            if len(args)<2 or pathlib.Path(args[1]).name not in ('refresh_graph.py','refresh_publish.py','resume_refresh_observations.py','migrate_source_identity.py'):continue
            start=(folder/'stat').read_text().rsplit(')',1)[1].split()[19]
            found.append({'pid':int(folder.name),'start_ticks':start,'script':args[1]})
        except (OSError,IndexError):continue
    return sorted(found,key=lambda x:x['pid'])


def classify(pending,live,endpoint_status):
    if live:return 'publication_running'
    if endpoint_status=='migration_pending':return 'waiting_for_pve_cutover'
    if pending:return 'publication_pending_no_live_process'
    return 'no_pending_publication'


def observe():
    stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    pending=None;errors=[]
    try:
        with (ROOT/'dependency-graph/state/context.lock').open('r') as lock:
            fcntl.flock(lock,fcntl.LOCK_SH | fcntl.LOCK_NB)
            with sqlite3.connect((ROOT/'dependency-graph/state/refresh-index.sqlite').as_uri()+'?mode=ro',uri=True,timeout=1) as c:
                row=c.execute('SELECT value FROM meta WHERE key="pending"').fetchone()
                pending=row[0] if row else None
    except BlockingIOError:
        pending=(read_json(OUT/'status.json') or {}).get('pending_delta')
    except (OSError,sqlite3.Error) as exc:errors.append('journal observation failed: '+str(exc))
    endpoint=read_json(ROOT/'dependency-graph/state/memgraph-endpoint.json') or {}
    live=processes();health=None
    if endpoint.get('uri'):
        try:
            uri=urlsplit(endpoint['uri'])
            with socket.create_connection((uri.hostname,uri.port or 7687),timeout=2):health='tcp_reachable_not_a_query_check'
        except (OSError,ValueError) as exc:health='unreachable: '+str(exc)
    log=None
    if pending:
        folder=pathlib.Path(pending)
        if folder.is_relative_to(ROOT):
            logs=list(folder.glob('resume-*.log'))+list(folder.glob('publish.log'))
            if logs:
                newest=max(logs,key=lambda p:p.stat().st_mtime_ns)
                with newest.open('rb') as stream:
                    stream.seek(max(0,newest.stat().st_size-8192));tail=stream.read().decode(errors='replace')
                lines=[s.strip() for s in tail.splitlines() if any(t in s for t in ('Error:','Memory limit exceeded','Connection refused','Traceback'))]
                log={'path':str(newest.relative_to(ROOT)),'size':newest.stat().st_size,'last_error':lines[-1] if lines else None}
    value={'observed_at_utc':stamp,'phase':classify(pending,live,endpoint.get('status')),
           'pending_delta':pending,'live_producers':live,'endpoint':endpoint,'tcp_health':health,'latest_publication_log':log,
           'source_generation':read_json(ROOT/'dependency-graph/ACTIVE.json'),'observation_errors':errors,
           'policy':'read-only observation; no auto restart/retry, no graph rebuild, no agent launch; no automatic chat delivery'}
    OUT.mkdir(parents=True,exist_ok=True)
    previous=read_json(OUT/'status.json')
    meaningful=lambda x:{k:x.get(k) for k in ('phase','pending_delta','live_producers','endpoint','tcp_health','observation_errors')}
    if previous is None or meaningful(previous)!=meaningful(value):
        with (OUT/'events.jsonl').open('a') as stream:stream.write(json.dumps(value,ensure_ascii=False)+'\n')
        print(json.dumps({'state_changed':True,'phase':value['phase'],'at':stamp},ensure_ascii=False))
    temp=OUT/'status.new';temp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n');temp.replace(OUT/'status.json')
    (OUT/'STATUS.md').write_text('# Publication monitor\n\n'+value['phase']+'\n\nObserved UTC: '+stamp+'\n\nPending delta: '+str(pending)+'\n\nLive producers: '+str(len(live))+'\n\nNo automatic retry, restart, rebuild, or chat notification.\n')
    return value


if __name__=='__main__':observe()
