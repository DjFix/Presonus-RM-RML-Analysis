"""Execute exact Group bodies with real original nested Channel initialization."""
import importlib.util, json, sys
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0 as R0, UC_ARM_REG_R1 as R1
SPEC=importlib.util.spec_from_file_location('channel_init_provider', 'uc-library/tests/recovery/sqlite07_daw_channel_production_init/native.py')
provider=importlib.util.module_from_spec(SPEC); sys.modules[SPEC.name]=provider; SPEC.loader.exec_module(provider)
INIT='_ZN8Presonus10DAWChannel4initEb'
CAST='_ZN8Presonus10DAWChannel6castToEi'

def setup(original, flag, count, value=2):
    p=provider.provider
    p.check_range(original)
    m=provider.InitMachine(original)
    group=m.allocate(0x88); m.construct('15DAWChannelGroup',group)
    used=m.construct_parameter(0,'used',value)
    # Group tests include negative used and above available values without clamping.
    from struct import pack
    m.uc.mem_write(used+0x2c,pack('<f',value))
    m.parameter_list(group,[used])
    children=[]; channels=[]
    for index in range(count):
        child=m.allocate(0x94)
        channel=index%2==1
        m.construct('10DAWChannel' if channel else None,child)
        if channel:
            params=[m.construct_parameter(tag,'tag-'+str(tag),.5) for tag in (0,5,6,8,9,18,21,22,23)]
            m.parameter_list(child,params)
            channels.append((index,child,params))
        children.append(child)
    m.children(group,children)
    trace=[]
    def hook(uc,address,size,data):
        a,b=uc.reg_read(R0),uc.reg_read(R1)
        if address==m.address(INIT):
            assert a in children
            m.context={'receiver':a}
            trace.append(['init',children.index(a),b])
        elif a in children:
            trace.append(['cast',children.index(a),b])
    for name in (INIT,CAST,p.CAST_BASE):
        address=m.address(name); m.uc.hook_add(UC_HOOK_CODE,hook,begin=address,end=address)
    m.events.clear()
    return m,group,used,children,channels,trace

def observe(original):
    cases=[]
    for flag in (0,1):
      for count in (0,4):
        m,g,u,children,channels,trace=setup(original,flag,count)
        m.invoke(original['mangled'],g,flag)
        assert m.load(g+0x84)==u and m.feedback(u)==1
        assert trace==sum(([['cast',i,0x44617743]]+([['init',i,flag]] if i%2 else [] ) for i in range(count)),[]),trace
        # Group first performs exact tag lookup then genuine feedback before casts.
        assert m.events[:2]==[[provider.provider.BY_TAG,g+0x28,0],[provider.provider.FEEDBACK,u,1]],m.events[:2]
        output=['feedback 1']
        for i in range(count):
          output.append('cast '+str(i))
          if i%2: output.append('init '+str(i)+' '+str(flag))
        for i,child,params in channels:
          assert m.load(child+0x88)==params[0]
          assert m.load(child+0x38)==(7 if flag else 12)
          output.append('channel '+str(i)+' '+str(m.load(child+0x38)))
        cases.append(dict(flag=flag,count=count,expected=output,trace=trace,events=m.events))
    return dict(original=original,cases=cases)

def run(packet):
    return [observe(e['original']) for e in json.loads(Path(packet).read_text())['originals']]
if __name__=='__main__': print(json.dumps(run(sys.argv[1]),indent=2))
