#!/usr/bin/env python3
"""Source-text triage. Never treats an unpublished venue as an open contract."""
import re
from datetime import date, datetime

SPEAKER_ONLY = re.compile(r'\b(?:call for (?:papers|abstracts|presentations|speakers|session proposals)|speaker proposals?|presenter applications?|submit (?:a )?session|abstract review committee)\b', re.I)
VIRTUAL_ONLY = re.compile(r'\b(?:fully online|entirely virtual|virtual-only|virtual conference|online-only conference)\b', re.I)
SITE_COMMITTED = re.compile(r'\b(?:venue (?:has been |is )?(?:booked|selected|confirmed|contracted)|hotel (?:has been |is )?(?:booked|selected|contracted)|contract signed|booked at|official (?:conference )?hotel|host city (?:has been |is )?(?:selected|confirmed))\b', re.I)
HOST_BID = re.compile(r'\b(?:call for (?:conference )?(?:hosts?|host cities|host communities|host sites)|(?:accepting|inviting|seeking|requesting) (?:applications|proposals|invitations|letters of intent|host (?:cities|sites|communities|institutions))\b.{0,130}\b(?:host|site|location|conference|convention)|(?:host|site)\b.{0,65}\b(?:bids?|proposals?|applications|letters of intent))\b', re.I)
VENUE_BID = re.compile(r'\b(?:venue|hotel|conference site|meeting site|host city)\b.{0,85}\b(?:rfp|bids?|proposals? (?:due|requested|under review)|soliciting quotes)|\b(?:request for proposals|request for bids)\b.{0,85}\b(?:venues?|hotels?|meeting (?:site|space)|conference location)\b', re.I)
EARLY_CHANGE = re.compile(r'\b(?:site selection committee|(?:conference|annual meeting|convention)\b.{0,70}(?:planning committee|(?:location|venue|hotel|site|budget) (?:review|discussion|options|consideration)|committee (?:formed|forming|recruiting)|moving to (?:spring|summer|fall|winter)|being shifted to (?:spring|summer|fall|winter)|costs? (?:rising|under review|increasing)|new (?:date|format)))\b', re.I)
HOTEL_SCOPE = re.compile(r'\b(?:hotel|lodging|room blocks?|food and beverage|venue|meeting space|site selection|host city|conference center|resort)\b', re.I)
DEADLINE = re.compile(r'\b(?:proposals?|applications?|bids?|letters? of intent|submissions?)(?:\s+\w+){0,4}\s+(?:due|close|deadline|must be received by)\s*(?:on|by|is|:)?\s*([A-Z][a-z]+\s+\d{1,2}(?:st|nd|rd|th)?[,]?\s+20\d{2}|\d{1,2}[/-]\d{1,2}[/-]20\d{2})', re.I)
DATE_FALLBACK = re.compile(r'\b(?:application|proposal|submission|host(?:ing)? bid) deadline\s*[:\-]?\s*([A-Z][a-z]+\s+\d{1,2}(?:st|nd|rd|th)?[,]?\s+20\d{2})', re.I)

def dated_deadline(text):
    """Only a stated host/bid submission deadline, not the event date."""
    m=DEADLINE.search(text) or DATE_FALLBACK.search(text)
    if not m:return ''
    value=re.sub(r'(\d)(?:st|nd|rd|th)\b',r'\1',m.group(1))
    for fmt in ('%B %d, %Y','%B %d %Y','%m/%d/%Y','%m-%d-%Y'):
        try:return datetime.strptime(value,fmt).date().isoformat()
        except ValueError:pass
    return ''

def assess(text, today=None):
    """Classify source excerpts. Never returns a qualified or open buyer."""
    today=today or date.today()
    text=' '.join(str(text or '').split())[:1600]
    deadline=dated_deadline(text)
    future=bool(re.search(r'\b20(?:27|28|29|30|31)\b',text))
    speaker=bool(SPEAKER_ONLY.search(text))
    committed=bool(SITE_COMMITTED.search(text))
    host_bid=bool(HOST_BID.search(text))
    venue_bid=bool(VENUE_BID.search(text))
    early=bool(EARLY_CHANGE.search(text))
    virtual=bool(VIRTUAL_ONLY.search(text))
    flags=[]
    if virtual: flags.append('Virtual-only event may lack hotel scope')
    if committed: flags.append('Venue/hotel named or selected; confirm specific year and contract')
    if deadline and deadline<today.isoformat(): flags.append('Posted bid deadline has passed')
    if host_bid: flags.append('Host-institution bid is not a hotel/planner services RFP')
    if speaker and not (host_bid or venue_bid or early): flags.append('Speaker/session proposal only')
    if virtual:
        stage='virtual_only'
        action='Exclude unless a separate in-person event with hotel requirements is identified.'
    elif venue_bid:
        stage='venue_rfp_or_bidding'
        action='An RFP or bid process may already be underway; verify whether outside help remains influenceable.'
    elif host_bid:
        stage='host_bid_in_progress'
        action='Host selection is underway; identify who owns subsequent hotel decisions and their deadline.'
    elif virtual:
        stage='virtual_only'
        action='Exclude unless a separate in-person event with hotel requirements is identified.'
    elif speaker and not early:
        stage='programming_only'
        action='Find independent venue/finance/site evidence; speaker calls are not hotel sourcing.'
    elif early and future:
        stage='possible_pre_rfp'
        action='Confirm which future venue or event budget decision remains uncommitted and who can approve help.'
    else:
        stage='watch_only'
        action='Find original, dated evidence of a specific future planning or cost decision.'
    if (host_bid or venue_bid) and deadline and deadline<today.isoformat():
        stage='bid_deadline_passed'
        action='Posted bid deadline passed. Check next cycle before sending to Robert.'
    if stage=='possible_pre_rfp' and committed:stage='possible_pre_rfp_with_venue_risk'
    return {'stage':stage,'deadline':deadline,'future_event_year_mentioned':future,
            'hotel_scope_mentioned':bool(HOTEL_SCOPE.search(text)),
            'commitment_clues':flags,'pre_rfp_research_candidate':stage=='possible_pre_rfp',
            'qualified':False,'open_contract_verified':False,'next_step':action,
            'warning':'Source-excerpt triage only; buyer, contract and outside-planner openness unverified.'}
