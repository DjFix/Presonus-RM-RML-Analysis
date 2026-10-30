"""Independent whole-graph fixed-point and sampled reverse-trace audit."""
from pathlib import Path
from collections import defaultdict,deque
from array import array
import hashlib,json,sys

ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
OUT=ROOT/'evidence/recovery/2026-10-27/nimh-fpga-connectivity-02'

def rows(p):
    with p.open() as f:
        for line in f:yield json.loads(line)

assert sys.byteorder=='little'
state=array('i');state.frombytes((OUT/'driver-signatures.i32le').read_bytes())
phase=(OUT/'driver-polarities.u8').read_bytes();n=len(state)
assert len(phase)==n
root_names=json.loads((OUT/'abstract-sources.json').read_text())
seed={r['net']:set(r['root_ids']) for r in rows(OUT/'source-bindings.jsonl')}
acc=array('i',[0])*n;accphase=bytearray(n)
rev=[[] for _ in range(n)];edges=set()
def merge(v,root,p):
    if root==0:return
    if acc[v]==0:acc[v]=root;accphase[v]=p
    elif acc[v]==root:accphase[v]|=p
    else:acc[v]=-1;accphase[v]=3
for v,roots in seed.items():
    for root in roots:
        assert 0<root<=len(root_names)
        merge(v,root,1)
for r in rows(OUT/'export/global-edges.jsonl'):
    u,v=r['src'],r['dst']
    assert u is not None and v is not None
    key=(u,v,r['inv'])
    if key in edges:continue
    edges.add(key)
    if u==v:continue
    p=phase[u]
    if r['inv']:p=((p&1)<<1)|((p&2)>>1)
    merge(v,state[u],p);rev[v].append((u,int(r['inv'])))
assert acc==state
assert accphase==phase

# Independently walk backwards to source bindings. Do not reuse the forward
# propagation algorithm; every sampled traversal completes to its source set.
samples=set(range(0,n,max(1,n//160)))
for p in json.loads((OUT/'bonded-io-connectivity.json').read_text()):
    if p['output_driver_configured']:
        for field in ('data','tristate'):
            if p[field].get('net') is not None:samples.add(p[field]['net'])
for r in rows(OUT/'export/ambiguous-edges.jsonl'):samples.add(r['dst'])
walks=[]
for start in sorted(samples):
    q=deque([(start,0)]);seen=set();roots=set()
    while q:
        v,inv=q.popleft()
        if (v,inv) in seen:continue
        seen.add((v,inv))
        for root in seed.get(v,()):roots.add((root,inv))
        for u,edge_inv in rev[v]:q.append((u,inv^edge_inv))
    root_ids={r for r,_ in roots}
    expected=0 if not root_ids else next(iter(root_ids)) if len(root_ids)==1 else -1
    expected_phase=0
    for _,inv in roots:expected_phase|=1<<inv
    if expected==-1:expected_phase=3
    assert state[start]==expected,(start,state[start],expected)
    assert phase[start]==expected_phase,(start,phase[start],expected_phase)
    walks.append(dict(net=start,visited_oriented_nodes=len(seen),root_count=len(root_ids),source_status='none' if expected==0 else 'multiple' if expected==-1 else 'unique'))
coverage=json.loads((OUT/'netlist-coverage.json').read_text())
assert sum(coverage['all_node_source_status'].values())==n
assert sum(coverage['primitive_input_reference_source_status'].values())==coverage['primitive_input_references']
assert sum(coverage['primitive_input_net_source_status'].values())==coverage['unique_primitive_input_nets']
assert coverage['active_ambiguous_selector_destinations']==0

fields=list(rows(OUT/'investigation/field-encodings.jsonl'))
dcm=[r for r in fields if r['attribute']=='MODE']
assert len(dcm)==8
assert all(not any(r['bits_lsb_first']) for r in dcm)
assert all([p['value'] for p in r['patterns']]==['DCM_CLKGEN'] for r in dcm)
assert all(any(r['patterns'][0]['bits_lsb_first']) for r in dcm)
spi=next(r for r in fields if r['attribute']=='SPI_BUSWIDTH')
assert spi['physical_bits']==['Reg(Cor1, 11)','Reg(Cor1, 12)']
regs=json.loads((ROOT/'evidence/recovery/2026-10-27/nimh-fpga-decode-01/decoded-final/registers.json').read_text())
assert ((regs['Cor1']>>11)&3)==3 and ((regs['Mode']>>11)&3)==0
tile_geometry=json.loads((OUT/'investigation/clock-tile-geometry.json').read_text())
hclk=next(r for r in tile_geometry if r['tile']=='D0X18Y120.HCLK')
assert hclk['class']=='HCLK' and hclk['rects']==['Main(8473, 31, 512, 16, false)']
assert not any(r['tile']=='D0X18Y120.HCLK_BEL' for r in tile_geometry)
old=ROOT/'evidence/recovery/2026-10-27/nimh-fpga-decode-01/decoded-final'
data=(old/'configuration-bits.u8').read_bytes();mask=(old/'database-referenced-mask.u8').read_bytes()
unmodeled=[]
for frame,bit in [(8491,513),(8492,512)]:
    i=frame*1040+bit
    assert data[i]==1 and mask[i]==0
    unmodeled.append(dict(frame=frame,bit=bit,hclk_rect_frame=frame-8473,hclk_rect_bit=bit-512,value=1))
hclk_report=dict(status='still_unresolved',bits=unmodeled,tile=hclk,
    facts=['Both bits are outside HCLK buffer controls stored in rect frames 0..15.',
           'No HCLK_BEL mask instance is expanded at this CMT clock-column location.',
           'Neighbouring CLEXL/CLEXM HCLK mask schemas use this general frame/bit area, but that analogy does not identify these CMT bits.'],
    conclusion='No new feature meaning or routing edge is admitted. Dependency on functional clock nets remains unproven.',
    source_paths=['public/spartan6/src/expand.rs:fill_logic/fill_hclk','public/spartan6/src/expanded.rs:btile_hclk/tile_bits','databases/spartan6.txt:HCLK/HCLK_CLEXL/HCLK_CLEXM'])
(OUT/'hclk-investigation.json').write_text(json.dumps(hclk_report,indent=2)+'\n')
proof=dict(passed=True,nodes_fixed_point_checked=n,unique_directed_edges_checked=len(edges),sampled_complete_reverse_traces=len(walks),
    sampled_reverse_traces=walks,field_schema_checks='passed',hclk_storage_and_geometry_checks='passed',
    scope='Software graph consistency, polarity and selected source-trace audit; no primitive behavioral or hardware equivalence claim.')
(OUT/'graph-audit.json').write_text(json.dumps(proof,indent=2)+'\n')
print('Graph fixed-point audit passed:',n,'nodes;',len(edges),'unique directed edges.')
print('Independent complete reverse traces:',len(walks))
print('DCM baseline omission, SPI register correction and unresolved HCLK coordinates verified against pinned data.')
