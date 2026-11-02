"""Conservative Linux batch concurrency planning, independent of agent counts.

Memory estimates are operator-tunable planning estimates, not container limits.
No claim is made that a process cannot exceed them. Unknown constraints select
one job. Detection accounts for every visible cgroup ancestor, not just the leaf.
"""
import math
import os
import pathlib

MIB = 1024 * 1024


def _read(path):
    try:
        return path.read_text().strip()
    except OSError:
        return None


def _integer(value):
    try:
        result = int(value)
        return result if result >= 0 else None
    except (ValueError, TypeError):
        return None


def _ancestors(leaf, root):
    if not leaf.is_relative_to(root):
        return []
    return [leaf, *[p for p in leaf.parents if p == root or p.is_relative_to(root)]]


def detect_resources(*, proc_root='/proc', cgroup_root='/sys/fs/cgroup', affinity=None):
    """Read host availability and visible cgroup v2/v1 CPU/memory ceilings.

    Alternate roots and affinity support isolated tests without host mutation.
    Missing controller information is explicit and handled conservatively.
    """
    proc = pathlib.Path(proc_root)
    cgroot = pathlib.Path(cgroup_root)
    unknown = []
    if affinity is None:
        try:
            affinity = len(os.sched_getaffinity(0))
        except (AttributeError, OSError):
            affinity = None
    if not isinstance(affinity, int) or affinity < 1:
        affinity = None
        unknown.append('CPU affinity unavailable')
    mem_available = None
    for line in (_read(proc / 'meminfo') or '').splitlines():
        fields = line.split()
        if fields and fields[0] == 'MemAvailable:' and len(fields) >= 2:
            value = _integer(fields[1])
            mem_available = value * 1024 if value is not None else None
    if mem_available is None:
        unknown.append('host available memory unavailable')
    cgroups = (_read(proc / 'self/cgroup') or '').splitlines()
    quotas, headrooms, observations = [], [], []
    cpu_seen = memory_seen = False
    for line in cgroups:
        fields = line.split(':', 2)
        if len(fields) != 3:
            continue
        _, controllers, relative = fields
        # Reject traversal before joining an untrusted/proc-fixture path.
        parts = pathlib.PurePosixPath(relative).parts
        if '..' in parts:
            unknown.append('invalid cgroup path')
            continue
        if not controllers:  # unified hierarchy
            roots = [('v2', cgroot)]
        else:
            roots = []
            for controller in controllers.split(','):
                if controller in ('cpu', 'memory'):
                    candidates = [cgroot / controllers, cgroot / controller]
                    root = next((p for p in candidates if p.exists()), candidates[-1])
                    roots.append((controller, root))
        for kind, root in roots:
            leaf = root / relative.lstrip('/')
            for parent in _ancestors(leaf, root):
                if kind == 'v2':
                    raw_cpu = _read(parent / 'cpu.max')
                    if raw_cpu is not None:
                        cpu_seen = True
                        words = raw_cpu.split()
                        if len(words) == 2 and words[0] == 'max' and (_integer(words[1]) or 0) > 0:
                            observations.append({'path': str(parent / 'cpu.max'), 'value': raw_cpu})
                        elif len(words) == 2 and (_integer(words[0]) or 0) > 0 and (_integer(words[1]) or 0) > 0:
                            quotas.append(int(words[0]) / int(words[1]))
                            observations.append({'path': str(parent / 'cpu.max'), 'value': raw_cpu})
                        else:
                            unknown.append('invalid CPU quota: ' + str(parent))
                elif kind == 'cpu':
                    quota = _read(parent / 'cpu.cfs_quota_us')
                    period = _read(parent / 'cpu.cfs_period_us')
                    if quota is not None:
                        cpu_seen = True
                        if quota == '-1':
                            pass
                        elif (_integer(quota) or 0) > 0 and (_integer(period) or 0) > 0:
                            quotas.append(int(quota) / int(period))
                        else:
                            unknown.append('invalid v1 CPU quota: ' + str(parent))
                        observations.append({'path': str(parent / 'cpu.cfs_quota_us'), 'value': quota, 'period': period})
                if kind in ('v2', 'memory'):
                    limit_path = parent / ('memory.max' if kind == 'v2' else 'memory.limit_in_bytes')
                    raw_limit = _read(limit_path)
                    if raw_limit is not None:
                        memory_seen = True
                        observation = {'path': str(limit_path), 'value': raw_limit}
                        if raw_limit == 'max':
                            pass
                        elif _integer(raw_limit) is not None:
                            usage = _integer(_read(parent / ('memory.current' if kind == 'v2' else 'memory.usage_in_bytes')))
                            observation['current'] = usage
                            if usage is None:
                                unknown.append('cgroup memory usage unavailable: ' + str(parent))
                            else:
                                headrooms.append(max(0, int(raw_limit) - usage))
                        else:
                            unknown.append('invalid cgroup memory limit: ' + str(parent))
                        observations.append(observation)
    if not cpu_seen:
        unknown.append('cgroup CPU constraint unavailable')
    if not memory_seen:
        unknown.append('cgroup memory constraint unavailable')
    cpu = min([affinity] if affinity is not None else [1])
    if quotas:
        cpu = min(cpu, max(1, math.floor(min(quotas))))
    memory_values = headrooms + ([mem_available] if mem_available is not None else [])
    return {'affinity_cpus': affinity, 'quota_cpus': min(quotas) if quotas else None,
            'available_cpus': cpu, 'host_available_memory_bytes': mem_available,
            'cgroup_headroom_bytes': min(headrooms) if headrooms else None,
            'available_memory_bytes': min(memory_values) if memory_values else None,
            'unknown': sorted(set(unknown)), 'cgroup_observations': observations}


def _positive(value, name):
    if isinstance(value, bool):
        raise ValueError(name + ' must be a positive integer')
    try:
        result = int(value)
    except (ValueError, TypeError):
        raise ValueError(name + ' must be a positive integer') from None
    if str(result) != str(value) or result < 1:
        raise ValueError(name + ' must be a positive integer')
    return result


def choose_limits(jobs, task_count, selection_jobs=None, slicing_jobs=None, *,
                  memgraph_cap=4, selection_memory_mib=512,
                  slicing_memory_mib=1536, reserve_memory_mib=1024, resources=None):
    """Return JSON-ready limits and every detected constraint/reason.

    `jobs` and per-stage overrides are upper bounds, never bypasses of resource
    or graph safety ceilings. Defaults budget 512 MiB selection/validation and
    1536 MiB AST slicing per concurrent builder, plus 1024 MiB host reserve.
    Builders budget the larger stage estimate because stages may overlap.
    Unknown resource observations force one builder. A zero-memory headroom
    also uses one job; the operator should handle runtime allocation failure.
    """
    count = _positive(task_count, 'task_count')
    graph = _positive(memgraph_cap, 'memgraph_cap')
    select_mem = _positive(selection_memory_mib, 'selection_memory_mib')
    slice_mem = _positive(slicing_memory_mib, 'slicing_memory_mib')
    reserve = _positive(reserve_memory_mib, 'reserve_memory_mib')
    automatic = jobs == 'auto'
    requested = count if automatic else _positive(jobs, 'jobs')
    detected = detect_resources() if resources is None else dict(resources)
    cpu = max(1, int(detected.get('available_cpus') or 1))
    available = detected.get('available_memory_bytes')
    memory_jobs = max(1, (max(0, available - reserve * MIB) // (max(select_mem, slice_mem) * MIB))) if available is not None else 1
    unknown = bool(detected.get('unknown')) or available is None or not detected.get('available_cpus')
    builders = min(requested, count, cpu, memory_jobs, 1 if unknown else count)
    select = min(builders, graph, _positive(selection_jobs, 'selection_jobs') if selection_jobs is not None else builders)
    slicing = min(builders, _positive(slicing_jobs, 'slicing_jobs') if slicing_jobs is not None else builders)
    reasons = [f'independent tasks ceiling={count}', f'CPU ceiling={cpu}',
               f'memory ceiling={memory_jobs}', f'Memgraph stage ceiling={graph}',
               'unknown resources force one builder' if unknown else 'all required resource observations available',
               'memory estimates are configurable planning estimates; container limits are not demand measurements']
    return {'jobs': jobs, 'automatic': automatic, 'selection_jobs': select,
            'validation_jobs': select, 'slicing_jobs': slicing, 'builder_jobs': builders,
            'limits': {'builders': builders, 'selection': select, 'validation': select, 'slicing': slicing},
            'resources': detected, 'reasons': reasons,
            'policy': {'memgraph_cap': graph, 'selection_memory_mib': select_mem,
                       'slicing_memory_mib': slice_mem, 'reserve_memory_mib': reserve,
                       'requested_jobs_ceiling': requested}}
