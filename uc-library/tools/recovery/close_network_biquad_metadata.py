"""Record admitted NetworkManager services and the one original Biquad constructor."""
import hashlib,json,subprocess,sys
from pathlib import Path
assert sys.platform.startswith('linux')
repo=Path.cwd().resolve();lib=repo/'uc-library';phase=repo/'evidence/recovery/2026-10-27/network-biquad-root'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=repo/'uc-library/tools/recovery/count_current_unique.py';target=repo/'uc-library/tools/recovery/count_network_biquad_unique.py'
assert not target.exists();target.write_text(source.read_text().replace('file-transfer-panel-root/unique-current.json','network-biquad-root/unique-current.json'))
subprocess.run([sys.executable,str(target)],check=True)
counter=json.loads((phase/'unique-current.json').read_text())
assert (counter['remaining_unique'],counter['complete_all_roles'],counter['per_elf_ready'],counter['per_elf_pending'])==(9830,343,639,403)
tracker=lib/'validation/embedded-efm/SYMBOLS.md';old=tracker.read_text();assert '## Network/Biquad archive refresh' not in old
tracker.write_text(old+f'''
## Network/Biquad archive refresh — 2026-10-27 UTC

Eight retained raw suites freshly pass against current role archives:
115,933 cases including88 independent guards. Proof
`evidence/recovery/2026-10-27/network-biquad-root/raw-active-01/validation.json`,
SHA `{sha(phase/'raw-active-01/validation.json')}`. No raw domain/code change.
Canonical Linux132/132 CTest;108 production CPPs compiled once;87 app headers.
''')
subprocess.run([sys.executable,str(lib/'tools/generate_checkpoint.py'),'--library',str(lib),'--repository',str(repo),'--phase','network-biquad','--baseline',str(repo/'temp/recovery-work/checkpoints/2026-10-27-single-pole-closed.json'),'--output',str(repo/'temp/recovery-work/checkpoints/2026-10-27-network-biquad.md')],check=True)
(phase/'README.md').write_text(f'''# NetworkManager services and Biquad constructor

Linux132/132 CTest;108 production CPPs compiled once:73common,25CS18,10RM.
87 installed application headers. Original namespaces/mangled identities retained.

Adds one original RM DSP::BiquadCalc<double,false> C1 bounded-ready identity,
with original416B range checked, native C1/C2 alias relationship recorded and
three seeded/sentried full-state fixtures in Release/San and actual production.
Original nonempty C2 absent; no invented original row. Nine ordinary calculation
methods remain undefined, not compiled-pending. Independent helper stays outside
production, and no original object-size/ARM layout/padding/field-name claim.

Adds five UC NetworkManager methods /ten per-ELF declaration-pending identities.
Fresh2056 exact original/native cases (main1732 and coalescence324), actual40k
payload composition and TCP127.0.0.1 loopback pass in Release and sanitizers.
Uses genuine CCL lock/container/buffer and existing dispatcher/factory/codec/
framing/receive/socket sources. Unsupported virtual slots remain abstract;
fixture overrides are explicit, not production providers. Default manager
lifecycle, full network services, unknown original returns, concurrency/callback
mutation, malformed input outside fixtures, LAN and hardware remain unverified.

Ledger639ready /343 distinct ready names /403 compiled-pending records.
Remaining unique names:{counter['remaining_unique']};outsideCore
{counter['manual_remaining']};CCL source route{counter['core_source_route_remaining']}.
Manual buckets:`{json.dumps(counter['manual_buckets'],sort_keys=True)}`.
Two legacy Dice3Manager ready records have separately identified missing static
return declarations; a guarded demotion packet is being prepared with fresh
validation. No classification is silently dropped or changed by this batch.

Existing6ready/10pending SPI CMake bindings refreshed. All prior records retained.
Raw MCU115,933-case domain remains separate from original host ELF readiness.
See source table uc-library/SYMBOLS.md and complete retained phase receipts.
''')
print(json.dumps(dict(ready=639,names=343,pending=403,remaining=9830)))
