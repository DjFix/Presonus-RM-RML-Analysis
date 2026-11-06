"""Run owned checks and seal one v1 handoff per immutable GridPainter packet."""
import datetime,hashlib,importlib.util,json,os,platform,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
E=Path('evidence/recovery/2026-11-06/rolling200-03/grid140-worker')
P=Path('temp/recovery-work/rolling200-03/grid140/prepared140/packets')
PYTHON='uc-library/.venv/bin/python';CHECK='uc-library/tests/recovery/grid_painter/check.py'
SOURCES=['uc-library/include/presonus/GridPainter.hpp','uc-library/include/presonus/IBackgroundGridProvider.hpp','uc-library/include/presonus/mixer_dsp/EQControl.hpp','uc-library/src/Presonus/GridPainter.cpp','uc-library/src/Presonus/GridPainterLifecycle.cpp','uc-library/src/Presonus/GridPainterRendering.cpp']
TEST='uc-library/tests/recovery/GridPainterReplay.cpp'
REPLAYS=[CHECK,'uc-library/tests/recovery/grid_painter/native.py','uc-library/tests/recovery/grid_painter/seal.py']
DEPENDENCIES=['AGENTS.md','docs/worker-handoff.md','docs/core-framework-lineage.md','uc-library/src/Presonus/BackgroundPainter.cpp','uc-library/include/presonus/BackgroundPainter.hpp','uc-library/src/Presonus/EQControl.cpp','third_party/ccl-framework/core/public/corevector.h','third_party/ccl-framework/core/public/coreformatter.h','third_party/ccl-framework/core/public/coreformatter.cpp','third_party/ccl-framework/core/public/corestringbuffer.h','third_party/ccl-framework/core/public/corestringtraits.h','third_party/ccl-framework/core/public/gui/corecolor.h','third_party/ccl-framework/core/portable/gui/corefont.h','third_party/ccl-framework/core/portable/gui/corefont.cpp','third_party/ccl-framework/core/portable/gui/coregraphics.h','third_party/ccl-framework/core/portable/gui/coregraphics.cpp','third_party/ccl-framework/core/portable/gui/corebitmap.h','third_party/ccl-framework/core/portable/gui/corebitmap.cpp','third_party/ccl-framework/core/portable/gui/coreviewshared.h','third_party/ccl-framework/core/portable/gui/coreviewshared.cpp','third_party/ccl-framework/core/extras/fonts/tuffy16.fnt','third_party/ccl-framework/core/extras/fonts/tuffy16.png','temp/core-upstream/root-integration-01/libpresonus_uc.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','rootfs/CS18_v13840/home/root/surface']
LIMITS=[
 'Intentional portable source composition and safe virtual provider destructor; original inheritance, fields, vtable/layout, ordinary method return declarations and ARM ABI are not recovered. No hardware validation.',
 'Original C1/C2 and D1/D2 are distinct native addresses/ranges. Host compiler may alias variants; every original range is independently SHA-256 checked and executed. No GridPainter D0 target is claimed.',
 'Core bodies never execute in guest and are never reconstructed. Native oracle intercepts Core/CRT/libgcc at explicitly named provider boundaries. Actual CCL implementations and existing EQControl are compiled/replayed independently on Linux.',
 'Successful allocation, synchronous nonaliasing readable finite float inputs, valid formatters writing null-terminated strings within32 bytes, bounded nonoverflowing rectangles and positive cached dimensions only. Allocation/exception cleanup paths and NaN/infinite or out-of-int-range labels are untested. Invalid cache setup receives explicit source-port exceptions instead of unsafe native dereference.',
 'Modern RGBA cache intentionally replaces native RGB565: modern ColorBitmapRenderer rejects mismatched source/destination formats. Trace geometry/order and provider-based RGBA raster checksums are validated; original RGB565 pixel quantization is not claimed. RGB565 renderer is available upstream; this adaptation is for modern RGBA destination compatibility, not provider absence.',
 'External font tests use actual pinned tuffy16 descriptor/PNG. Cache renderer default font is null in tested provider configuration. Other fonts, arbitrary formatter output and non-null global default cache-font configuration remain untested.',
 'Provider coordinate results and text widths originate in an isolated --providers path using actual CCL font and existing EQControl; raster expectations originate in original ARM events executed through actual CCL, never GridPainter source-derived expected calls.',
 'Pixel checks use FNV-1a32 checksums of all RGBA pixels as a regression check, alongside exact event trace comparisons. They are not cryptographic byte-equivalence or ARM/hardware evidence.',
 'Native vector resize boundary models successful capacity sufficient for fixtures; original and host allocator capacity/layout are not compared. Native constructor/vector/destructor side effects and actual CCL RAII/bitmap-memory return-to-baseline are separate observations.',
 'Borrowed AxisState compatibility constructor intentionally has no provider; rendering nonempty vectors requires the original encoded provider constructor. Provider must outlive the painter.',
]
DOMAIN='Exact original application instructions for setGridValues, paint, full1676-byte paintGrid, C1/C2 and D1/D2; expanded64-byte BackgroundPainter fallback. Two axes including nonzero/negative/max selectors, negative/zero/positive counts, growth/copy and unchanged cache. Both grid loops, out-of-bounds/inverted clips, all label modes and invalid modes, formatter/null fallback, real font/null font, labels on/off, saturation/alpha, nonzero rectangle origins, cache reuse/value changes and dimension replacement. Exact native call order/geometry plus actual pinned CCL provider raster checksums. Original variants separately range-verified; actual bitmap lifecycle measured after scope destruction. Original orientation and EQControl draw regressions replayed.'
INTEGRATION={
 'production_partition':'Propose CS18 OBJECT ownership for new GridPainterLifecycle.cpp and GridPainterRendering.cpp from all seven original client identities; Root must review existing common GridPainter.cpp orientation ownership and its new virtual dependency on CS18 BackgroundPainter. Do not leave RM with unresolved common vtable references or duplicate any source. Keep shared/mixed units common if original/native dependency evidence establishes sharing; otherwise reclassify the coherent client class. Root runs role and installed/compile-once audits.',
 'public_headers':['presonus/GridPainter.hpp','presonus/IBackgroundGridProvider.hpp','presonus/mixer_dsp/EQControl.hpp'],
 'test_target':'GridPainterReplay built from uc-library/tests/recovery/GridPainterReplay.cpp with current canonical production sources; do not link stale EQControl objects after changing its provider base.',
 'link_dependencies':['actual pinned CCL Core','actual EQControl and existing DSP adapters','PNG/zlib','private glibc29 provider where configured'],
 'ctest_argv':[PYTHON,CHECK,'replay','<canonical GridPainterReplay executable>'],
 'fixture':'uc-library/tests/recovery/grid_painter/fixtures.json',
 'provider_only_pixel_argv':['<canonical GridPainterReplay executable>','--raster'],
 'native_argv':[PYTHON,CHECK,'native'],
 'root_retains':'Shared CMake/registry/tracker, full Linux integration, namespace/symbol/active-source, installed-role/compile-once/mirror audits and guarded readiness dry-run/admission. No admission is claimed by these handoffs.'}
def sha(p):return hashlib.sha256((R/p).read_bytes()).hexdigest()
def artifact(kind,path):return dict(kind=kind,path=str(path),sha256=sha(path))
def write(path,j):(R/path).parent.mkdir(parents=True,exist_ok=True);(R/path).write_text(json.dumps(j,indent=2)+'\n')
def run(mode):
 argv=[PYTHON,CHECK,mode];start=datetime.datetime.now(datetime.timezone.utc).isoformat();before=time.monotonic();p=subprocess.run(argv,cwd=R,capture_output=True,text=True)
 path=E/(mode+'-final.log');(R/path).write_text(json.dumps(argv)+'\n'+p.stdout+p.stderr)
 record=dict(mode=mode,argv=argv,start_utc=start,seconds=time.monotonic()-before,returncode=p.returncode,log=str(path))
 if p.returncode:raise RuntimeError(record)
 return record
if __name__=='__main__':
 (R/E).mkdir(parents=True,exist_ok=True)
 results=[run(m) for m in ['format','compile','symbols','replay','regression','native']]
 fixtures=json.loads((T/'fixtures.json').read_text())
 inputs=[artifact('source',p) for p in SOURCES]+[artifact('test',TEST)]+[artifact('replay',p) for p in REPLAYS]+[artifact('fixture','uc-library/tests/recovery/grid_painter/fixtures.json')]+[artifact('dependency',p) for p in DEPENDENCIES]
 for i in range(1,8):
  packet=P/f'rolling200_03_grid140_{i:02}'
  inputs.extend(artifact('packet',packet/n) for n in ['context.json','request.json','native-context.json','TASK.md','CONTEXT.md','SOURCE_SLICES.md','ELF_CONTEXT.md'])
 for generation in [179,180]:
  expansion=Path(f'temp/recovery-work/rolling200-03/grid140/expansion{generation}')
  for n in ['native-context.json','ELF_CONTEXT.md','expansion.json',f'TRANSPORT{generation}.json']:inputs.append(artifact('context_expansion',expansion/n))
 for item in results:inputs.append(artifact('log',item['log']))
 for name in ['remarks.json','development-observations.json','regressions.log','historical-regressions-producer.py']:inputs.append(artifact('remarks' if name.endswith('.json') else 'historical_evidence',E/name))
 native_generator=E/'native-generation.log'
 inputs.append(artifact('log',native_generator))
 proof=E/'proof.json'
 write(proof,dict(version=1,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),worker_session_id=os.getenv('CODEX_THREAD_ID'),worker_task='/root/rolling200_03_grid140',repository=str(R),base_commit='3a5d52a2677966b0b6e2e6a662bc0e3b5588965b',platform=platform.platform(),formatter=subprocess.check_output([str(R/'uc-library/.venv/bin/clang-format'),'--version'],text=True).strip(),compiler=subprocess.check_output(['/usr/bin/c++','--version'],text=True).splitlines()[0],python=platform.python_version(),upstream_commit=subprocess.check_output(['git','-C',str(R/'third_party/ccl-framework'),'rev-parse','HEAD'],text=True).strip(),ranges=fixtures['ranges'],expanded_background='temp/recovery-work/rolling200-03/grid140/expansion180',superseded_context_request='expansion179 contained paint root, not requested BackgroundPainter;180 supplies actual body; no original packet was changed',native_render_cases=len(fixtures['cases']),native_variant_cases=len(fixtures['lifecycle']),native_vector_cases=len(fixtures['vectors']),native_provider_observations=fixtures['providers'],domain=DOMAIN,limitations=LIMITS,contract_discrepancies=[dict(identities=[fixtures['elf_sha256'],fixtures['ranges'][0]['mangled']],observation='Original172-byte setGridValues writes only selected vector, never cache flag/pointer. Native traces keep cache unchanged; implementation deliberately does not invalidate cache. Root explicitly directed native semantics on2026-11-06.',status='resolved native behavior preserved',retry='New independent original evidence only'),dict(identity=fixtures['ranges'][2]['mangled'],observation='Original Y line branch at0x6d4a4 is bge followed by bgt, producing y>=top OR y<=bottom. Original Y label overlap uses event.updateRect; X uses supplied clip. Preserved and inverted/outside cases replayed.',status='resolved observed behavior preserved')],checks=results,artifacts=inputs,readiness_admitted=False,hardware_verified=False,ordinary_returns_verified=False,arm_abi_verified=False))
 inputs.append(artifact('proof',proof))
 for i in range(1,8):
  task=f'rolling200_03_grid140_{i:02}';packet=P/task;j=json.loads((R/packet/'request.json').read_text());identities=[]
  for item in j['originals']:
   o=item['original'];identities.append(dict(elf_sha256=o['elf'],firmware=o['firmware'],role=o['role'],mangled=o['mangled'],address=o['address'],size=o['size'],section=o['section_json']))
  checks=[dict(kind=m,argv=[PYTHON,CHECK,m],timeout_seconds=900 if m=='native' else 240) for m in ['format','compile','symbols','replay','native']]
  handoff=dict(version=1,task_id=task,namespace='Presonus',packet_manifest=str(packet/'context.json'),originals=identities,artifacts=inputs,checks=checks,validation_domain=DOMAIN,limitations=LIMITS,build_integration=INTEGRATION)
  write(Path('uc-library/candidates')/task/'HANDOFF.json',handoff)
 # Stock validator: exact artifact roles and current hashes, without admission.
 sp=importlib.util.spec_from_file_location('accept_worker',R/'uc-library/tools/recovery/accept_worker.py');module=importlib.util.module_from_spec(sp);sp.loader.exec_module(module)
 for i in range(1,8):
  h=Path(f'uc-library/candidates/rolling200_03_grid140_{i:02}/HANDOFF.json');module.validate(json.loads((R/h).read_text()));print(str(h),sha(h),'stock validate passed')
