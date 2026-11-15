"""Finite publication budgets; estimates are not physical-write guarantees.

Charge rows/transfers BEFORE executing or sending them. Put the transaction body
inside sqlite_progress_guard, and commit only AFTER that scope exits successfully.
The guard never commits; exceptions and SQLite progress interrupts roll back.
Commit/WAL/cache flushes can write later: call observe after commit too, but that
observation cannot undo an already committed transaction. Process IO is cumulative,
process-wide and includes unrelated writes; disk/server/network IO is not inferred.
"""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path


class BudgetExceeded(RuntimeError):
    pass


class AccountingUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class BudgetLimits:
    journal_bytes: int = 1024**3
    sqlite_write_bytes: int = 4 * 1024**3
    rows: int = 10_000_000
    transfer_bytes: int = 1024**3

    def __post_init__(self):
        for name, value in asdict(self).items():
            if type(value) is not int or value <= 0:
                raise ValueError('Budget must be a finite positive integer: ' + name)


def read_proc_write_bytes():
    try:
        fields = dict(line.split(':', 1) for line in Path('/proc/self/io').read_text().splitlines())
        value = int(fields['write_bytes'])
        if value < 0:
            raise ValueError('negative write_bytes')
        return value
    except (OSError, KeyError, ValueError) as exc:
        raise AccountingUnavailable('Cannot account process write_bytes from /proc/self/io') from exc


class PublicationBudget:
    def __init__(self, limits=None, *, mode='routine', rebuild_limits=None,
                 rebuild_authorization=None, io_reader=read_proc_write_bytes):
        if mode not in ('routine', 'full_rebuild'):
            raise ValueError('Unknown publication mode')
        if mode == 'full_rebuild':
            if not rebuild_authorization or not isinstance(rebuild_authorization, str) or not rebuild_authorization.strip() or not isinstance(rebuild_limits, BudgetLimits):
                raise ValueError('Full rebuild needs explicit authorization and finite rebuild limits')
            limits = rebuild_limits
        elif rebuild_authorization is not None or rebuild_limits is not None:
            raise ValueError('Rebuild override requires explicit full_rebuild mode')
        self.limits = limits or BudgetLimits()
        if not isinstance(self.limits, BudgetLimits):
            raise TypeError('limits must be BudgetLimits')
        self.mode = mode
        self.authorization = rebuild_authorization
        self.io_reader = io_reader
        self.baseline = self._read_io()
        self.last_io = self.baseline
        self.write_bytes = 0
        self.rows = 0
        self.transfer_bytes = 0
        self.journals = {}
        self.sqlite_databases = set()
        self.estimates = None
        self.failure = None
        self.progress_samples = 0
        self.precommit_checks = 0
        self._guard_active = False

    def _read_io(self):
        try:
            value = self.io_reader()
            if type(value) is not int or value < 0:
                raise ValueError('invalid write_bytes')
            return value
        except AccountingUnavailable:
            raise
        except Exception as exc:
            raise AccountingUnavailable('Process write accounting unavailable') from exc

    def _require_live(self):
        if self.failure:
            raise BudgetExceeded(self.failure)

    def _bound(self, name, value):
        if type(value) is not int or value < 0:
            raise ValueError('Accounting requires a nonnegative integer: ' + name)
        if value > getattr(self.limits, name):
            self.failure = '{} budget exceeded: {} > {}'.format(name, value, getattr(self.limits, name))
            raise BudgetExceeded(self.failure)

    def preflight(self, *, journal_estimate_bytes, sqlite_write_estimate_bytes, rows, transfer_bytes):
        self._require_live()
        estimates = dict(journal_bytes=journal_estimate_bytes,
                         sqlite_write_bytes=sqlite_write_estimate_bytes, rows=rows,
                         transfer_bytes=transfer_bytes)
        for name, value in estimates.items():
            self._bound(name, value)
        self.estimates = estimates
        return dict(estimates)

    def _require_preflight(self):
        self._require_live()
        if self.estimates is None:
            raise RuntimeError('Preflight required before publication work')

    def charge_rows(self, rows):
        """Charge attempted rows before mutation; rollbacks do not refund work."""
        self._require_preflight()
        self._bound('rows', rows)
        self._bound('rows', self.rows + rows)
        self.rows += rows

    def charge_transfer(self, payload):
        """Charge the actual serialized bytes BEFORE transmission; return bytes."""
        self._require_preflight()
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        if not isinstance(payload, bytes):
            raise TypeError('Transfer accounting requires serialized bytes or text')
        self._bound('transfer_bytes', self.transfer_bytes + len(payload))
        self.transfer_bytes += len(payload)
        return payload

    def observe(self, journal_paths=(), *, sqlite_paths=()):
        """Sample process IO plus strict files and explicit SQLite sidecars.

        SQLite can create/remove its -journal/-wal files during normal operation.
        Only these explicitly derived sidecars permit absence; their sampled
        high-water sizes remain charged after disappearance. Missing database
        files, ordinary strict paths and other stat errors always fail closed.
        """
        self._require_preflight()
        try:
            current = self._read_io()
            if current < self.last_io:
                raise AccountingUnavailable('Process write_bytes counter went backwards')
        except AccountingUnavailable as exc:
            self.failure = str(exc)
            raise
        self.last_io = current
        self.write_bytes = current - self.baseline
        self._bound('sqlite_write_bytes', self.write_bytes)
        def record(path, allow_absent=False):
            path = Path(path).absolute()
            try:
                size = path.stat().st_size
            except FileNotFoundError as exc:
                if not allow_absent:
                    self.failure = 'Journal accounting unavailable: ' + str(path)
                    raise AccountingUnavailable(self.failure) from exc
                size = 0
            except OSError as exc:
                self.failure = 'Journal accounting unavailable: ' + str(path)
                raise AccountingUnavailable(self.failure) from exc
            self.journals[str(path)] = max(size, self.journals.get(str(path), 0))

        for path in journal_paths:
            record(Path(path).resolve())
        for database in sqlite_paths:
            database = Path(database).resolve()
            try:
                database.stat()  # A missing DB is not a normal sidecar lifecycle.
            except OSError as exc:
                self.failure = 'SQLite database accounting unavailable: ' + str(database)
                raise AccountingUnavailable(self.failure) from exc
            self.sqlite_databases.add(str(database))
            for suffix in ('-journal', '-wal'):
                record(Path(str(database) + suffix), allow_absent=True)
        self._bound('journal_bytes', sum(self.journals.values()))

    @contextmanager
    def sqlite_progress_guard(self, connection, *, opcode_interval=1000, journal_paths=(),
                              sqlite_paths=(), other_connections=()):
        """Guard an existing transaction; caller commits after successful exit.

        Owns SQLite's progress handler for this scope (no existing handler may be
        installed). Bounded opcode sampling can overshoot by work within one
        interval, and IO may be deferred until commit or a later cache flush.
        """
        self._require_preflight()
        if type(opcode_interval) is not int or opcode_interval <= 0:
            raise ValueError('opcode_interval must be a positive integer')
        if self._guard_active:
            raise RuntimeError('Nested budget progress guard')
        journal_paths = tuple(journal_paths)
        sqlite_paths = tuple(sqlite_paths)
        connections = (connection, *tuple(other_connections))
        if len({id(value) for value in connections}) != len(connections):
            raise ValueError('Duplicate SQLite connection in budget guard')
        self.observe(journal_paths, sqlite_paths=sqlite_paths)
        self._guard_active = True

        def progress():
            self.progress_samples += 1
            try:
                self.observe(journal_paths, sqlite_paths=sqlite_paths)
            except (BudgetExceeded, AccountingUnavailable):
                return 1
            return 0

        try:
            for current in connections:
                current.set_progress_handler(progress, opcode_interval)
            yield self
            self.observe(journal_paths, sqlite_paths=sqlite_paths)  # Required precommit check.
            self.precommit_checks += 1
        except BaseException:
            for current in connections:
                current.set_progress_handler(None, 0)
            for current in connections:
                current.rollback()
            raise
        finally:
            for current in connections:
                current.set_progress_handler(None, 0)
            self._guard_active = False

    def observe_final_io(self):
        """Sample physical IO after cleanup even when failed; never clears failure."""
        original_failure = self.failure
        try:
            current = self._read_io()
            if current < self.last_io:
                raise AccountingUnavailable('Process write_bytes counter went backwards')
            self.last_io = current
            self.write_bytes = current - self.baseline
            if original_failure is None:
                self._bound('sqlite_write_bytes', self.write_bytes)
        except (BudgetExceeded, AccountingUnavailable) as exc:
            self.final_accounting_failure = str(exc)
            if original_failure is None:
                self.failure = str(exc)
                raise
        finally:
            if original_failure is not None:
                self.failure = original_failure
        return self.write_bytes

    def receipt(self):
        return {'version': 1, 'mode': self.mode, 'rebuild_authorization': self.authorization,
                'limits': asdict(self.limits), 'preflight_estimates': self.estimates,
                'observed': {'process_write_bytes_delta': self.write_bytes, 'rows_charged': self.rows,
                             'serialized_transfer_bytes': self.transfer_bytes,
                             'journal_high_water_logical_bytes': sum(self.journals.values())},
                'journal_files': dict(self.journals),
                'sqlite_sidecar_databases': sorted(self.sqlite_databases), 'failure': self.failure,
                'final_accounting_failure': getattr(self, 'final_accounting_failure', None),
                'progress_samples': self.progress_samples, 'precommit_checks': self.precommit_checks,
                'uncertainty': ['Preflight estimates do not guarantee physical writes.',
                    'Process write_bytes includes unrelated process IO; excludes other processes/server IO.',
                    'Opcode sampling permits bounded-opcode overshoot, not a fixed byte overshoot.',
                    'SQLite WAL/cache/commit flushes may defer writes beyond precommit sampling.',
                    'Journal accounting measures supplied files, logical high-water sizes, not device writes.']}
