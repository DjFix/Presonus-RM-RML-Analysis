"""Directed global graph audit and bounded abstract-driver reachability.

Primitive outputs are abstract boundaries, not behavioral equations. Defaults
are included; unrooted nets are not diagnosed as hardware defects.
"""
from pathlib import Path
from collections import defaultdict,Counter,deque
from array import array
import csv,hashlib,json,re

ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
OUT=ROOT/'evidence/recovery/2026-10-27/nimh-fpga-connectivity-02'
BASE=OUT/'export'
OLD=ROOT/'evidence/recovery/2026-10-27/nimh-fpga-decode-01'

def rows(p):
    with p.open() as f:
        for line in f:
            yield json.loads(line)

def save(name,obj):
    (OUT/name).write_text(json.dumps(obj,indent=2)+'\n')

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest()

old_manifest=json.loads((OLD/'evidence-manifest.json').read_text())['files']
for n in ['routing-settings.jsonl','primitive-settings.jsonl','decoder-issues.jsonl']:
    assert sha(OLD/'decoded-final'/n)==old_manifest['decoded-final/'+n]['sha256']

attrs=defaultdict(dict)
selected={'ENABLE','DLL_ENABLE','DFS_ENABLE','OUTPUT_ENABLE','IBUF_MODE','PULL','MUX_AOUT','MUX_BOUT','MUX_COUT','MUX_DOUT','REG_INTERFACE',
          'MUX_D','I_DELAY_ENABLE','FFI_DELAY_ENABLE','MUX_O','MUX_T','MUX_IN_O','MUX_IN_T'}
for r in rows(OLD/'decoded-final/primitive-settings.jsonl'):
    if r.get('attribute') in selected:
        attrs[(r['tile'].split('.')[0]+'.'+r['bel'])][r['attribute']]=r['value']

def off(cls,p):
    a=attrs.get(p,{})
    if cls=='DCM':return a.get('DLL_ENABLE')=='0' and a.get('DFS_ENABLE')=='0'
    if cls in ('PLL','BUFPLL','PCILOGICSE'):return a.get('ENABLE')=='0'
    return False

# Preserve every prior issue; contextual classifications never invent a route.
investigation=[]
for r in rows(OLD/'decoded-final/decoder-issues.jsonl'):
    entry=dict(r)
    if r['kind']=='routing_mux_unknown_pattern':
        m=re.search(r'\[(\d+)\]$',r['dst'])
        assert m
        primitive=r['tile'].split('.')[0]+f'.DCM[{m.group(1)}]'
        entry.update(primitive=primitive,disabled=off('DCM',primitive),classification='ambiguous clock input selector; keep both source and off possibilities')
    elif r.get('attribute')=='MODE' and r['class']=='CMT_DCM':
        primitive=r['tile'].split('.')[0]+'.'+r['bel']
        entry.update(primitive=primitive,disabled=off('DCM',primitive),classification='zero encoding is the DCM baseline omitted by the single-value DCM_CLKGEN difference table',analysis_value='DCM baseline; presence/enable classified separately',basis='Pinned re/xilinx/ise-hammer/src/spartan6/dcm.rs:949-958')
    elif r.get('attribute')=='SPI_BUSWIDTH':
        regs=json.loads((OLD/'decoded-final/registers.json').read_text())
        mode=regs['Mode'];width=(mode>>11)&3
        assert width in (0,1,2)
        entry.update(classification='Pinned database references COR1 rect 0; UG380 places BUSWIDTH in MODE rect 8',mode_register=mode,analysis_value=[1,2,4][width],new_mode=bool(mode&0x2000),basis='UG380 table 5-44; pinned misc.rs:862-875; defs.rs GLOBAL bitrect order')
    elif r.get('attribute','').startswith('DIVIDE') or r.get('attribute')=='PCI_CE_DELAY':
        primitive=r['tile'].split('.')[0]+'.'+r['bel']
        entry.update(primitive=primitive,disabled=off(r['bel'],primitive),classification='zero/default pattern absent from sparse parameter table; do not infer a numeric value')
    else:entry['classification']='Register absent from stream; value remains unobserved'
    investigation.append(entry)
save('field-investigation.json',investigation)

nodes=list(rows(BASE/'global-nets.jsonl'));n=len(nodes)
assert [r['id'] for r in nodes]==list(range(n))
assert len({r['wire'] for r in nodes})==n
fwd=[[] for _ in range(n)]
rev=[[] for _ in range(n)]
unique_edges=set();edge_records=0;null_edges=[];self_edges=0
for r in rows(BASE/'global-edges.jsonl'):
    edge_records+=1
    u,v=r['src'],r['dst']
    if u is None or v is None:
        null_edges.append(r);continue
    assert 0<=u<n and 0<=v<n
    e=(u,v,r['inv'])
    if e in unique_edges:continue
    unique_edges.add(e)
    if u==v:
        self_edges+=1
        continue
    fwd[u].append((v,r['inv']));rev[v].append((u,r['inv']))

root_names=[];root_ids={};state=array('i',[0])*n;polarity=bytearray(n)
seed_bindings=defaultdict(set)
queue=deque();queued=bytearray(n)
def schedule(v):
    if not queued[v]:queue.append(v);queued[v]=1
def add(v,r,phase=1):
    old=state[v]
    new=r if old==0 else old if r==0 or old==r else -1
    new_phase=phase if old==0 else polarity[v] if r==0 else (polarity[v]|phase) if old==r else 3
    if new!=old or new_phase!=polarity[v]:state[v]=new;polarity[v]=new_phase;schedule(v)
def root(v,name):
    rid=root_ids.get(name)
    if rid is None:
        rid=len(root_names)+1;root_ids[name]=rid;root_names.append(name)
    seed_bindings[v].add(rid)
    add(v,rid)

for r in nodes:
    if r['constant']:root(r['id'],'constant:'+r['kind'])

schema=Counter();mapped_input_refs=0;primitive_classes=Counter();skipped_outputs=Counter()
output_nets=defaultdict(set)
io_bindings=defaultdict(dict)
for r in rows(BASE/'primitives.jsonl'):primitive_classes[r['class']]+=1
package={r['primitive'] if 'primitive' in r else r['cell']+'.'+r['bel']:r for r in json.loads((OLD/'package-io-settings.json').read_text())}
port_sink_nets=set();port_output_pins=[]
for r in rows(BASE/'primitive-terminals.jsonl'):
    schema[r['status']]+=1
    if r['status']!='mapped':continue
    v=r['net'];assert isinstance(v,int) and 0<=v<n
    if r['class'] in ('ILOGIC','OLOGIC') and r['direction']=='input':
        io_bindings[r['primitive']][r['pin']]=v
    if r['direction']=='output':
        a=attrs.get(r['primitive'],{})
        disabled=off(r['class'],r['primitive'])
        if r['class']=='IOB':
            disabled=disabled or r['primitive'] not in package or a.get('IBUF_MODE')==['NONE']
        if r['class']=='SLICE' and r['pin'] in ('AMUX','BMUX','CMUX','DMUX'):
            disabled=disabled or a.get('MUX_'+r['pin'][0]+'OUT')==['NONE']
        if disabled:skipped_outputs[r['class']]+=1
        else:
            label='primitive:'+r['primitive']+'.'+r['pin']
            root(v,label);output_nets[label].add(v)
    elif r['direction']=='input':
        mapped_input_refs+=1
        if r['class']=='IOB' and r['primitive'] in package and package[r['primitive']]['output_driver_configured']:
            port_sink_nets.add(v)
            port_output_pins.append(dict(ball=package[r['primitive']]['ball'],pin=r['pin'],net=v))

while queue:
    u=queue.popleft();queued[u]=0
    for v,inv in fwd[u]:
        phase=polarity[u]
        if inv:phase=((phase&1)<<1)|((phase&2)>>1)
        add(v,state[u],phase)

ambiguous_nodes=set();active_ambiguous=set()
for r,issue in zip(rows(BASE/'ambiguous-edges.jsonl'),(r for r in investigation if r['kind']=='routing_mux_unknown_pattern')):
    assert r['tile']==issue['tile'] and r['dst_local']==issue['dst']
    v=r['dst']
    assert v is not None
    ambiguous_nodes.add(v)
    if not issue['disabled']:active_ambiguous.add(v)
def reach(seed):
    seen=bytearray(n);q=deque(seed)
    for v in seed:seen[v]=1
    while q:
        for v,_ in fwd[q.popleft()]:
            if not seen[v]:seen[v]=1;q.append(v)
    return seen
ambiguous_reach=reach(ambiguous_nodes)
active_reach=reach(active_ambiguous)

inputs_by_net=Counter();classes=defaultdict(Counter)
input_status=Counter();disabled_input_status=Counter()
def status(v):return 'no_abstract_source' if state[v]==0 else 'multiple_abstract_sources' if state[v]==-1 else 'unique_abstract_source'
with (OUT/'input-pin-net-status.jsonl').open('w') as f:
    for r in rows(BASE/'primitive-terminals.jsonl'):
        if r['status']!='mapped' or r['direction']!='input':continue
        v=r['net'];st=status(v);inputs_by_net[v]+=1
        input_status[st]+=1;classes[r['class']][st]+=1
        if off(r['class'],r['primitive']):disabled_input_status[st]+=1
        result=dict(primitive=r['primitive'],pin=r['pin'],net=v,source_status=st,
                    ambiguous_route_in_fanin=bool(ambiguous_reach[v]),active_ambiguous_route_in_fanin=bool(active_reach[v]),
                    inversion_paths_mask=polarity[v],terminal_inversion=r.get('inv',False))
        if state[v]>0:result['abstract_source']=root_names[state[v]-1]
        f.write(json.dumps(result)+'\n')
net_status=Counter();sink_status=Counter()
with (OUT/'net-status.jsonl').open('w') as f,(OUT/'unresolved-nets.csv').open('w',newline='') as csvf:
    keys=['id','wire','source_status','primitive_input_references','incoming_routes','outgoing_routes','ambiguous_fanin','active_ambiguous_fanin']
    w=csv.DictWriter(csvf,fieldnames=keys);w.writeheader()
    for v,r in enumerate(nodes):
        st=status(v);net_status[st]+=1
        if inputs_by_net[v]:sink_status[st]+=1
        result=dict(id=v,wire=r['wire'],source_status=st,primitive_input_references=inputs_by_net[v],incoming_routes=len(rev[v]),outgoing_routes=len(fwd[v]),ambiguous_fanin=bool(ambiguous_reach[v]),active_ambiguous_fanin=bool(active_reach[v]))
        f.write(json.dumps(result)+'\n')
        if st!='unique_abstract_source' or ambiguous_reach[v]:w.writerow(result)

for r in port_output_pins:
    r['source_status']=status(r['net'])
    if state[r['net']]>0:r['abstract_source']=root_names[state[r['net']]-1]
save('bonded-output-pin-sources.json',port_output_pins)
# The public primitive schema omits dedicated OLOGIC OQ/TQ and ILOGIC D
# terminals. The pinned rdverify/spartan6 implementation explicitly connects
# same-cell/index IOB to ILOGIC/OLOGIC, with optional IODELAY in those paths.
# Export these as separate abstract dedicated paths, retaining delay ambiguity.
dedicated_io=[]
for primitive,p in package.items():
    m=re.fullmatch(r'(D\d+X\d+Y\d+)\.IOB\[(\d+)\]',primitive)
    assert m
    cell,index=m.groups()
    ilogic=cell+f'.ILOGIC[{index}]';ologic=cell+f'.OLOGIC[{index}]';delay=cell+f'.IODELAY[{index}]'
    assert ilogic in attrs and ologic in attrs
    ai=attrs[ilogic];ao=attrs[ologic]
    source_index=int(index)^1 if ai.get('MUX_D')==['OTHER_IOB_I'] else int(index)
    q=dict(ball=p['ball'],iob=primitive,ilogic=ilogic,ologic=ologic,iodelay=delay,
           input_pad_source=cell+f'.IOB[{source_index}].I',input_mux=ai.get('MUX_D'),
           input_delay_enable=ai.get('I_DELAY_ENABLE'),
           output_driver_configured=p['output_driver_configured'],data={},tristate={},
           basis='Pinned re/xilinx/rdverify/spartan6/src/lib.rs verify_ilogic/verify_ologic/verify_iodelay/verify_iob',
           scope='Dedicated endpoint topology; optional delay path and sequential equations remain abstract, not a timing model.')
    for which,muxname,inname,direct,registered in [('data','MUX_O','MUX_IN_O','D1','FFO'),('tristate','MUX_T','MUX_IN_T','T1','FFT')]:
        mux=ao.get(muxname);upstream=ao.get(inname)
        part=dict(selection=mux,input_selection=upstream,output_endpoint=ologic+('.OQ' if which=='data' else '.TQ'),destination=primitive+('.O' if which=='data' else '.T'))
        if mux==[direct] and upstream==['INT']:
            v=io_bindings[ologic].get(direct)
            part.update(net=v,source_status=status(v) if v is not None else 'unmapped_dedicated_path')
            if v is not None and state[v]>0:part['abstract_source']=root_names[state[v]-1]
        elif mux==[registered]:
            part.update(source_status='abstract_registered_ologic_output',abstract_source=ologic+'.'+registered)
        else:
            part.update(source_status='unresolved_mcb_or_dedicated_selection')
        q[which]=part
    dedicated_io.append(q)
assert len(dedicated_io)==218
save('bonded-io-connectivity.json',dedicated_io)
configured=[p for p in dedicated_io if p['output_driver_configured']]
dedicated_status=Counter(p['data']['source_status'] for p in configured)
tristate_status=Counter(p['tristate']['source_status'] for p in configured)
save('dedicated-io-summary.json',dict(package_user_io_paths=len(dedicated_io),configured_output_data_paths=len(configured),
    configured_output_data_source_status=dict(dedicated_status),configured_tristate_source_status=dict(tristate_status),
    caveat='Sources end at primitive boundaries. Delay-path and clocked OLOGIC behavior is not simulated; board signal names remain unassigned.'))
save('abstract-sources.json',root_names)
with (OUT/'source-bindings.jsonl').open('w') as f:
    for v,roots in sorted(seed_bindings.items()):f.write(json.dumps(dict(net=v,root_ids=sorted(roots)))+'\n')
import sys
assert sys.byteorder=='little'
(OUT/'driver-signatures.i32le').write_bytes(state.tobytes())
(OUT/'driver-polarities.u8').write_bytes(polarity)
save('primitive-input-coverage-by-class.json',dict(classes))
summary=dict(global_wire_nodes=n,routing_edge_records=edge_records,unique_routing_edges=len(unique_edges),canonical_self_edges=self_edges,
    unresolved_routing_endpoints=len(null_edges),declared_terminal_binding_status=dict(schema),
    primitive_instances_by_class=dict(primitive_classes),abstract_source_count=len(root_names),
    ignored_explicitly_disabled_output_bindings=dict(skipped_outputs),
    all_node_source_status=dict(net_status),primitive_input_reference_source_status=dict(input_status),
    primitive_input_net_source_status=dict(sink_status),disabled_clock_input_reference_source_status=dict(disabled_input_status),
    ambiguous_selector_destinations=len(ambiguous_nodes),active_ambiguous_selector_destinations=len(active_ambiguous),
    nodes_reachable_from_raw_ambiguities=sum(ambiguous_reach),nodes_reachable_from_active_ambiguities=sum(active_reach),
    primitive_input_references=mapped_input_refs,unique_primitive_input_nets=len(inputs_by_net),
    primitive_input_unique_abstract_source_percent=100*input_status['unique_abstract_source']/mapped_input_refs,
    single_source_nets_with_conflicting_polarities=sum(s>0 and p==3 for s,p in zip(state,polarity)),
    configured_bonded_output_input_bindings=len(port_output_pins),
    configured_bonded_output_source_status=dict(Counter(r['source_status'] for r in port_output_pins)),
    dedicated_package_io_paths=len(dedicated_io),configured_output_data_paths=len(configured),
    dedicated_output_data_source_status=dict(dedicated_status),dedicated_tristate_source_status=dict(tristate_status),
    limitations=['Driver reachability terminates at abstract primitive outputs; primitive equations and sequential behavior have not been synthesized.',
                'Defaults and unused routing are present. No-source or multiple-source categories are conservative structural diagnostics, not hardware faults.',
                'Dedicated carry-neighbor geometry is exported separately; complete internal primitive/cascade connectivity remains outside the routed-wire graph.',
                'Unmodeled HCLK bit dependencies are unknown; routing model closure cannot prove that those bits do not affect functional connectivity.',
                'Original HDL hierarchy, board net names, timing and hardware equivalence are unverified.'])
save('netlist-coverage.json',summary)
save('netlist.json',dict(format='presonus-analysis-global-connectivity-v1',device='xc6slx45',
    files=dict(nodes='export/global-nets.jsonl',edges='export/global-edges.jsonl',primitives='export/primitives.jsonl',terminals='export/primitive-terminals.jsonl',ambiguous_edges='export/ambiguous-edges.jsonl',package_pads='export/package-pads.jsonl',carry_neighbors='export/dedicated-neighbors.jsonl',sources='abstract-sources.json',dedicated_io='bonded-io-connectivity.json'),
    primitive_settings_relative_to_project=str((OLD/'decoded-final/primitive-settings.jsonl').relative_to(ROOT)),
    primitive_settings_sha256=old_manifest['decoded-final/primitive-settings.jsonl']['sha256'],
    coverage='netlist-coverage.json',scope=summary['limitations']))
print(json.dumps(summary,indent=2))
