#!/usr/bin/env python3
"""Organizer-first prospect universe from official recurring-conference directories.

This is NOT a source of automatically qualified leads. Directory presence is
only a real organization + one dated conference. It does not establish a
future buying window or that Robert can access the site-selection process.

Seeded from named organizations on NACAC's 2026 affiliate-conference directory
and PRIMA's official chapter meetings page. Free public source access only.
"""
from __future__ import annotations
import json, re, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'data'/'prospect_universe.json'
NACAC='https://www.nacacnet.org/affiliate-annual-conferences/'
PRIMA='https://primacentral.org/community/chapters/'

# Official directory organization labels. Event history and legal identity
# are DIFFERENT fields and require independent source checks.
NACAC_NAMES=[
 'Indiana Association for College Admission Counseling',
 'Kentucky Association for College Admission Counseling',
 'Ohio Association for College Admission Counseling',
 'Michigan Association for College Admission Counseling',
 'Southern Association for College Admission Counseling',
 'Great Plains Association for College Admission Counseling',
 'Missouri Association for College Admission Counseling',
 'Texas Association for College Admission Counseling',
 'Potomac and Chesapeake Association for College Admission Counseling',
 'Rocky Mountain Association for College Admission Counseling',
 'Hawaii Association for College Admission Counseling',
 'Illinois Association for College Admission Counseling',
 'Minnesota Association for College Admission Counseling',
 'Iowa Association for College Admission Counseling',
 'Dakota Association for College Admission Counseling',
 'Wisconsin Association for College Admission Counseling',
 'New Jersey Association for College Admission Counseling',
 'Pacific Northwest Association for College Admission Counseling',
 'Western Association for College Admission Counseling',
 'New York State Association for College Admission Counseling',
 'New England Association for College Admission Counseling',
 'Pennsylvania Association for College Admission Counseling',
 'International Association for College Admission Counseling',
]
PRIMA_NAMES=['Colorado PRIMA','Oregon PRIMA','Ohio PRIMA','Texas PRIMA','Tennessee PRIMA']
SEEDS=[(name,NACAC,'Regional admissions association; 2026 affiliate conference directory',True) for name in NACAC_NAMES]
SEEDS += [(name,PRIMA,'Public-risk-management state chapter; 2026 conference listing',True) for name in PRIMA_NAMES]

class Text(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.skip=0;self.parts=[]
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style','noscript','svg'):self.skip+=1
  elif tag in ('li','p','h1','h2','h3','h4','td','th','tr','br'):self.parts.append(' ')
 def handle_endtag(self,tag):
  if tag in ('script','style','noscript','svg') and self.skip:self.skip-=1
  elif tag in ('li','p','h1','h2','h3','h4','td','th','tr','br'):self.parts.append(' ')
 def handle_data(self,data):
  if not self.skip:self.parts.append(data)

def normalize(x):
 return ' '.join(re.sub(r'[^a-z0-9]+',' ',str(x or '').lower()).split())

def read_page(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; SignalForge/6.0; nonprofit research)','Accept':'text/html'})
 with urllib.request.urlopen(req,timeout=12) as f:raw=f.read(800000)
 p=Text();p.feed(raw.decode('utf-8','replace'))
 return ' '.join(' '.join(p.parts).split())

def previous():
 try:
  d=json.loads(DEST.read_text(encoding='utf-8'))
  return {normalize(x['name']):x for x in d.get('organizers',[]) if x.get('name')}
 except (OSError,ValueError,TypeError):return {}

def load_known():
 try:d=json.loads((ROOT/'watchlist.json').read_text(encoding='utf-8'))
 except (OSError,ValueError):return set()
 return {normalize(x.get('name','')) for x in d.get('targets',[]) if x.get('name')}

def build(now=None,pages=None,old=None):
 """Offline-friendly pure builder; pages mapping is injected by tests."""
 now=now or datetime.now(timezone.utc)
 old=old if old is not None else previous()
 pages=pages if pages is not None else {}
 known=load_known()
 date=now.date().isoformat()
 items=[]
 for name,url,context,is_conference in SEEDS:
  key=normalize(name)
  prior=old.get(key,{})
  page=pages.get(url)
  exact=bool(page and key in normalize(page))
  # A few association titles are not literally on the NACAC joint
  # conference page: count them only as directory-branch research seeds,
  # never as an independently verified 2026 event.
  if url==NACAC and name in ('Missouri Association for College Admission Counseling',
      'Minnesota Association for College Admission Counseling',
      'Iowa Association for College Admission Counseling',
      'Dakota Association for College Admission Counseling',
      'Wisconsin Association for College Admission Counseling'):
   exact=False
  status='official_page_confirmed' if exact else (
    'previously_observed_unrechecked' if prior.get('source_status')=='official_page_confirmed'
    else 'directory_research_seed_unverified')
  item={'name':name,'key':key,'directory_source_url':url,
    'source_context':context,'source_status':status,
    'first_seen':prior.get('first_seen') or date,
    'last_source_confirmed':date if exact else prior.get('last_source_confirmed',''),
    'last_checked':date if page else prior.get('last_checked',''),
    'event_year_example':2026 if exact and is_conference else None,
    'future_site_status':'unknown','buyer_decision_verified':False,
    'event_level_spend_verified':False,'qualified':False,'robert_ready':False,
    'existing_watchlist':key in known,
    'next_verification':'Verify correct EIN and annual revenue, 2 conference cycles, the NEXT sourcing decision, hotel/room-block scale and signed/incumbent commitments.'}
  if prior.get('financial'):item['financial']=prior['financial']
  items.append(item)
 return items

def run():
 now=datetime.now(timezone.utc)
 pages={};errors=[]
 for url in (NACAC,PRIMA):
  try:pages[url]=read_page(url)
  except Exception as err:errors.append(url+': '+type(err).__name__)
 roster=build(now,pages)
 prior=previous()
 # Rate-bound only two financial lookups per deep run. The free source
 # may be blocked or have stale tax data. Never infer a missing 990.
 checked=0
 try:
  from enrich import financial
  for item in roster:
   if checked>=2:break
   if not item['source_status']=='official_page_confirmed':continue
   if item.get('financial') and item['financial'].get('fiscal_year',0)>=now.year-3:continue
   try:
    item['financial']=financial({'name':item['name'],'state':'','ein':''})
    checked+=1
   except Exception as err:errors.append(item['name']+': '+type(err).__name__)
 except Exception as err:errors.append('financial:' + type(err).__name__)
 output={'generated_at':now.isoformat(timespec='seconds'),
  'purpose':'Broad official-directory organizer universe; not qualified leads or confirmed future contracts.',
  'organizers':roster,
  'total':len(roster),
  'source_verified_count':sum(x['source_status']=='official_page_confirmed' for x in roster),
  'financials_attempted':checked,
  'errors':errors,
  'source_urls':[NACAC,PRIMA]}
 DEST.parent.mkdir(parents=True,exist_ok=True)
 DEST.write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print('Organizer universe',len(roster),'official matches',output['source_verified_count'],'finance checks',checked)
 return 0

if __name__=='__main__':raise SystemExit(run())
