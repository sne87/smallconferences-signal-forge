#!/usr/bin/env python3
"""Conference-cycle-specific opportunity classification.

One organizer can have a contracted 2027 conference AND a genuine 2029
site decision. Never let evidence for another year imply the new cycle is
contracted, open, budgeted, or otherwise qualified. Everything here is
research triage, NOT proof of an unawarded contract or buyer intent.
"""
from __future__ import annotations
import re
from datetime import date
from opportunity_gate import assess

YEAR = re.compile(r'(?<!\d)20(?:27|28|29|30|31|32)(?!\d)')
SENTENCE = re.compile(r'(?<=[.!?;])\s+(?=[A-Z0-9])|\n+')
EVENT = re.compile(r'\b(?:annual (?:conference|meeting|convention)|conference|convention|symposium|future sites?|site selection|venue|hotel|meeting site)\b',re.I)
COMPLETE = re.compile(r'\b(?:signed|contracted|finalized|confirmed|already selected|chosen|booked|awarded)\b',re.I)
PRIORITY = {'possible_pre_rfp':0,'possible_pre_rfp_with_venue_risk':1,
            'planning_change_watch':2,'venue_rfp_or_bidding':3,
            'host_bid_in_progress':4,'bid_deadline_passed':5,
            'watch_only':6,'programming_only':7,'virtual_only':8}

def _sentences(text):
    return [s.strip() for s in SENTENCE.split(str(text or '')) if s.strip()]

def assess_cycles(text, today=None):
    """Return one decision assessment per explicitly named conference year.

    When two years share one sentence they share its evidence, which is
    reported as potentially ambiguous. A separate 2027 hotel booking never
    becomes evidence that a 2028 site is contracted.
    """
    today = today or date.today()
    sentences = _sentences(text)
    observations={}
    for i, sentence in enumerate(sentences):
        years=sorted(set(YEAR.findall(sentence)))
        if not years:continue
        if not EVENT.search(sentence):
            # A sentence mentioning a fiscal year or publication date cannot
            # establish a conference cycle on its own.
            continue
        passage=sentence
        # Pull in the immediate follow-up when it lacks another event year.
        # Minutes commonly separate "2028 Conference" from "The committee
        # will review locations" into two short sentences.
        for j in (i+1,i+2):
            if j>=len(sentences) or YEAR.search(sentences[j]):break
            follow=sentences[j]
            if EVENT.search(follow) or re.search(r'\b(?:committee|board|vote|proposals?|cities|locations?|contracts?|discussed|decision|approved|hotel)\b',follow,re.I):
                passage+=' '+follow
            else:break
        for yr in years:
            # Tax-filing and fiscal years are not necessarily conference years.
            # Do not turn a statement about 2029 financials and a 2026 event
            # into a phantom 2029 meeting.
            if re.search(r'\b'+re.escape(yr)+r'\s+(?:financials?|fiscal|tax|revenue|filing|Form 990)\b',sentence,re.I) and not re.search(r'\b(?:conference|annual meeting|venue|site)\s+(?:in|for|of)?\s*'+re.escape(yr)+r'\b',sentence,re.I):
                continue
            # Keep source passage and year traceability, not a fabricated
            # future decision deadline.
            obs=observations.setdefault(yr,[])
            if passage not in obs:obs.append(passage)
    results=[]
    for yr in sorted(observations):
        passages=observations[yr]
        # Avoid combining contradictory years through page-wide context.
        # Assess each passage independently, then surface both the strongest
        # possible opening and any commitment or RFP counterevidence.
        assessments=[assess(p,today) for p in passages]
        ranked=sorted(zip(assessments,passages),
                      key=lambda x:(PRIORITY.get(x[0]['stage'],99),
                                    -int(x[0]['hotel_scope_mentioned'])))
        strongest,excerpt=ranked[0]
        flags=sorted({flag for item in assessments for flag in item['commitment_clues']})
        all_stages=sorted({item['stage'] for item in assessments})
        mixed_commitment=any(x in all_stages for x in ('possible_pre_rfp_with_venue_risk',))
        committed_evidence=any(COMPLETE.search(p) and
                               re.search(r'\b(?:hotel|venue|location|site|contract)\b',p,re.I)
                               for p in passages)
        # A signed/selected venue in this SAME year is a risk, even when a
        # separate note within the year discusses another event component.
        possible=strongest['stage']=='possible_pre_rfp' and not committed_evidence
        stage='possible_pre_rfp_with_venue_risk' if (
            strongest['stage']=='possible_pre_rfp' and committed_evidence) else strongest['stage']
        results.append({'event_year':int(yr),'stage':stage,
                        'pre_rfp_research_candidate':bool(possible),
                        'evidence_excerpt':excerpt[:800],
                        'other_stages':all_stages,
                        'counterevidence_flags':flags,
                        'commitment_evidence_same_year':bool(committed_evidence),
                        'multi_year_sentence':any(len(set(YEAR.findall(p)))>1 for p in passages),
                        'qualified':False,'open_contract_verified':False,
                        'next_step':strongest['next_step']})
    return results

def outreach_screen(cycles, *, legal_entity_verified=False, revenue_verified=False,
                    recurring_event_verified=False, scope_verified=False,
                    decision_owner_verified=False, decision_ahead_verified=False,
                    incumbent_checked=False, external_advisor_path_verified=False):
    """Strict Robert outreach gate, distinct from research priority.

    Missing information is never treated as a negative commitment check.
    An RFP/host bid, venue commitment, or ambiguous same-year cycle blocks
    outreach regardless of the numerical research priority.
    """
    required = {
        'legal_entity_verified': legal_entity_verified,
        'revenue_verified': revenue_verified,
        'recurring_event_verified': recurring_event_verified,
        'scope_verified': scope_verified,
        'decision_owner_verified': decision_owner_verified,
        'decision_ahead_verified': decision_ahead_verified,
        'incumbent_checked': incumbent_checked,
        'external_advisor_path_verified': external_advisor_path_verified,
    }
    eligible = [c for c in (cycles or [])
                if c.get('stage') == 'possible_pre_rfp'
                and c.get('pre_rfp_research_candidate') is True
                and not c.get('commitment_evidence_same_year')
                and not any(s in ('host_bid_in_progress','venue_rfp_or_bidding',
                                  'bid_deadline_passed','possible_pre_rfp_with_venue_risk')
                            for s in c.get('other_stages', []))
                and not c.get('counterevidence_flags')]
    missing = [key for key, verified in required.items() if verified is not True]
    return {
        'approach_ready': bool(eligible) and not missing,
        'eligible_event_years': [c['event_year'] for c in eligible],
        'missing_checks': missing,
        'status': ('approach_soon' if eligible and not missing else
                   'research_further' if eligible else 'future_watch_or_skip'),
        'warning': 'Research gate only. Never automatically qualify or contact an organizer.',
    }


def select_next_cycle(cycles, fallback):
    """Choose the strongest research window, never imply an open contract."""
    if not cycles:return dict(fallback,event_year=None,cycle_evidence='',cycle_assessed=False)
    ranked=sorted(cycles,key=lambda c:(PRIORITY.get(c['stage'],99),c['event_year']))
    top=ranked[0]
    out=dict(fallback)
    out.update(stage=top['stage'],event_year=top['event_year'],
               commitment_clues=top['counterevidence_flags'],
               cycle_evidence=top['evidence_excerpt'],
               cycle_assessed=True,pre_rfp_research_candidate=top['pre_rfp_research_candidate'],
               next_step=top['next_step'],qualified=False,open_contract_verified=False)
    return out
