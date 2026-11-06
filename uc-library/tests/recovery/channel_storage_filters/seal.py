"""Produce hash-bound local observations and one v1 handoff per sealed identity."""
import hashlib,json,subprocess,sys,datetime
from pathlib import Path
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
sys.path.insert(0,str(T));import check,native
E=R/'evidence/recovery/2026-11-06/channel-preset82';E.mkdir(parents=True,exist_ok=True)
PYTHON='uc-library/.venv/bin/python';CHECK=str(T.relative_to(R)/'check.py')
def sha(p):return hashlib.sha256((R/p).read_bytes()).hexdigest()
checks=[];logs=[]
for mode in ['format','compile','symbols','native','replay']:
 argv=[PYTHON,CHECK,mode];p=subprocess.run(argv,cwd=R,text=True,capture_output=True)
 path=E/(mode+'.log');path.write_text(p.stdout+p.stderr);assert p.returncode==0,path
 checks.append({'kind':mode,'argv':argv,'timeout_seconds':300});logs.append(str(path.relative_to(R)))
files=[check.CPP,check.HPP,check.DRIVER,CHECK,str(T.relative_to(R)/'native.py'),str(T.relative_to(R)/'fixtures.json'),str(T.relative_to(R)/'seal.py')]
deps=['third_party/ccl-framework/core/portable/'+p for p in ['corestorage.h','coretypeinfo.h','corecomponent.h','corecomponent.cpp','coreparams.h','coreparams.cpp','coreparaminfo.h']]+[check.LIB+'libcorelib.a',check.LIB+'libpresonus_core_allocator.a']
versions={a:subprocess.check_output(args,cwd=R,text=True).strip() for a,args in {'formatter':['uc-library/.venv/bin/clang-format','--version'],'compiler':['/usr/bin/c++','--version'],'ccl_commit':['git','-C','third_party/ccl-framework','rev-parse','HEAD'],'ccl_history':['git','-C','third_party/ccl-framework','rev-list','--parents','-n','1','e8cbdea4a4a20e15111f5a690798a259c0374b31']}.items()}
import unicorn,elftools,platform
versions.update(unicorn=unicorn.__version__,pyelftools=elftools.__version__,python=platform.python_version())
data=json.loads((T/'fixtures.json').read_text());assert data['ranges']==native.RANGES
literals={}
with native.ELF.open('rb') as f:
 from elftools.elf.elffile import ELFFile
 elf=ELFFile(f)
 for addr in [0x35b15c,0x420b30,0x15fc60,0x15fc78,0x15fc90,0x161274]:
  sec=next(s for s in elf.iter_sections() if s['sh_addr']<=addr<s['sh_addr']+s['sh_size'] and s['sh_type']!='SHT_NOBITS');off=sec['sh_offset']+addr-sec['sh_addr'];b=native.RAW[off:].split(b'\0',1)[0];literals[hex(addr)]={'text':b.decode(),'file_offset':off,'terminated_hex':(b+b'\0').hex()}
limitations=['Portable CCL source port; original ordinary return declarations, class layout, ARM ABI and hardware compatibility remain unverified.','Original shouldLoad at 0x503e8 compares literal Comp 0x436f6d70 loaded at 0x503dc, not Para as earlier task prose states. Exact original hash and range are retained.','Original provider/string/dynamic_cast boundaries are intercepted in ARM observations; native __aeabi_fcmpgt and its comparison subcalls execute original instructions. CCL provider behavior is separately executed in host tests, never claimed as original binary behavior.','Target and three real Parameter controls are borrowed and must outlive the filter. Para save objects must be actual Parameter instances. No ownership or original field-layout claim.','Native synthetic controller/cast results test application decision logic. Production host replay uses actual CCL Component controllers and actual noncomponent IParamObserver; controller identity and real notification lifecycle are checked.','ChannelParamTag and other shared shouldSave work excluded. Root retains full integration and guarded admission.']
proof={'version':1,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elf_sha256':native.SHA,'elf_path':str(native.ELF.relative_to(R)),'ranges':native.RANGES,'literals':literals,'native_helper_ranges':[{'address':a,'size':z,'sha256':hashlib.sha256(native.RAW[a-0x8000:a-0x8000+z]).hexdigest()} for a,z in [(0x157848,112),(0x1578b8,40),(0x157940,24)]],'versions':versions,'native_cases':len(data['cases']),'native_float_calls':sum(c['output']['native_float_calls'] for c in data['cases']),'native_memory_domain':'All writes constrained to bounded synthetic stack; no writes to target/parameter/controller memory permitted. All executed PCs constrained to two app bodies and actual float helper interval; intercepted external boundary entry points explicit.','source_hashes':{p:sha(p) for p in files},'dependency_hashes':{p:sha(p) for p in deps},'commands':checks,'logs':logs,'limitations':limitations}
proofpath=str((E/'proof.json').relative_to(R));(R/proofpath).write_text(json.dumps(proof,indent=2)+'\n')
for index in [1,2]:
 task=f'rolling200_02_channel_filters25_0{index}';packet=f'temp/recovery-work/rolling200-02/next-implementation118/prepared118/packets/{task}';request=json.loads((R/packet/'request.json').read_text());o=request['originals'][0]['original'];original={k:o[k] for k in ['firmware','role','mangled','address','size']};original.update(elf_sha256=o['elf'],section='.text')
 artifacts=[]
 for kind,paths in [('source',files[:2]),('test',[check.DRIVER]),('replay',[CHECK,str(T.relative_to(R)/'native.py'),str(T.relative_to(R)/'seal.py')]),('fixture',[str(T.relative_to(R)/'fixtures.json')]),('proof',[proofpath,*logs]),('dependency',deps),('packet',[packet+'/context.json',packet+'/request.json',packet+'/ELF_CONTEXT.md'])]:
  artifacts +=[{'kind':kind,'path':p,'sha256':sha(p)} for p in paths]
 handoff={'version':1,'task_id':task,'namespace':'Presonus::Mixer','packet_manifest':packet+'/context.json','originals':[original],'artifacts':artifacts,'checks':checks,'validation_domain':'2520 cases: 2400 load combinations across Comp/Para/other types, 10 names including null, all 8 control-presence masks and 10 IEEE-754 bit patterns; 120 save combinations across type, target equality, null/real parameter, no/noncomponent/real named Component controller. Real provider identity and parameter edit notification checked. Native value call selection and return outputs compared with host.', 'limitations':limitations,'build_integration':{'production_partition':'common','sources':[check.CPP],'public_headers':[check.HPP],'test_sources':[check.DRIVER],'test_target':'channel_storage_filters_replay','link_dependencies':['pinned CCL corelib','presonus_core_allocator'],'ctest_argv':[PYTHON,CHECK,'replay','<canonical-built-channel_storage_filters_replay>',str(T.relative_to(R)/'fixtures.json')],'fixture_binding':{'path':str(T.relative_to(R)/'fixtures.json'),'sha256':sha(str(T.relative_to(R)/'fixtures.json'))}}}
 target=R/f'uc-library/candidates/{task}/HANDOFF.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(handoff,indent=2)+'\n')
print(proofpath)
