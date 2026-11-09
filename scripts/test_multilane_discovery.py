#!/usr/bin/env python3
"""Offline acceptance tests for source-owned and social discovery lanes."""
import unittest
from datetime import datetime,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import social_monitor as sm
import primary_source as ps
class SourceTests(unittest.TestCase):
 def test_passage_requires_real_future_site_decision(self):
  t="Association of State Historians. The 2028 annual conference site selection committee will review hotel and host city options in January 2027."
  self.assertIn("site selection",ps.source_excerpt(t).lower())
 def test_program_planning_does_not_prove_venue(self):
  t="Professional Association. 2028 annual conference program planning committee is selecting speakers and sessions."
  self.assertEqual(ps.source_excerpt(t),"")
 def test_generic_index_result_does_not_trigger_fetch(self):
  self.assertFalse(ps.plausible_direct_page({'url':'https://news.google.com/rss/articles/zzz','title':'Conference site selection 2028','summary':''}))
 def test_source_enrichment_surfaces_actual_page_passage(self):
  a={'url':'https://example.org/conference/site-selection','title':'Association of State Historians conference','summary':'Association website','source':'Association of State Historians'}
  with patch.object(ps,'fetch_source_passage',return_value={'excerpt':'The 2029 annual conference site selection committee is reviewing hotel options.','checked_on':'2026-11-08','site_title':'Future meetings','site_name':'Association of State Historians'}):
   r=ps.enrich_index_hit(a)
  self.assertIn("2029",r['summary'])
  self.assertTrue(r['source_page_checked'])
  self.assertEqual(r['published'],'')
 def test_targets_rotate_and_include_specific_organizations(self):
  z=datetime(2026,11,8,18,tzinfo=timezone.utc)
  qs=sm.social_searches(z,True,["North Carolina Association of Municipal Clerks","Nonprofit Association of Oregon"])
  self.assertEqual(len(qs),6)
  self.assertTrue(any("North Carolina Association of Municipal Clerks" in q or "Nonprofit Association of Oregon" in q for _,q in qs))
 def test_direct_social_post_not_profile_or_job(self):
  self.assertEqual(sm.platform_for_url('https://www.linkedin.com/posts/association_hello-activity-1234'),'linkedin')
  self.assertEqual(sm.platform_for_url('https://www.linkedin.com/in/some-person'),'')
  self.assertEqual(sm.platform_for_url('https://www.linkedin.com/jobs/view/123'),'')
  self.assertEqual(sm.platform_for_url('https://facebook.com/example/posts/123'),'facebook')
 def test_public_staff_mention_is_not_assumed_authority(self):
  a={'url':'https://www.linkedin.com/posts/test_annual-conference-activity-12345',
  'title':'Our conference committee is considering future venues | Example Association',
  'summary':'Example Association site selection committee is discussing 2029 hotel options.',
  'published':'2026-11-08'}
  r=sm.watch_record(a,'social-linkedin-org-roles',['Example Association'],datetime(2026,11,8,tzinfo=timezone.utc))
  self.assertEqual(r['organizer_mentioned'],'Example Association')
  self.assertFalse(r['author_affiliation_verified'])
  self.assertFalse(r['public_post_date_verified'])
 def test_social_archive_merges_duplicate_and_keeps_first_seen(self):
  now=datetime(2026,11,8,tzinfo=timezone.utc)
  a={'url':'https://www.linkedin.com/posts/test_annual-conference-activity-12345',
  'title':'Example Association conference venue discussions',
  'summary':'2029 committee reviewing possible locations'}
  x=sm.watch_record(a,'social-linkedin-org-roles',['Example Association'],now)
  prior=[dict(x,first_seen='2026-11-06')]
  merged=sm.combine_records(prior,[x],now)
  self.assertEqual(len(merged),1)
  self.assertEqual(merged[0]['first_seen'],'2026-11-06')
 def test_merge_retains_social_posts_from_remote_chatgpt_sync(self):
  import json
  import merge_public_social as mp
  from unittest.mock import patch
  with TemporaryDirectory() as tmp:
   local=Path(tmp)/'social_watch.json'
   remote=Path(tmp)/'latest_git.json'
   local.write_text(json.dumps({'items':[{'id':'local','url':'https://www.linkedin.com/posts/local','post_title':'Local'}]}))
   remote.write_text(json.dumps({'generated_at':'2026-11-09','items':[{'id':'external','url':'https://www.linkedin.com/posts/external','post_title':'External','organizer_mentioned':'Named Association'}]}))
   with patch.object(mp,'LOCAL',local):
    mp.merge(remote)
   out=json.loads(local.read_text())
   self.assertEqual(out['public_posts_retained'],2)
   self.assertEqual({x['id'] for x in out['items']},{'local','external'})

 def test_social_save_no_personal_data(self):
  with TemporaryDirectory() as tmp:
   now=datetime(2026,11,8,tzinfo=timezone.utc)
   obj=sm.save_archive([],now,6,0,42,[],Path(tmp)/'social_watch.json')
   self.assertEqual(obj['public_posts_retained'],0)
   self.assertEqual(obj['social_queries_attempted'],6)
if __name__=='__main__':unittest.main()
