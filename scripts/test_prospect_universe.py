"""Prospect directory is a broad research universe, never a qualified lead."""
import unittest
from datetime import datetime,timezone
from prospect_universe import build,NACAC,PRIMA,SEEDS
NOW=datetime(2026,11,8,23,0,tzinfo=timezone.utc)
class UniverseTests(unittest.TestCase):
 def test_official_page_name_matches_create_investigations(self):
  fake={NACAC:'Indiana Association for College Admission Counseling 2026 conference and Ohio Association for College Admission Counseling',
        PRIMA:'Oregon PRIMA Fall Conference and Texas PRIMA Annual Conference 2026'}
  out=build(NOW,fake,old={})
  by={x['name']:x for x in out}
  for name in ('Indiana Association for College Admission Counseling','Ohio Association for College Admission Counseling','Oregon PRIMA','Texas PRIMA'):
   self.assertEqual(by[name]['source_status'],'official_page_confirmed')
   self.assertEqual(by[name]['event_year_example'],2026)
   self.assertFalse(by[name]['qualified'])
   self.assertFalse(by[name]['buyer_decision_verified'])
  self.assertEqual(by['Kentucky Association for College Admission Counseling']['source_status'],'directory_research_seed_unverified')
 def test_no_claim_from_outage(self):
  item=build(NOW,{},old={})[0]
  self.assertFalse(item['qualified'])
  self.assertIsNone(item['event_year_example'])
  self.assertFalse(item['last_source_confirmed'])
 def test_retains_confirmation_date_without_claiming_new_fetch(self):
  name=SEEDS[0][0]
  prev={name.lower():{'name':name,'source_status':'official_page_confirmed','last_source_confirmed':'2026-10-10','first_seen':'2026-10-10'}}
  by={x['name']:x for x in build(NOW,{},old=prev)}
  self.assertEqual(by[name]['source_status'],'previously_observed_unrechecked')
  self.assertEqual(by[name]['last_source_confirmed'],'2026-10-10')
  self.assertIsNone(by[name]['event_year_example'])
 def test_universe_contains_more_than_existing_watchlist(self):
  self.assertGreaterEqual(len(SEEDS),25)
if __name__=='__main__':unittest.main()
