#!/usr/bin/env python3
"""Execute only original UC app ranges; bind Core boundaries to actual CCL source."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn import arm_const as a

CLASSES=('FileRequestHandler','FileReader','FileWriter','FileListReader','FileListWriter')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def word(v):return struct.pack('<I',v&0xffffffff)
def enc(s):return s.encode().hex() or '-'
def dec(s):return bytes.fromhex(s).decode() if s!='-' else ''
class Bridge:
    def __init__(self,path,out):
        self.stderr=(out/'bridge-stderr.log').open('w');self.log=(out/'bridge-protocol.jsonl').open('w')
        self.p=subprocess.Popen([str(path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.stderr,text=True,bufsize=1)
        self.digest=sha(path)
    def ask(self,text):
        self.p.stdin.write(text+'\n');self.p.stdin.flush();reply=self.p.stdout.readline().strip()
        self.log.write(json.dumps(dict(request=text,response=reply))+'\n');self.log.flush()
        assert reply and not reply.startswith('ERROR'),(text,reply,self.p.poll())
        return reply
    def close(self):
        if self.p.poll() is None:self.ask('quit')
        assert self.p.wait(timeout=10)==0
        self.log.close();self.stderr.close()
class Original:
    heap,stack,stop=0x10000000,0x20000000,0x30000000
    obj,stream,event=heap+0x1000,heap+0x3000,heap+0x4000
    def __init__(self,repo,role,bridge):
        self.bridge=bridge;root=repo/'uc-library/recovered-all'/role
        self.manifest=json.loads((root/'manifest.json').read_text());binary=repo/self.manifest['path'];assert sha(binary)==self.manifest['sha256']
        rows=json.loads((root/'symbols.json').read_text());self.addresses={r['address']:r for r in rows if r['kind']=='STT_FUNC'}
        self.methods={}
        for r in rows:
            if r['kind']!='STT_FUNC' or not r['demangled'].startswith(tuple('Presonus::UC::'+c+'::' for c in CLASSES)):continue
            cls=r['demangled'].split('::')[2]
            variant=next((k for k in ('C1','C2','D0','D1','D2') if cls+k+'E' in r['mangled']),None)
            self.methods[cls,variant or r['demangled'].split('::')[3].split('(')[0]]=r
        assert len(self.methods)==27
        self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM);raw=binary.read_bytes()
        with binary.open('rb') as stream:
            elf=ELFFile(stream);ranges=[]
            for s in elf.iter_segments():
                if s['p_type']!='PT_LOAD':continue
                lo=int(s['p_vaddr'])&~4095;hi=(int(s['p_vaddr'])+int(s['p_memsz'])+4095)&~4095
                if ranges and lo<=ranges[-1][1]:ranges[-1]=(ranges[-1][0],max(hi,ranges[-1][1]))
                else:ranges.append((lo,hi))
            for lo,hi in ranges:self.u.mem_map(lo,hi-lo)
            for s in elf.iter_segments():
                if s['p_type']=='PT_LOAD':self.u.mem_write(int(s['p_vaddr']),s.data())
            for r in self.methods.values():
                s=elf.get_section(r['section']);off=int(s['sh_offset'])+r['address']-int(s['sh_addr']);data=raw[off:off+r['size']]
                assert off==r['file_offset'] and hashlib.sha256(data).hexdigest()==r['sha256'] and data==(root/r['export_path']).read_bytes()
        for address,size in ((self.heap,0x100000),(self.stack,0x20000),(self.stop,4096)):self.u.mem_map(address,size)
        self.u.hook_add(UC_HOOK_CODE,self.code);self.covered=set();self.boundaries={}
    def get(self,p):return struct.unpack('<I',self.u.mem_read(p,4))[0]
    def put(self,p,v):self.u.mem_write(p,word(v))
    def text(self,p):
        if not p:return ''
        data=bytearray()
        while True:
            b=bytes(self.u.mem_read(p+len(data),1))
            if not b:return data.decode()
            if b==b'\0':return data.decode()
            data+=b;assert len(data)<8192
    def alloc(self):
        p=self.heap+self.next;self.next+=0x400;assert self.next<0xf0000;return p
    def string(self,s):
        p=self.alloc();data=s.encode();assert len(data)<1024;self.u.mem_write(p,data+b'\0');return p
    def ret(self,value=0,high=None):
        self.u.reg_write(a.UC_ARM_REG_R0,value&0xffffffff)
        if high is not None:self.u.reg_write(a.UC_ARM_REG_R1,high&0xffffffff)
        self.u.reg_write(a.UC_ARM_REG_PC,self.u.reg_read(a.UC_ARM_REG_LR))
    def reset(self):
        self.next=0x10000;self.attrs={};self.qids={};self.qptrs={};self.values={};self.archives={};self.input='';self.output='';self.deleted=0;self.deallocated=0;self.io=[]
        self.u.mem_write(self.obj,b'\xa5'*0x100);self.u.mem_write(self.event,b'\xa5'*0x1100)
        self.put(self.stream,self.stream+0x100)
        for offset,marker in ((4,0x104),(12,0x10c),(16,0x110),(20,0x114)):
            self.put(self.stream+0x100+offset,self.stop+marker)
    def queue(self,qid):
        if not qid:return 0
        if qid not in self.qptrs:self.qptrs[qid]=self.alloc();self.qids[self.qptrs[qid]]=qid
        p=self.qptrs[qid];reply=list(map(int,self.bridge.ask(f'q_snapshot {qid}').split()));n=reply[0];assert len(reply)==1+2*n and n<=32
        data=p+0x40
        self.put(p+8,data);self.put(p+12,n)
        for index in range(n):
            typ,aid=reply[1+2*index:3+2*index];v=self.alloc();self.put(data+4*index,v);self.u.mem_write(v+4,struct.pack('<H',typ))
            if aid:
                ap=next((k for k,val in self.attrs.items() if val==aid),None)
                if ap is None:ap=self.alloc();self.attrs[ap]=aid
                self.put(v+8,ap)
            else:self.put(v+8,0)
        return p
    def code(self,u,address,size,unused):
        if address==self.stop:u.emu_stop();return
        if any(r['address']<=address<r['address']+r['size'] for r in self.methods.values()):self.covered.add(address);return
        r=[u.reg_read(a.UC_ARM_REG_R0+i) for i in range(4)];b=self.bridge
        if address==self.stop+0x104:
            assert r[0]==self.stream;self.deleted+=1;self.ret();return
        if address==self.stop+0x10c:
            assert r[0]==self.stream and r[2]==r[3]==0 and self.get(u.reg_read(a.UC_ARM_REG_SP))==0
            self.io.append(['seek',0,0]);self.ret(0,0);return
        if address in (self.stop+0x110,self.stop+0x114):
            assert r[0]==self.stream and r[1]==self.event+32
            if address==self.stop+0x110:
                assert r[2]==4096
                if self.forced>0:u.mem_write(r[1],bytes((i*17+3)&255 for i in range(min(4096,self.forced))))
                self.io.append(['read',r[2]])
            else:self.io.append(['write',r[2]])
            self.ret(self.forced);return
        row=self.addresses.get(address);assert row,hex(address)
        self.boundaries[address]=row;name=row['demangled']
        if name.startswith('operator delete('):
            assert r[0]==self.obj;self.deallocated+=1;self.ret();return
        if name.startswith('Core::Portable::AttributeAllocator::getDefault('):self.ret(self.heap+0x8000);return
        if name.startswith('Core::Portable::Attributes::Attributes('):
            assert r[1]==self.heap+0x8000;self.attrs[r[0]]=int(b.ask('a_new'));self.put(r[0]+8,r[1]);self.ret(r[0]);return
        if name.startswith('Core::Portable::Attributes::~Attributes('):
            b.ask('a_destroy '+str(self.attrs.pop(r[0])));self.ret(r[0]);return
        if name.startswith('Core::Portable::Attributes::lookupOrAdd('):
            p=self.alloc();self.values[p]=(self.attrs[r[0]],self.text(r[1]));self.ret(p);return
        if name.startswith('Core::Portable::AttributeValue::makeQueue('):
            aid,key=self.values[r[0]];qid=int(b.ask(f'a_makequeue {aid} {enc(key)}'));self.ret(self.queue(qid));return
        if name.startswith('Core::Portable::AttributeQueue::appendAttributes('):
            aid=int(b.ask(f'q_append {self.qids[r[0]]} {self.attrs[self.obj]}'));p=self.alloc();self.attrs[p]=aid;self.ret(p);return
        if name.startswith('Core::Portable::AttributeValue::set(char const*, bool)'):
            aid,key=self.values[r[0]];assert r[2]==0;b.ask(f'a_setstr {aid} {enc(key)} {enc(self.text(r[1]))}');self.ret();return
        if name.startswith('Core::Portable::AttributeValue::set(long long)'):
            aid,key=self.values[r[0]];v=(r[3]<<32)|r[2];v=v-(1<<64) if v>>63 else v;b.ask(f'a_setint {aid} {enc(key)} {v}');self.ret();return
        if name.startswith('Core::Portable::Attributes::getString('):
            value=dec(b.ask(f'a_getstr {self.attrs[r[0]]} {enc(self.text(r[1]))}'));self.ret(self.string(value));return
        if name.startswith('Core::Portable::Attributes::getInt('):
            value=int(b.ask(f'a_getint {self.attrs[r[0]]} {enc(self.text(r[1]))}'));self.ret(value,value>>32);return
        if name.startswith('Core::CStringBuffer<128>::operator=(char const*)'):
            value=dec(b.ask('cstring '+enc(self.text(r[1]))));u.mem_write(r[0],value.encode()+b'\0');self.ret(r[0]);return
        if name.startswith('Core::Portable::Attributes::getQueue('):
            qid=int(b.ask(f'a_queue {self.attrs[r[0]]} {enc(self.text(r[1]))}'));self.ret(self.queue(qid));return
        if name.startswith('Core::Portable::Archiver::Archiver('):
            assert r[1]==self.stream and r[2]==0 and r[3] in (0,1);self.archives[r[0]]=r[3];self.ret(r[0]);return
        if name.startswith('Core::Portable::Archiver::load('):
            assert self.archives[r[0]]==0;self.ret(int(b.ask(f'a_load {self.attrs[r[1]]} {enc(self.input)}')));return
        if name.startswith('Core::Portable::Archiver::save('):
            assert self.archives[r[0]]==1;reply=b.ask(f'a_save {self.attrs[r[1]]}').split();self.output=reply[1];self.ret(int(reply[0]));return
        raise AssertionError('Forbidden external execution: '+name)
    def call(self,cls,method,*args,stack=()):
        for reg in range(a.UC_ARM_REG_R0,a.UC_ARM_REG_R12+1):self.u.reg_write(reg,0)
        self.u.reg_write(a.UC_ARM_REG_R0,self.obj)
        for i,v in enumerate(args,1):self.u.reg_write(a.UC_ARM_REG_R0+i,v&0xffffffff)
        sp=self.stack+0x18000
        for i,v in enumerate(stack):self.put(sp+4*i,v)
        self.u.reg_write(a.UC_ARM_REG_SP,sp);self.u.reg_write(a.UC_ARM_REG_LR,self.stop)
        self.u.emu_start(self.methods[cls,method]['address'],self.stop,count=100000)
        assert self.u.reg_read(a.UC_ARM_REG_PC)==self.stop,(cls,method,hex(self.u.reg_read(a.UC_ARM_REG_PC)))
        return self.u.reg_read(a.UC_ARM_REG_R0)
    def read(self,total,pos,result,part,count,ctor):
        self.reset();self.forced=result;self.call('FileReader',ctor,self.stream,total);self.put(self.obj+12,pos)
        self.put(self.event+16,0x12345678);self.put(self.event+20,0x11223344);self.put(self.event+24,0x55667788);self.u.mem_write(self.event+28,struct.pack('<HH',part,count))
        ret=self.call('FileReader','readData',self.event);part,count=struct.unpack('<HH',self.u.mem_read(self.event+28,4));data=bytes(self.u.mem_read(self.event+32,4096)).hex()
        answer=f'{ret} {self.get(self.obj+12)} {self.get(self.event+20)} {self.get(self.event+24)} {part} {count} {self.get(self.event+16)} {len(self.io)} {self.io[0][1]} {data}'
        self.call('FileReader','D1');assert self.deleted==1 and self.deallocated==0;return answer
    def write(self,part,count,result,old,ctor):
        self.reset();self.forced=result;self.call('FileWriter',ctor,self.stream);self.u.mem_write(self.obj+8,bytes([old]));self.u.mem_write(self.event+28,struct.pack('<HH',part,count))
        ret=self.call('FileWriter','writeData',self.event);answer=f'{ret} {bytes(self.u.mem_read(self.obj+8,1))[0]} {len(self.io)} {self.io[0][1] if self.io else 0}'
        self.call('FileWriter','D1');assert self.deleted==1 and self.deallocated==0;return answer
    def list_read(self,text,index,ctor):
        self.reset();self.call('FileListReader',ctor);assert self.get(self.obj+32)==self.get(self.obj+36)==0
        self.put(self.obj+36,index);self.input=text;loaded=self.call('FileListReader','fromStream',self.stream)
        target=self.event;self.u.mem_write(target,b'sentinel-name\0');self.u.mem_write(target+128,b'sentinel-title\0');self.u.mem_write(target+256,struct.pack('<qB',-123,1))
        result=self.call('FileListReader','getNextEntry',target);size=struct.unpack('<q',self.u.mem_read(target+256,8))[0];directory=bytes(self.u.mem_read(target+264,1))[0];idx=self.get(self.obj+36);idx=idx-(1<<32) if idx>>31 else idx
        answer=f'{loaded} {result} {idx} {enc(self.text(target))} {enc(self.text(target+128))} {size} {directory}'
        self.bridge.ask('a_destroy '+str(self.attrs[self.obj]));return answer
    def list_write(self,entries,ctor):
        self.reset();self.call('FileListWriter',ctor)
        for name,title,size,directory in entries:
            self.call('FileListWriter','addEntry',self.string(name),0 if title is None else self.string(title),stack=(size&0xffffffff,(size>>32)&0xffffffff,int(directory)))
        self.call('FileListWriter','toStream',self.stream);assert self.io==[['seek',0,0]]
        answer='0 '+self.output;self.bridge.ask('a_destroy '+str(self.attrs[self.obj]));return answer
    def lifecycle(self,kind,ctor,dtor,has_stream):
        self.reset();cls=('FileRequestHandler','FileReader','FileWriter')[kind]
        stream=self.stream if has_stream else 0
        self.call(cls,ctor,*((stream,17) if kind==1 else (stream,)))
        equal=int(self.call('FileRequestHandler','getStream')==stream)
        read=write=0
        if kind==0:
            read=self.call(cls,'readData',self.event);write=self.call(cls,'writeData',self.event)
        self.call('FileRequestHandler' if dtor=='finish' else cls,dtor)
        # Only observer state is read after destruction; never the ended object.
        return f'{equal} {read} {write} {self.deleted} {self.deallocated}'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--bridge',type=Path,required=True);p.add_argument('--run',required=True);args=p.parse_args()
    repo=args.repo.resolve();out=repo/'evidence/recovery/2026-10-27/uc-file-services'/args.run;out.mkdir(parents=True,exist_ok=False)
    bridge=Bridge(args.bridge.resolve(),out);records=(out/'cases.jsonl').open('w');totals={};metadata={};count=0
    def check(role,kind,ctor,command,expected):
        nonlocal count
        actual=bridge.ask(command);record=dict(role=role,kind=kind,constructor=ctor,command=command,expected=expected,actual=actual,passed=actual==expected)
        records.write(json.dumps(record)+'\n');records.flush();assert record['passed'],record
        count+=1;totals[kind]=totals.get(kind,0)+1
    try:
        for role in ('client','server'):
            arm=Original(repo,role,bridge)
            for ctor in ('C1','C2'):
                for kind in (0,1,2):
                    for has_stream in (0,1):
                        for dtor in (('D0','D1','D2','finish') if kind==0 else ('D0','D1','finish')):
                            command=f'variant {kind} {ctor} {dtor} {has_stream}'
                            check(role,'lifecycle',ctor,command,arm.lifecycle(kind,ctor,dtor,has_stream))
                for total in (0,1,4095,4096,4097,0xffffffff):
                    for pos in (0,1,4095,0xfffffff0,0xffffffff):
                        for result in (-2147483648,-1,0,1,4095,4096,65535,2147483647):
                            command=f'read {total} {pos} {result} 7 54321';check(role,'read',ctor,command,arm.read(total,pos,result,7,54321,ctor))
                for part in (0,1,2,3,65535):
                    for length in (0,1,4095,4096,4097,65535):
                        for result in (-2147483648,-1,0,1,4096,2147483647):
                            for old in (0,1):
                                command=f'write {part} {length} {result} {old}';check(role,'write',ctor,command,arm.write(part,length,result,old,ctor))
                docs=['{}','{"files":[]}','{"files":[{}]}','{"files":[null,{}]}','{"files":[1,{}]}','{"files":[[],{}]}','{"files":[{"name":"one","title":"title","size":-1,"dir":-7},{}]}','{"files":[{"name":"'+('x'*140)+'","title":"'+('y'*150)+'","size":9223372036854775807,"dir":4294967296}]}','{"files":[{"name":12,"title":false,"size":"42","dir":0}]}','{','{"files":[{},','{"files":{}}']
                for text in docs:
                    for index in (-2147483648,-1,0,1,2,2147483647):
                        command=f'list_read {enc(text)} {index}';check(role,'list_read',ctor,command,arm.list_read(text,index,ctor))
                lists=[[],[('one',None,0,False)],[('one','',1,True)],[('one','title',-1,False)],[('a"\\\n','title\t',9223372036854775807,True)],[('x'*160,'y'*180,-9223372036854775808,True)],[('one','t',0,False),('two',None,1,True),('one','',-8,False)]]
                for entries in lists:
                    command='list_write '+str(len(entries))+''.join(f' {enc(n)} {"NULL" if t is None else enc(t)} {s} {int(d)}' for n,t,s,d in entries)
                    check(role,'list_write',ctor,command,arm.list_write(entries,ctor))
            assert all(row['address'] in arm.covered for row in arm.methods.values())
            metadata[role]=dict(original_elf_sha256=arm.manifest['sha256'],functions=list(arm.methods.values()),external_boundaries=list(arm.boundaries.values()),executed_app_addresses=sorted(arm.covered))
            print(role,'passed',count,flush=True)
    finally:
        records.close();bridge.close()
    (out/'validation.json').write_text(json.dumps(dict(passed=True,cpp_differential_passed=True,arm_differential_passed=True,original_core_binary_executed=False,cases=count,totals=totals,results_sha256=sha(out/'cases.jsonl'),bridge_sha256=bridge.digest,metadata=metadata,ordinary_return_declarations_verified=False,lifecycle_variant_native_validation_complete=True,domain='Source CCL API boundary adaptation; no original Core behavior/ABI claim. Owned in-memory streams, no physical IO. Data array full4096 retained; injected signed read/write results may violate stream contracts but fixture writes at most4096. List string prefixes only, indeterminate tails excluded; bounded32values, no concurrent mutation or allocation failures.'),indent=2)+'\n')
    print(out/'validation.json',flush=True)
if __name__=='__main__':main()
