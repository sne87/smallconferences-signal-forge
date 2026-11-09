#!/usr/bin/env python3
"""Public, source-linked org investigation for Robert's conference prospects.

The data is *investigation prompts*, not a claim that purchases or contracts are open.
Requires explicit public organization watchlist, never scans the private browser queue.
stdlib only; failures persist visibly in output; API / RSS feeds may be unavailable.
"""
from __future__ import annotations
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCHLIST = ROOT / 'watchlist.json'
OUT = ROOT / 'data' / 'intelligence.json'
NOW = datetime.now(timezone.utc)
UA = 'SignalForgePublicResearch/3.0 (+https://projects.propublica.org/nonprofits/api/; public data only)'
MONTHS = 'January February March April May June July August September October November December'.split()
RECORD_LIMIT = 48
SOURCE_CAP = 5
SCANS = [
    ('event-history', '"annual conference" OR "annual convention" OR "annual meeting"', 2025),
    ('event-history', '"annual conference" OR "annual convention" OR "annual meeting"', 2026),
    ('upcoming-event', '"annual conference" OR "annual convention" OR "annual meeting"', 2027),
    ('upcoming-event', '"annual conference" OR "annual convention" OR "annual meeting"', 2028),
    ('venue-commitment', '"hotel" OR "room block" OR "host venue" "conference"', None),
    ('incumbent-planner', '"meeting planner" OR "association management" OR "event management"', None),
    ('decision-path', '"executive director" OR "conference chair" OR "meetings director"', None),
    ('early-decision', '"conference committee" OR "site selection" OR "venue proposals"', None),
]
# Suppress no evidence. Search results are leads only; phrases do not establish a decision.
KEYWORDS = {
 'possible-commitment': re.compile(r'\b(room block|official hotel|host hotel|hosted at|venue selected|venue confirmed|contract signed|event registration|housing link|meeting planner|association management company)\b',re.I),
 'possible-planning': re.compile(r'\b(conference committee|future sites?|site selection|venue proposals|request for proposal|new chair|planning meeting|attendee survey|feedback)\b',re.I),
 'decision-role': re.compile(r'\b(executive director|conference chair|meetings director|conference coordinator|event director|board president)\b',re.I),
}

def clean(s):
    s=html.unescape(re.sub('<[^>]*>', ' ', str(s or '')))
    return re.sub(r'\s+',' ',s).strip()

def fetch(url, limit=1_000_000, timeout=14):
    req=urllib.request.Request(url, headers={'User-Agent':UA,'Accept':'application/json,application/rss+xml,application/xml,*/*'})
    with urllib.request.urlopen(req,timeout=timeout) as r: return r.read(limit)

def as_date(s):
    try: return parsedate_to_datetime(s).astimezone(timezone.utc).date().isoformat()
    except (TypeError,ValueError,OverflowError): return ''

def norm(s):
    return re.sub(r'[^a-z0-9]','',str(s or '').lower())

def normlegal(s):
    # Suppress only legal-form suffixes. Preserve every substantive
    # organization name word, state and supplied EIN checks.
    words=re.sub(r'[^a-z0-9]+',' ',str(s or '').lower()).split()
    while words and words[-1] in ('inc','incorporated','corp','corporation'):
        words.pop()
    return ''.join(words)

def load_targets():
    try: data=json.loads(WATCHLIST.read_text(encoding='utf8'))
    except (OSError,ValueError): return []
    out=[]; seen=set()
    for r in data.get('targets',[])[:RECORD_LIMIT]:
        if not isinstance(r,dict):continue
        name=clean(r.get('name',''))[:160]; state=clean(r.get('state','')).upper()[:2]
        ein=re.sub(r'\D','',str(r.get('ein') or ''))
        if not name or len(name)<6 or (ein and len(ein)!=9):continue
        key=(norm(name),ein)
        if key in seen:continue
        seen.add(key);out.append({'name':name,'state':state if re.fullmatch('[A-Z]{2}',state) else '', 'ein':ein})
    return out

def get_json(url):
    return json.loads(fetch(url,limit=2_400_000).decode('utf-8'))

def financial(target):
    name=target['name']; state=target['state']; ein=target['ein']
    api='https://projects.propublica.org/nonprofits/api/v2/'
    result={'status':'not-checked','match':'unresolved','ein':'','legal_name':'','fiscal_year':None,'revenue':None,
            'fit':'unknown','source_url':None, 'caveat':'Form 990 revenue is organization revenue, not conference spend.'}
    if ein:
        candidate={'ein':ein,'name':name,'state':state}
        result['match']='EIN supplied in watchlist'
    else:
        q=urllib.parse.quote(name)
        url=f'{api}search.json?q={q}'+(f'&state%5Bid%5D={state}' if state else '')
        search=get_json(url)
        matches=[x for x in search.get('organizations',[]) if norm(x.get('name'))==norm(name) and (not state or str(x.get('state','')).upper()==state)]
        if len(matches)!=1:
            result['status']='identity-review'
            result['caveat']=f'Found {len(matches)} exact name-and-state matches on first search page. Verify correct legal entity and EIN manually.'
            result['search_url']=url
            return result
        candidate=matches[0]
        result['match']='unique exact name match, EIN confirmation required'
    found_ein=str(candidate.get('ein','')).zfill(9)
    if not re.fullmatch(r'\d{9}',found_ein):
        result['status']='identity-review';return result
    url=f'{api}organizations/{int(found_ein)}.json'
    filing=get_json(url)
    org=filing.get('organization') or {}
    legal=clean(org.get('name'))
    if legal and normlegal(legal)!=normlegal(name):
        # No false automatic match: legal alias is possible, but needs a human.
        result['status']='identity-review'
        result['match']='legal name mismatch, investigate alias or chapter'
        result['legal_name']=legal
        result['ein']=found_ein
        result['source_url']=url
        return result
    if state and org.get('state') and str(org.get('state','')).upper()!=state:
        result['status']='identity-review';result['match']='state mismatch';result['legal_name']=legal;result['ein']=found_ein;result['source_url']=url;return result
    result.update({'ein':found_ein,'legal_name':legal or name,'source_url':url})
    filings=sorted([x for x in filing.get('filings_with_data',[]) if isinstance(x,dict)],key=lambda x:str(x.get('tax_prd',0)),reverse=True)
    for f in filings:
        rev=f.get('totrevenue')
        if rev is None:continue
        try: revenue=int(rev)
        except (ValueError,TypeError):continue
        try: year=int(str(f.get('tax_prd_yr') or str(f.get('tax_prd'))[:4]))
        except (ValueError,TypeError):continue
        result.update({'revenue':revenue,'fiscal_year':year})
        break
    if result['revenue'] is None:
        result['status']='no-financial-filing';result['caveat']='No comparable numeric total revenue in available filings.'
    else:
        result['fit']='within' if 500_000<=result['revenue']<=7_000_000 else ('below' if result['revenue']<500_000 else 'above')
        result['status']='filing-found' if result['match']=='EIN supplied in watchlist' else 'provisional-identity'
        if result['fiscal_year']<NOW.year-3:
            result['caveat']='Revenue filing is stale; verify newer returns before using as an eligibility decision.'
        elif result['match']!='EIN supplied in watchlist':
            result['caveat']='Revenue found on exact name match, but confirm EIN against original organization website or filing.'
    return result

def rss_search(name,tag,terms,year):
    query=f'"{name}" ({terms})'
    if year:query+=f' {year}'
    rss='https://news.google.com/rss/search?q='+urllib.parse.quote(query)+'&hl=en-US&gl=US&ceid=US:en'
    doc=ET.fromstring(fetch(rss))
    results=[]
    for item in doc.findall('./channel/item')[:SOURCE_CAP]:
        title=clean(item.findtext('title'))[:210]
        summary=clean(item.findtext('description'))[:460]
        url=clean(item.findtext('link'))
        if not url.startswith('https://'):continue
        body=title+' '+summary
        # A search hit is not supporting evidence unless it explicitly names the watched organization.
        if norm(name) not in norm(body):
            continue
        patterns=[k for k,rx in KEYWORDS.items() if rx.search(body)]
        # RSS index returns index time, not proof of original announcement date.
        results.append({'category':tag,'query_year':year,'title':title,'summary':summary,'url':url,
            'index_date':as_date(item.findtext('pubDate')),'clues':patterns,'date_warning':'Original source date and event date unverified.'})
    return results

def analyze(target):
    result={'name':target['name'],'state':target['state'],'input_ein':target['ein'],
        'financial':{},'sources':[],'checks':[],'historical_years':[],
        'next_step':'Confirm the event and identify who controls the upcoming purchasing decision.', 'errors':[],
        'status':'investigation-only'}
    try: result['financial']=financial(target)
    except Exception as exc:
        result['financial']={'status':'source-unavailable','match':'unknown','revenue':None,'fit':'unknown','caveat':'Public financial API unavailable; do not infer revenue.'}
        result['errors'].append('ProPublica: '+str(exc)[:120])
    # Spend the limited free news lookups on financially plausible organizations.
    # An out-of-band nonprofit remains in the audit with its sourced financials,
    # but cannot consume the same 8 public-index searches as top budget matches.
    if result['financial'].get('fit') in ('above','below'):
        result['next_step']='Outside the preferred $500K-$7M revenue band. Reconsider only with evidence of strong event-specific spend and external planning need.'
        result['status']='financial-out-of-band'
        return result
    for tag,query,base_year in SCANS:
        year=NOW.year+(base_year-2026) if base_year is not None else None
        try:
            found=rss_search(target['name'],tag,query,year)
            for x in found:
                if not any(y['url']==x['url'] for y in result['sources']):result['sources'].append(x)
            time.sleep(.2)
        except Exception as exc:result['errors'].append(tag+': '+type(exc).__name__)
    result['historical_years']=sorted({s['query_year'] for s in result['sources'] if s['category']=='event-history' and s['query_year']},reverse=True)
    tags={s['category'] for s in result['sources']}
    # Missing one source means absence of evidence, not absence of a commitment.
    if result['financial'].get('status') in ('identity-review','provisional-identity','source-unavailable'):
        result['next_step']='Verify EIN and latest Form 990 identity before treating revenue as screened.'
    elif not {'event-history','upcoming-event'}.issubset(tags):
        result['next_step']='Confirm at least two past conference cycles and exact future event from organizer pages.'
    elif 'venue-commitment' in tags or 'incumbent-planner' in tags:
        result['next_step']='Open planner, hotel and venue sources; verify if contracts are already executed or scopes remain influenceable.'
    else:
        result['next_step']='Identify and verify contract approver plus the actual hotel/planner purchasing decision date.'
    return result

def run():
    targets=load_targets();rows=[]
    for i,target in enumerate(targets):
        print(f'Investigating {i+1}/{len(targets)}: {target["name"]}',flush=True)
        rows.append(analyze(target))
    report={'generated_at':NOW.isoformat(timespec='seconds'), 'version':'3.0',
        'scope':'Public target-only pre-RFP due diligence. Not confirmed opportunities, contract status, or decision dates.',
        'data_privacy':'Watchlist and output reside in public repository if deployed with GitHub Pages. Do not include private notes.',
        'fiscal_source':'https://projects.propublica.org/nonprofits/api/',
        'readme':'A search-index match is a lead for source review; source index dates are not original post dates. Revenue is not event spend.',
        'targets':rows}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(f'Wrote {len(rows)} organizations to {OUT}')
    return 0

if __name__=='__main__':sys.exit(run())