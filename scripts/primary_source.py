#!/usr/bin/env python3
"""Free, bounded association-owned web-page discovery.

Google News omits quiet association notices. Bing's public WEB RSS sometimes
indexes them. We screen the indexed result, then retrieve a small number of
direct HTML pages to confirm that a planning/site decision appears in the
organizer's own text. No commercial API, no claim of an open contract.
"""
from __future__ import annotations
import html, re, urllib.parse, urllib.request, io
from html.parser import HTMLParser
from datetime import datetime, timezone

# Favor two-to-four-word search concepts that occur in public association
# governance, rather than conference announcements, CFPs or generic news.
PRIMARY_QUERIES = [
 ('official-2029-site', '"2029" "annual conference" "site selection"'),
 ('official-2028-site', '"2028" "annual meeting" "site selection"'),
 ('official-2029-host', '"2029" "annual meeting" "host site" association'),
 ('official-future-meetings', '"future meetings" "site" "association"'),
 ('official-2028-location', '"2028" "conference" "location" "committee" association'),
 ('official-2029-sites', '"2029" "conference sites" "committee"'),
 ('official-2030-sites', '"2030" "annual conference" "site selection"'),
 ('official-museum-host', '"museum association" "2029" "annual meeting" "host"'),
 ('official-library-host', '"library association" "2028" "conference" "site"'),
 ('official-education-hotel', '"education association" "2028" "conference" "hotel"'),
 ('official-nonprofit-host', '"nonprofit" "2029 conference" "host application"'),
 ('official-conference-hotel', '"conference" "hotel selection" "board" association'),
 ('official-chapter-host', '"2028" "conference host" "association"'),
 ('official-site-vote', '"2028" "annual meeting" "site voting"'),
 ('official-next-venue', '"conference" "future venues" "association"'),
 ('official-budget-venue', '"association" "conference" "hotel" "budget review"'),
 ('official-retreat-venues', '"association" "annual retreat" "site selection"'),
 ('official-2029-committee', '"2029" "site selection committee" conference'),
 ('official-2027-restructure', '"2027" "conference" "restructuring" "association"'),
 ('official-2027-sourcing', '"2027" "conference" "venue options" association'),
 ('official-location-proposals', '"2028 annual conference" "location proposals"'),
 ('official-contract-timing', '"conference site selection" "contract" "association"'),
 ('official-site-invite', '"invites interested sites" "annual meeting"'),
 ('official-hotel-expiration', '"conference" "hotel contract" "renewal" association'),
 # Governance-first lane: association board minutes expose decisions earlier
 # than news/RFP announcements. Use indexed public PDFs only, never scrape
 # inaccessible private board records.
 ('minutes-future-sites', '"2028" "2029" "future sites" "board" pdf'),
 ('minutes-location-options', '"2028" "annual meeting" "locations" "board minutes" pdf'),
 ('minutes-hotel-negotiation', '"2028" "annual conference" "hotel" "negotiation" "board" pdf'),
 ('minutes-site-review', '"2029" "site selection committee" "board minutes" pdf'),
 ('minutes-budget-review', '"conference" "hotel contracts" "board minutes" 2026 pdf'),
 ('minutes-conference-redesign', '"annual meeting" "rotation" "locations" "2028" pdf'),
]
# RSS direct-web endpoint, not Google News. Can be blocked by the provider.
def web_search_url(query: str) -> str:
    return 'https://www.bing.com/search?q='+urllib.parse.quote(query)+'&format=rss'

def selected_queries(now: datetime, light: bool, shortfall: bool):
    if not shortfall:
        return []
    # At most 8 per deep run, 3 per hourly light run. Rotate on each hour;
    # cover all 24 search angles across the day while under target.
    count=3 if light else 8
    offset=(now.hour*(3 if light else 8)+now.toordinal()*5)%len(PRIMARY_QUERIES)
    return [PRIMARY_QUERIES[(offset+i)%len(PRIMARY_QUERIES)] for i in range(count)]

class SourceText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip=0;self.parts=[];self.title=[];self.in_title=False;self.site_name=''
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ('script','style','noscript','svg','nav','footer'):self.skip+=1
        if tag=='title':self.in_title=True
        if tag=='meta' and a.get('property')=='og:site_name':
            self.site_name=a.get('content','')[:130]
        if tag in ('h1','h2','h3','h4','p','li','div','section','br'):
            self.parts.append(' ')
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript','svg','nav','footer') and self.skip:self.skip-=1
        if tag=='title':self.in_title=False
        if tag in ('h1','h2','h3','h4','p','li','div','section','br'):
            self.parts.append(' ')
    def handle_data(self,data):
        if self.in_title:self.title.append(data)
        if not self.skip:self.parts.append(data)

RELEVANT_PATH=re.compile(r'(conference|meeting|convention|site|selection|committee|host|event|future|leadership|minutes|board|news|annual|forms|venue|about)',re.I)
EVENT=re.compile(r'\b(conference|convention|annual meeting|annual gathering|regional meeting|summit|retreat)\b',re.I)
VENUE_SCOPE=re.compile(r'\b(site selection|host site|host city|site voting|conference location|hotel|venue|future meetings|meeting site|conference site|location proposals?|annual meeting host|interested sites)\b',re.I)
DECISION=re.compile(r'\b(review|reviewing|committee|seeking|select|selection|recommend|vote|application|apply|consider|proposal|contract|invite|host|new|upcoming|future|planning|decid)\w*',re.I)
FUTURE=re.compile(r'\b(?:2027|2028|2029|2030|2031)\b')
PROOF_CEILING=1000
# Whitelisted official domains only. The organization identity is a research
# candidate, not proof of conference ownership or tax EIN.
OFFICIAL_SOURCE_ORGANIZERS={
    'msera.org':'Mid-South Educational Research Association',
    'ncamc.nclm.org':'North Carolina Association of Municipal Clerks',
    'algaonline.org':'Association of Local Government Auditors',
}
EXCLUDED_DOMAINS=('news.google.com','bing.com','linkedin.com','facebook.com','x.com','reddit.com','youtube.com',
    'wikipedia.org','eventbrite.com','medium.com','10times.com','allevents.in','instagram.com')
def host(url):
    return (urllib.parse.urlsplit(url).hostname or '').lower().removeprefix('www.')

def plausible_direct_page(article):
    url=str(article.get('url',''))
    try:u=urllib.parse.urlsplit(url)
    except ValueError:return False
    if u.scheme!='https' or not u.netloc or u.path.lower().endswith(('.doc','.docx','.png','.jpg','.zip')):return False
    h=host(url)
    if any(h==n or h.endswith('.'+n) for n in EXCLUDED_DOMAINS):return False
    title=article.get('title','');snippet=article.get('summary','')
    txt=(title+' '+snippet)
    # PDFs can have opaque CMS filenames. Only accept when the indexed title
    # itself describes future board, site, venue, or meeting decisions.
    if u.path.lower().endswith('.pdf'):
        return bool(re.search(r'\b(?:board|minutes|future sites?|site selection|venue|hotel|annual meeting)\b',txt,re.I)) and (
            bool(FUTURE.search(txt)) or bool(re.search(r'\b(?:future sites|board meeting|site selection)\b',txt,re.I)))
    return (bool(RELEVANT_PATH.search(u.path)) or (bool(EVENT.search(txt)) and bool(FUTURE.search(txt)))) and (
        bool(VENUE_SCOPE.search(txt)) or bool(RELEVANT_PATH.search(u.path))
    )

def source_excerpt(page_text):
    # Require event context plus future cycle and an actual location/hotel
    # decision clue. Reject generic volunteer/program-only committees.
    normalized=re.sub(r'\s+',' ',page_text).strip()
    if not normalized or not EVENT.search(normalized) or not FUTURE.search(normalized):
        return ''
    candidates=[]
    for match in VENUE_SCOPE.finditer(normalized):
        left=max(0,match.start()-210);right=min(len(normalized),match.end()+300)
        excerpt=normalized[left:right]
        if not FUTURE.search(excerpt) or not DECISION.search(excerpt):continue
        # 2029 host invitations and venue-review passages rank ahead of
        # routine site maps or event-navigation menus.
        score=3*bool(re.search(r'\b(?:2028|2029|2030|2031)\b',excerpt))
        score+=3*bool(re.search(r'\b(?:site selection|site voting|host application|call for host|host sites|interested sites|venue options|hotel contracts?)\b',excerpt,re.I))
        score+=2*bool(re.search(r'\b(?:seeking|invites?|reviewing|applications?|committee|recommended|proposals?|contract)\b',excerpt,re.I))
        score+=bool(EVENT.search(excerpt))
        candidates.append((score,match.start(),excerpt))
    if not candidates:return ''
    candidates.sort(key=lambda p:(p[0],-p[1]),reverse=True)
    # Passage-backed signal only, never a full-page speculative synthesis.
    return candidates[0][2][:PROOF_CEILING]

def read_public_pdf(raw, *, max_pages=22):
    """Extract PDF text only; never interpret scans or silently OCR content."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError('pypdf missing: install free pypdf package in GitHub Actions') from exc
    pdf=PdfReader(io.BytesIO(raw), strict=False)
    sections=[]
    for i,page in enumerate(pdf.pages[:max_pages]):
        try:
            t=page.extract_text() or ''
        except Exception:
            t=''
        if t.strip():
            sections.append((i+1,t))
    return sections

def fetch_source_passage(url,timeout=8):
    req=urllib.request.Request(url,headers={
        'User-Agent':'Mozilla/5.0 (compatible; SignalForge/5.2; public-source-research)',
        'Accept':'text/html,application/xhtml+xml,application/pdf'})
    with urllib.request.urlopen(req,timeout=timeout) as res:
        content_type=res.headers.get('Content-Type','').lower()
        is_pdf='application/pdf' in content_type or urllib.parse.urlsplit(url).path.lower().endswith('.pdf')
        size_limit=2_000_000 if is_pdf else 650_000
        payload=res.read(size_limit+1)
        if len(payload)>size_limit:raise ValueError('source_too_large')
    if is_pdf:
        sections=read_public_pdf(payload)
        if not sections:raise ValueError('pdf_has_no_extractable_text')
        matches=[]
        for page_num,page_text in sections:
            excerpt=source_excerpt(page_text)
            if excerpt:
                strength=3*bool(re.search(r'\b(?:future sites?|site selection|hotel contract|venue options|location proposals)\b',excerpt,re.I))
                strength+=bool(re.search(r'\b(?:2028|2029|2030|2031)\b',excerpt))
                matches.append((strength,page_num,excerpt))
        if not matches:return None
        matches.sort(key=lambda x:(x[0],-x[1]),reverse=True)
        _,page_num,excerpt=matches[0]
        return {'excerpt':excerpt,'site_title':'Public conference governance PDF',
                'site_name':OFFICIAL_SOURCE_ORGANIZERS.get(host(url),''),
                'source_type':'pdf','source_page_number':page_num,
                'checked_on':datetime.now(timezone.utc).date().isoformat()}
    if 'html' not in content_type:raise ValueError('not_html_or_pdf')
    parser=SourceText()
    parser.feed(payload.decode('utf-8','replace'))
    page=re.sub(r'\s+',' ',' '.join(parser.parts)).strip()
    excerpt=source_excerpt(page)
    if not excerpt:return None
    return {'excerpt':excerpt,'site_title':re.sub(r'\s+',' ',' '.join(parser.title)).strip()[:160],
        'site_name':parser.site_name,'source_type':'html','source_page_number':None,
        'checked_on':datetime.now(timezone.utc).date().isoformat()}

def enrich_index_hit(article,timeout=8):
    if not plausible_direct_page(article):return None
    proof=fetch_source_passage(article['url'],timeout)
    if not proof:return None
    enriched=dict(article)
    original_title=article.get('title','')
    title_parts=[original_title,proof['site_title'],proof['site_name']]
    enriched['title']=' | '.join(dict.fromkeys(p for p in title_parts if p))[:220]
    enriched['summary']=proof['excerpt']
    enriched['published']='' # page fetch date is NOT a publication date
    enriched['source_page_checked']=True
    enriched['source_page_checked_on']=proof['checked_on']
    enriched['original_index_title']=original_title
    enriched['source_page_excerpt']=proof['excerpt']
    enriched['source_type']=proof.get('source_type','html')
    enriched['source_page_number']=proof.get('source_page_number')
    enriched['official_source_organizer_candidate']=proof.get('site_name','')
    return enriched
