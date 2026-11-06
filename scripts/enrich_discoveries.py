#!/usr/bin/env python3
"""Best-effort research assist for public indexed Signal Forge discoveries.

Only guesses a potential organizer from headlines that BEGIN with a complete
association name. It does not verify the legal organizer, vendor contracts,
conference recurrence, purchase authority or buying windows.
"""
from __future__ import annotations
import json,re,sys,time,urllib.parse
from pathlib import Path
from datetime import datetime,timezone
from enrich import financial, rss_search, norm, ROOT

DEST=ROOT/'data'/'signals.json'
NAME=re.compile(r'^((?:[A-Z][\w\'&.–-]*\s+|of\s+|the\s+){1,12}?(?:Association|Society|Alliance|Council|Coalition|Federation|Foundation|Network|Guild|Chamber))\b(?=\s*[:\-|–:]|\s+(?:announces|plans|seeks|invites|launches|hosts|opens|appoints|reviews|explores|discusses|will|is|has|prepares|202[6-9]))',re.I)
JOBS=[
 ('historical_event_mentions','"annual conference" OR "annual convention" OR "annual meeting"',None),
 ('planner_and_hotel_counterchecks','"host hotel" OR "room block" OR "event planner" OR "meeting planner" OR "association management"',None),
 ('decision_and_leadership_clues','"conference chair" OR "executive director" OR "conference committee" OR "site selection" OR "venue proposals"',None),
]
def candidate_name(title):
 m=NAME.match((title or '').strip())
 return m.group(1).strip() if m else ''

def get_research(name):
 data={}
 for key,q,yr in JOBS:
  search_q=f'"{name}" ({q})'
  url='https://www.google.com/search?q='+urllib.parse.quote(search_q)
  try:
   raw=rss_search(name,key,q,yr)
   rows=[]
   for article in raw:
    body=norm((article.get('title') or '')+' '+(article.get('summary') or ''))
    if norm(name) not in body:continue
    text=(article.get('title') or '')+' '+(article.get('summary') or '')
    rows.append({'title':article.get('title','')[:170],'url':article.get('url',''),
     'index_date':article.get('index_date',''), 'excerpt':article.get('summary','')[:290],
     'event_year_mentions':sorted(set(re.findall(r'20(?:25|26|27|28|29|30)',text)))})
    if len(rows)>=4:break
   data[key]={'results':rows,'search_url':url,'status':'indexed clues only, no original-source confirmation'}
  except Exception as exc:
   data[key]={'results':[],'search_url':url,'status':'lookup unavailable: '+type(exc).__name__}
  time.sleep(.15)
 return data

def assist(item,financial_fn=financial,research_fn=get_research):
 name=candidate_name(item.get('title',''))
 if not name:return None
 obj={'organization_name_candidate':name,'status':'unverified organizer',
      'checked_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
      'decision_window':'unknown','decision_maker':'unknown','planner_venue_status':'unknown'}
 try:
  f=financial_fn({'name':name,'state':'','ein':''})
  f['revenue_range']='in-range' if f.get('fit')=='within' else ('out-of-range' if f.get('fit') in ('above','below') else 'unknown')
  f['filing_url']='https://projects.propublica.org/nonprofits/organizations/'+str(f.get('ein')) if f.get('ein') else ''
  obj['financial']=f
 except Exception as exc:obj['financial']={'status':'source-unavailable','error':type(exc).__name__,'revenue':None}
 try:obj['research']=research_fn(name)
 except Exception as exc:obj['research']={'status':'source-unavailable','error':type(exc).__name__}
 return obj

def run(path=DEST):
 if not path.exists():print('No scanner feed');return 0
 d=json.loads(path.read_text(encoding='utf-8'));rows=d.get('signals',[])
 candidates=[r for r in rows if not r.get('research_assist') and candidate_name(r.get('title',''))]
 candidates.sort(key=lambda r:(r.get('detected') or '',r.get('priority',0)),reverse=True)
 count=0
 for x in candidates[:4]:
  a=assist(x)
  if a:x['research_assist']=a;count+=1
 d['discovery_enrichment']={'status':'public-index triage, not buyer qualification','new_this_run':count,
  'caveat':'Only headlines with explicit full nonprofit names are enriched. Other discoveries require manual organizer identity.'}
 path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Enriched public-index discovery records:',count)
 return 0
if __name__=='__main__':sys.exit(run())