"""Tests for source-stage triage, including hostile false positives."""
import unittest
from datetime import date
from opportunity_gate import assess

TODAY=date(2026,11,8)
class OpportunityGateTests(unittest.TestCase):
    def test_programming_only_not_sourcing(self):
        r=assess('NAO 2027 annual conference call for session proposals. Speakers are under review.',TODAY)
        self.assertEqual(r['stage'],'programming_only')
        self.assertFalse(r['pre_rfp_research_candidate'])
    def test_virtual_host_not_hotel(self):
        r=assess('The association is seeking a host for its fully online virtual conference in 2028.',TODAY)
        self.assertEqual(r['stage'],'virtual_only')
    def test_expired_host_bid_not_current(self):
        r=assess('The Public Management Research Association invites applications to host the 2028 conference. Proposals are due November 1, 2026.',TODAY)
        self.assertEqual(r['stage'],'bid_deadline_passed')
        self.assertEqual(r['deadline'],'2026-11-01')
    def test_future_host_bid_is_not_pre_rfp(self):
        r=assess('The association is seeking host cities for the 2029 annual conference. Applications are due December 10, 2026.',TODAY)
        self.assertEqual(r['stage'],'host_bid_in_progress')
        self.assertFalse(r['pre_rfp_research_candidate'])
    def test_early_site_committee_research_only(self):
        r=assess('The Professional Association 2028 annual conference site selection committee is considering cities before hotel contracts.',TODAY)
        self.assertEqual(r['stage'],'possible_pre_rfp')
        self.assertTrue(r['pre_rfp_research_candidate'])
        self.assertFalse(r['qualified'])
        self.assertFalse(r['open_contract_verified'])
    def test_announced_hotel_is_risk(self):
        r=assess('2028 annual conference site selection committee; official conference hotel is confirmed.',TODAY)
        self.assertEqual(r['stage'],'possible_pre_rfp_with_venue_risk')
        self.assertFalse(r['pre_rfp_research_candidate'])
    def test_routine_announcement_not_action(self):
        r=assess('Registration now open for 2027 conference. Speakers announced.',TODAY)
        self.assertEqual(r['stage'],'watch_only')
    def test_extract_bid_deadline_not_event_date(self):
        r=assess('Annual conference July 10-12, 2028. Hosting applications are due December 4, 2026.',TODAY)
        self.assertEqual(r['deadline'],'2026-12-04')
    def test_no_invented_opening_from_unknown_venue(self):
        r=assess('Our 2027 annual conference will be held in the summer. Venue to be announced.',TODAY)
        self.assertFalse(r['open_contract_verified'])
        self.assertFalse(r['qualified'])

if __name__=='__main__':unittest.main()
