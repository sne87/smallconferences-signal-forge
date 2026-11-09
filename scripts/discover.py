#!/usr/bin/env python3
"""Signal Forge two-lane public discovery and organization signal stacking.

Public indexes only. Named organizers plus documented early change clues are
retained as WATCH; specific purchasing or operational changes are PRIORITY.
Never infer that an unsigned contract, external planning need, or buyer exists.
"""
from __future__ import annotations
import hashlib, html, json, os, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta
from pathlib import Path
from daily_target import read_history, today_progress, update_history, write_history

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


# Broad association-owned pages are needed because exact 4-phrase news queries
# rarely return anything. These are still gated by *article content*, not by
# matching a search phrase. More matches never means more qualified prospects.
QUERIES += [
 ('committee-current','"2027 conference committee" "association"'),
 ('committee-current-alt','"2027 conference planning committee" "society"'),
 ('conference-survey','"association" "2027" "conference survey"'),
 ('future-site','"association" "2028" "conference" "locations"'),
 ('site-selection','"association" "conference" "site selection"'),
 ('conference-budget','"association" "conference" "budget review"'),
 ('conference-change','"association" "conference" "change next year"'),
 ('new-chair-open','"association" "conference chair" "volunteers"'),
 ('planning-window','"annual conference" "committee" "2027"'),
 ('location-decision','"conference" "location" "2027" "proposals"'),
 ('nonprofit-venue','"nonprofit" "conference" "venue options"'),
 ('society-conference-planning','"professional society" "2027" "conference planning"'),
 ('convention-2028','"state association" "2028 convention" "planning"'),
 ('members-next-event','"association" "conference" "what would you change"'),
 ('site-host-interest','"annual meeting" "host site" "association"'),
 ('conference-finance-board','"conference committee" "budget" "board"'),
 ('after-conference-feedback','"association" "conference" "evaluation results"'),
 ('regional-attendee','"regional conference" "planning committee" "2027"'),
 # Broader, buyer-oriented queries to catch quiet committee notes and
 # changes without insisting all signal words appear in a short RSS excerpt.
 ('association-site-options','"annual conference" "venue options" association'),
 ('association-chair-search','"conference planning committee" "new chair"'),
 ('association-annual-survey','"conference" "survey" "what should" association'),
 ('association-budget-notes','"conference committee" "expenses"'),
 ('association-committee-minutes','"conference committee" "board" "hotel"'),
 ('association-host-interest','"conference" "future host" "association"'),
 ('association-date-change','"annual conference" "moving to" association'),
 ('association-hotel-review','"conference" "hotel contract" "review"'),
 ('association-event-feedback','"annual conference" "improve" "feedback"'),
 ('regional-convention-committee','"regional convention" "committee" "planning"'),
]

# More precise future-cycle, owner-side planning and contract-review searches.
# These are search terms only. Only source content can pass the gate.
QUERIES += [
 ('board-scheduled-location', '"association" "2029 conference" "site selection"'),
 ('conference-host-lead', '"association" "2028" "site selection committee"'),
 ('future-venue-committee', '"society" "2029" "conference planning"'),
 ('future-meetings-board', '"association" "board minutes" "conference site"'),
 ('chapter-host-search', '"state association" "host committee" "2028"'),
 ('venue-comparison-board', '"association" "annual conference" "venue options"'),
 ('hotel-block-review', '"society" "conference" "room block" "review"'),
 ('member-conference-committee', '"association" "2028" "conference committee"'),
 ('future-location-members', '"association" "2029" "future conference locations"'),
 ('annual-conference-committee', '"state" "association" "conference" "committee formed"'),
 ('nonprofit-site-selection', '"nonprofit" "conference" "site selection" "2028"'),
 ('meeting-association-host', '"historical society" "annual meeting" "host" "2028"'),
 ('board-venue-discussion', '"professional society" "annual meeting" "location" "committee"'),
 ('venue-affordability-board', '"association" "conference" "hotel rates" "board"'),
 ('fraternal-future-host', '"fraternal" "2028 convention" "host location"'),
 ('campus-conference-review', '"educational association" "conference" "host site"'),
 ('association-retreat-review', '"association" "annual retreat" "new venue"'),
 ('conference-contract-renewal', '"nonprofit" "conference" "venue contract" "renewal"'),
 ('conference-debrief-future', '"association" "conference" "debrief" "future"'),
 ('committee-room-blocks', '"association" "2028" "hotel block" "planning committee"'),
]

# Additional rotating search angles when today's target is unmet. No relaxing of evidence gates.
CATCHUP_QUERIES = [
 ('catch-site-committee', '"2028" "site selection committee" "association"'),
 ('catch-host-site', '"2029" "annual conference" "host site"'),
 ('catch-venue-board', '"2028 conference" "board" "location options"'),
 ('catch-convention-location', '"2029 convention" "site selection" "society"'),
 ('catch-financial-minutes', '"conference" "board minutes" "hotel" association'),
 ('catch-committee-created', '"annual conference" "new committee" "2028"'),
 ('catch-change-venue', '"regional association" "conference" "considering venues"'),
 ('catch-hosting-proposals', '"annual meeting" "host site" "society" "2029"'),
 ('catch-budget-planning', '"association" "conference committee" "financial review"'),
 ('catch-hotel-negotiation', '"association" "hotel contract" "2028" "review"'),
 ('catch-museum-society', '"museum association" "conference" "site selection"'),
 ('catch-library-association', '"library association" "annual conference" "2028" "planning"'),
 ('catch-healthcare-association', '"healthcare association" "2028 conference" "committee"'),
 ('catch-historical-society', '"historical society" "annual meeting" "2028" "host"'),
 ('catch-faith-convention', '"religious association" "2029" "convention" "site"'),
 ('catch-education-venue', '"education association" "2028 conference" "venue"'),
 ('catch-fraternal-convention', '"fraternal organization" "2028" "convention" "site"'),
 ('catch-member-feedback', '"association" "conference" "feedback" "2027" "changes"'),
 ('catch-local-host', '"professional association" "local host committee" "2028"'),
 ('catch-retreat-planning', '"nonprofit association" "retreat" "location" "2027"'),
 ('catch-site-next', '"2029" "site selection" "state association"'),
 ('catch-site-2030', '"2030" "conference" "site selection committee"'),
 ('catch-new-director', '"association" "conference" "new executive director" "2027"'),
 ('catch-conference-pricing', '"association" "conference" "rising costs" "2028"'),
]
CATCHUP_PER_RUN=6

# Lower-friction public-index queries for regional organizers. These still pass
# the named-buyer, event-context and early-change filters in as_candidate().
# Broader discovery must not be presented as verified demand.
QUERIES += [
 ('regional-committee-open','"2027 conference" "planning committee"'),
 ('regional-committee-volunteer','"conference committee" "volunteers needed"'),
 ('regional-board-minutes','"conference" "board minutes" "2027"'),
 ('regional-budget-reset','"annual conference" "budget" "committee"'),
 ('regional-event-survey','"annual conference" "survey results"'),
 ('regional-location-vote','"annual conference" "location vote"'),
 ('regional-site-selection','"2028 conference" "site selection"'),
 ('regional-host-call','"2028 annual conference" "host" "proposals"'),
 ('regional-new-chair','"conference" "new planning chair"'),
 ('regional-attendee-feedback','"conference" "feedback" "next year"'),
 ('regional-hotel-costs','"conference" "hotel costs" "board"'),
 ('regional-event-staff','"association" "events manager" "vacancy"'),
 ('regional-reimagine','"annual conference" "new format"'),
 ('regional-venue-rethink','"annual conference" "venue change"'),
 ('regional-planner-services','"nonprofit" "conference planning services" "proposal"'),
]

# Extra SMERF/nonprofit, pre-RFP discovery lanes. Never delete general
# signal coverage. Requiring real organizer and change wording still applies.
QUERIES += [
 ('smerf-board-site', '"nonprofit association" "board minutes" "conference" "location"'),
 ('smerf-conference-chair', '"regional association" "new conference chair"'),
 ('smerf-nonprofit-cost', '"nonprofit" "annual conference" "financial report"'),
 ('smerf-attendee-feedback', '"state association" "conference" "member survey" "next"'),
 ('smerf-venue-undecided', '"historical society" "annual meeting" "site selection"'),
 ('smerf-museum-host-support', '"museum association" "annual conference" "host committee"'),
 ('smerf-veterans', '"veterans association" "convention committee" "site"'),
 ('smerf-religious', '"religious association" "annual conference" "planning committee"'),
 ('smerf-education', '"education association" "conference" "board minutes" "venue"'),
 ('smerf-fraternal', '"fraternal" "annual convention" "host committee"'),
 ('smerf-retreat', '"nonprofit" "annual retreat" "venue" "committee"'),
 ('smerf-finance-pressure', '"association" "conference" "post event" "budget"'),
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

# Extract a defensible candidate organizer name. A name is not proof of EIN,
# nonprofit status, buying authority, or ownership of a specific event.
ORG_SUFFIX = r'(?:Association|Society|Federation|Council|Alliance|Coalition|Foundation|Chamber|Guild|Network|Fraternity|Sorority|Chapter)'
ORG_NAME_1 = re.compile(
    r"\b((?:[A-Z][A-Za-z0-9&'.-]+\s+){1,9}" + ORG_SUFFIX +
    r"(?:\s+of\s+(?:[A-Z][A-Za-z&'.-]+\s*){1,7})?)\b")
ORG_NAME_2 = re.compile(
    r"\b(" + ORG_SUFFIX + r"\s+(?:of|for)\s+(?:(?:[A-Z][A-Za-z&'.-]+|the|of|and)\s*){2,9})\b")
BAD_NAME_START = {'The','Our','Your','Upcoming','National Conference','Annual','Event','Join','Conference','2027','2028','2029'}
BAD_ORG_NAMES = {'association','society','association conference','conference association','planning association', 'conference planning committee'}

def candidate_organization(title, summary='', source='', known_names=()):
    txt=' '.join((title or '',summary or ''))
    # Confirm a known watchlist organization only when the full name occurs.
    for name in sorted(known_names,key=len,reverse=True):
        if re.search(r'(?<![\w])'+re.escape(name)+r'(?![\w])',txt,re.I):return name
    matches=[]
    for fragment in (title or '',source or '',summary or ''):
        for rx in (ORG_NAME_1,ORG_NAME_2):
            for m in rx.finditer(fragment):
                name=re.sub(r'\s+',' ',m.group(1)).strip(' -:|,.')
                name=re.sub(r'^The\s+','',name)
                if len(name)<12 or len(name)>130 or name.lower() in BAD_ORG_NAMES:continue
                if name.split()[0] in BAD_NAME_START:continue
                if re.search(r'\b(?:Planning|Conference|Annual|Meeting|Hotel|Session|Program|Event)\s+'+ORG_SUFFIX+r'$' ,name):continue
                matches.append((len(name),name))
        if matches:break
    return max(matches)[1] if matches else ''

def org_key(name):
    return re.sub(r'[^a-z0-9]+',' ',re.sub(r'^the\s+','',name.lower())).strip()


def read_watchlist_names():
    try:
        source=json.loads((ROOT/'watchlist.json').read_text(encoding='utf-8'))
        return [v['name'].strip() for v in source.get('targets',[]) if isinstance(v,dict) and v.get('name')]
    except (OSError,ValueError,KeyError):return []

WATCHLIST_NAMES=read_watchlist_names()

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
  r'\b(?:conference|convention|annual meeting|meeting)\b.{0,100}\b(?:venue (?:fell through|cancelled|unavailable)|relocat|reschedul|mov(?:ed|ing) to (?:spring|summer|fall|winter)|shift(?:ed|ing) to (?:spring|summer|fall|winter)|changed dates|new dates due to|hotel renovation|lost (?:hotel|venue))\w*',
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


# Robert's nonprofit/SMERF research preference. Historical experience: 25-2500
# guests, but 75-500 is the preferred solo-service research band. Always verify.
# These are research heuristics, never buyer probabilities or qualification.
ROBERT_EARLY_FAMILIES = {
 'board-location': 13, 'committee-forming': 12, 'event-financial-review': 15,
 'event-review': 11, 'location-exploration': 12, 'local-host-support': 11,
 'operating-transition': 10, 'committee-reset': 12, 'economics': 14,
 'attendee-change': 11, 'economics-watch': 8, 'capacity': 10,
 'strategic-shift': 10, 'future-site-research': 11,
 'committee-research': 10, 'financial-research': 10,
}
SMERF_FIT = re.compile(
 r'\b(?:nonprofit|non-profit|501\(c\)|charitable|foundation|historical society|'
 r'museum association|heritage society|educators? association|school boards?|'
 r'library association|community development|religious|church|faith.based|'
 r'ministr(?:y|ies)|veterans?|military families|fraternal|sorority|fraternity|'
 r'civic association|senior centers?|social club|membership organization|'
 r'state association|regional association|chapter)\b',re.I)
CLEAR_NON_FIT = re.compile(r'\b(?:corporate product launch|investor roadshow|enterprise tech expo|commercial trade fair)\b',re.I)
VENUE_FIXED = re.compile(r'\b(?:official (?:conference |host )?hotel|room block (?:now )?(?:open|available)|book your (?:hotel|room)|venue (?:is |has been )?(?:confirmed|contracted|booked))\b',re.I)
RFP_PHASE = re.compile(r'\b(?:RFP|request for proposals|request for bids|accepting proposals|soliciting bids|hotel proposals under review)\b',re.I)
def robert_discovery_priority(types, text, flags, baseline):
    """Rank for investigation, not probability; verify legal identity and venue."""
    types=set(types)
    bonus=min(27,sum(ROBERT_EARLY_FAMILIES.get(t,0) for t in types))
    fit='Possible nonprofit/SMERF clue' if SMERF_FIT.search(text) else 'Sector not yet verified'
    if CLEAR_NON_FIT.search(text):bonus-=35;fit='Possible outside-specialty event'
    if not SMERF_FIT.search(text):bonus-=9
    if 'procurement' in types or RFP_PHASE.search(text):bonus-=11
    if VENUE_FIXED.search(text):bonus-=20
    if flags:bonus-=11
    return max(0,min(92,baseline+bonus)),fit

# Weaker, early indicators deserve review but MUST NOT be called buying intent.
# A routine conference announcement, speaker CFP, or abstract call is not enough.
EARLY_SIGNALS = {
 'board-location': [
   r'\b(?:board|trustees|executive committee|site selection committee)\b.{0,110}\b(?:next|future|upcoming|annual) (?:conference|convention|meeting)\b.{0,95}\b(?:location|city|host|venue|format|site)\b',
   r'\b(?:board minutes|committee minutes)\b.{0,100}\b(?:conference|convention|annual meeting)\b'],
 'event-financial-review': [
   r'\b(?:conference|convention|annual meeting)\b.{0,75}\b(?:financial report|budget discussion|post.event financial|net proceeds|operating loss|expense review|cost assessment)\b',
   r'\b(?:board|finance committee|treasurer)\b.{0,90}\b(?:conference|meeting) (?:costs|expenses|budget|margin|deficit)\b'],
 'local-host-support': [
   r'\b(?:local host|host committee|chapter host|host organization)\b.{0,100}\b(?:conference|convention|annual meeting)\b.{0,70}\b(?:support|assistance|volunteers|logistics|planning|site)\b',
   r'\b(?:conference|annual meeting)\b.{0,90}\b(?:local host|host chapter)\b.{0,60}\b(?:help|planning|logistics|assistance)\b'],
 'committee-forming': [
   r'\b(?:20(?:26|27|28|29|30) )?(?:annual |national |regional )?conference (?:planning )?committee\b',
   r'\bconference committee\b.{0,80}\b(?:apply|join|volunteer|recruit|meeting|open positions|new members|202[6-9])\b',
   r'\b(?:volunteers|nominations|applications|interest form)\b.{0,90}\bconference (?:planning )?committee\b'],
 'location-exploration': [
   r'\b(?:future conference|conference locations?|host (?:cities|city|sites?)|site selection)\b.{0,100}\b(?:recommendations?|suggestions?|input|consider|looking|proposals|options|committee)\b',
   r'\b(?:2027|2028|2029)\b.{0,80}\b(?:conference|convention)\b.{0,75}\b(?:location|host city|host site|venue)\b.{0,60}\b(?:exploring|considering|seeking|proposals|input|recommendations|options|not yet decided)\b'],
 'event-review': [
   r'\b(?:conference|annual meeting|annual convention)\b.{0,75}\b(?:survey|evaluation|feedback|debrief|improvements)\b',
   r'\b(?:attendee|member)\b.{0,40}\b(?:survey|feedback)\b.{0,50}\bconference\b'],
 'operating-transition': [
   r'\b(?:annual conference|convention|annual meeting)\b.{0,110}\b(?:new chair|new executive director|new planning team|planning changes|new format|moving to summer)\b',
   r'\b(?:new conference chair|conference chair transition|conference planning handoff)\b'],
 'economics-watch': [
   r'\b(?:conference|convention|annual meeting)\b.{0,80}\b(?:budget|costs|revenue|hotel contract|room block|food and beverage)\b'],
}

# Do not mistake a host hotel's construction, a generic event consultant blog,
# or a speaker-session CFP for organizer purchasing intent.
HARD_NEGATIVE = re.compile(r'\b(?:what is a conference|dictionary|wikipedia|conference planning tips|best conferences to attend|top \d+ conferences|conference industry trends|conference industry outlook|industry outlook survey|conference sector survey|how to plan a conference)\b',re.I)

# A *completed* hotel/city selection is a counter-signal, not a sourcing window.
CLOSED_LOCATION = re.compile(
 r'\b(?:selects?|selected|chooses?|chosen|announces?|confirms?|finalizes?|finalized)\b.{0,60}\b(?:20\d{2}\s+)?(?:conference|convention|annual meeting)\b.{0,40}\b(?:location|site|host city|venue|hotel)\b|'
 r'\b(?:conference|convention|annual meeting)\b.{0,65}\b(?:location|site|host city|venue|hotel)\b.{0,45}\b(?:selected|chosen|confirmed|already booked|contracted)\b',re.I)

def weak_evidence(txt):
    found={}
    for family,patterns in EARLY_SIGNALS.items():
        for p in patterns:
            m=re.search(p,txt,re.I)
            if m:
                found[family]=txt[max(0,m.start()-24):min(len(txt),m.end()+54)].strip()
                break
    return found

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

# Collect why indexed material failed. This is the most important
# diagnostic for a scanner that fetches hundreds of hits but finds few leads.
REJECTION_COUNTS={}
LAST_REJECTION_REASON=""
def reject(reason):
    global LAST_REJECTION_REASON
    LAST_REJECTION_REASON=reason
    REJECTION_COUNTS[reason]=REJECTION_COUNTS.get(reason,0)+1
    return None

# The older signal patterns look for very specific word order. The fallback
# accepts a few more arrangements, but only for explicit future committee,
# cost, site or operational decisions. It never calls them qualified leads.
FUTURE_CYCLE=re.compile(r'\b(?:2027|2028|2029|2030|2031)\b')
PLANNING_CHANGE=[
 ('future-site-research',re.compile(r'\b(?:site selection|host site|host city|conference venue|future conference location)\b.{0,135}\b(?:committee|review|reviewing|consider|discuss|decision|vote|seeking|search|evaluate|future|next)\b|\b(?:committee|review|reviewing|consider|discuss|decision|vote|seeking|evaluate)\b.{0,135}\b(?:site selection|host site|host city|conference venue|future conference location)\b',re.I)),
 ('committee-research',re.compile(r'\b(?:conference|convention|annual meeting)\b.{0,75}\b(?:site selection|planning committee|conference chair|host committee)\b.{0,80}\b(?:formed|appointed|recruiting|future|new|seeking|202[7-9]|203[0-1])\b|\b(?:appointed|new|volunteer|selected)\b.{0,80}\b(?:conference|convention)\b.{0,60}\b(?:chair|committee|host)\b',re.I)),
 ('financial-research',re.compile(r'\b(?:conference|annual meeting|convention)\b.{0,100}\b(?:expenses?|costs?|budget|room block|hotel rates|venue contract)\b.{0,100}\b(?:review|concerns?|increase|shortfall|discussion|consider|rising|negotiat)\b|\b(?:board|budget committee)\b.{0,85}\b(?:conference|annual meeting)\b.{0,85}\b(?:costs?|budget|hotel rates|room block)\b',re.I)),
]
def alternative_early_evidence(text):
    if not FUTURE_CYCLE.search(text):return {}
    for name,pattern in PLANNING_CHANGE:
        match=pattern.search(text)
        if match:
            return {name:text[max(0,match.start()-30):match.end()+70][:330]}
    return {}

def relevance(article,label):
    """Return concrete/early evidence tiers or None for junk.

    This is a discovery heuristic, never an eligibility or buying conclusion.
    """
    title=article.get('title','').strip()
    summary=article.get('summary','').strip()
    url=article.get('url','')
    if not title or not url.startswith(('https://','http://')):return reject('no_http_title')
    h=host_name(url)
    if any(h==x or h.endswith('.'+x) for x in EXCLUDED_HOSTS):return reject('excluded_host')
    if GENERIC_BLOG.search(title) or HARD_NEGATIVE.search(title) or CLOSED_LOCATION.search(title):return reject('blog_or_completed_site')
    txt=event_context(title,summary)
    if not EVENT_REGEX.search(txt):return reject('no_event_reference')
    if FOREIGN_CONTEXT.search(txt):return reject('foreign_reference')
    if not source_platform(article,label) and label.startswith('social-'):return reject('unverified_social_platform')
    org=candidate_organization(title,summary,article.get('source',''),WATCHLIST_NAMES)
    if not org:return reject('organizer_name_missing')
    # Guard against a generic article that mentions someone else's association
    # but is not about an organization's conference planning.
    strong=evidence_groups(txt)
    weak=weak_evidence(txt)
    if not strong and not weak:weak=alternative_early_evidence(txt)
    if not strong and not weak:return reject('no_actionable_change_evidence')
    if ANNOUNCEMENT_ONLY.search(title) and not any(k in strong for k in ('venue-decision','economics','disruption','capacity','committee-reset','strategic-shift')):
        return reject('routine_event_announcement')
    if re.search(r'\b(?:calls? for|invites?|requests?)\s+(?:speaker|session|presentation|paper|abstract)\s+proposals\b',title,re.I) and not strong:
        return reject('speaker_proposal_not_venue')
    date=article.get('published','')
    if date:
        try:
            age=(NOW.date()-datetime.fromisoformat(date).date()).days
            if age<0 or age>150:return reject('stale_or_future_index_date')
        except ValueError:return reject('invalid_date')
    # Priority requires actual source-text evidence. Watch can be exploratory.
    tier='priority' if strong else 'watch'
    return {'strong':strong,'weak':weak,'tier':tier,'organization':org}

def next_action(types,flags,play):
    if flags:return 'Check named hotel, planner and room-block commitments first. Is any useful scope still influenceable?'
    if play=='Safe':return 'Verify the actual consultant RFP scope, deadline, bidder eligibility and contracting decision-maker.'
    if 'venue-decision' in types or 'future-site-research' in types:return 'Identify which conference cycle is under site review, the venue decision deadline and who can approve an external advisor.'
    if 'capacity' in types or 'committee-reset' in types:return 'Check who owns conference planning after the staffing/committee change and whether outside assistance is allowed.'
    if 'economics' in types:return 'Find the actual conference financial issue (rooms, food, AV, attrition, registration) and the responsible committee.'
    if 'attendee-change' in types:return 'Read the original attendee feedback and determine when the next conference format, location or budget will be decided.'
    return 'Confirm legal organizer, prior event cycles, next decision point, hotel commitments and current planner.'

def as_candidate(article,query_label):
    global LAST_REJECTION_REASON
    LAST_REJECTION_REASON=""
    assessment=relevance(article,query_label)
    if not assessment:return None
    title,summary,url=article['title'],article['summary'],article['url']
    txt=event_context(title,summary)
    flags=[k for k,pattern in COMMITMENT_CLUES if re.search(pattern,txt,re.I)]
    types=list(assessment['strong'])+ [k for k in assessment['weak'] if k not in assessment['strong']]
    has_direct=('procurement' in assessment['strong'] and re.search(r'\b(?:planner|planning services|management services|consultant)\b',txt,re.I))
    play='Safe' if has_direct else ('Bold' if ('economics' in types or 'attendee-change' in types or 'economics-watch' in types) and not ('venue-decision' in types or 'committee-reset' in types) else 'Smart')
    score=min(92, (49 if assessment['tier']=='priority' else 28) + 9*min(len(assessment['strong']),3) + 5*min(len(assessment['weak']),3) + (7 if has_direct else 0) - 12*bool(flags))
    score,robert_fit=robert_discovery_priority(types,txt,flags,score)
    platform=source_platform(article,query_label) or ''
    is_social=bool(platform)
    date=article.get('published','')
    ident=hashlib.sha256((url.split('#')[0].lower()+'|'+title.lower()).encode()).hexdigest()[:20]
    return {'id':ident,'title':title[:220],'summary':summary[:550],'url':url,
      'source':article.get('source') or 'Public news index',
      'published':('' if is_social else date),'indexed_date':(date if is_social else ''),
      'date_basis':('Index/feed date; original social post date unknown' if is_social else 'Public search-feed timestamp; confirm original publication date'),
      'origin':('social_index' if is_social else 'news_index'),'platform':platform,
      'original_post_checked':False,'detected':NOW.date().isoformat(),
      'organization_candidate':assessment['organization'],
      'organization_key':org_key(assessment['organization']),
      'review_tier':assessment['tier'],
      'strong_evidence':assessment['strong'],'early_evidence':assessment['weak'],
      'types':types,'priority':score,'robert_fit_clue':robert_fit,'pre_rfp_priority':bool(set(types)&set(ROBERT_EARLY_FAMILIES)) and not bool(flags) and not bool(RFP_PHASE.search(txt)),'query_id':query_label,'play':play,
      'next_action':next_action(types,flags,play),'flags':flags,
      'signal_strength':('Specific indexed buying/planning clue, not a confirmed buyer' if assessment['tier']=='priority' else 'Early indexed clue; no purchasing intent established'),
      'signal_evidence':assessment['strong'] or assessment['weak'],
      'evidence_gate':'Named organizer + event + planning/financial/venue clue; original source unverified',
      'verified_revenue':False,'verified_event':False,'verified_opening':False,
      'qualification':'Unverified discovery'}

# Official-organization source watches cover quiet pages that rarely appear in
# RSS/news. These start as transparent, manually chosen source watches, not
# auto-discovered buyer intent. Failed fetches are reported, never filled in.
class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip=0; self.text=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','noscript','svg'):self.skip+=1
        if tag in ('p','h1','h2','h3','li','section','br'):self.text.append(' ')
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript','svg') and self.skip:self.skip-=1
        if tag in ('p','h1','h2','h3','li','section','br'):self.text.append(' ')
    def handle_data(self,data):
        if not self.skip:self.text.append(data)

def official_watches(old_items):
    try:
        raw=json.loads((ROOT/'watch_pages.json').read_text(encoding='utf-8'))
        pages=raw.get('sources',[])
    except (ValueError,OSError):pages=[]
    old_by_id={v.get('id'):v for v in old_items}
    result=[];checks=0;failed=[]
    for spec in pages[:20]:
        url=spec.get('url','');org=spec.get('organization','');needle=spec.get('needle','')
        if not url.startswith('https://') or not org or len(needle)<10:continue
        try:
            req=urllib.request.Request(url,headers={'User-Agent':HEADERS['User-Agent'],'Accept':'text/html,*/*'})
            with urllib.request.urlopen(req,timeout=10) as res:
                if 'application/pdf' in res.headers.get('Content-Type','').lower():
                    raise ValueError('PDF source requires visual review, preserving dated research snapshot only')
                raw_html=res.read(800_000).decode('utf-8','replace')
            parser=PageText();parser.feed(raw_html)
            page=re.sub(r'\s+',' ',' '.join(parser.text)).strip()
            needle_norm=re.sub(r'\s+',' ',needle).strip()
            # An exact known public passage must still exist. If not, escalate
            # for manual review and do not pretend this source is current.
            match=re.search(re.escape(needle_norm),page,re.I)
            if not match:
                # Preserve a dated snapshot with explicit stale-source warning.
                raise ValueError('expected source passage absent or changed')
            checks+=1
            excerpt=page[max(0,match.start()-60):min(len(page),match.end()+110)]
            ident=hashlib.sha256(('watch:'+url).encode()).hexdigest()[:20]
            old=old_by_id.get(ident,{})
            family=spec.get('family','committee-reset')
            is_priority=spec.get('tier')=='priority'
            item={'id':ident,'title':org+' | '+spec.get('label','Organizational conference watch'),
               'summary':excerpt[:360],'url':url,'source':'Official association page (monitored)',
               'published':'','indexed_date':'','date_basis':'Public webpage checked on '+NOW.date().isoformat()+'; original publication date not established',
               'origin':'official_watch','platform':'','original_post_checked':False,
               'detected':old.get('detected',NOW.date().isoformat()),
               'first_detected':old.get('first_detected',NOW.date().isoformat()),
               'last_checked':NOW.isoformat(timespec='seconds'),
               'monitor_status':'Official source page fetched during this scan',
               'organization_candidate':org,'organization_key':org_key(org),
               'review_tier':'priority' if is_priority else 'watch','strong_evidence':{family:excerpt} if is_priority else {},
               'early_evidence':{} if is_priority else {family:excerpt},
               'types':[family],'priority':61 if is_priority else 36,
               'query_id':'official-page-monitor','play':'Smart',
               'next_action':spec.get('next_action','Check the next event decision and incumbent planner.'),
               'flags':spec.get('counterevidence_flags',[]),
               'source_document_date':spec.get('source_document_date',''),
               'signal_strength':'Monitored official source passage; NOT proof of an open external contract',
               'signal_evidence':{family:excerpt},
               'evidence_gate':'Named association and verifiable original page; recurring event/financial fit not yet verified',
               'verified_revenue':False,'verified_event':False,'verified_opening':False,
               'qualification':'Unverified source watch'}
            if old.get('research_assist'):item['research_assist']=old['research_assist']
            result.append(item)
        except Exception as exc:
            failed.append(org+': '+type(exc).__name__+' '+str(exc)[:90])
            # A researcher-verified public page passage can provide a TEMPORARY
            # fallback when automation is blocked (403). Mark this as a cached
            # source observation, NOT proof the page remains unchanged today.
            baseline_date=spec.get('baseline_as_of','')
            baseline_text=spec.get('baseline_excerpt','')
            try:age=(NOW.date()-datetime.fromisoformat(baseline_date).date()).days
            except ValueError:age=9999
            if baseline_text and 0<=age<=180:
                ident=hashlib.sha256(('watch:'+url).encode()).hexdigest()[:20]
                old=old_by_id.get(ident,{})
                family=spec.get('family','committee-reset')
                is_priority=spec.get('tier')=='priority'
                item={'id':ident,'title':org+' | '+spec.get('label','Organizational conference watch'),
                  'summary':baseline_text[:280], 'url':url,'source':'Official association page (research snapshot)',
                  'published':'','indexed_date':'',
                  'date_basis':'Research snapshot checked '+baseline_date+'; runner could not access page in latest scan',
                  'origin':'official_watch','platform':'','original_post_checked':False,
                  'detected':old.get('detected',baseline_date),'first_detected':old.get('first_detected',baseline_date),
                  'last_checked':old.get('last_checked',''),
                  'monitor_status':('STALE RESEARCH ONLY: original page not rechecked since '+baseline_date if age>30 else 'NOT RECHECKED LIVE: saved public-source research baseline from '+baseline_date),
                  'organization_candidate':org,'organization_key':org_key(org),
                  'review_tier':'priority' if is_priority else 'watch',
                  'strong_evidence':{family:baseline_text} if is_priority else {},
                  'early_evidence':{} if is_priority else {family:baseline_text},
                  'types':[family],'priority':(20 if age>30 else 48 if is_priority else 30),
                  'query_id':'official-page-baseline','play':'Smart',
                  'next_action':'Recheck original source because automated access failed. '+spec.get('next_action',''),
                  'flags':spec.get('counterevidence_flags',[]),
                  'source_document_date':spec.get('source_document_date',''),
                  'signal_strength':'Previously verified public passage, NOT confirmed current; outside planning need unverified',
                  'signal_evidence':{family:baseline_text},
                  'evidence_gate':'Known public research baseline; URL not reachable from automated runner',
                  'verified_revenue':False,'verified_event':False,'verified_opening':False,
                  'qualification':'Unverified source watch'}
                result.append(item)
        time.sleep(.1)
    return result,checks,failed

def existing():
    if not DEST.exists():return []
    try:
        d=json.loads(DEST.read_text(encoding='utf-8'))
        return d.get('signals',[]) if isinstance(d.get('signals',[]),list) else []
    except (ValueError,OSError):return []



# Research-gate status is deliberately conservative. Public snippets cannot
# establish a signed contract's absence, event-level budget, solo workload or
# decision-maker authority. Keep all candidates but clearly flag missing proof.
ROBERT_REQUIRED_CHECKS = ('nonprofit_smerf_identity','recurring_event',
                         'event_level_spend','manageable_logistics',
                         'decision_maker','pre_rfp_window','venue_planner_crosscheck')
def preliminary_fit_gates(group):
    families=set(group.get('families',[]))
    flags=group.get('commitment_flags',[])
    event_clues=bool(families & {'event-cycle','event-review','attendee-change',
                       'committee-forming','location-exploration','board-location',
                       'future-site-research','committee-research','financial-research',
                       'local-host-support','venue-decision','committee-reset'})
    # A clue can initiate investigation, NEVER satisfy a qualification gate.
    return {
      'specialty':'Requires legal identity / nonprofit or SMERF confirmation',
      'recurring_event':'Research previous two event cycles' if event_clues else 'No confirmed recurring event history',
      'event_spend':'Event budget, room nights and supplier spend unverified',
      'workload':'Attendance, days, tracks, exhibitors and staff unverified',
      'decision_maker':'Named purchasing authority and accessibility unverified',
      'venue_planner':'Potential commitment evidence present' if flags else 'Venue and planner agreement status unknown',
      'pre_rfp':'Cannot confirm open sourcing from public silence; check decision owner',
      'qualified':False,
      'review_goal':'25-50 researched organizers, 12 sourced manual-ready prospects',
      'suggested_next_check':'Confirm exact event, committee/decision-maker, future hotel and current planner, then event spending',
    }

def organization_stacks(items):
    """Group EXACT named-organizer candidates, never merge chapters heuristically.

    Multiple categories in one post are not counted as independent sources.
    All matching and timing fields remain unverified.
    """
    groups={}
    for x in items:
        key=x.get('organization_key')
        if not key:continue
        group=groups.setdefault(key,{'key':key,'name':x.get('organization_candidate',''),
             'signal_ids':[],'families':set(),'sources':set(),'commitment_flags':set(),
             'evidence':[],'priority_count':0,'watch_count':0,'most_recent':'',
             'play':'Smart','qualifying_status':'Requires manual verification'})
        group['signal_ids'].append(x['id'])
        group['first_detected']=min(group.get('first_detected','9999-12-31'),x.get('first_detected') or x.get('detected') or '9999-12-31')
        group['families'].update(x.get('types',[]))
        if x.get('review_tier')=='priority':group['priority_count']+=1
        else:group['watch_count']+=1
        group['commitment_flags'].update(x.get('flags',[]))
        group['most_recent']=max(group['most_recent'],x.get('published') or x.get('indexed_date') or x.get('detected') or '')
        host=host_name(x['url'])
        if host in ('news.google.com','bing.com','www.bing.com'):
            publisher=(x.get('source') or 'unresolved-index-source').lower().strip()
            src='publisher:'+publisher
        else:src=host
        group['sources'].add(src)
        group['evidence'].append({'id':x['id'],'title':x['title'],'url':x['url'],
               'source':x.get('source',''),'published':x.get('published') or x.get('indexed_date') or '',
               'document_date':x.get('source_document_date',''),
               'freshness':x.get('monitor_status',''),
               'counterevidence_flags':x.get('flags',[]),
               'families':x.get('types',[]),'tier':x.get('review_tier','watch')})
    out=[]
    for group in groups.values():
        source_count=len(group['sources'])
        # No per-item query bonus; independent publishers beat repeated snippets.
        kind_count=len(group['families'])
        n=len(group['signal_ids'])
        group['mentions']=n
        group['distinct_sources']=source_count
        group['families']=sorted(group['families'])
        group['commitment_flags']=sorted(group['commitment_flags'])
        group['early_signal_families']=sorted(set(group['families']) & set(ROBERT_EARLY_FAMILIES))
        group['robert_fit_screen']=preliminary_fit_gates(group)
        group['pre_rfp_research_priority']=bool(group['early_signal_families']) and not group['commitment_flags'] and 'procurement' not in group['families']
        group['priority']=min(92,28 + min(kind_count,4)*8 + min(source_count,3)*7 +
                              min(20,len(group['early_signal_families'])*10) +
                              (5 if group['priority_count'] else 0) -
                              (18 if group['commitment_flags'] else 0) -
                              (12 if 'procurement' in group['families'] else 0))
        # Revenue filings and the recurring event calendar support fit, but do
        # NOT independently corroborate an open planning or procurement window.
        buying_families=set(group['families'])-{'verified-financial-fit','event-cycle','decision-cadence','venue-committed'}
        group['stack_stage']=('multiple sourced planning clues, contract openness unverified' if source_count>=2 and len(buying_families)>=2
            else 'multiple evidence items, no verified buying window' if n>=2
            else 'single-source clue')
        group['first_question']=(
           'Which next conference decision is not yet contracted, and who authorizes an external planner?' if group['priority_count']
           else 'What is this organization deciding next, and does it have an independent planning need?')
        if 'procurement' in group['families']:group['play']='Safe'
        elif any(k in group['families'] for k in ('economics','attendee-change','economics-watch')):group['play']='Bold'
        group.pop('sources')
        out.append(group)
    return sorted(out,key=lambda g:(g['pre_rfp_research_priority'],g['distinct_sources']>=2,g['priority'],g['most_recent']),reverse=True)

# A bounded, transparent journal of near-miss indexed results. The previous
# scanner did not store rejects, so historical rejects must be rediscovered.
# Save only public URL/title/short indexed excerpt. Never call these leads.
REJECTION_ARCHIVE=ROOT/'data'/'rejected_candidates.json'
REPLAY_REASONS={'organizer_name_missing','no_actionable_change_evidence',
                'routine_event_announcement','speaker_proposal_not_venue'}
REPLAY_MAX=350
REPLAY_LOOKBACK_DAYS=90

def rejected_archive():
    try:
        d=json.loads(REJECTION_ARCHIVE.read_text(encoding='utf-8'))
        return [x for x in d.get('items',[]) if isinstance(x,dict) and x.get('url')]
    except (OSError,ValueError,TypeError):
        return []

def rejected_record(article,reason,label,engine):
    if reason not in REPLAY_REASONS:return None
    url=article.get('url','').strip()
    title=article.get('title','').strip()
    if not url.startswith(('https://','http://')) or len(title)<10:return None
    # RSS snippets can be incomplete or misleading; this remains a caution bucket.
    ident=hashlib.sha256((url.split('#')[0].lower()+'|'+title.lower()).encode()).hexdigest()[:20]
    return {'id':ident,'url':url[:700],'title':title[:200],
            'summary':article.get('summary','')[:475],
            'source':article.get('source','')[:120],
            'published':article.get('published',''),
            'query_id':label,'engine':engine,'reason':reason,
            'first_seen':NOW.date().isoformat(),
            'last_seen':NOW.date().isoformat(),
            'review_status':'unqualified_near_miss',
            'caution':'Public-index snippet only. No venue availability, buying intent or buyer fit established.'}

def archive_rejected_item(archive,article,reason,label,engine):
    item=rejected_record(article,reason,label,engine)
    if item:
        old=archive.get(item['id'])
        if old:item['first_seen']=old.get('first_seen',item['first_seen'])
        archive[item['id']]=item

def replay_archived(previous_archive,seen):
    checked=0;recovered=0
    # Re-screen previously discarded snippets using the CURRENT filters.
    # Rejected candidates never become qualified by being replayed.
    for old in previous_archive:
        if checked>=REPLAY_MAX:break
        try:age=(NOW.date()-datetime.fromisoformat(old.get('last_seen','')).date()).days
        except ValueError:age=9999
        if age>REPLAY_LOOKBACK_DAYS:continue
        checked+=1
        source={k:old.get(k,'') for k in ('title','summary','url','source','published')}
        item=as_candidate(source,old.get('query_id','replay'))
        if item and item['id'] not in seen:
            item['first_detected']=old.get('first_seen',NOW.date().isoformat())
            item['replay_recovered']=True
            item['replay_note']='Previously rejected indexed excerpt, now research-only under revised filters. Check original source before use.'
            seen[item['id']]=item
            recovered+=1
    return checked,recovered

def run():
    previous=existing()
    daily_history=read_history()
    before_goal=today_progress(daily_history,NOW)
    catchup_active=bool(before_goal['remaining'])
    seen={}
    prior_rejections=rejected_archive()
    near_misses={x['id']:x for x in prior_rejections if x.get('id')}
    archive_recovered=0
    checked_rejected=0
    dropped_previous=0
    # Re-evaluate the old feed under new strict criteria. This is the *public*
    # discovery feed only. It does not erase private saved review/evidence notes.
    for x in previous:
        if not isinstance(x,dict) or not x.get('id'):continue
        if x.get('origin')=='official_watch':continue
        source={'title':x.get('title',''),'summary':x.get('summary',''),
                'url':x.get('url',''),'source':x.get('source',''),
                'published':x.get('published','')}
        curr=as_candidate(source,x.get('query_id',''))
        if curr:
            # Keep existing research assist, flagged counter-evidence and dates.
            curr.update({k:x[k] for k in ('research_assist','first_detected') if k in x})
            curr['first_detected']=x.get('first_detected') or x.get('detected') or curr['detected']
            curr['detected']=x.get('detected',curr['detected'])
            seen[curr['id']]=curr
        else:dropped_previous+=1
    # Replay before polling live public sources so filter changes can recover
    # relevant older indexed snippets without losing the original audit trail.
    checked_rejected,archive_recovered=replay_archived(prior_rejections,seen)
    fetched=0;failed=[];fresh=0;rejected=0;social_attempted=0;social_found=0
    light=os.environ.get('SF_LIGHT_SCAN','false').lower()=='true'
    selected=[(i,pair) for i,pair in enumerate(QUERIES) if not light or i % 6 == NOW.hour % 6]
    extra_count=0
    if catchup_active:
        # Rotate six additional nonprofit/SMERF planning searches per run.
        offset=(NOW.hour*CATCHUP_PER_RUN+NOW.toordinal()*3)%len(CATCHUP_QUERIES)
        additions=[(len(QUERIES)+j,CATCHUP_QUERIES[(offset+j)%len(CATCHUP_QUERIES)])
                   for j in range(CATCHUP_PER_RUN)]
        selected.extend(additions)
        extra_count=len(additions)
    for i,(label,query) in selected:
        engines=['google']
        if i in (0,2,4,6,8):engines.append('bing')
        # Association board minutes, member surveys and official notices often
        # never reach a news index. Sample the general public web index too;
        # the same strict buyer/action gates apply to every returned page.
        if i % 3 == 1:engines.append('web')
        for engine in engines:
            try:
                articles=fetch_rss(scan_url(query,engine));fetched+=1
                for a in articles[:25]:
                    item=as_candidate(a,label)
                    if item is None:
                        rejected+=1
                        archive_rejected_item(near_misses,a,LAST_REJECTION_REASON,label,engine)
                        continue
                    if item['id'] in seen:
                        old=seen[item['id']]
                        old['types']=sorted(set(old.get('types',[])+item['types']))
                        old['priority']=max(old.get('priority',0),item['priority'])
                    else:
                        item['first_detected']=item['detected']
                        seen[item['id']]=item;fresh+=1
            except Exception as ex:
                failed.append(f'{label} ({engine}): {type(ex).__name__}: {str(ex)[:100]}')
        time.sleep(.25)
    social_queries=list(social_searches())
    if light:
        social_queries=social_queries[(NOW.hour * 7) % max(1,len(social_queries)):] + social_queries[:(NOW.hour * 7) % max(1,len(social_queries))]
        social_queries=social_queries[:7]
    for label,query in social_queries:
        social_attempted+=1
        try:
            articles=fetch_rss(scan_url(query,'web'));fetched+=1
            for a in articles[:20]:
                item=as_candidate(a,label)
                if item is None:
                    rejected+=1
                    archive_rejected_item(near_misses,a,LAST_REJECTION_REASON,label,'public-web-index')
                    continue
                social_found+=1
                if item['id'] in seen:
                    old=seen[item['id']]
                    old['types']=sorted(set(old.get('types',[])+item['types']))
                    old['priority']=max(old.get('priority',0),item['priority'])
                else:
                    item['first_detected']=item['detected']
                    seen[item['id']]=item;fresh+=1
        except Exception as ex:
            failed.append(f'{label} (public index): {type(ex).__name__}: {str(ex)[:100]}')
        time.sleep(.2)
    watched,watched_ok,watch_errors=official_watches(previous)
    for item in watched:
        if item['id'] in seen:
            # Direct official source supersedes an indexed duplicate only when the
            # exact same source ID was previously present.
            seen[item['id']].update(item)
        else:
            seen[item['id']]=item
            if not any(x.get('id')==item['id'] for x in previous):fresh+=1
    failed.extend('official watch: '+x for x in watch_errors)
    # Preserve a recently verified official watch during temporary HTTP failure.
    # Mark it stale, keep the original last-checked timestamp, and NEVER call
    # the cached observation a fresh source confirmation.
    watched_ids={x['id'] for x in watched}
    for old in previous:
        if old.get('origin')!='official_watch' or old.get('id') in watched_ids:continue
        last_checked=old.get('last_checked','')[:10]
        try:age=(NOW.date()-datetime.fromisoformat(last_checked).date()).days
        except ValueError:continue
        if 0<=age<=30:
            x=dict(old)
            x['monitor_status']='Source was not revalidated in latest scan; last verified '+last_checked
            x['priority']=max(10,int(x.get('priority',36))-12)
            x['next_action']='Reopen the original page; source watch was unreachable or the expected phrase changed. '+x.get('next_action','')
            seen[x['id']]=x
    cutoff=(NOW.date()-timedelta(days=180)).isoformat()
    kept=[x for x in seen.values() if (x.get('published') or x.get('detected') or '0000')>=cutoff]
    kept.sort(key=lambda x:(x.get('published') or x.get('indexed_date') or x.get('detected') or '',x.get('priority',0)),reverse=True)
    kept=kept[:180]
    organizations=organization_stacks(kept)
    old_org_keys={x.get('organization_key') for x in previous if x.get('organization_key')}
    indexed_keys={x.get('organization_key') for x in kept if x.get('origin') in ('news_index','social_index')}
    new_organizations=[g['name'] for g in organizations if g.get('key') in indexed_keys and g.get('key') not in old_org_keys]
    new_source_watch_organizations=[g['name'] for g in organizations if g.get('key') not in indexed_keys and g.get('key') not in old_org_keys]
    try:
        watches=json.loads((ROOT/'watch_pages.json').read_text(encoding='utf-8')).get('sources',[])
        curated_count=len({w.get('organization') for w in watches if w.get('curated_by_chatgpt')})
    except (OSError,ValueError):
        curated_count=0
    previous_ids={x.get('id') for x in previous}
    fresh_indexed=sum(1 for x in kept if x.get('origin') in ('news_index','social_index') and x.get('id') not in previous_ids)
    daily_history,daily_goal,daily_additions=update_history(daily_history,organizations,kept,NOW)
    daily_goal['catchup_queries_used']=extra_count
    daily_goal['newly_added_this_scan']=[x['name'] for x in daily_additions]
    out={'generated_at':NOW.isoformat(timespec='seconds'), 'scanner_version':'5.0-hourly-robert-pre-rfp', 'scan_mode':'light' if light else 'deep',
         'purpose':'Two-lane named-organizer clues, with conservative source-aware stacking. No automatic qualification.',
         'scan_sources_ok':fetched,'official_pages_checked':watched_ok,
         'official_pages_monitored':len(watched),'official_watch_errors':watch_errors,
         'scan_sources_failed':len(failed),
         'scan_queries':len(selected)+social_attempted,'social_index_queries':social_attempted,
         'social_index_candidates_seen':social_found,
         'social_by_platform':{p:sum(1 for x in kept if x.get('platform')==p) for p,_ in SOCIAL_DOMAINS},
         'sources_attempted':len(selected)+sum(i in (0,2,4,6,8) for i,_ in selected)+sum(i%3==1 for i,_ in selected)+social_attempted+len(watched),
         'coverage_warning':'Public RSS/indexed social plus a small set of manually chosen official page watches. Social indexes are incomplete; original post dates unverified. Official watch pages do not prove buyer demand or open sourcing.',
         'daily_goal':daily_goal,'new_discoveries':fresh_indexed,'new_organizations':new_organizations,
         'new_organizations_count':len(new_organizations),
         'new_source_watch_organizations':new_source_watch_organizations,
         'new_source_watch_count':len(new_source_watch_organizations),
         'curated_research_additions':curated_count,
         'review_priority_count':sum(x.get('review_tier')=='priority' for x in kept),
         'review_watch_count':sum(x.get('review_tier')=='watch' for x in kept),
         'stacked_organizations':len(organizations),
         'organizations':organizations,'rejected_irrelevant_hits':rejected,
         'previous_noise_removed':dropped_previous,'rejection_reasons':dict(sorted(REJECTION_COUNTS.items(),key=lambda x:-x[1])),
         'errors':failed[:15],'signals':kept}
    # Old material is retained only for bounded audit/replay, not indefinitely.
    live_ids={x.get('id') for x in kept}
    for ident in list(near_misses):
        entry=near_misses[ident]
        if ident in live_ids:
            near_misses.pop(ident,None)
            continue
        try:age=(NOW.date()-datetime.fromisoformat(entry.get('last_seen','')).date()).days
        except ValueError:age=9999
        if age>REPLAY_LOOKBACK_DAYS:near_misses.pop(ident,None)
    archive_items=sorted(near_misses.values(),key=lambda x:(x.get('last_seen',''),x.get('reason','')),reverse=True)[:REPLAY_MAX]
    REJECTION_ARCHIVE.parent.mkdir(parents=True,exist_ok=True)
    REJECTION_ARCHIVE.write_text(json.dumps({
        'generated_at':NOW.isoformat(timespec='seconds'),
        'purpose':'Auditable near-miss INDEXED RESULTS, not leads; automatically re-screened when discovery criteria change.',
        'historical_warning':'Before this feature, discarded indexed items were NOT stored. Replaying earlier misses requires running the public searches again.',
        'count':len(archive_items),'replayed_this_run':checked_rejected,
        'recovered_this_run':archive_recovered,
        'items':archive_items},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    out['rejection_audit']={'archived_near_misses':len(archive_items),
      'replayed_this_run':checked_rejected,'recovered_this_run':archive_recovered,
      'historical_rejections_available':False,
      'explanation':'Legacy rejected items were not preserved. This new journal saves near-misses and tests them again.'}
    write_history(daily_history)
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f'Feeds OK={fetched}, failed={len(failed)}, new={fresh}, retained={len(kept)}, filtered={rejected}, old_noise_removed={dropped_previous}')
    if failed:print('\n'.join(failed[:5]))
    return 2 if fetched==0 and not kept else 0

if __name__=='__main__':sys.exit(run())