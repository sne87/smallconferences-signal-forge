"""Regression tests for detecting real conference decisions in public PDF minutes."""
import unittest
from unittest.mock import patch
from datetime import date
import primary_source as p
import opportunity_gate as g

MSERA = (
  "MSERA Spring Board Meeting February 26 2026. "
  "Future Sites committee: 2027 Annual Meeting has signed contract at Hilton Pensacola Beach. "
  "Ideas discussed for the 2028 Annual Meeting included Arkansas Little Rock, Kentucky Lexington, Tennessee Nashville. "
  "The 2026 Future Sites committee shall present proposals for the 2028 and 2029 Annual Meetings "
  "to the Fall 2026 Board Meeting. Executive Director should play a larger role in negotiations."
)
class GovernanceTests(unittest.TestCase):
    def test_pdf_with_opaque_wix_filename(self):
        item={'url':'https://www.msera.org/_files/ugd/90ff5d_d5ca989918fb46bb82163a0026f5d727.pdf',
              'title':'MSERA Spring Board Meeting minutes',
              'summary':'Future Sites 2028 2029 site selection planning'}
        self.assertTrue(p.plausible_direct_page(item))
    def test_board_minutes_yield_relevant_source_passage(self):
        snippet=p.source_excerpt(MSERA)
        self.assertIn('2028',snippet)
        self.assertIn('Future Sites',snippet)
    def test_excluded_social_or_speaker_pdf(self):
        self.assertFalse(p.plausible_direct_page({
            'url':'https://www.example.org/uploads/call-for-papers.pdf',
            'title':'Call for papers for 2028 conference',
            'summary':'Speaker submissions'}))
    def test_no_venue_decision_without_future_year(self):
        self.assertEqual(p.source_excerpt('2026 annual meeting hotel on sale today.'),'')
    def test_future_site_discussion_not_open_contract_assertion(self):
        r=g.assess('The 2028 annual meeting site selection committee is reviewing venue options and hotel contracts.',date(2026,11,8))
        self.assertFalse(r['open_contract_verified'])
        self.assertFalse(r['qualified'])
    def test_pdf_page_limit_argument(self):
        # PdfReader is loaded lazily inside read_public_pdf, so a stubbed
        # extractor confirms that the original source page is retained.
        class Page:
            def __init__(self,text):self.text=text
            def extract_text(self):return self.text
        class Reader:
            def __init__(self,stream,strict):self.pages=[Page(MSERA),Page('unrelated')]
        with patch('pypdf.PdfReader',Reader):
            rows=p.read_public_pdf(b'%PDF-synthetic',max_pages=1)
        self.assertEqual(rows,[(1,MSERA)])

if __name__=='__main__':
    unittest.main()
