import json
import pathlib
import sqlite3
import sys
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'dependency-graph'))
import ranking
import recovery_frontier as f

class FrontierTests(unittest.TestCase):
    def test_fewer_unreconstructed_inputs_then_more_recovered(self):
        self.assertLess(f.priority(0,3,0,[4,3],'a'),f.priority(1,0,0,[4,0],'b'))
        self.assertLess(f.priority(1,8,0,[4,3],'a'),f.priority(1,0,0,[4,0],'b'))
    def test_zero_recovery_and_no_header_are_not_exclusions(self):
        c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;c.executescript(ranking.SCHEMA)
        for name in ('new_class','known_callee'):
            identities=[{'native_id':name,'elf_sha256':'elf','original_mangled':name}]
            c.execute('insert into items values(?,?,?,?,?,?,?)',(name,'function_reconstruction','reconstruct','NewClass',json.dumps(identities),'{}','hash'))
            c.execute('insert into states values(?,?,?,?)',(name,'remaining',0,'v1'))
            c.execute('insert into evaluations values(?,?,?,?,?,?,?)',(name,'research_required',json.dumps([0,4,1,1,1,0,name]),'[]',0,0,'{}'))
        c.execute('insert into requirements values(?,?,?,?,?,?)',('call','new_class','known_callee','callable_behavior',json.dumps({'native_dst':'known_callee'}),0))
        rows=f.order(c,set());self.assertEqual(len(rows),2)
        target=next(x for x in rows if x['work_item_id']=='new_class');self.assertEqual(target['unreconstructed_inputs'],1);self.assertEqual(target['recovered_inputs'],0)
        rows=f.order(c,{('elf','known_callee')});target=next(x for x in rows if x['work_item_id']=='new_class')
        self.assertEqual(target['recovered_inputs'],1);self.assertFalse(target['required_inputs'][0]['behavior_requirement_satisfied']);self.assertFalse(target['dispatch_authorized'])


    def test_same_target_unmet_data_scope_is_not_hidden_by_recovered_code(self):
        c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;c.executescript(ranking.SCHEMA)
        for name in ('caller','callee'):
            ids=[{'native_id':name,'elf_sha256':'elf','original_mangled':name}]
            c.execute('insert into items values(?,?,?,?,?,?,?)',(name,'function_reconstruction','reconstruct','A',json.dumps(ids),'{}','h'))
            c.execute('insert into states values(?,?,?,?)',(name,'remaining',0,'v1'))
            c.execute('insert into evaluations values(?,?,?,?,?,?,?)',(name,'reconstruction_eligible',json.dumps([0,4,1,1,1,0,name]),'[]',0,0,'{}'))
        for order in (('callable_behavior','data_binding_behavior'),('data_binding_behavior','callable_behavior')):
            c.execute('delete from requirements')
            for scope in order:
                ev={'native_dst':'callee'} if scope=='callable_behavior' else {'address':4}
                c.execute('insert into requirements values(?,?,?,?,?,?)',(scope,'caller','callee',scope,json.dumps(ev),0))
            row=next(x for x in f.order(c,{('elf','callee')}) if x['work_item_id']=='caller')
            self.assertEqual(row['unreconstructed_inputs'],1)
            self.assertFalse(row['required_inputs'][0]['behavior_requirement_satisfied'])

class ScopeCostTests(unittest.TestCase):
    def test_shared_inputs_and_cycles_count_once(self):
        rows=[{'work_item_id':'a','required_inputs':[{'target':'base','state':'unreconstructed'}]},
              {'work_item_id':'b','required_inputs':[{'target':'base','state':'unreconstructed'}]},
              {'work_item_id':'base','required_inputs':[{'target':'a','state':'unreconstructed'}]}]
        result=f.scope_cost(rows[:2],rows)
        self.assertEqual(result['unique_work_with_prerequisites'],3)
        self.assertEqual(result['external_inputs_needing_separate_binding_or_research'],[])

if __name__=='__main__':unittest.main()
