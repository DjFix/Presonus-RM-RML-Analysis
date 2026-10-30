#!/usr/bin/env python3
"""Original Presonus app-only execution vs native app, both bound to actual CCL."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn import arm_const as a

def word(v):return struct.pack('<I',v&0xffffffff)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def encode(s):return s.encode().hex() or '-'
def decode(s):return bytes.fromhex(s).decode() if s!='-' else ''

class Bridge:
    def __init__(self,executable,root,out):
        self.stderr=(out/'bridge-stderr.log').open('w');self.log=(out/'bridge-protocol.jsonl').open('w')
        self.p=subprocess.Popen([str(executable),str(root)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.stderr,text=True,bufsize=1)
        (out/'bridge-process.json').write_text(json.dumps(dict(pid=self.p.pid,executable=str(executable),sha256=sha(executable),owned_filesystem_root=str(root)),indent=2)+'\n')
    def ask(self,text):
        self.p.stdin.write(text+'\n');self.p.stdin.flush();response=self.p.stdout.readline().strip()
        self.log.write(json.dumps(dict(request=text,response=response))+'\n');self.log.flush()
        assert response and not response.startswith('ERROR'),(text,response,self.p.poll())
        return response
    def trace(self):
        fields=self.ask('trace_get').split();n=int(fields.pop(0));fs=[decode(fields.pop(0)) for _ in range(n)];n=int(fields.pop(0));arrays=[decode(fields.pop(0)) for _ in range(n)];assert not fields
        return sorted(fs),arrays
    def close(self):
        if self.p.poll() is None:self.ask('quit')
        assert self.p.wait(timeout=10)==0
        self.log.close();self.stderr.close()

class Original:
    heap,stack,stop=0x10000000,0x20000000,0x30000000
    obj,base,arg=heap+0x1000,heap+0x3000,heap+0x4000
    def __init__(self,repo,role,bridge):
        self.bridge=bridge;root=repo/'uc-library/recovered-all'/role
        self.manifest=json.loads((root/'manifest.json').read_text());binary=repo/self.manifest['path'];assert sha(binary)==self.manifest['sha256']
        rows=json.loads((root/'symbols.json').read_text());self.addresses={r['address']:r for r in rows if r['kind']=='STT_FUNC'}
        self.methods={}
        for r in rows:
            if r['kind']!='STT_FUNC' or not r['demangled'].startswith('Presonus::FileCleanup::'):continue
            n=r['mangled'];key='C1' if 'FileCleanupC1E' in n else 'C2' if 'FileCleanupC2E' in n else 'D1' if 'FileCleanupD1E' in n else 'F' if 'addFileToRemove' in n else 'D' if 'addDirectoryToRemove' in n else 'cleanup'
            self.methods[key]=r
        assert len(self.methods)==6
        self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM);raw=binary.read_bytes()
        with binary.open('rb') as stream:
            elf=ELFFile(stream);ranges=[]
            for s in elf.iter_segments():
                if s['p_type']!='PT_LOAD':continue
                start=int(s['p_vaddr'])&~4095;end=(int(s['p_vaddr'])+int(s['p_memsz'])+4095)&~4095
                if ranges and start<=ranges[-1][1]:ranges[-1]=(ranges[-1][0],max(end,ranges[-1][1]))
                else:ranges.append((start,end))
            for start,end in ranges:self.u.mem_map(start,end-start)
            for s in elf.iter_segments():
                if s['p_type']=='PT_LOAD':self.u.mem_write(int(s['p_vaddr']),s.data())
            for r in self.methods.values():
                s=elf.get_section(r['section']);off=int(s['sh_offset'])+r['address']-int(s['sh_addr']);data=raw[off:off+r['size']]
                assert off==r['file_offset'] and hashlib.sha256(data).hexdigest()==r['sha256'] and data==(root/r['export_path']).read_bytes()
        for p,size in ((self.heap,0x100000),(self.stack,0x20000),(self.stop,4096)):self.u.mem_map(p,size)
        self.boundaries={};self.executed=set();self.u.hook_add(UC_HOOK_CODE,self.code)
    def read(self,p):return struct.unpack('<I',self.u.mem_read(p,4))[0]
    def text(self,p):
        data=bytearray()
        while True:
            b=bytes(self.u.mem_read(p+len(data),1))
            if b==b'\0':return data.decode()
            data+=b;assert len(data)<4096
    def filename(self,p,s):
        data=s.encode()[:255];self.u.mem_write(p,data+b'\0'*(256-len(data)))
    def ret(self,value=0):
        self.u.reg_write(a.UC_ARM_REG_R0,value&0xffffffff);self.u.reg_write(a.UC_ARM_REG_PC,self.u.reg_read(a.UC_ARM_REG_LR))
    def code(self,u,address,size,unused):
        if address==self.stop:u.emu_stop();return
        if any(r['address']<=address<r['address']+r['size'] for r in self.methods.values()):self.executed.add(address);return
        r=[u.reg_read(a.UC_ARM_REG_R0+i) for i in range(4)];row=self.addresses.get(address);assert row,hex(address)
        self.boundaries[address]=row;name=row['demangled'];b=self.bridge
        if name.startswith('memcpy'):
            assert r[2]==256;u.mem_write(r[0],bytes(u.mem_read(r[1],r[2])));self.ret(r[0]);return
        if name.startswith('Core::Vector<Core::Portable::FileName>::resize('):
            assert r[1]==0 and r[0] in (self.obj+0x100,self.obj+0x114)
            self.peers[r[0]]=int(b.ask('vector_new'));self.ret(1);return
        if name.startswith('Core::MutableVector<Core::Portable::FileName') and '::add(' in name:
            vector=r[0]-4;peer=self.peers[vector];result=int(b.ask(f'vector_add {peer} {encode(self.text(r[1]))}'))
            snapshot=b.ask(f'vector_snapshot {peer}').split();count=int(snapshot[0]);assert count==len(snapshot)-1 and count<=32
            data=self.heap+(0x10000 if vector==self.obj+0x100 else 0x20000)
            for i,s in enumerate(snapshot[1:]):self.filename(data+i*256,decode(s))
            u.mem_write(vector+4,word(data if count else 0));u.mem_write(vector+8,word(count));self.ret(result);return
        if name.startswith('Core::Vector<Core::Portable::FileName>::~Vector'):
            vector=r[0];peer=self.peers.pop(vector);self.destroy_order.append('files' if vector==self.obj+0x100 else 'directories')
            b.ask(f'vector_destroy {peer}');self.ret(r[0]);return
        if name.startswith('Core::Portable::FileName::descend('):
            result=decode(b.ask(f'descend {encode(self.text(r[0]))} {encode(self.text(r[1]))}'));self.filename(r[0],result);self.ret(r[0]);return
        operations={'Core::Portable::FileUtils::fileExists(':'file_exists','Core::Portable::FileUtils::dirExists(':'dir_exists','Core::Portable::FileUtils::deleteFile(':'delete_file','Core::Portable::FileUtils::removeDirectory(':'remove_directory'}
        for prefix,operation in operations.items():
            if name.startswith(prefix):self.ret(int(b.ask(operation+' '+encode(self.text(r[0])))));return
        if 'FileIterator::FileIterator(' in name:
            self.iterators[r[0]]=int(b.ask('iterator_new '+encode(self.text(r[1]))));self.ret(r[0]);return
        if 'FileIterator::next()' in name:
            response=b.ask('iterator_next '+str(self.iterators[r[0]])).split()
            if response==['NONE']:self.ret(0);return
            assert len(response)==4 and response[0]=='ENTRY'
            data=self.heap+0x30000;self.filename(data,decode(response[1]));u.mem_write(data+256,bytes([int(response[2]),int(response[3])]))
            self.ret(data);return
        if 'FileIterator::~FileIterator' in name:
            b.ask('iterator_destroy '+str(self.iterators.pop(r[0])));self.ret(r[0]);return
        raise AssertionError('Forbidden external execution: '+name)
    def call(self,kind,arg=None):
        for reg in range(a.UC_ARM_REG_R0,a.UC_ARM_REG_R12+1):self.u.reg_write(reg,0)
        self.u.reg_write(a.UC_ARM_REG_R0,self.obj)
        if arg is not None:self.filename(self.arg,arg);self.u.reg_write(a.UC_ARM_REG_R1,self.arg)
        self.u.reg_write(a.UC_ARM_REG_SP,self.stack+0x18000);self.u.reg_write(a.UC_ARM_REG_LR,self.stop)
        self.u.emu_start(self.methods[kind]['address'],self.stop,count=1000000)
        assert self.u.reg_read(a.UC_ARM_REG_PC)==self.stop
        return self.u.reg_read(a.UC_ARM_REG_R0)
    def run(self,case,path,variant):
        self.peers={};self.iterators={};self.destroy_order=[];self.u.mem_write(self.obj,b'\xa5'*0x300)
        self.bridge.ask('reset');self.bridge.ask('trace_begin');self.call(variant,str(path))
        assert self.text(self.obj)==str(path)
        for offset in (0x100,0x114):
            assert self.read(self.obj+offset+4)==0 and self.read(self.obj+offset+8)==0 and self.read(self.obj+offset+16)==5
        # Caller filename storage is independent after the app copies its base.
        self.filename(self.arg,'caller-name-mutated-after-construction')
        added=[self.call('F',s) for s in case['files']]+[self.call('D',s) for s in case['directories']]
        result=self.call('cleanup');self.call('D1');assert not self.peers and not self.iterators
        fs,arrays=self.bridge.trace();arrays=['files' if x=='peer:1' else 'directories' if x=='peer:2' else x for x in arrays]
        assert self.destroy_order==['directories','files']
        return dict(result=result,add_results=added,filesystem_trace=fs,array_deallocation_trace=arrays)

def recipes():
    def item(path,kind='file',mode=0o600):return dict(path=path,kind=kind,mode=mode)
    def case(files=(),directories=(),nodes=(),mode=0o700):return dict(files=list(files),directories=list(directories),nodes=list(nodes),mode=mode)
    return [case(),case(['missing']),case(['one'],nodes=[item('one')]),case(['one','one'],nodes=[item('one')]),
      case(['unreadable','after'],nodes=[item('unreadable',mode=0),item('after')]),
      case(['one','after'],nodes=[item('one'),item('after')],mode=0o500),
      case(directories=['missing']),case(directories=['cache'],nodes=[item('cache','directory',0o700)]),
      case(directories=['cache'],nodes=[item('cache','directory',0o700),item('cache/one'),item('cache/two')]),
      case(directories=['cache'],nodes=[item('cache','directory',0o700),item('cache/.hidden')]),
      case(directories=['cache'],nodes=[item('cache','directory',0o700),item('cache/nested','directory',0o700)]),
      case(directories=['cache'],nodes=[item('cache','directory',0o700),item('cache/one'),item('cache/.hidden'),item('cache/nested','directory',0o700)]),
      case(directories=['locked','after'],nodes=[item('locked','directory',0o500),item('locked/one'),item('after','directory',0o700)]),
      case(directories=['locked','after'],nodes=[item('locked','directory',0),item('locked/one'),item('after','directory',0o700)]),
      case(directories=['cache','cache'],nodes=[item('cache','directory',0o700),item('cache/one')]),
      case(files=['cache'],directories=['cache'],nodes=[item('cache','directory',0o700)]),
      case(files=['cache'],directories=['cache'],nodes=[item('cache','directory',0o700),item('cache/one')]),
      case(files=[f'file{i}' for i in range(8)],directories=[f'dir{i}' for i in range(7)],nodes=[item(f'file{i}') for i in range(8)]+[item(f'dir{i}','directory',0o700) for i in range(7)])]

def prepare(root,case):
    assert not root.exists();root.mkdir()
    for item in sorted(case['nodes'],key=lambda x:x['path'].count('/')):
        p=root/item['path'];assert p.is_relative_to(root) and '..' not in Path(item['path']).parts
        if item['kind']=='directory':p.mkdir()
        else:p.write_bytes(('owned fixture:'+item['path']).encode())
    for item in sorted(case['nodes'],key=lambda x:x['path'].count('/'),reverse=True):(root/item['path']).chmod(item['mode'])
    root.chmod(case['mode'])
def snapshot(root,case):
    # Restore only known generated modes after the tested operation, solely to
    # inspect survivors; capture their original mode before each restoration.
    if not root.exists():return dict(root_exists=False,nodes={})
    modes={'':root.stat().st_mode&0o777}
    root.chmod(0o700)
    for item in sorted(case['nodes'],key=lambda x:x['path'].count('/')):
        if item['kind']=='directory':
            try:
                p=root/item['path'];modes[item['path']]=p.stat().st_mode&0o777;p.chmod(0o700)
            except FileNotFoundError:pass
    nodes={}
    for p in sorted(root.rglob('*')):
        relative=str(p.relative_to(root))
        if p.is_dir():nodes[relative]=dict(kind='directory',mode=modes[relative])
        else:
            mode=p.stat().st_mode&0o777;p.chmod(0o600)
            nodes[relative]=dict(kind='file',mode=mode,sha256=sha(p))
    return dict(root_exists=True,mode=modes[''],nodes=nodes)

def main():
    repo=Path(sys.argv[1]).resolve();executable=Path(sys.argv[2]).resolve();run=sys.argv[3]
    assert os.geteuid()!=0,'Permission cases require unprivileged fixture owner'
    work=repo/'temp/application-runtime'/run;out=repo/'evidence/recovery/2026-10-27/application-runtime'/run
    for p in (work,out):p.mkdir(exist_ok=False,parents=True)
    owned=work/'owned';owned.mkdir();archive=work/'original-survivors';archive.mkdir()
    bridge=Bridge(executable,owned,out);results=[];metadata={}
    try:
        for role in ('client','server'):
            original=Original(repo,role,bridge)
            for index,case in enumerate(recipes()):
                for variant in ('C1','C2'):
                    name=f'{role}-{index:03d}-{variant}';root=owned/name
                    prepare(root,case);expected=original.run(case,root,variant);expected['tree']=snapshot(root,case)
                    if root.exists():root.rename(archive/name)
                    prepare(root,case);bridge.ask('reset');bridge.ask('trace_begin');bridge.ask('native_new '+encode(str(root)))
                    added=[int(bridge.ask('native_add_file '+encode(s))) for s in case['files']]+[int(bridge.ask('native_add_directory '+encode(s))) for s in case['directories']]
                    actual=dict(result=int(bridge.ask('native_cleanup')),add_results=added)
                    bridge.ask('native_destroy');actual['filesystem_trace'],actual['array_deallocation_trace']=bridge.trace();actual['tree']=snapshot(root,case)
                    row=dict(role=role,index=index,constructor=variant,input=case,expected=expected,actual=actual,passed=actual==expected)
                    results.append(row);(out/'cases.json').write_text(json.dumps(results,indent=2)+'\n')
                    assert row['passed'],row
            metadata[role]=dict(original_elf_sha256=original.manifest['sha256'],functions=list(original.methods.values()),boundaries=list(original.boundaries.values()),executed_app_addresses=sorted(original.executed))
            print(role,'passed',len(recipes())*2,flush=True)
    finally:bridge.close()
    (out/'validation.json').write_text(json.dumps(dict(passed=True,cpp_differential_passed=True,original_core_binary_executed=False,native_backend='Actual pinned CCL source Provider',cases=len(results),results_sha256=sha(out/'cases.json'),metadata=metadata,bridge_sha256=sha(executable),allocation_failure_cases=False,ordinary_return_declarations_verified=False,scope='Fresh owned trees only, regular files/directories, no symlinks/concurrent mutation/exceptions; source-backed vector/filesystem contracts; pointer-size Core ABI differs and is not claimed'),indent=2)+'\n')
    print(out/'validation.json')
if __name__=='__main__':main()
