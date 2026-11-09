"""Regression tests for conservative rescanning of discarded public RSS hits."""
import unittest
from datetime import datetime, timezone
import discover as d

class ReplayTest(unittest.TestCase):
    def example(self):
        return {
            'title':'North Carolina Association of Municipal Clerks 2029 annual conference site selection committee',
            'summary':'The association is reviewing potential future host sites for its annual conference.',
            'url':'https://example.org/ncamc-2029-site-selection',
            'source':'Association website',
            'published':datetime.now(timezone.utc).date().isoformat(),
        }
    def test_classifies_named_conference_site_committee(self):
        self.assertIsNotNone(d.as_candidate(self.example(),'future-site-research'))
    def test_keeps_near_miss_as_unqualified_record(self):
        item=d.rejected_record(self.example(),'organizer_name_missing','query-label','google')
        self.assertEqual(item['review_status'],'unqualified_near_miss')
        self.assertEqual(item['reason'],'organizer_name_missing')
    def test_no_archive_for_generic_non_event_content(self):
        self.assertIsNone(d.rejected_record(self.example(),'no_event_reference','query-label','google'))
    def test_replay_can_recover_a_formerly_missed_item(self):
        old=d.rejected_record(self.example(),'organizer_name_missing','future-site-research','google')
        seen={}
        checked,recovered=d.replay_archived([old],seen)
        self.assertEqual((checked,recovered),(1,1))
        self.assertEqual(len(seen),1)
        first=next(iter(seen.values()))
        self.assertTrue(first['replay_recovered'])
        self.assertFalse(first['verified_opening'])
    def test_does_not_recover_keyword_only_blog(self):
        x=self.example()
        x['title']='Conference Planning Tips: The Annual Conference Guide'
        x['summary']='How to plan a conference is a general subject.'
        old=d.rejected_record(x,'organizer_name_missing','future-site-research','google')
        seen={}
        checked,recovered=d.replay_archived([old],seen)
        self.assertEqual((checked,recovered),(1,0))
        self.assertEqual(seen,{})

if __name__=='__main__':unittest.main()
