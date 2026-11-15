"""Conservative deferred-I/O reserve, not a mathematical physical-write guarantee."""
from pathlib import Path
import math
from numbers import Real
from publication_budget import AccountingUnavailable, BudgetExceeded

MARGIN = 4 * 1024 * 1024


def staging_cache_kib(write_limit):
    """Leave conservative deferred-write headroom under every finite budget."""
    return min(262144, max(2048, write_limit // (3 * 1024)))


def deferred_reserve(connections, paths, budget):
    configs = []
    marker = getattr(budget, 'completed_stage_estimate', None)
    if not isinstance(marker, dict) or marker.get('complete') is not True:
        raise AccountingUnavailable('Complete delta/prune stage estimate required')
    estimates = budget.estimates
    if marker.get('estimates') != estimates or not isinstance(estimates, dict):
        raise AccountingUnavailable('Completed stage estimate changed')
    estimate = estimates.get('sqlite_write_bytes')
    if isinstance(estimate, bool) or not isinstance(estimate, Real) or not math.isfinite(estimate) or estimate < 0:
        raise AccountingUnavailable('Finite nonnegative final write estimate required')
    residual = max(0, estimate - budget.write_bytes)
    wal_total = 0
    for connection, path in zip(connections, paths, strict=True):
        page_size = connection.execute('PRAGMA page_size').fetchone()[0]
        cache = connection.execute('PRAGMA cache_size').fetchone()[0]
        mode = connection.execute('PRAGMA journal_mode').fetchone()[0]
        if page_size <= 0 or cache == 0 or mode not in ('wal', 'delete'):
            raise AccountingUnavailable('Unsupported deferred SQLite configuration')
        cache_bytes = -cache * 1024 if cache < 0 else cache * page_size
        wal = Path(str(path) + '-wal')
        try:
            wal_bytes = wal.stat().st_size
        except FileNotFoundError:
            wal_bytes = 0
        # Cache configuration remains diagnostic; reserve uses complete stage cost.
        # WAL adds an explicit checkpoint estimate, not a physical-write guarantee.
        wal_total += wal_bytes
        configs.append(dict(path=str(path), page_size=page_size, cache_size=cache,
                            cache_bytes=cache_bytes, journal_mode=mode,
                            existing_wal_bytes=wal_bytes))
    total = max(residual, wal_total + 16 * 1024**2) + MARGIN
    return dict(bytes=total, margin_bytes=MARGIN, configurations=configs,
                final_stage_write_estimate=estimate, observed_write_bytes=budget.write_bytes,
                residual_estimate_bytes=residual, wal_checkpoint_estimate_bytes=wal_total,
                floor_bytes=16 * 1024**2,
                interpretation='maximum of remaining total staged-cost estimate or WAL+floor; not a physical bound')


def commit_and_close(main, delta, budget, paths, *, pending_value):
    """Own both closes, preserving committed pending state on late failure.

    Caller has completed staging; pending marker is inserted BEFORE final reserve.
    Returns a durable-state receipt. Raises on any accounting/checkpoint failure.
    On failure budget.deferred_sqlite records whether main was committed.
    """
    connections = (main, delta)
    state = {'state': 'uncommitted', 'reserve': None, 'closed': False}
    budget.deferred_sqlite = state
    error = None
    def sample(phase):
        budget.observe([paths[1]], sqlite_paths=paths)
        state.setdefault('samples', []).append({'phase': phase, 'process_write_bytes': budget.write_bytes})
    def require_reserve(phase):
        reserve = deferred_reserve(connections, paths, budget)
        state['reserve'] = reserve
        state.setdefault('reserves', []).append({'phase': phase, **reserve})
        projected = budget.write_bytes + reserve['bytes']
        if projected > budget.limits.sqlite_write_bytes:
            raise BudgetExceeded('Deferred SQLite write reserve exceeds remaining cap: '
                                 + str(projected) + ' > ' + str(budget.limits.sqlite_write_bytes))
    try:
        main.execute('INSERT OR REPLACE INTO meta VALUES(?,?)', ('pending', pending_value))
        sample('before_delta_commit')
        require_reserve('before_delta_commit')
        # Reserve remains an estimate, never charged/reported as actual bytes.
        delta.commit()
        state['state'] = 'delta_committed_main_uncommitted'
        sample('before_main_commit')
        require_reserve('before_main_commit')
        # A fresh sample immediately before the irreversible main commit.
        main.commit()
        state['state'] = 'committed_pending'
        sample('after_main_commit')
        for connection, path in zip(connections, paths, strict=True):
            if connection.execute('PRAGMA journal_mode').fetchone()[0] == 'wal':
                result = tuple(connection.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone())
                state.setdefault('checkpoints', []).append({'path': str(path), 'result': result})
                if result[0] != 0:
                    raise AccountingUnavailable('SQLite checkpoint busy; committed pending retained')
                sample('after_checkpoint')
    except BaseException as exc:
        error = exc
        state['failure'] = str(exc)
        if state['state'] != 'committed_pending':
            for connection in connections:
                connection.rollback()
            state['state'] = ('delta_committed_main_rolled_back' if state['state'].startswith('delta_committed')
                              else 'rolled_back')
    finally:
        for connection in connections:
            try:
                connection.close()
            except BaseException as exc:
                state.setdefault('cleanup_failures', []).append(str(exc))
                error = error or exc
        state['closed'] = True
        try:
            budget.observe_final_io()  # Includes cleanup bytes even after a failed budget.
        except BaseException as exc:
            state.setdefault('cleanup_failures', []).append(str(exc))
            error = error or exc
        state['actual_process_write_bytes_at_close'] = budget.write_bytes
    if error is not None:
        raise error
    return state
