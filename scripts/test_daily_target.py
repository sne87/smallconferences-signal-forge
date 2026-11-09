#!/usr/bin/env python3
"""Daily research target acceptance tests; entirely offline."""
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import daily_target as t

NOW=datetime(2026,11,9,0,25,tzinfo=timezone.utc)  # Nov 8 in Chicago
LATER=datetime(2026,11,9,6,15,tzinfo=timezone.utc) # Nov 9 in Chicago

def base():
    return {'version':1,'baseline_keys':['known association'],'target_per_day':10,'discoveries':[]}

def article(name='New Association',origin='news_index',qualified_for_research=True):
    return {'organization_candidate':name,'origin':origin,
            'url':'https://example.org/meeting-site',
            'title':name+' annual conference venue discussion',
            'pre_rfp_priority':qualified_for_research,
            'types':['committee-research']}

class TargetTests(unittest.TestCase):
    def test_chicago_local_boundary(self):
        self.assertEqual(t.local_date(NOW),'2026-11-08')
        self.assertEqual(t.local_date(LATER),'2026-11-09')
    def test_baseline_never_counted(self):
        h,p,added=t.update_history(base(),[{'name':'Known Association'}],[article('Known Association')],NOW)
        self.assertEqual(p['new_today'],0)
        self.assertEqual(added,[])
    def test_new_named_indexed_candidate_counts_once(self):
        h,p,added=t.update_history(base(),[{'name':'New Association'}],[article()],NOW)
        self.assertEqual((p['new_today'],p['remaining'],len(added)),(1,9,1))
        h,p,added=t.update_history(h,[{'name':'NEW ASSOCIATION'}],[article('NEW ASSOCIATION')],NOW)
        self.assertEqual((p['new_today'],len(added)),(1,0))
        h,p,added=t.update_history(h,[{'name':'New Association'}],[article()],LATER)
        self.assertEqual(p['new_today'],0)
    def test_watchlist_and_unqualified_dont_pad_goal(self):
        h,p,added=t.update_history(base(),[{'name':'Old Watch'},{'name':'No Evidence'}],
            [article('Old Watch','official_watch'),article('No Evidence','news_index',False)],NOW)
        self.assertEqual(p['new_today'],0)
        self.assertEqual(added,[])
    def test_goal_met_at_ten_distinct_candidates(self):
        names=['Regional Association '+str(i) for i in range(10)]
        h,p,added=t.update_history(base(),[{'name':n} for n in names],[article(n) for n in names],NOW)
        self.assertEqual(p['new_today'],10)
        self.assertTrue(p['goal_met'])
        self.assertEqual(p['remaining'],0)
        self.assertEqual(len(h['daily_counts']),1)
    def test_persistence(self):
        h,p,_=t.update_history(base(),[{'name':'New Association'}],[article()],NOW)
        with TemporaryDirectory() as temp:
            path=Path(temp)/'history.json'
            t.write_history(h,path)
            self.assertEqual(t.read_history(path)['discoveries'][0]['name'],'New Association')
    def test_first_run_falls_back_to_existing_baseline(self):
        groups=[{'name':'Existing Association'}]
        h,p,added=t.update_history(None,groups,[article('Existing Association')],NOW)
        self.assertEqual(p['new_today'],0)
        self.assertIn('existing association',h['baseline_keys'])

if __name__=='__main__':unittest.main()
