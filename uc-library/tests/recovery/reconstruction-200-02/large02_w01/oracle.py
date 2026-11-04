"""Independent exact ARM application instruction oracle. Core provider bodies excluded."""
import argparse, hashlib, json, struct
from functools import lru_cache
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
ROOT = next(p for p in Path(__file__).resolve().parents if (p/'uc-library/tools/recovery/accept_worker.py').is_file())
ELF = ROOT / 'rootfs/CS18_v13840/home/root/surface'
SHA = '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
EXTRA = ['eqpage','geqcount','bankOffset','secondaryInputs','channelLink','busLink','busMain','channelMain','channelMainPresent','busPresent','groupPresent','meter','bankSwitchBlocked']
DEFAULT = [0,4,3,0,0,0,0,0,0,1,1,0,0]
REG = [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]

@lru_cache(None)
def binary():
    raw=ELF.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==SHA
    with ELF.open('rb') as stream:
        elf=ELFFile(stream)
        symbols={s.name:{'address':s['st_value'],'size':s['st_size'],'section_index':s['st_shndx']} for s in elf.get_section_by_name('.symtab').iter_symbols() if s['st_info']['type']=='STT_FUNC'}
        sections={i:{'address':sec['sh_addr'],'offset':sec['sh_offset'],'name':sec.name} for i,sec in enumerate(elf.iter_sections())}
        segments=[(seg['p_vaddr'],seg.data()) for seg in elf.iter_segments() if seg['p_type']=='PT_LOAD']
    return raw,symbols,sections,segments

def execute(index, args):
    raw,symbols,sections,segments=binary()
    packet=ROOT/f'temp/recovery-work/reconstruction-200-02/isolated-batch01/packets/large02_w01_{index:02}'
    target=json.loads((packet/'request.json').read_text())['targets'][0]
    symbol=symbols[target['mangled']]
    assert symbol['address']==target['address'] and symbol['size']==target['size']
    section=sections[symbol['section_index']]
    offset=section['offset']+symbol['address']-section['address']
    checked={'elf_sha256':SHA,'mangled':target['mangled'],'address':symbol['address'],'size':symbol['size'],'section':section['name'],'file_offset':offset,'range_sha256':hashlib.sha256(raw[offset:offset+symbol['size']]).hexdigest()}
    native=json.loads((packet/'native-context.json').read_text())
    matches=[v for v in native['bodies'].values() if v.get('address')==symbol['address'] and v.get('size')==symbol['size']]
    assert matches and all(v['bytes_sha256']==checked['range_sha256'] for v in matches)
    uc=Uc(UC_ARCH_ARM,UC_MODE_ARM);uc.mem_map(0,0x400000)
    for address,data in segments:uc.mem_write(address,data)
    obj=0x300000; ctl=0x301000; pbase=0x310000; table=0x320000; end=0x330000
    def w(a,v): uc.mem_write(a,struct.pack('<I',v & 0xffffffff))
    def r(a): return struct.unpack('<I',uc.mem_read(a,4))[0]
    def ret(value=0): uc.reg_write(UC_ARM_REG_R0,value & 0xffffffff);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    hooks={}; trace=[]
    def add(a,fn): hooks[a]=fn
    def param(tag): return pbase+((tag & 255)*0x100)
    def lparam(tag): return 0x340000+((tag & 4095)*0x40)
    def value(tag): return args.get('values',{}).get(str(tag),0)
    for tag in range(256):
        ptr=param(tag);w(ptr,table);w(ptr+0xc,ptr+0x20);w(ptr+0x24,tag)
        ptr=lparam(tag);w(ptr,table);w(ptr+0xc,ptr+0x20);w(ptr+0x24,tag)
    w(ctl,0x321000);w(0x321004,0x330100);w(obj+8,ctl if args.get('controller',True) else 0)
    add(0x330100,lambda:ret(args.get('radio',-1)))
    w(table+0x44,0x330104)
    def getvalue():
        ptr=uc.reg_read(REG[0]);tag=(ptr-0x340000)//0x40 if ptr>=0x340000 else (ptr-pbase)//0x100
        ret(value(tag))
    add(0x330104,getvalue)
    def getparam():
        tag=uc.reg_read(REG[1]); trace.append(['param',tag]);ret(param(tag))
    add(0x80eb0,getparam)
    w(0x32100c,0x330154);add(0x330154,getparam)
    def bytag():
        tag=uc.reg_read(REG[1]);trace.append(['local',tag]);ret(lparam(tag) if args.get('present',True) else 0)
    add(0x11f24c,bytag)
    def fgt():
        a,b=[struct.unpack('<f',struct.pack('<I',uc.reg_read(x)))[0] for x in REG[:2]];ret(a>b)
    add(0x1877e0,fgt)
    w(obj,0x322000);w(0x322010,0x330108)
    def update(): trace.append(['update']);ret()
    add(0x330108,update)
    w(obj+0x20,0x302000 if args.get('mixer',False) else 0);w(0x302004,int(args.get('secondary',False)))
    if index==7:
        w(obj+0xc0,args.get('saved',0)); add(0x12110,lambda:ret(args.get('long',False)))
        def reset():trace.append(['reset']);ret()
        add(0x11ff8,reset);w(table+0x58,0x33010c)
        def setvalue():ptr=uc.reg_read(REG[0]);trace.append(['set','local' if ptr>=0x340000 else 'mapping',(ptr-0x340000)//0x40 if ptr>=0x340000 else (ptr-pbase)//0x100,uc.reg_read(REG[1]),uc.reg_read(REG[2])]);ret()
        add(0x33010c,setvalue)
    if index==11:
        uc.reg_write(REG[1],0x303000 if args.get('component',True) else 0)
        add(0x11acf0,lambda:ret(param(600) if args.get('present',True) else 0))
        w(table+0x70,0x330110)
        def tostring():
            uc.mem_write(uc.reg_read(REG[1]),args.get('text','').encode()[:31]+b'\0');ret()
        add(0x330110,tostring)
        add(0xb02c,lambda:ret(len(bytes(uc.mem_read(uc.reg_read(REG[0]),32)).split(b'\0')[0])))
    # Additional original application queries. All Core/provider dispatch is explicit.
    extra_ranges=[]
    if index in [1,10,15,16,17,18,20]:
        extra_ranges += [(0x80f30,0x810c8)]
        w(0x302000,0x323000)
        w(0x321008,0x330120);add(0x330120,lambda:ret(args.get('bankOffset',3)))
        for offset,address in [(0x48,0x330124),(0x4c,0x330128),(0x50,0x33012c),(0x20,0x330130),(0x28,0x330134)]:w(0x323000+offset,address)
        add(0x330124,lambda:ret(args.get('geqcount',4)))
        add(0x330128,lambda:ret(2000+uc.reg_read(REG[1])))
        def busgeq():
            n=uc.reg_read(REG[1]);ret(1000+n if n<args.get('geqcount',4) else 0)
        add(0x33012c,busgeq)
        add(0x330130,lambda:ret(0x304000+uc.reg_read(REG[1])*0x100))
        add(0x330134,lambda:ret(0x305000 if args.get('secondaryInputs',False) else 0))
        w(0x305000,0x323100);w(0x323120,0x330138);add(0x330138,lambda:ret(0x305100))
    # Scalar app arithmetic and real provider-call observations.
    def scalar_float(reg):return struct.unpack('<f',struct.pack('<I',uc.reg_read(reg)))[0]
    def floatbits(value):return struct.unpack('<I',struct.pack('<f',value))[0]
    add(0x187314,lambda:ret(floatbits(uc.reg_read(REG[0])-(1<<32) if uc.reg_read(REG[0])&(1<<31) else uc.reg_read(REG[0]))))
    add(0x18730c,lambda:ret(floatbits(uc.reg_read(REG[0]))))
    add(0x18714c,lambda:ret(floatbits(scalar_float(REG[0])-scalar_float(REG[1]))))
    add(0x187780,lambda:ret(scalar_float(REG[0])==scalar_float(REG[1])))
    add(0x187798,lambda:ret(scalar_float(REG[0])<scalar_float(REG[1])))
    w(table+0x58,0x33010c)
    def setvalue():
        ptr=uc.reg_read(REG[0]);local=0x340000<=ptr<0x350000
        tag=(ptr-0x340000)//0x40 if local else (ptr-pbase)//0x100
        trace.append(['set','local' if local else 'mapping',tag,uc.reg_read(REG[1]),uc.reg_read(REG[2])]);ret()
    add(0x33010c,setvalue)
    def cstring(ptr):return bytes(uc.mem_read(ptr,256)).split(b'\0')[0].decode()
    w(table+0x74,0x330140)
    def fromstring():
        ptr=uc.reg_read(REG[0]);trace.append(['string',(ptr-0x340000)//0x40,cstring(uc.reg_read(REG[1])),uc.reg_read(REG[2])]);ret()
    add(0x330140,fromstring)
    def radio():
        trace.append(['radio',uc.reg_read(REG[1])-(1<<32) if uc.reg_read(REG[1])&(1<<31) else uc.reg_read(REG[1]),uc.reg_read(REG[2]),uc.reg_read(REG[3]),r(uc.reg_read(UC_ARM_REG_SP))]);ret()
    w(0x321028,0x330144);add(0x330144,radio)
    w(0x321010,0x330148);add(0x330148,lambda:ret(param(128+uc.reg_read(REG[1]))))
    add(0x81150,lambda:ret(args.get('meter',0)))
    if index in [16,18]:
        uc.reg_write(REG[1],param(args.get('tag',0)));w(param(args.get('tag',0))+0x24,args.get('tag',0))
        extra_ranges += [(0x80f70,0x810c8)]
        w(0x302688,int(args.get('bankSwitchBlocked',False)))
        def color():trace.append(['color',cstring(uc.reg_read(REG[1])),cstring(uc.reg_read(REG[2]))]);ret()
        add(0x76c6c,color)
        def format32():
            outp=uc.reg_read(REG[0]);fmt=cstring(uc.reg_read(REG[1]));name=cstring(uc.reg_read(REG[2]));number=uc.reg_read(REG[3]);uc.mem_write(outp,(fmt%(name,number)).encode()+b'\0');ret()
        add(0x4b47c,format32)
    if index==1:
        data=0x307000;w(data+0x18,args.get('mix',33));uc.reg_write(REG[1],data)
        w(obj+4,0x309800)
        add(0x762f0,lambda:ret(param(200) if args.get('monoPresent',False) else 0))
        listptr=0x304400;bus=0x30b000;w(bus,0x323300);w(0x323318,0x33014c)
        w(listptr+0x58,0x324000);w(listptr+0x5c,16)
        for n in range(16):w(0x324000+n*4,bus if args.get('busPresent',True) else 0)
        add(0x11acf0,lambda:ret(param(201) if args.get('busPresent',True) else 0))
        add(0x33014c,lambda:ret(param(202) if args.get('usernamePresent',True) else 0))
        w(table+0x70,0x330150)
        def username():uc.mem_write(uc.reg_read(REG[1]),args.get('username','Bus').encode()[:63]+b'\0');ret()
        add(0x330150,username)
        def constructstring():
            ptr=uc.reg_read(REG[1]);uc.mem_write(uc.reg_read(REG[0]),(cstring(ptr).encode() if ptr else b'')+b'\0');ret()
        add(0x3ae34,constructstring);add(0x4c790,constructstring)
        def format256():
            outp=uc.reg_read(REG[0]);fmt=cstring(uc.reg_read(REG[1]));n=uc.reg_read(REG[2]);uc.mem_write(outp,(fmt%n).encode()+b'\0');ret()
        add(0x24490,format256)
    extra={};native_lists=[]
    if index in [10,15]:
        add(0x1877f8,lambda:ret(int(struct.unpack('<f',struct.pack('<I',uc.reg_read(REG[0])))[0])))
    if index==15:
        w(obj+0x28,0x306000 if args.get('eqpage',False) else 0)
        extra_ranges += [(0x8dc50,0x8dc7c)]
        ptr=lparam(1000);w(ptr,table)
    if index==17:
        out=0x307000;uc.reg_write(REG[1],out);w(out,0xeeeeeeee);w(out+0x18,0xdddddddd);w(out+0x1c,1)
        def vectoradd():
            ptr=r(uc.reg_read(REG[1]));native_lists.append(ptr);ret(1)
        add(0x8c04c,vectoradd)
        w(0x302030,0x323200);w(0x323214,0x33013c)
        def groupfind():
            ptr=uc.reg_read(REG[1]);name=bytes(uc.mem_read(ptr,32)).split(b'\0')[0].decode();ret(0x308000 if name=='filtergroup' else 0x308100)
        add(0x33013c,groupfind)
        extra_ranges += [(0x815e4,0x81630)]
    if index==20:
        channel=0x309000;out=0x30a000;uc.reg_write(REG[1],channel);uc.reg_write(REG[2],out);uc.reg_write(REG[3],out+4)
        w(out,0xdead);w(out+4,0xbeef)
        bus=0x30b000;listptr=0x304400
        w(listptr+0x58,0x324000);w(listptr+0x5c,16)
        for n in range(16):w(0x324000+n*4,bus if args.get('busPresent',True) else 0)
        def bycomponent():
            objp=uc.reg_read(REG[0]);tag=uc.reg_read(REG[1]);ptr=0x360000+(0 if objp==channel else 0x1000)+tag*4
            if tag==411 and objp==channel and not args.get('channelMainPresent',False):ret(0);return
            w(ptr,table);ret(ptr)
        add(0x11acf0,bycomponent)
        def channelvalue():
            ptr=uc.reg_read(REG[0]);isbus=ptr>=0x361000;tag=(ptr-(0x361000 if isbus else 0x360000))//4
            if ptr>=0x360000:ret(args.get(('bus' if isbus else 'channel')+('Link' if tag==21 else 'Main'),0))
            else:getvalue()
        add(0x330104,channelvalue)
        def feq():
            a,b=[struct.unpack('<f',struct.pack('<I',uc.reg_read(x)))[0] for x in REG[:2]];ret(a==b)
        add(0x187780,feq)

    uc.reg_write(REG[0],obj);uc.reg_write(UC_ARM_REG_SP,0x3e0000);uc.reg_write(UC_ARM_REG_LR,end)
    def code(uc,address,size,user):
        if address==end: uc.emu_stop();return
        if address in hooks: hooks[address]();return
        if not(target['address']<=address<target['address']+target['size'] or (index==19 and 0x80f70<=address<0x810c8) or any(lo<=address<hi for lo,hi in extra_ranges)):raise RuntimeError(f'unbound provider {address:x}')
    uc.hook_add(UC_HOOK_CODE,code)
    uc.emu_start(target['address'],end,count=10000)
    result=uc.reg_read(REG[0]); result=result-(1<<32) if result & (1<<31) else result
    if index in [1,7,18,19]:result=0
    if index==17:
        result=bool(result);extra={'data':[r(out),r(out+0x18),r(out+0x1c)&255,native_lists]}
    if index==20:
        result=0;extra={'pan':r(out),'link':r(out+4)}
    if index==18:extra={'meterFlag':r(0x30268c)&255}
    return {'result':int(result),'trace':trace,**extra},checked

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);a=parser.parse_args()
    cases=[];ranges={}
    def case(i,args):
        expected,checked=execute(i,args);cases.append({'index':i,'args':args,'expected':expected});ranges[str(i)]=checked
    for radio in [-2147483648,-1,0,13,32,33,2147483647]:case(5,{'radio':radio})
    case(5,{'controller':False})
    for i in [8,12]:
        for present in [False,True]:
            for bits in [0,0x80000000,0x3f800000,0xbf800000,0x7f800000,0xff800000,0x7fc00000]:case(i,{'present':present,'values':{str(10 if i==8 else 9):bits}})
    for tag in [-1,0,1,2,3,4,5,6]:case(9,{'values':{str(tag):0x3f800000}})
    case(9,{'controller':False})
    for component in [False,True]:
        for present in [False,True]:
            for text in ['', 'a','x'*31]:case(11,{'component':component,'present':present,'text':text})
    for long in [False,True]:
        for saved in [0,1,5,-34,2147483647]:case(7,{'long':long,'saved':saved})
    for bank in [0,6]:
        for mixer in [False,True]:
            for secondary in [False,True]:case(19,{'values':{str(bank):0x3f800000},'mixer':mixer,'secondary':secondary})
    for n in [-2,0,1,3,4,19,20,21,22]:case(10,{'mixer':True,'values':{'2':struct.unpack('<I',struct.pack('<f',float(n)))[0]}})
    for page in [False,True]:
        for n in [-3.75,0,1.25,2.99,99]:case(15,{'eqpage':page,'values':{'1000':struct.unpack('<I',struct.pack('<f',n))[0]}})
    for bank in [0,4,5,6]:
        for secondary in [False,True]:
            for auto in [0,0x3f800000]:case(17,{'mixer':True,'secondary':secondary,'secondaryInputs':secondary,'radio':17,'values':{str(bank):0x3f800000,'10':auto}})
    case(17,{'mixer':False});case(17,{'controller':False,'mixer':True})
    for bank in [0,4]:
        for mix in [13,14,28,29,33]:
            for linked in [0,0x3f800000]:
                for busMain in [0,0x3f800000]:case(20,{'mixer':True,'radio':mix,'values':{str(bank):0x3f800000},'channelLink':linked,'busLink':0x3f800000,'busMain':busMain})
    for bank in [0,4,5,6]:
        for tag in [0,4,13,28,29,32,34,37,99]:
            case(18,{'tag':tag,'mixer':True,'meter':2,'values':{str(bank):0x3f800000,'29':0x3f800000}})
    case(18,{'tag':99,'mixer':False})
    for tag in [-1,0,4,5,6,7]:
        for bits in [0,0x3f000000,0x3f800000]:
            for groups in [0,0x3f800000]:case(16,{'tag':tag,'mixer':True,'values':{str(tag):bits,'6':groups}})
    case(16,{'tag':5,'mixer':True,'secondary':True,'bankSwitchBlocked':True})
    for mix in [0,12,13,14,28,29,32,33,34,35]:
        for count in [0,4,16]:
            for busLink in [0,0x3f800000]:case(1,{'mix':mix,'mixer':True,'geqcount':count,'values':{'201':busLink},'username':'Mix Bus'})
    case(16,{'tag':6,'mixer':True,'values':{'6':0x3f000000}})
    for mix in [13,33]:
        for linked in [0,0x3f800000]:
            for gate in [0,0x3f800000]:case(20,{'mixer':True,'radio':mix,'values':{'0':0x3f800000},'channelLink':linked,'busLink':0x3f800000,'busMain':0x3f800000,'channelMainPresent':True,'channelMain':gate})
    case(1,{'mix':13,'mixer':True,'username':'x'*63})
    Path(a.out).write_text(json.dumps({'version':1,'oracle':'Unicorn exact original app instructions; explicit provider hooks; no Core binary execution','unicorn_version':__import__('unicorn').__version__,'ranges':ranges,'cases':cases},indent=2)+'\n')
if __name__=='__main__': main()
