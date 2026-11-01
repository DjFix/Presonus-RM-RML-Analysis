import unittest
from monitor_publication import classify

class MonitorTests(unittest.TestCase):
    def test_running_is_not_restart_candidate(self):
        self.assertEqual(classify('/delta',[{'pid':1}],'migration_pending'),'publication_running')
    def test_pending_is_not_completion(self):
        self.assertEqual(classify('/delta',[],'ready'),'publication_pending_no_live_process')
        self.assertEqual(classify('/delta',[],'migration_pending'),'waiting_for_pve_cutover')
    def test_quiet_has_no_claim_of_query_readiness(self):
        self.assertEqual(classify(None,[],'ready'),'no_pending_publication')
