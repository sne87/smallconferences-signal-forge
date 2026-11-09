#!/usr/bin/env python3
"""Audit honest daily SOURCE-BACKED NEW-organizer discovery targets.

This is an operational research target, not a quota that can manufacture leads.
Known/watchlisted organizers are seeded as baseline and never retroactively
counted. A new independently indexed early/pre-RFP clue counts once when its
organizer first appears, even if later scans have no new results.
"""
import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
HISTORY_PATH=ROOT/'data'/'discovery_history.json'
TZ=ZoneInfo('America/Chicago')
DEFAULT_TARGET=10

def clean_key(name):
    return re.sub(r'[^a-z0-9]+',' ',re.sub(r'^the\s+','',str(name or '').lower())).strip()

def local_date(now):
    return now.astimezone(TZ).date().isoformat()

def read_history(path=HISTORY_PATH):
    try:
        data=json.loads(Path(path).read_text(encoding='utf-8'))
        if isinstance(data,dict) and data.get('version')==1:return data
    except (OSError,ValueError,TypeError):
        pass
    return None

def current_target(history):
    try:
        t=int(os.getenv('SIGNAL_FORGE_DAILY_TARGET','') or (history or {}).get('target_per_day',DEFAULT_TARGET))
    except (ValueError,TypeError):t=DEFAULT_TARGET
    return max(1,min(t,50))

def today_progress(history,now):
    goal=current_target(history)
    day=local_date(now)
    entries=(history or {}).get('discoveries',[])
    today={clean_key(x.get('name')) for x in entries if x.get('discovered_on')==day and x.get('name')}
    return {'date':day,'timezone':'America/Chicago','target':goal,'new_today':len(today),
        'remaining':max(0,goal-len(today)),'goal_met':len(today)>=goal,
        'shortfall':len(today)<goal,'names_today':sorted(x.get('name') for x in entries if x.get('discovered_on')==day),
        'meaning':'New distinct named organizers with independently indexed early-planning clues, not verified buyers.',
        'baseline_known':len((history or {}).get('baseline_keys',[]))}

def update_history(history,groups,signals,now,prior_groups=()):
    day=local_date(now)
    if history is None:
        # First run fallback. Avoid counting pre-existing candidates as new.
        baseline={clean_key(x.get('name')) for x in prior_groups}
        baseline.update(clean_key(x.get('name')) for x in groups)
        history={'version':1,'tracking_started_at':day,'local_timezone':'America/Chicago',
                 'target_per_day':DEFAULT_TARGET,'baseline_keys':sorted(k for k in baseline if k),
                 'discoveries':[]}
    known={clean_key(x) for x in history.get('baseline_keys',[])}
    records=list(history.get('discoveries',[]))
    known.update(clean_key(x.get('name')) for x in records)
    matches={}
    for item in signals:
        if item.get('origin') not in ('news_index','social_index'):continue
        if not item.get('pre_rfp_priority') or not item.get('url','').startswith(('https://','http://')):continue
        key=clean_key(item.get('organization_candidate') or item.get('organization_key'))
        if not key:continue
        matches.setdefault(key,item)
    newly_added=[]
    for group in groups:
        key=clean_key(group.get('name') or group.get('key'))
        if not key or key in known or key not in matches:continue
        item=matches[key]
        entry={'name':group.get('name',key),'key':key,'discovered_on':day,
               'evidence_url':item['url'],'source_title':item.get('title',''),
               'signal_families':list(item.get('types',[])),
               'origin':item.get('origin','news_index'),
               'recovered_from_rejected_archive':bool(item.get('replay_recovered')),
               'qualification':'Public indexed research candidate only. Timing, contracts, financial fit, decision-maker and actual buying intent unverified.'}
        records.append(entry)
        known.add(key)
        newly_added.append(entry)
    history['discoveries']=records
    counts=Counter(x.get('discovered_on') for x in records if x.get('discovered_on'))
    history['daily_counts']=[{'date':d,'count':counts[d]} for d in sorted(counts)[-45:]]
    history['last_scanned_on']=day
    history['local_timezone']='America/Chicago'
    history['target_per_day']=current_target(history)
    return history,today_progress(history,now),newly_added

def write_history(history,path=HISTORY_PATH):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(history,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
