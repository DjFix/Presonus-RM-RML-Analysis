#!/usr/bin/env python3
"""Capture exact provider counters and whole wall time for a Root session tree.

Cached input/reasoning output are subsets, never extra tokens. Guardian sessions
are a separate subtotal, without a billing/pricing claim. Transcript byte offsets
avoid rereading old coordinator history after a captured baseline.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import time

KEYS = ('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens',
        'output_tokens', 'reasoning_output_tokens', 'total_tokens')


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def discover(directory, root):
    sessions = {}
    for path in directory.rglob('*.jsonl'):
        try:
            with path.open('rb') as stream:
                line = stream.readline()
            meta = json.loads(line)['payload']
        except (OSError, ValueError, KeyError):
            continue
        if meta.get('id'):
            sessions[meta['id']] = dict(meta=meta, path=str(path),
                meta_sha256=hashlib.sha256(line).hexdigest())
    selected = {root}
    while True:
        added = {sid for sid, row in sessions.items()
                 if row['meta'].get('parent_thread_id') in selected} - selected
        if not added:
            break
        selected.update(added)
    assert root in sessions, 'Root provider session must be present'
    return {sid: sessions[sid] for sid in selected}


def last_counter(path):
    # Retry larger tails if the last tool result is unusually large.
    with Path(path).open('rb') as stream:
        end = stream.seek(0, 2)
        size = min(end, 262144)
        while True:
            start = end-size
            stream.seek(start)
            if start:
                stream.readline()
            offset = stream.tell()
            found = None
            for line in stream:
                following = offset+len(line)
                try:
                    value = json.loads(line)
                    payload = value.get('payload', {})
                    if value.get('type') == 'event_msg' and payload.get('type') == 'token_count' and payload.get('info'):
                        found = dict(counters=payload['info']['total_token_usage'],
                                     utc=value['timestamp'], offset=following,
                                     line_sha256=hashlib.sha256(line).hexdigest())
                except (ValueError, KeyError, TypeError):
                    pass
                offset = following
            if found or not start:
                return found or dict(counters={}, utc=None, offset=0)
            size = min(end, size*4)


def capture(sessions):
    return {sid: dict(row, baseline=last_counter(row['path']))
            for sid, row in sessions.items()}


def cutoff(sessions, baseline):
    actors = []
    for sid, row in sessions.items():
        before = baseline['actors'].get(sid, {}).get('baseline',
                    dict(counters={}, utc=None, offset=0))
        counters = before['counters']
        end = counters
        events = []
        malformed = []
        pending = {}
        intervals = []
        with Path(row['path']).open('rb') as stream:
            stream.seek(before['offset'])
            while line := stream.readline():
                try:
                    value = json.loads(line)
                except ValueError:
                    malformed.append(dict(end_offset=stream.tell(), bytes=len(line),
                                          sha256=hashlib.sha256(line).hexdigest()))
                    continue
                payload = value.get('payload', {})
                kind, utc = payload.get('type'), value.get('timestamp')
                if value.get('type') == 'event_msg' and kind == 'token_count' and payload.get('info'):
                    end = payload['info']['total_token_usage']
                    events.append(dict(utc=utc, counters=end))
                if value.get('type') == 'response_item':
                    cid = payload.get('call_id')
                    if kind in ('function_call', 'custom_tool_call'):
                        pending[cid] = dict(name=payload.get('name'), start_utc=utc)
                    elif kind in ('function_call_output', 'custom_tool_call_output') and cid in pending:
                        call = pending.pop(cid)
                        call.update(end_utc=utc, wall_seconds=(
                            datetime.datetime.fromisoformat(utc.replace('Z', '+00:00')) -
                            datetime.datetime.fromisoformat(call['start_utc'].replace('Z', '+00:00'))).total_seconds())
                        intervals.append(call)
        delta = {key: end.get(key, 0)-counters.get(key, 0) for key in KEYS}
        assert all(value >= 0 for value in delta.values()), sid
        delta['noncached_input_tokens'] = delta['input_tokens']-delta['cached_input_tokens']
        assert delta['noncached_input_tokens'] >= 0
        actors.append(dict(provider_session_id=sid, agent_path=row['meta'].get('agent_path', 'Root' if sid == baseline['root_session'] else sid),
            thread_source=row['meta'].get('thread_source'), session_path=row['path'],
            baseline=before, cumulative_end=end, tokens=delta, usage_events=events,
            tool_intervals=intervals, pending_tools=list(pending.values()),
            malformed_lines=malformed, tool_intervals_may_be_incomplete=bool(malformed)))
    return actors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('baseline', 'cutoff'))
    parser.add_argument('--sessions', type=Path, default=Path('/home/rs/.codex/sessions'))
    parser.add_argument('--root-session', required=True)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[3]
    out = args.out.resolve()
    assert out.is_relative_to(repository/'temp') or out.is_relative_to(repository/'evidence/recovery')
    assert not out.exists(), 'Preserve old receipts; select a new output file'
    started = time.monotonic()
    sessions = discover(args.sessions, args.root_session)
    common = dict(root_session=args.root_session, label=args.label,
        recorded_utc=stamp(), producer=dict(path=str(Path(__file__).relative_to(repository)),
        sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    if args.action == 'baseline':
        result = dict(common, actors=capture(sessions),
            scope='Actual preceding provider counters before preparation. Counter tails not yet observed are charged at the next observed cumulative counter.')
    else:
        assert args.baseline, '--baseline required for cutoff'
        baseline = json.loads(args.baseline.read_text())
        assert baseline['root_session'] == args.root_session
        actors = cutoff(sessions, baseline)
        result = dict(common, baseline=str(args.baseline),
            baseline_sha256=hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
            actors=actors, continuous_elapsed_seconds=(
                datetime.datetime.fromisoformat(common['recorded_utc'])-
                datetime.datetime.fromisoformat(baseline['recorded_utc'])).total_seconds(),
            subtotals={label: {key: sum(a['tokens'][key] for a in actors if
                (a['thread_source'] == 'guardian_review') == guardian)
                for key in (*KEYS, 'noncached_input_tokens')}
                for label, guardian in [('Root and workers', False), ('Automatic approval review', True)]},
            cached_input_is_subset=True, reasoning_output_is_subset=True,
            parallel_wall_not_summed=True, reporting_tail_not_yet_observed=True,
            scope='Whole session-tree counter deltas. Includes new descendants; separate guardian subtotal. No billing claim. Tool intervals crossing baseline are partial; full wall time is authoritative.')
    result['collector_wall_seconds'] = time.monotonic()-started
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(output=str(out), actors=len(result['actors']),
                          collector_wall_seconds=result['collector_wall_seconds'])))


if __name__ == '__main__':
    main()
