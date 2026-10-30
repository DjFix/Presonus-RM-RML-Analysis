"""Evidence-backed firmware register labels and physical interface candidates."""
from pathlib import Path
from collections import defaultdict,Counter
import json,re,hashlib
from capstone import *
from capstone.arm import *
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
B=ROOT/'evidence/recovery/2026-10-27/nimh-functional-03'
PREV=ROOT/'evidence/recovery/2026-10-27/nimh-fpga-connectivity-02'
FW=ROOT/'evidence/recovery/2026-10-27/xmen-stm32/images/mixer-analysis/_ZL13nimh_arm_code.bin'
d=FW.read_bytes();BASE=0x08000000
save=lambda n,v:(B/n).write_text(json.dumps(v,indent=2)+'\n')
md=Cs(CS_ARCH_ARM,CS_MODE_THUMB);md.detail=True
def flashword(addr):return int.from_bytes(d[addr-BASE:addr-BASE+4],'little')
def literal(i):
    if len(i.operands)>1 and i.operands[1].type==ARM_OP_MEM and i.operands[1].mem.base==ARM_REG_PC:
        a=((i.address+4)&~3)+i.operands[1].mem.disp
        return a,flashword(a)
    return None,None
def at(addr):return next(md.disasm(d[addr-BASE:addr-BASE+4],addr,count=1))
# Independently bind .data mapping to three exact reset instructions and copy-loop bytes.
assert literal(at(0x08004550))[1]==0x080340e8
assert literal(at(0x08004554))[1]==0x20000400
assert literal(at(0x08004556))[1]==0x20001264
mapping=dict(flash=0x080340e8,ram=0x20000400,end=0x20001264,proof_instructions=['0x08004550','0x08004554','0x08004556','0x0800455a','0x0800455e'])
def ramword(a):
    if mapping['ram']<=a<=mapping['end']-4:return flashword(mapping['flash']+a-mapping['ram'])
    return None
globals_=[]
for a in range(mapping['ram'],mapping['end'],4):
    w=ramword(a)
    if 0x60000000<=w<0x70000000:
        globals_.append(dict(ram_address=hex(a),initial_value=hex(w),flash_address=hex(mapping['flash']+a-mapping['ram'])))
save('stm32-initialized-data-map.json',dict(mapping=mapping,external_pointer_candidates=globals_,scope='Initial .data state only; runtime stores can replace these pointers.'))

windows=[('startup-fsmc',0x08004ada,0x08004b10),('ptp-software-statistics',0x08019260,0x080192ce),
 ('rtc-ptp-init',0x08019a6c,0x08019a9c),('rtc-snapshot',0x0801a29c,0x0801a2b0),
 ('clock-diagnostic',0x0801ce22,0x0801ce92),('router-diagnostic',0x0801ce92,0x0801cea4),
 ('router-table-loop',0x0801ceae,0x0801cef2),('hpll-diagnostic',0x0801cef2,0x0801cf9c),
 ('avb-talker-diagnostic',0x0801c93c,0x0801ca4c),('avb-listener-diagnostic',0x0801ca74,0x0801cb10),
 ('ins-clock-control',0x08011778,0x080117f8),('ins-line-control',0x08011804,0x08011978)]
labels=[];code_windows=[]
for tag,start,end in windows:
    regs={};records=[];recent_memory=None
    for i in md.disasm(d[start-BASE:end-BASE],start):
        rec=dict(pc=hex(i.address),bytes=i.bytes.hex(),instruction=i.mnemonic+' '+i.op_str)
        la,lv=literal(i)
        if la is not None:
            rec.update(literal_address=hex(la),literal_value=hex(lv))
            if BASE<=lv<BASE+len(d):
                txt=d[lv-BASE:].split(b'\0',1)[0]
                if txt and all(c in b'\t\r\n' or 32<=c<127 for c in txt):rec['literal_text']=txt.decode()
        before=dict(regs)
        for reg in i.regs_access()[1]:regs.pop(reg,None)
        ops=i.operands;mn=i.mnemonic.split('.')[0]
        dest=ops[0].reg if ops and ops[0].type==ARM_OP_REG else None
        if la is not None:regs[dest]=lv
        elif mn in ('mov','movs','movw') and len(ops)>1:
            if ops[1].type==ARM_OP_IMM:regs[dest]=ops[1].imm&0xffffffff
            elif ops[1].reg in before:regs[dest]=before[ops[1].reg]
        elif mn=='movt' and isinstance(before.get(dest),int):regs[dest]=(before[dest]&65535)|(ops[1].imm<<16)
        elif mn.startswith('ldr') and len(ops)>1 and ops[1].type==ARM_OP_MEM:
            mem=ops[1].mem;v=before.get(mem.base)
            if isinstance(v,int) and not mem.index:
                a=(v+mem.disp)&0xffffffff;initial=ramword(a)
                rec['data_address']=hex(a)
                if initial is not None:
                    regs[dest]=initial;rec['initial_data_value']=hex(initial)
                else:
                    regs[dest]=dict(address=hex(a),read_pc=hex(i.address))
        elif mn.startswith('str') and len(ops)>1 and ops[1].type==ARM_OP_MEM:
            mem=ops[1].mem;v=before.get(mem.base)
            if isinstance(v,int) and not mem.index:
                rec['data_address']=hex((v+mem.disp)&0xffffffff)
                if isinstance(before.get(dest),int):rec['write_value']=hex(before[dest])
        if mn=='bl':
            target=ops[0].imm
            if target==0x08014d68:
                fmt=before.get(ARM_REG_R0);val=before.get(ARM_REG_R1)
                if isinstance(fmt,int) and BASE<=fmt<BASE+len(d):
                    text=d[fmt-BASE:].split(b'\0',1)[0].decode(errors='replace')
                    if isinstance(val,dict):labels.append(dict(window=tag,print_pc=hex(i.address),format=text,**val))
            for reg in [ARM_REG_R0,ARM_REG_R1,ARM_REG_R2,ARM_REG_R3,ARM_REG_R12,ARM_REG_LR]:regs.pop(reg,None)
        records.append(rec)
    code_windows.append(dict(name=tag,start=hex(start),end_exclusive=hex(end),records=records,
                             scope='Bounded static disassembly; embedded pools/branches are preserved, not claimed executed.'))
save('firmware-code-windows.json',code_windows)
save('firmware-register-labels.json',labels)
assert any(r['address']=='0x60005000' and 'ROUTER1_SETUP' in r['format'] for r in labels)
assert any(r['address']=='0x60005104' and 'ROUTER_CLK_SEL' in r['format'] for r in labels)
assert any(r['address']=='0x60006000' and 'caf_enable' in r['format'] for r in labels)

# These three instructions implement (id + 0x03000000 + bias) << 5.
# The preceding unsigned bounds checks constrain the diagnostic id to 0..3.
for addr,bias in [(0x0801c956,0x90),(0x0801ca8c,0x60)]:
    seq=list(md.disasm(d[addr-BASE:addr-BASE+8],addr))
    assert len(seq)==3 and seq[0].mnemonic.startswith('add') and seq[0].operands[-1].imm==0x03000000
    assert seq[1].mnemonic=='adds' and seq[1].operands[-1].imm==bias
    assert seq[2].mnemonic=='lsls' and seq[2].operands[-1].imm==5
for addr in [0x0801c93e,0x0801ca76]:
    i=at(addr);assert i.mnemonic=='cmp' and i.operands[-1].imm==3
save('avb-register-map.json',dict(
    listener=dict(base='0x60000c00',stride='0x20',diagnostic_id_range=[0,3],
        base_calculation_instructions=['0x0801ca8c','0x0801ca90','0x0801ca92'],
        registers=[dict(offset='0x4',name='CTL',fields=dict(enable=31,mute=30,phase=29,channels_used='15:8',first_channel='7:0')),
                   dict(offset='0x8',name='MSK0'),dict(offset='0xc',name='MSK1'),
                   dict(offset='0x10',name='Stream_ID first word'),dict(offset='0x14',name='Stream_ID second word')]),
    talker=dict(base='0x60001200',stride='0x20',diagnostic_id_range=[0,3],
        base_calculation_instructions=['0x0801c956','0x0801c95a','0x0801c95c'],
        registers=[dict(offset='0x0',name='CTL0',fields=dict(enable=31,mute=30,label_on=29,midi=28,channels='27:22',timestamp_delta='21:0')),
                   dict(offset='0x4',name='CTL1; additional fields retained in annotated disassembly'),
                   dict(offset='0x8',name='Additional word; decoded format retained in evidence')]),
    scope='Firmware-addressed hardware register interface; four diagnostic-addressable instances per direction. Not proof of current live streams, full packet formats, or exact FPGA cell ownership.'))
ins_table=literal(at(0x08011796))[1]
assert ins_table==0x080284ec
save('ins-register-map.json',dict(clock_table=hex(ins_table),clock_registers=[hex(flashword(ins_table+4*i)) for i in range(3)],
    proof_instructions=['0x08011796','0x0801179c','0x080117e4'],
    argument_bit_packing=dict(argument_1='1:0',argument_2='3:2',argument_3_boolean=4,argument_4_boolean=5,
                              argument_5_boolean=6,argument_6_boolean=7,argument_7_boolean=8),
    SDK_path_reference_pcs=['0x080117ee','0x08011828','0x0801188c','0x0801196e'],
    scope='Static table and code-backed serial-audio clock control; line order, runtime settings and FPGA package assignments remain unverified.'))

attrs=defaultdict(dict)
for line in (PREV/'dependencies/primitive-settings.jsonl').open():
    r=json.loads(line)
    if 'bel' in r and 'value' in r:attrs[r['tile'].split('.')[0]+'.'+r['bel']][r['attribute']]=r['value']
pins=json.loads((B/'functional-input-pins.json').read_text())
io=[]
for r in json.loads((PREV/'bonded-io-connectivity.json').read_text()):
    ia=attrs[r['ilogic']];oa=attrs[r['ologic']];ioba=attrs[r['iob']]
    entry=dict(ball=r['ball'],iob=r['iob'],input_enabled=ioba.get('IBUF_MODE')!=['NONE'],
               output_enabled=r['output_driver_configured'],ilogic=r['ilogic'],ologic=r['ologic'],
               input_ddr=ia.get('ENABLE')=='1' and ia.get('DDR')=='1',
               output_ioce=oa.get('ENABLE')=='1' and oa.get('IOCE_ENABLE')=='1',
               output_rank2_clock=oa.get('ENABLE')=='1' and oa.get('FFO_RANK2_CLK_ENABLE')=='1',
               input_clock=pins.get(r['ilogic'],{}).get('CLK'),
               output_clock=pins.get(r['ologic'],{}).get('CLK'),
               input_settings=ia,output_settings=oa)
    io.append(entry)
save('physical-interface-pins.json',io)
ddr_in=[r['ball'] for r in io if r['input_ddr']]
ddr_out=[r['ball'] for r in io if r['output_rank2_clock']]
ioce_out=[r['ball'] for r in io if r['output_ioce']]
save('interface-candidates.json',dict(rgmii=dict(status='strong structural candidate; individual signal names unverified',
    evidence=['Five enabled DDR input lanes fit RXD[3:0]+RX_CTL.',
              'Six enabled rank2-clock output lanes are compatible with TXD[3:0]+TX_CTL+TXC.',
              'NIMH photo has a Marvell 88E6240 and firmware has MAC/PHY control paths.'],
    ddr_input_balls=ddr_in,rank2_output_balls=ddr_out,ioce_output_balls=ioce_out,
    gaps=['No continuity or schematic confirms lane order, direction or switch-port association.',
          'Dedicated DDR equations and exact clock phases remain unresolved; these counts alone do not establish an RGMII implementation.']),
    stm32_bus=dict(status='firmware-backed FSMC interface; FPGA-ball mapping pending',
      evidence=['Startup stores 0x81915 to FSMC_BCR1 and BCR2, and 0x1011 to BCR4; MWID field encodes 16 bits.',
                'MMIO and initialized globals identify 0x6000xxxx and 0x6400xxxx external regions.'],
      gaps=['FPGA pad-to-FSMC address/data/chip-select mapping is not established.']),
    board_evidence='Use previous phase card photos; hidden BGA traces are not physical continuity evidence.'))

docs=ROOT/'uc-library/validation/nimh-functional-03/operator-inputs/inputs/docs'
refs=[]
for name,pages in [('DICE_III_User_Guide_ETH',[5,6,7,8,9,10,11,12,13,14,15,16,22]),
                   ('DICE_III_User_Guide_Router',[5,6,7,8,9,10,11,12]),
                   ('DICE_III_User_Guide_InS',[5,6,7,8,9,10,11]),
                   ('DICE_III_User_Guide_ClockController',[5,6,7,8,9,10,11,12]),
                   ('DICE_III_User_Guide_JetPLL',[5,6,7,8,9,10,11])]:
    texts=json.loads((docs/(name+'.pages.json')).read_text())
    refs.append(dict(document=name+'.pdf',pages=[r for r in texts if r['page'] in pages]))
save('dice-relevant-pages.json',refs)
print('Confirmed diagnostic register labels:',len(labels))
print('DDR input balls:',ddr_in,'rank2 output balls:',ddr_out,'IOCE output balls:',ioce_out)
print('Initialized HPLL base:',hex(ramword(0x20000e08)))
