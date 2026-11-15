"""No-change planning must not re-query interned rows for unchanged memberships."""
import sqlite3
import unittest
from compact_facts import CompactFacts, create_schema


class SparseOwnerPlanningTests(unittest.TestCase):
    def setUp(self):
        self.c=sqlite3.connect(':memory:');create_schema(self.c)
        self.addCleanup(self.c.close)
        self.store=CompactFacts(self.c)
        self.nodes={str(i):{'kind':'Function','label':str(i),'metadata':{}} for i in range(30)}
        self.edges={(str(i),str((i+1)%30),'CALLS','same evidence') for i in range(30)}
        self.store.replace_owner('owner',self.nodes,self.edges)

    def test_noop_checks_types_but_only_looks_up_owner(self):
        queries=[];self.c.set_trace_callback(queries.append)
        plan=self.store.plan_owner_rows('owner',self.nodes,self.edges,set(),set())
        self.c.set_trace_callback(None)
        self.assertEqual(plan['rows'],0)
        self.assertEqual(len(queries),1)
        invalid=dict(self.nodes);invalid['0']=dict(invalid['0'],metadata=[])
        with self.assertRaises(ValueError):
            self.store.plan_owner_rows('owner',invalid,self.edges,set(),set())

    def test_local_edit_plan_still_matches_actual_writes(self):
        nodes=dict(self.nodes);nodes['0']=dict(nodes['0'],label='edited')
        plan=self.store.plan_owner_rows('owner',nodes,self.edges,{'0'},set())
        before=self.c.total_changes
        self.store.replace_owner('owner',nodes,self.edges)
        self.assertEqual(plan['rows'],self.c.total_changes-before)
        self.assertEqual(plan['tables']['compact_node_memberships'],1)

    def test_deleted_membership_keeps_shared_value(self):
        self.store.replace_owner('other',self.nodes,self.edges)
        nodes=dict(self.nodes);nodes.pop('0')
        plan=self.store.plan_owner_rows('owner',nodes,self.edges,{'0'},set())
        before=self.c.total_changes
        self.store.replace_owner('owner',nodes,self.edges)
        self.assertEqual(plan['rows'],self.c.total_changes-before)
        self.assertEqual(self.c.execute("SELECT count(*) FROM node_facts WHERE id='0'").fetchone()[0],1)


if __name__=='__main__':unittest.main()
