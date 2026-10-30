"""Logical BRAM content semantics and hash-bound physical pin assemblies.

Reset/output pipeline timing and cross-port collisions remain outside this model.
"""
from pathlib import Path
from collections import defaultdict
import json,random
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
B=ROOT/'evidence/recovery/2026-10-27/nimh-bus-04'
PREV=ROOT/'evidence/recovery/2026-10-27/nimh-fpga-connectivity-02'
class LogicalRAM:
    WIDTH={1:(1,0,0),2:(2,0,1),4:(4,0,2),9:(8,1,3),18:(16,2,4),36:(32,4,5)}
    def __init__(self,data_bits):self.data_bits=data_bits;self.data=0;self.parity=0;self.out=(0,0)
    def location(self,width,address):
        d,p,s=self.WIDTH[width];word=address>>s
        if (word+1)*d>self.data_bits:raise IndexError((width,address))
        return d,p,word*d,word*p
    def read(self,width,address):
        d,p,di,pi=self.location(width,address)
        return (self.data>>di)&((1<<d)-1),(self.parity>>pi)&((1<<p)-1)
    def write(self,width,address,data,parity=0,we=None):
        d,p,di,pi=self.location(width,address)
        if we is None:we=(1<<max(1,d//8))-1
        for lane in range(max(1,d//8)):
            if not (we>>lane)&1:continue
            size=min(8,d);mask=((1<<size)-1)<<(di+8*lane)
            self.data=(self.data&~mask)|(((data>>(8*lane))&((1<<size)-1))<<(di+8*lane))
            if p:
                mask=1<<(pi+lane);self.parity=(self.parity&~mask)|(((parity>>lane)&1)<<(pi+lane))
    def tick(self,width,address,data=0,parity=0,we=0,enable=True,mode='READ_FIRST'):
        if not enable:return self.out
        before=self.read(width,address)
        if we:self.write(width,address,data,parity,we)
        if not we or mode=='READ_FIRST':self.out=before
        elif mode=='WRITE_FIRST':self.out=self.read(width,address)
        elif mode!='NO_CHANGE':raise ValueError(mode)
        return self.out

def export():
    attrs=defaultdict(dict)
    for line in (PREV/'dependencies/primitive-settings.jsonl').open():
        r=json.loads(line)
        if r.get('bel_class')=='BRAM' and 'value' in r:attrs[r['tile'].split('.')[0]+'.'+r['bel']][r['attribute']]=r['value']
    eq={r['signal']:r for r in (json.loads(l) for l in (B/'functional-equations.jsonl').open())}
    raw={r['signal']:r for r in (json.loads(l) for l in (B/'physical-equations.jsonl').open())}
    pins=json.loads((B/'functional-input-pins.json').read_text())
    def resolve(n):
        sign=n.startswith('~');n=n.lstrip('~');seen=set()
        while n not in eq and n in raw and raw[n]['op']=='alias' and n not in seen:
            seen.add(n);x=raw[n]['args'][0];sign^=x.startswith('~');n=x.lstrip('~')
        if n in ('0','1'):return str(int(n)^sign)
        return ('~' if sign else '')+n
    def value(p,key,inv=False):
        v=resolve(pins[p][key])
        if inv:v=str(1-int(v)) if v in ('0','1') else v[1:] if v.startswith('~') else '~'+v
        return v
    used={r['signal'].rsplit('.',1)[0] for r in eq.values() if r['op']=='gap' and r.get('reason','').startswith('BRAM')}
    groups={tuple(p.rsplit('.',1)[0]+'.BRAM['+str(i)+']' for i in range(2)) if attrs[p]['COMBINE']=='1' else (p,) for p in used}
    records=[]
    for group in sorted(groups):
        p=group[0];a=attrs[p];combined=len(group)==2
        assert all(int(attrs[q]['DATA'],16)==0 and int(attrs[q]['DATAP'],16)==0 for q in group)
        for key in ['RAM_MODE','DATA_WIDTH_A','DATA_WIDTH_B']:
            assert all(attrs[q][key]==a[key] for q in group),(group,key)
        mode=a['RAM_MODE'][0];ports={}
        for ab in ['A','B']:
            addr=[value(p,f'ADDR{ab}[{i}]') for i in range(13)]
            if combined:addr=addr[:4]+[value(group[1],f'ADDR{ab}[0]')]+addr[4:]
            width=int(a['DATA_WIDTH_'+ab][0].lstrip('_'))
            port=dict(width=width,address_low_to_high=addr,
                clock=value(p,'CLK'+ab,a['CLK'+ab+'_INV']=='1'),enable=value(p,'EN'+ab,a['EN'+ab+'_INV']=='1'),
                reset=value(p,'RST'+ab,a['RST'+ab+'_INV']=='1'),regce=value(p,'REGCE'+ab,a['REGCE'+ab+'_INV']=='1'),
                write_mode=a['WRITE_MODE_'+ab][0],output_register=a['DO'+ab+'_REG']=='1',
                write_data=[value(q,f'DI{ab}[{i}]') for q in group for i in range(16)],
                write_parity=[value(q,f'DIP{ab}[{i}]') for q in group for i in range(2)],
                write_enable=[value(q,f'WE{ab}[{i}]') for q in group for i in range(2)],
                read_data=[q+f'.DO{ab}[{i}]' for q in group for i in range(16)],
                read_parity=[q+f'.DOP{ab}[{i}]' for q in group for i in range(2)])
            ports[ab]=port
        if not combined and mode=='SDP':
            assert ports['A']['width']==ports['B']['width']==36
            ports['A']['write_data']+=ports['B']['write_data'];ports['A']['write_parity']+=ports['B']['write_parity'];ports['A']['write_enable']+=ports['B']['write_enable']
            ports['B']['read_data']=ports['A']['read_data']+ports['B']['read_data'];ports['B']['read_parity']=ports['A']['read_parity']+ports['B']['read_parity']
            ports['A']['role']='write';ports['B']['role']='read'
        else:
            for port in ports.values():port['role']='read_write'
        for port in ports.values():
            d,pbits,_=LogicalRAM.WIDTH[port['width']]
            port['write_data']=port['write_data'][:d];port['write_parity']=port['write_parity'][:pbits]
            port['write_enable']=port['write_enable'][:max(1,d//8)]
            port['read_data']=port['read_data'][:d];port['read_parity']=port['read_parity'][:pbits]
        records.append(dict(cell=group[0]+('.COMBINED' if combined else ''),physical_primitives=list(group),data_bits=16384 if combined else 8192,
            parity_bits=2048 if combined else 1024,mode=mode,ports=ports,initial_data=0,initial_parity=0,
            basis='Pinned Spartan-6 defs.rs combined-bus/address mapping and UG383 widths/read/write modes; this image has zero INIT.',
            supported='Logical content read/write, mixed widths, byte enables and READ_FIRST/WRITE_FIRST/NO_CHANGE under one-port-at-a-time collision-free events.',
            unresolved=['Reset/output-register timing and EN_RSTRAM/RST_PRIORITY sequencing','Cross-port read/write and write/write collision timing','Pin-level clock/delay and independent silicon validation']))
    (B/'bram-storage-models.json').write_text(json.dumps(records,indent=2)+'\n')
    print('BRAM logical storage groups:',len(records),'physical halves:',len(set(q for r in records for q in r['physical_primitives'])))
    return records

def test():
    rng=random.Random(0x4252414d);cases=0
    for size in [8192,16384]:
        ram=LogicalRAM(size);data=[0]*size;parity=[0]*(size//8)
        for _ in range(4000):
            w=rng.choice(list(ram.WIDTH));dw,pw,shift=ram.WIDTH[w]
            address=rng.randrange(size//dw)<<shift
            dv=rng.getrandbits(dw);pv=rng.getrandbits(pw);we=rng.randrange(1<<max(1,dw//8))
            if rng.randrange(2):
                ram.write(w,address,dv,pv,we)
                word=address>>shift
                for j in range(dw):
                    if we>>(j//8)&1:data[word*dw+j]=(dv>>j)&1
                for j in range(pw):
                    if we>>j&1:parity[word*pw+j]=(pv>>j)&1
            else:
                d,p=ram.read(w,address);word=address>>shift
                assert d==sum(data[word*dw+j]<<j for j in range(dw))
                assert p==sum(parity[word*pw+j]<<j for j in range(pw))
            cases+=1
    for mode,expected in [('READ_FIRST',(0,0)),('WRITE_FIRST',(0xa5,1)),('NO_CHANGE',(0x55,0))]:
        ram=LogicalRAM(8192);ram.out=(0x55,0)
        assert ram.tick(9,0,data=0xa5,parity=1,we=1,mode=mode)==expected
        assert ram.read(9,0)==(0xa5,1)
    result=dict(passed=True,random_mixed_width_events=cases,write_mode_cases=3,
      scope='Integer storage model versus independent bit-array reference; no cross-port collisions, reset/pipeline timing or hardware proof.')
    (B/'bram-model-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
if __name__=='__main__':export();test()
