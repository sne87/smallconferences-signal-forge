#!/usr/bin/env python3
"""Signal Forge evidence-first public-source discovery for Robert Kraus.

Only public RSS/indexed pages; no private social scraping, no paid APIs.
An event announcement alone is NOT a prospect. This tool requires a recognizable
organizer AND evidence of an influenceable conference planning decision/problem.
All results remain unverified until a human checks original sources.
"""
from __future__ import annotations
import hashlib, html, json, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'data' / 'signals.json'
NOW = datetime.now(timezone.utc)
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; SignalForgePublicRSS/3.1; public-research-indexer)',
           'Accept': 'application/rss+xml,application/xml,text/xml,*/*'}

# Every search describes an ACTION or a CHANGE. "conference" by itself is
# deliberately not a search strategy. Terms refer to organizer operations,
# rather than the subject of a conference (e.g. one *about* rising costs).
QUERIES = [
 ('planner-rfp', '"association" "conference" "event planning services" "proposals"'),
 ('outsourced-planning', '"association" "outsourced conference management"'),
 ('venue-evaluation', '"association" "conference" "reviewing venue proposals"'),
 ('site-committee', '"annual conference" "site selection committee" "association"'),
 ('host-city-search', '"association" "conference" "host city proposals"'),
 ('host-site-search', '"association" "annual conference" "host site" "proposals"'),
 ('committee-formation', '"association" "conference planning committee" "volunteers"'),
 ('committee-turnover', '"conference committee" "new chair" "association"'),
 ('new-leadership-cycle', '"executive director" "conference" "planning changes" "association"'),
 ('committee-debrief', '"association" "conference" "committee" "debrief"'),
 ('board-event-review', '"association" "board minutes" "conference" "budget"'),
 ('expense-review', '"association" "conference expenses" "review"'),
 ('event-margin', '"association" "conference revenue" "decline"'),
 ('rate-pushback', '"association" "conference" "hotel rates" "concerns"'),
 ('room-block-risk', '"association" "conference" "room block" "attrition"'),
 ('f-and-b-minimum', '"association" "conference" "food and beverage minimum"'),
 ('contract-renewal', '"association" "conference" "hotel contract" "renewal"'),
 ('multi-year-contract', '"association" "convention" "multi-year" "hotel contract"'),
 ('attendee-survey', '"association" "conference" "attendee survey" "improvements"'),
 ('member-feedback', '"association" "annual meeting" "member feedback" "changes"'),
 ('conference-reimagine', '"association" "reimagine our conference"'),
 ('conference-redesign', '"association" "conference format" "redesign"'),
 ('younger-members', '"association" "conference" "younger members" "feedback"'),
 ('declining-participation', '"association" "conference attendance" "declining"'),
 ('attendance-concerns', '"association" "annual convention" "attendance concerns"'),
 ('registration-affordability', '"association" "conference" "registration fee" "increasing"'),
 ('exhibitor-attrition', '"association" "conference" "exhibitor" "decline"'),
 ('sponsor-value', '"association" "conference" "sponsor feedback" "improve"'),
 ('sponsor-revenue', '"association" "conference" "sponsorship revenue" "down"'),
 ('venue-disruption', '"association" "annual meeting" "venue unavailable"'),
 ('hotel-renovation', '"association" "conference" "hotel renovation" "relocate"'),
 ('schedule-change', '"association" "annual conference" "moving to summer"'),
 ('staff-vacancy', '"association" "meetings director" "vacancy"'),
 ('planner-resignation', '"association" "conference planner" "resigned"'),
 ('committee-shortage', '"association" "conference committee" "needs volunteers"'),
 ('new-overnight-event', '"association" "conference" "overnight" "new format"'),
 ('local-experience-review', '"association" "conference" "local experience" "feedback"'),
 ('religious-site', '"church association" "annual convention" "site selection"'),
 ('education-meeting', '"education association" "conference" "planning committee"'),
 ('fraternal-site', '"fraternal association" "annual convention" "location proposals"'),
 ('veterans-site', '"veterans association" "annual convention" "site proposals"'),
]

SOCIAL_TOPICS = [
 ('volunteer-shortage','"conference planning committee" "need volunteers"'),
 ('hotel-frustration','"association" "conference hotel" "too expensive"'),
 ('venue-still-open','"association" "conference" "venue suggestions"'),
 ('chair-turnover','"association" "conference chair" "stepping down"'),
 ('post-event-feedback','"association" "what should we change" "conference"'),
 ('budget-rethink','"association" "conference budget" "review"'),
 ('roomblock-pain','"association" "room block" "attrition"'),
 ('committee-kickoff','"association" "conference planning committee" "first meeting"'),
 ('attendance-decline','"association" "conference attendance" "down"'),
 ('member-price-complaint','"association" "conference" "registration fees" "too high"'),
 ('host-committee','"association" "convention" "host committee" "proposals"'),
 ('new-planner','"association" "annual meeting" "need a planner"'),
 ('exhibitor-feedback','"association" "conference" "exhibitor feedback" "changes"'),
 ('rework-program','"association" "conference format" "rethink"'),
 ('city-change','"association" "conference" "different city" "suggestions"'),
 ('new-events-director','"association" "conference director" "position open"'),
 ('hotel-proposals','"association" "reviewing hotel proposals" "conference"'),
 ('venue-disruption','"association" "conference" "venue fell through"'),
 ('post-event-review','"association" "conference debrief" "next year"'),
 ('local-event-experiences','"association" "conference" "local businesses" "new ideas"'),
]
SOCIAL_DOMAINS = [
 ('linkedin', 'site:linkedin.com/posts/'),
 ('facebook', 'site:facebook.com/'),
 ('threads', 'site:threads.net/'),
 ('x', 'site:x.com/'),
 ('reddit', 'site:reddit.com/r/'),
]
SOCIAL_CORE = {'volunteer-shortage','hotel-frustration','venue-still-open','post-event-feedback','roomblock-pain','committee-kickoff'}

def social_searches():
    rotation = [x for i,x in enumerate(SOCIAL_TOPICS) if i % 4 == NOW.toordinal() % 4]
    selected = list(dict((key, (key, phrase)) for key,phrase in SOCIAL_TOPICS
                         if key in SOCIAL_CORE or (key,phrase) in rotation).values())
    for platform,restrict in SOCIAL_DOMAINS:
        for topic,phrase in selected:
            yield f'social-{platform}-{topic}', f'{restrict} {phrase}'

QUERIES = [(label, q.replace('2027',str(NOW.year+1)).replace('2028',str(NOW.year+2))) for label,q in QUERIES]

EVENT_REGEX = re.compile(r'\b(?:conference|convention|annual meeting|annual gathering|regional meeting|symposium|summit|member retreat|delegate assembly)\b',re.I)
BUYER_REGEX = re.compile(r'\b(?:association|professional society|historical society|nonprofit|non-profit|federation|fraternal|sorority|fraternity|chamber of commerce|membership organization|member association|faith-based organization|church association|veterans organization|guild|regional chapter|state chapter|education council)\b',re.I)
# Name-like organization references, not just the word "association" alone.
NAMED_BUYER_REGEX = re.compile(r'\b(?:(?:[A-Z][A-Za-z0-9&\x27.\-]*|of|the|for|and)\s+){1,11}(?:Association|Society|Federation|Council|Alliance|Coalition|Foundation|Chamber|Guild|Network|Fraternity|Sorority|Chapter)\b|\b(?:Association|Society|Federation|Council|Alliance|Coalition|Foundation|Chamber|Guild)\s+of\s+(?:(?:[A-Z][A-Za-z\x27.\-]+|the|and)\s*){1,7}', re.I)
# U.S.-specific foreign-place terms used as cautious exclusions, not as proof of
# geography when absent. A source could still require human confirmation.
FOREIGN_CONTEXT = re.compile(r'\b(?:Nigeria|Kenya|Scotland|Britain|British|United Kingdom|London|Southampton|Australia|India|Pakistan|Philippines|Jamaica|Toronto|Ottawa|Canadian)\b',re.I)
EXCLUDED_HOSTS = ('wikipedia.org','wiktionary.org','dictionary.cambridge.org','merriam-webster.com',
                  'dictionary.com','investopedia.com','quora.com','medium.com','eventbrite.com',
                  '10times.com','allevents.in')
# These announcements may relate to a recurring event but are not evidence of
# an influenceable planning/service decision. If a clear decision signal appears
# independently, the article can still pass.
ANNOUNCEMENT_ONLY = re.compile(r'\b(?:save the date|register now|registration now open|early bird registration|call for (?:abstracts|papers|presentations|speakers|session proposals)|speaker lineup|keynote speaker|conference agenda|conference is coming|join us for|conference highlights|conference concludes|conference wraps up|conference to discuss|conference will address|conference set to address|what is a conference|definition of conference)\b',re.I)
GENERIC_BLOG = re.compile(r'\b(?:best conferences to attend|top \d+ conferences|conferences you should attend|how to (?:plan|run|organize) (?:a|your) conference|conference planning tips|what (?:is|are) conferences?|guide to conference|conference trends (?:for|in) 20\d\d)\b',re.I)

# Strong evidence of intent, a change or an organizer pain point. Requiring an
# actual phrase (not search-term fallback) eliminates keyword-only results.
SIGNALS = {
 'procurement': [
  r'\b(?:request(?:ing)?|seeking|solicit(?:ing)?) (?:proposals|bids|quotes)\b.{0,110}\b(?:conference|convention|meeting|venue|hotel|event planning|planner)\b',
  r'\b(?:conference|meeting|convention|event)\b.{0,80}\b(?:planner|planning services|management services)\b.{0,45}\b(?:rfp|proposals|bids|consultant|outside|contract)\b',
  r'\b(?:seeking|looking for|hiring|needs) (?:an? |outside |independent )?(?:conference planner|meeting planner|conference planning consultant|event planning consultant|conference management firm)\b',
 ],
 'venue-decision': [
  r'\b(?:reviewing|evaluating|comparing|requesting|inviting)\b.{0,75}\b(?:venue|resort|hotel|host (?:city|site)|location)\b.{0,40}\b(?:proposal|bid|options?|quotes?|sites?)\b',
  r'\b(?:venue|hotel|host city|host site|conference location|site selection)\b.{0,75}\b(?:proposals|bids|under review|being evaluated|being considered|suggestions|not yet (?:selected|booked))\b',
  r'\b(?:site selection|host site selection|conference location) committee\b',
 ],
 'committee-reset': [
  r'\b(?:conference|convention|annual meeting|meeting) (?:planning )?(?:committee|chair|co-chair)\b.{0,75}\b(?:forming|formed|recruiting|seeking|new|appointed|vacancy|volunteers|stepping down|resign|kickoff|first meeting|needs help)\b',
  r'\b(?:new|appoint(?:ed|ment)|resign(?:ed|ation)|stepping down)\b.{0,65}\b(?:conference|convention|meeting) (?:chair|planner|director|committee)\b',
  r'\b(?:seeking|need|recruiting) (?:new )?(?:conference|convention|meeting) (?:committee )?volunteers\b',
 ],
 'economics': [
  r'\b(?:conference|convention|annual meeting|event) (?:revenue|margin|expenses?|costs?|budget|hotel rates|registration fees?|sponsorship revenue)\b.{0,85}\b(?:declin|rising|increase|decreas|over budget|review|shortfall|concern|loss|pressure|too high|affordab|lower|cut|deficit|profitability)\w*',
  r'\b(?:rising|higher|increased|unaffordable|too high|under budget review)\b.{0,75}\b(?:conference|convention|annual meeting|event) (?:hotel|catering|costs?|fees?|expenses?|budget)\b',
  r'\b(?:room block|f&b minimum|food and beverage minimum|attrition clause|hotel contract)\b.{0,85}\b(?:concern|renegotiat|review|expir|penalt|risk|cost|overcommit|shortfall|disput|increase)\w*',
 ],
 'attendee-change': [
  r'\b(?:conference|convention|annual meeting|event|attendee|member) (?:survey|feedback|evaluation|debrief)\b.{0,90}\b(?:next year|changes?|improve|rethink|redesign|reimagin|format|concern|request|dissatisf|new ideas)\w*',
  r'\b(?:reimagining|redesigning|rethinking|overhauling)\b.{0,55}\b(?:conference|convention|annual meeting)\b',
  r'\b(?:conference|convention|annual meeting) (?:attendance|exhibitor|sponsorship)\b.{0,75}\b(?:declin|dropp|fell|decreas|worr|rethink|review|disappoint)\w*',
  r'\b(?:what should we change|what would you change|how can we improve)\b.{0,65}\b(?:conference|convention|annual meeting|event)\b',
 ],
 'disruption': [
  r'\b(?:conference|convention|annual meeting|meeting)\b.{0,100}\b(?:venue (?:fell through|cancelled|unavailable)|relocat|reschedul|moving to (?:spring|summer|fall|winter)|changed dates|new dates due to|hotel renovation|lost (?:hotel|venue))\w*',
  r'\b(?:venue fell through|hotel (?:closed|closing|renovation)|site unavailable)\b.{0,65}\b(?:conference|convention|annual meeting)\b',
 ],
 'capacity': [
  r'\b(?:conference|convention|meeting|event) (?:director|planner|coordinator|manager)\b.{0,65}\b(?:vacancy|vacant|resign|stepping down|short staffed|position open|interim)\w*',
  r'\b(?:staff(?:ing)? shortages?|volunteer shortages?|understaffed|overwhelmed staff)\b.{0,65}\b(?:conference|convention|annual meeting|event planning)\b',
 ],
 'strategic-shift': [
  r'\b(?:conference|convention|annual meeting)\b.{0,70}\b(?:new format|redesign|change(?:s|d)? format|more (?:accessible|affordable)|younger members|local experiences)\b.{0,70}\b(?:considering|planning|feedback|exploring|discuss|review|next year)\w*',
  r'\b(?:association|society|foundation) (?:board|leadership)\b.{0,95}\b(?:conference|convention)\b.{0,60}\b(?:strategy|redesign|budget|restructure|review|change)\w*',
 ],
}
COMMITMENT_CLUES = [
 ('venue_named',r'booked at|confirmed venue|venue has been selected|at the [A-Z][a-z]+ (?:Hotel|Resort|Convention Center)'),
 ('room_block',r'room block available|hotel block|reservation link|book your room'),
 ('vendor_award',r'contract awarded|selected planner|event management partner|already signed'),
]
SOCIAL_HOSTS = {'linkedin':('linkedin.com',),'facebook':('facebook.com',),
                'threads':('threads.net','threads.com'), 'x':('x.com','twitter.com'),
                'reddit':('reddit.com',)}


def clean(value):
    value=html.unescape(re.sub(r'<[^>]*>', ' ', str(value or '')))
    return re.sub(r'\s+', ' ', value).strip()

def to_date(s):
    if not s:return ''
    try:return parsedate_to_datetime(s).astimezone(timezone.utc).date().isoformat()
    except (ValueError,TypeError,OverflowError):return ''

def fetch_rss(url,timeout=17):
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=timeout) as res:raw=res.read(1_600_000)
    root=ET.fromstring(raw)
    out=[]
    for item in root.findall('.//item'):
        source=item.find('source')
        out.append({'title':clean(item.findtext('title')),
                    'summary':clean(item.findtext('description'))[:800],
                    'url':clean(item.findtext('link')),
                    'published':to_date(item.findtext('pubDate')),
                    'source':clean(source.text if source is not None else '') or 'Public news index'})
    return out

def scan_url(query,engine='google'):
    if engine=='web':return 'https://www.bing.com/search?q='+urllib.parse.quote(query)+'&format=rss'
    if engine=='bing':return 'https://www.bing.com/news/search?q='+urllib.parse.quote(query)+'&format=rss'
    return 'https://news.google.com/rss/search?q='+urllib.parse.quote(query)+'&hl=en-US&gl=US&ceid=US:en'

def host_name(url):
    h=urllib.parse.urlsplit(url).hostname or ''
    return h.lower().removeprefix('www.')

def source_platform(article,label):
    """Return actual platform only when the source or URL supports the claim."""
    try:
        expected=label.split('-')[1] if label.startswith('social-') else ''
        h=host_name(article.get('url',''))
        source=article.get('source','').strip().lower()
        for platform,hosts in SOCIAL_HOSTS.items():
            if any(h==domain or h.endswith('.'+domain) for domain in hosts):
                return platform
            if h=='news.google.com' and platform in source:
                return platform
        if expected:return None  # Bing ignores site: sometimes; do not mislabel.
        return ''
    except Exception:return None

def event_context(title,summary):
    return (title+' '+summary).strip()

def evidence_groups(text):
    found={}
    for kind,patterns in SIGNALS.items():
        for pattern in patterns:
            m=re.search(pattern,text,re.I)
            if m:
                found[kind]=text[max(0,m.start()-34):min(len(text),m.end()+60)].strip()
                break
    return found

def relevance(article,label):
    """Defensible discovery eligibility, not a verdict that the buyer is open."""
    title=article.get('title','').strip()
    summary=article.get('summary','').strip()
    url=article.get('url','')
    if not title or not url.startswith(('https://','http://')):
        return None
    txt=event_context(title,summary)
    h=host_name(url)
    if any(h==x or h.endswith('.'+x) for x in EXCLUDED_HOSTS):return None
    if GENERIC_BLOG.search(title):return None
    if not EVENT_REGEX.search(txt):return None
    if not BUYER_REGEX.search(txt):return None
    if not NAMED_BUYER_REGEX.search(txt):return None
    if FOREIGN_CONTEXT.search(txt):return None
    if not source_platform(article,label) and label.startswith('social-'):return None
    signals=evidence_groups(txt)
    if not signals:return None
    # "Call for proposals" is commonly programming/speakers, not a hotel/planner RFP.
    if ANNOUNCEMENT_ONLY.search(title) and len(signals)<2 and not any(k in signals for k in ('venue-decision','economics','disruption','capacity')):
        return None
    date=article.get('published','')
    if date:
        try:
            age=(NOW.date()-datetime.fromisoformat(date).date()).days
            if age<0 or age>120:return None
        except ValueError:return None
    # Source is a page about an organization, but an event with no dated
    # relevance would remain a research lead, never a qualified buyer.
    return signals

def next_action(types,flags,play):
    if flags:return 'Check named hotel, planner and room-block commitments first. Is any useful scope still influenceable?'
    if play=='Safe':return 'Verify the actual consultant RFP scope, deadline, bidder eligibility and contracting decision-maker.'
    if 'venue-decision' in types:return 'Identify which conference cycle is under site review, the venue decision deadline and who can approve an external advisor.'
    if 'capacity' in types or 'committee-reset' in types:return 'Check who owns conference planning after the staffing/committee change and whether outside assistance is allowed.'
    if 'economics' in types:return 'Find the actual conference financial issue (rooms, food, AV, attrition, registration) and the responsible committee.'
    if 'attendee-change' in types:return 'Read the original attendee feedback and determine when the next conference format, location or budget will be decided.'
    return 'Confirm legal organizer, prior event cycles, next decision point, hotel commitments and current planner.'

def as_candidate(article,query_label):
    signal_evidence=relevance(article,query_label)
    if not signal_evidence:return None
    title,summary,url=article['title'],article['summary'],article['url']
    txt=event_context(title,summary)
    flags=[k for k,pattern in COMMITMENT_CLUES if re.search(pattern,txt,re.I)]
    types=list(signal_evidence)
    has_direct=('procurement' in types and re.search(r'\b(?:planner|planning services|management services|consultant)\b',txt,re.I))
    play='Safe' if has_direct else ('Bold' if ('economics' in types or 'attendee-change' in types) and not ('venue-decision' in types or 'committee-reset' in types) else 'Smart')
    # Priority is evidence density, not probability of purchase.
    score=min(90, 38 + 11*min(len(types),3) + (10 if 'venue-decision' in types or has_direct else 0) + (6 if re.search(rf'\b({NOW.year+1}|{NOW.year+2}|{NOW.year+3})\b',txt) else 0) - 18*bool(flags))
    is_social=query_label.startswith('social-') or bool(source_platform(article,query_label))
    platform=source_platform(article,query_label) or ''
    date=article.get('published','')
    ident=hashlib.sha256((url.split('#')[0].lower()+'|'+title.lower()).encode()).hexdigest()[:20]
    return {'id':ident,'title':title[:220],'summary':summary[:550],'url':url,
      'source':article.get('source') or 'Public news index',
      'published':('' if is_social else date),'indexed_date':(date if is_social else ''),
      'date_basis':('Index/feed date. Original social post date NOT verified.' if is_social else 'RSS timestamp; verify on original source.'),
      'origin':('social_index' if is_social else 'news_index'),'platform':platform,
      'original_post_checked':False,'detected':NOW.date().isoformat(),
      'types':types,'priority':score,'query_id':query_label,'play':play,
      'next_action':next_action(types,flags,play),'flags':flags,
      'signal_strength':'Unverified specific planning/change clue; corroborate with official sources.',
      'signal_evidence':signal_evidence,'evidence_gate':'named organizer + recurring event + actual change/decision clue',
      'verified_revenue':False,'verified_event':False,'verified_opening':False,
      'qualification':'Unverified discovery'}

def existing():
    if not DEST.exists():return []
    try:
        d=json.loads(DEST.read_text(encoding='utf-8'))
        return d.get('signals',[]) if isinstance(d.get('signals',[]),list) else []
    except (ValueError,OSError):return []

def run():
    previous=existing()
    seen={}
    dropped_previous=0
    # Re-evaluate the old feed under new strict criteria. This is the *public*
    # discovery feed only. It does not erase private saved review/evidence notes.
    for x in previous:
        if not isinstance(x,dict) or not x.get('id'):continue
        source={'title':x.get('title',''),'summary':x.get('summary',''),
                'url':x.get('url',''),'source':x.get('source',''),
                'published':x.get('published','')}
        curr=as_candidate(source,x.get('query_id',''))
        if curr:
            # Keep existing research assist, flagged counter-evidence and dates.
            curr.update({k:x[k] for k in ('research_assist','first_detected') if k in x})
            curr['detected']=x.get('detected',curr['detected'])
            seen[curr['id']]=curr
        else:dropped_previous+=1
    fetched=0;failed=[];fresh=0;rejected=0;social_attempted=0;social_found=0
    for i,(label,query) in enumerate(QUERIES):
        engines=['google']
        if i in (0,2,4,6,8):engines.append('bing')
        for engine in engines:
            try:
                articles=fetch_rss(scan_url(query,engine));fetched+=1
                for a in articles[:25]:
                    item=as_candidate(a,label)
                    if item is None:rejected+=1;continue
                    if item['id'] in seen:
                        old=seen[item['id']]
                        old['types']=sorted(set(old.get('types',[])+item['types']))
                        old['priority']=max(old.get('priority',0),item['priority'])
                    else:seen[item['id']]=item;fresh+=1
            except Exception as ex:
                failed.append(f'{label} ({engine}): {type(ex).__name__}: {str(ex)[:100]}')
        time.sleep(.25)
    for label,query in social_searches():
        social_attempted+=1
        try:
            articles=fetch_rss(scan_url(query,'web'));fetched+=1
            for a in articles[:20]:
                item=as_candidate(a,label)
                if item is None:rejected+=1;continue
                social_found+=1
                if item['id'] in seen:
                    old=seen[item['id']]
                    old['types']=sorted(set(old.get('types',[])+item['types']))
                    old['priority']=max(old.get('priority',0),item['priority'])
                else:seen[item['id']]=item;fresh+=1
        except Exception as ex:
            failed.append(f'{label} (public index): {type(ex).__name__}: {str(ex)[:100]}')
        time.sleep(.2)
    cutoff=(NOW.date()-timedelta(days=120)).isoformat()
    kept=[x for x in seen.values() if (x.get('published') or x.get('detected') or '0000')>=cutoff]
    kept.sort(key=lambda x:(x.get('published') or x.get('indexed_date') or x.get('detected') or '',x.get('priority',0)),reverse=True)
    kept=kept[:180]
    out={'generated_at':NOW.isoformat(timespec='seconds'), 'scanner_version':'3.1-buyer-evidence-gates',
         'purpose':'Specific pre-RFP planning clues only. No automatic buyer qualification or contract claims.',
         'scan_sources_ok':fetched,'scan_sources_failed':len(failed),
         'scan_queries':len(QUERIES)+social_attempted,'social_index_queries':social_attempted,
         'social_index_candidates_seen':social_found,
         'social_by_platform':{p:sum(1 for x in kept if x.get('platform')==p) for p,_ in SOCIAL_DOMAINS},
         'sources_attempted':len(QUERIES)+5+social_attempted,
         'coverage_warning':'Public news and indexed social search only. Indexes are incomplete and may not preserve original social post dates. Not direct or private-platform monitoring.',
         'new_discoveries':fresh,'rejected_irrelevant_hits':rejected,
         'previous_noise_removed':dropped_previous,'errors':failed[:15],'signals':kept}
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f'Feeds OK={fetched}, failed={len(failed)}, new={fresh}, retained={len(kept)}, filtered={rejected}, old_noise_removed={dropped_previous}')
    if failed:print('\n'.join(failed[:5]))
    return 2 if fetched==0 and not kept else 0

if __name__=='__main__':sys.exit(run())