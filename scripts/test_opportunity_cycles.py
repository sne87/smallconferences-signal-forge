"""Regression tests for event-year isolation and contract-risk honesty."""
import unittest
from datetime import date
from opportunity_gate import assess
from opportunity_cycles import assess_cycles,select_next_cycle
TODAY=date(2026,11,8)

class CycleTests(unittest.TestCase):
 def test_separate_signed_2027_from_future_2029_site(self):
  text=('The 2027 annual conference hotel contract signed at the Riverside Inn. '
        'For the 2029 conference the site selection committee is reviewing venue options.')
  cycles=assess_cycles(text,TODAY)
  c={x['event_year']:x for x in cycles}
  self.assertIn(2027,c)
  self.assertIn(2029,c)
  self.assertTrue(c[2029]['pre_rfp_research_candidate'])
  self.assertFalse(c[2029]['commitment_evidence_same_year'])
  self.assertEqual(select_next_cycle(cycles,assess(text,TODAY))['event_year'],2029)
 def test_selected_2028_not_inferred_to_2030(self):
  text=('2028 annual conference venue selected at The Hague. '
        'The 2030 annual conference site selection committee is considering locations.')
  cycles={x['event_year']:x for x in assess_cycles(text,TODAY)}
  self.assertTrue(cycles[2030]['pre_rfp_research_candidate'])
  self.assertFalse(cycles[2028]['pre_rfp_research_candidate'])
 def test_speaker_proposals_not_venue(self):
  cycles=assess_cycles('2028 conference call for speakers and poster proposals due December 2026.',TODAY)
  self.assertFalse(cycles[0]['pre_rfp_research_candidate'])
 def test_unpublished_hotel_not_evidence_of_open_sourcing(self):
  cycles=assess_cycles('2029 annual conference venue will be announced in the spring.',TODAY)
  self.assertFalse(cycles[0]['pre_rfp_research_candidate'])
 def test_signed_2029_same_year_blocks_promotion(self):
  t='2029 annual conference site selection committee reviewed venue options. 2029 conference hotel contract signed at the Grand Hotel.'
  c=assess_cycles(t,TODAY)
  self.assertFalse(c[0]['pre_rfp_research_candidate'])
  self.assertTrue(c[0]['commitment_evidence_same_year'])
 def test_minute_without_year_not_cycle(self):
  self.assertEqual(assess_cycles('Board minutes: site selection is reviewing hotels.',TODAY),[])
 def test_future_fiscal_year_not_event(self):
  self.assertEqual(assess_cycles('2029 financials discussed at board committee; conference was held in 2026.',TODAY),[])
 def test_multi_year_sentence_reports_ambiguity(self):
  t='The 2028 and 2029 annual conference site selection committee is reviewing hotel options.'
  c=assess_cycles(t,TODAY)
  self.assertEqual([z['event_year'] for z in c],[2028,2029])
  self.assertTrue(all(z['multi_year_sentence'] for z in c))
if __name__=='__main__':unittest.main()
