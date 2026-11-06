#!/usr/bin/env python3
"""Signal Forge public-source discovery. stdlib only, no paid APIs, no social scraping.

Runs as a GitHub Action (or locally). Scans public news RSS and best-effort
web-indexed social pages; keeps
public DISCOVERY candidates, not validated organizations or sales opportunities.
Never visits private profiles, logs into social sites, contacts people, or guesses
revenue, event budgets, or contracts.
"""
from __future__ import annotations
import hashlib, html, json, os, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'data'/'signals.json'
NOW=datetime.now(timezone.utc)
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; SignalForgePublicRSS/1.0; research-indexer; no-private-content)', 'Accept':'application/rss+xml,application/xml,text/xml,*/*'}
QUERIES=[
('early-planning','("association" OR "nonprofit") "conference planning committee" (2027 OR 2028)'),
('leadership','("association" OR "society") "conference" "new chair"'),
('leadership-reset','("association" OR "nonprofit") "conference" "executive director" "planning"'),
('budget','("association" OR "nonprofit") "conference" "rising costs"'),
('budget-strain','("association" OR "nonprofit") "annual meeting" "budget concerns"'),
('retreat','("association" OR "nonprofit") "leadership retreat" "planning"'),
('redesign','("association" OR "society") "conference" "reimagining"'),
('attendee-feedback','("association" OR "nonprofit") "conference" "attendee feedback"'),
('experience','("association" OR "society") "conference" "new format"'),
('venue-review','("association" OR "society") "conference" "venue options"'),
('site-proposals','("association" OR "nonprofit") "conference" "site proposals" (2027 OR 2028)'),
('hotel-proposals','("association" OR "nonprofit") "hotel proposals" conference'),
('catering','("association" OR "society") "conference" "catering" "cost"'),
('reschedule','("association" OR "society") "conference" "rescheduled"'),
('staffing','("association" OR "nonprofit") "conference" "event manager" "vacancy"'),
('sponsor-feedback','("association" OR "society") "conference" "sponsor feedback"'),
('member-survey','("association" OR "society") "annual conference" "survey"'),
('local-vendors','("association" OR "nonprofit") "annual convention" "local businesses"'),
('religious','("religious" OR "faith-based") "annual conference" "venue"'),
('educational','("education association" OR "teacher association") "conference" "planning"'),
('fraternal','"fraternal" "annual convention" "planning"'),
('veterans','"veterans association" "annual convention" "planning"'),
('social','"heritage society" "annual meeting" "venue"'),
('hotel-risk','("association" OR "society") "conference" "room block" "attrition"'),
('exhibitor-issues','("association" OR "society") "conference" "exhibitor feedback"'),
('hotel-renovation','("annual conference" OR "annual meeting") "hotel renovation" nonprofit'),
('room-block-shift','("association" OR "society") "room block" "change"'),
('board-debrief','("association" OR "nonprofit") "conference" "board" "feedback"'),
('event-strategy','("association" OR "society") "event strategy" "members"'),
('sponsor-pressure','("association" OR "society") "conference" "sponsorship revenue"'),
('local-chamber','("association" OR "nonprofit") "conference" "local vendors"'),
('new-offer','("association" OR "nonprofit") "first annual conference" "planning"'),
('event-contractor','("association" OR "nonprofit") "outsourced conference management"'),
('site-lead','("association" OR "society") "venue selection" "committee"'),
('postmortem','("association" OR "nonprofit") "conference" "lessons learned"'),
('capacity-bottleneck','("association" OR "nonprofit") "conference" "short staffed"'),
('accreditation','("association" OR "nonprofit") "conference" "continuing education" "new format"'),
('conference-advisor','("association" OR "nonprofit") "meeting planner" "proposals"'),
('linkedin-public','site:linkedin.com/posts/ "association" "conference" "planning committee"'),
('facebook-public','site:facebook.com "association" "conference" "new location"'),
('threads-public','site:threads.net "nonprofit" "conference" "ideas"'),
]

# Uncommon pre-RFP social listening: search publicly indexed pages only.
# These are hypotheses, not buying intent. The indexed date is not the original post date.
SOCIAL_TOPICS = [
 ('post-event-regret', '"conference" "what would you change" "association"'),
 ('silent-committee', '"conference committee" "first meeting"'),
 ('committee-recruitment', '"looking for volunteers" "annual conference"'),
 ('planning-chair-churn', '"conference chair" "stepping down"'),
 ('budget-debate', '"conference" "registration fees" "too expensive"'),
 ('participant-dropoff', '"conference" "attendance" "disappointed"'),
 ('networking-discontent', '"conference" "more networking" "feedback"'),
 ('format-fatigue', '"annual conference" "same format"'),
 ('new-host-city', '"association" "host city suggestions" "conference"'),
 ('room-block-challenge', '"conference" "hotel block" "expensive"'),
 ('late-registration', '"annual conference" "registration extended"'),
 ('exhibitor-complaints', '"conference" "exhibitor feedback" "improve"'),
 ('sponsor-renewals', '"conference" "sponsorship packages" "changing"'),
 ('planner-vacancy', '"association" "meetings director" "hiring"'),
 ('staff-overload', '"nonprofit" "conference" "small team"'),
 ('catering-friction', '"conference" "catering" "budget"'),
 ('local-experience', '"conference" "local businesses" "new experience"'),
 ('location-fallback', '"conference" "venue fell through"'),
 ('speaker-dropout', '"conference" "speaker changes" "planning"'),
 ('schedule-split', '"conference" "moving to" "new date"'),
 ('annual-survey', '"annual conference" "survey results"'),
 ('board-workshop', '"association" "board retreat" "annual conference"'),
 ('accessibility-pressure', '"conference" "accessible hotel" "feedback"'),
 ('member-affordability', '"annual meeting" "member affordability"'),
]
SOCIAL_DOMAINS = [
 ('linkedin','site:linkedin.com/posts/'),
 ('facebook','site:facebook.com/'),
 ('threads','site:threads.net/'),
 ('x','site:x.com/'),
 ('reddit','site:reddit.com/r/'),
]
# Rotate multiple topic searches per platform across runs rather than aggressively
# querying every site repeatedly. Cross-platform coverage grows over successive scans.
# Always include committee, feedback, hotel-cost and vendor-change themes.
SOCIAL_CORE = {'committee-recruitment','annual-survey','room-block-challenge','location-fallback','planner-vacancy'}

def social_searches():
    day = NOW.toordinal()
    rotation = [x for i,x in enumerate(SOCIAL_TOPICS) if i % 4 == day % 4]
    chosen = list(dict((key,(key,q)) for key,q in SOCIAL_TOPICS if key in SOCIAL_CORE or (key,q) in rotation).values())
    for platform,restrict in SOCIAL_DOMAINS:
        for topic,phrase in chosen:
            yield f'social-{platform}-{topic}', f'{restrict} {phrase}'

# Keep forward-looking years current as this scanner runs in future years.
QUERIES=[(label,query.replace('2027',str(NOW.year+1)).replace('2028',str(NOW.year+2)).replace('2029',str(NOW.year+3))) for label,query in QUERIES]

PATTERNS={
'cost':[r'cost\b',r'budget',r'pricing',r'expense',r'inflat',r'cater',r'financial',r'concession',r'attrition',r'savings'],
'change':[r'redesign',r'reimagin',r'feedback',r'survey',r'new format',r'young(er)? members',r'innovation',r'new ideas',r'local (business|vendor|experience)'],
'timing':[r'planning committee',r'proposals?',r'request for',r'202[789]',r'venue',r'site select',r'site proposal',r'conference chair',r'annual meeting'],
'capacity':[r'vacanc',r'hir(e|ing)',r'new chair',r'new director',r'workload',r'volunteers?',r'understaffed'],
'disruption':[r'reschedul',r'relocat',r'renovat',r'cancell',r'moved to',r'switch(ing)? venues?',r'host city',r'room block'],
'commercial':[r'planner',r'outside consult',r'outsourc',r'proposals',r'contractors?',r'consultant',r'request for proposal'],
}
ORG_REGEX=re.compile(r'\b(association|society|nonprofit|non-profit|foundation|alliance|council|chapter|community|coalition|guild|fraternal|religious|religion|faith|veterans|education|membership|professional|conference|convention|meeting|retreat)\b',re.I)
EVENT_REGEX=re.compile(r'\b(conference|convention|meeting|summit|retreat|symposium|event|assembly)\b',re.I)
NEGATIVE_REGEX=re.compile(r'\b(political rally|campaign rally|concert tickets|sporting event|basketball|fantasy football|stock market|crypto)\b',re.I)
COMMITMENT_REGEX=re.compile(r'\b(booked at|confirmed venue|room block available|registration now open|hotel block|already signed|contract awarded)\b',re.I)

def clean(text):
    text=html.unescape(re.sub(r'<[^>]*>',' ',str(text or '')))
    return re.sub(r'\s+',' ',text).strip()

def to_date(s):
    if not s:return ''
    try:return parsedate_to_datetime(s).astimezone(timezone.utc).date().isoformat()
    except (ValueError,TypeError,OverflowError):return ''

def fetch_rss(url,timeout=17):
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=timeout) as res:
        raw=res.read(1_600_000)
    root=ET.fromstring(raw)
    out=[]
    for item in root.findall('.//item'):
        source=item.find('source')
        out.append({'title':clean(item.findtext('title')), 'summary':clean(item.findtext('description'))[:800],
                    'url':clean(item.findtext('link')), 'published':to_date(item.findtext('pubDate')),
                    'source':clean(source.text if source is not None else '') or 'Public news index'})
    return out

def scan_url(query,engine='google'):
    if engine=='web':return 'https://www.bing.com/search?q='+urllib.parse.quote(query)+'&format=rss'
    if engine=='bing':return 'https://www.bing.com/news/search?q='+urllib.parse.quote(query)+'&format=rss'
    return 'https://news.google.com/rss/search?q='+urllib.parse.quote(query)+'&hl=en-US&gl=US&ceid=US:en'

def categorize(article,query_label):
    t=(article['title']+' '+article['summary']).lower()
    types=[kind for kind,rxs in PATTERNS.items() if any(re.search(p,t) for p in rxs)]
    if not types:
        types=[{'budget':'cost','budget-strain':'cost','redesign':'change','attendee-feedback':'change','leadership':'capacity','leadership-reset':'capacity','reschedule':'disruption','hotel-risk':'cost'}.get(query_label,'timing')]
    return types

def next_action(types,flags,play):
    if flags:
        return 'Check the named hotel or planner commitment first; determine whether full-service work, a later cycle, or a second opinion is still possible.'
    if play=='Safe':
        return 'Read the full solicitation, deadline and permitted vendors; verify revenue, scope and procurement contact before recommending Robert.'
    if 'disruption' in types:
        return 'Establish what changed, whether prior contracts still apply, and the earliest date new event decisions can be made.'
    if 'capacity' in types:
        return 'Verify which planning responsibilities are unassigned, whether a permanent hire is underway, and who approves outside help.'
    if 'cost' in types:
        return 'Trace the specific cost pressure to room blocks, catering, F&B, venue rentals or total event economics. Do not assume hotel commission equals savings.'
    if 'change' in types:
        return 'Find original member survey or board minutes; identify the next programming/venue decision and the person who can sponsor an improvement.'
    return 'Verify the legal entity, recurring event, event cycle, hotel/planner arrangements and decision date from original organizational sources.'

COMMITMENT_CLUES=[
    ('venue_named',r'booked at|confirmed venue|at the [A-Z][a-z]+ (Hotel|Resort|Convention Center)|venue has been selected'),
    ('room_block',r'room block available|hotel block|reservation link|book your room'),
    ('vendor_award',r'contract awarded|selected planner|event management partner|already signed'),
]

def as_candidate(article,query_label):
    title=article.get('title','');summary=article.get('summary','');url=article.get('url','')
    if not title or not url.startswith(('https://','http://')):return None
    t=title+' '+summary
    if (not EVENT_REGEX.search(t)) or (not ORG_REGEX.search(t)) or NEGATIVE_REGEX.search(t):return None
    date=article.get('published','')
    if date:
        try:
            age=(NOW.date()-datetime.fromisoformat(date).date()).days
            if age<0 or age>100:return None
        except ValueError:pass
    types=categorize(article,query_label)
    # Review priority is a deterministic triage heuristic, NOT probability of buying.
    score=22+min(40,7*len(types))
    if re.search(r'planning|review|evaluat|feedback|reimagin|budget|site (search|selection)|venue proposals',t,re.I):score+=14
    if re.search(rf'({NOW.year+1}|{NOW.year+2}|{NOW.year+3})',t):score+=7
    flags=[key for key,rx in COMMITMENT_CLUES if re.search(rx,t,re.I)]
    if COMMITMENT_REGEX.search(t) or flags:score-=17
    if ('commercial' in types or re.search(r'"?request for proposals"?|seeking (event|meeting) planner|hiring an? (event|conference) planner',t,re.I)) and not flags:
        play='Safe'
    elif 'cost' in types and ('change' in types or 'disruption' in types):
        play='Bold'
    else:
        play='Smart'
    if query_label in ('early-planning','venue-review','attendee-feedback','budget-strain'):score+=5
    score=min(90,max(10,score))
    ident=hashlib.sha256((url.split('#')[0].lower()+'|'+title.lower()).encode()).hexdigest()[:20]
    is_social=query_label.startswith('social-') or article.get('origin')=='social_index'
    platform=(query_label.split('-')[1] if query_label.startswith('social-') else '')
    date_basis=('Search-index timestamp; verify date on original post' if is_social else 'Public feed date; verify on original source')
    return {'id':ident,'title':title[:220],'summary':summary[:550], 'url':url,
        'source':article.get('source') or 'Public RSS','published':('' if is_social else date),
        'indexed_date':(date if is_social else ''),'date_basis':date_basis,
        'origin':('social_index' if is_social else article.get('origin','news_index')),
        'platform':platform,
        'original_post_checked':False,
        'detected':NOW.date().isoformat(),'types':types, 'priority':score,
        'query_id':query_label,'play':play,'next_action':next_action(types,flags,play),
        'flags':flags,'signal_strength':'unverified indexed mention; corroboration required',
        'verified_revenue':False,'verified_event':False,
        'verified_opening':False,'qualification':'Unverified discovery'}

def existing():
    if not DEST.exists():return []
    try:
        d=json.loads(DEST.read_text());return d.get('signals',[]) if isinstance(d.get('signals',[]),list) else []
    except (ValueError,OSError):return []

def run():
    seen={x['id']:x for x in existing() if isinstance(x,dict) and x.get('id')}
    fetched=0;failed=[];fresh=0
    # Cap per-run sources to avoid aggressive requests and reduce risk of source blocking.
    for index,(label,query) in enumerate(QUERIES):
        engines=['google'];
        if index in (0,3,6,9,12):engines.append('bing')
        for engine in engines:
            try:
                articles=fetch_rss(scan_url(query,engine)); fetched+=1
                for article in articles[:30]:
                    item=as_candidate(article,label)
                    if item is None:continue
                    if item['id'] in seen:
                        old=seen[item['id']]; old['types']=sorted(set(old.get('types',[])+item['types']));old['priority']=max(old.get('priority',0),item['priority'])
                    else:seen[item['id']]=item;fresh+=1
            except Exception as ex:
                failed.append(f'{label} ({engine}): {type(ex).__name__}: {str(ex)[:100]}')
        time.sleep(0.4)
    # Social platform mentions are discovered through a public web index, not a
    # direct platform feed. Original post publication dates are NOT verified here.
    social_attempted=0
    social_found=0
    for label,query in social_searches():
        social_attempted+=1
        try:
            articles=fetch_rss(scan_url(query,'web'));fetched+=1
            for article in articles[:20]:
                article['origin']='social_index'
                item=as_candidate(article,label)
                if item is None:continue
                social_found+=1
                if item['id'] in seen:
                    old=seen[item['id']]
                    old['types']=sorted(set(old.get('types',[])+item['types']))
                    old['priority']=max(old.get('priority',0),item['priority'])
                    old['origin']=item.get('origin',old.get('origin',''))
                    old['platform']=item.get('platform',old.get('platform',''))
                    if item.get('indexed_date'):old['indexed_date']=item['indexed_date']
                else:seen[item['id']]=item;fresh+=1
        except Exception as ex:
            failed.append(f'{label} (public-web-index): {type(ex).__name__}: {str(ex)[:100]}')
        time.sleep(0.3)
    # preserve recent items even if public RSS is temporarily down, then expire old entries
    cutoff=(NOW.date()-timedelta(days=100)).isoformat()
    kept=[x for x in seen.values() if (x.get('published') or x.get('detected') or '0000')>=cutoff]
    kept.sort(key=lambda x:(x.get('published') or x.get('detected') or '',x.get('priority',0)),reverse=True)
    kept=kept[:350]
    outcome={'generated_at':NOW.isoformat(timespec='seconds'),'scanner_version':'2.1-social-radar',
       'purpose':'Public discovery only; not qualified organizations, venue availability, or confirmed buyer intent.',
       'scan_sources_ok':fetched,'scan_sources_failed':len(failed),
       'scan_queries':len(QUERIES)+social_attempted,
       'social_index_queries':social_attempted,'social_index_candidates_seen':social_found,
       'social_by_platform':{platform:sum(1 for x in kept if x.get('platform')==platform) for platform,_ in SOCIAL_DOMAINS},
       'sources_attempted':len(QUERIES)+5+social_attempted,
       'coverage_warning':'Public news RSS plus best-effort web-indexed social mentions only. Not direct Facebook/LinkedIn/Threads/X/Reddit API monitoring. Platform results may be absent, delayed, or incomplete; dates from the index are not original post timestamps. Reddit RSS is discontinued November 13, 2026. Check source links and dates manually.',
       'new_discoveries':fresh,
       'errors':failed[:15],'signals':kept}
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(outcome,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f'Feeds OK={fetched}, failed={len(failed)}, new={fresh}, retained={len(kept)}')
    if failed:print('\n'.join(failed[:5]))
    # Nonzero if everything failed and there is no saved feed to make failure visible.
    if fetched==0 and not kept:return 2
    return 0

if __name__=='__main__':sys.exit(run())