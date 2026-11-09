#!/usr/bin/env python3
"""Conservative, free-source pre-RFP evidence packets. Never auto-qualify."""
import json, re, urllib.request, urllib.parse, urllib.error
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"qualification_packets.json"
API="https://projects.propublica.org/nonprofits/api/v2"
BLOCK={"host_bid_in_progress","venue_rfp_or_bidding","bid_deadline_passed"}
def read(name):
    try:return json.loads((ROOT/"data"/name).read_text(encoding="utf-8"))
    except (OSError,ValueError):return {}
def get_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":"SignalForgePublicResearch/1.0 (public nonprofit research)","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=12) as resp:return json.load(resp)
def norm(s):return re.sub(r"[^a-z0-9]+"," ",str(s or "").lower()).strip()
def finance_lookup(name, known):
    """Find EIN candidates, never assert entity identity from a fuzzy match."""
    result={"status":"unverified","revenue_status":"unverified","candidates":[]}
    ein=re.search(r"/organizations/(\\d{8,9})(?:\\.json)?",str(known.get("source_url") or ""))
    if ein:
        result["known_ein_source"]=known["source_url"]
        try:
            data=get_json(API+"/organizations/"+ein.group(1)+".json")
            org=data.get("organization") or {}
            filings=sorted(data.get("filings_with_data") or [],key=lambda f:int(f.get("tax_prd") or 0),reverse=True)
            latest=next((f for f in filings if isinstance(f.get("totrevenue"),(int,float))),None)
            exact=norm(org.get("name"))==norm(name)
            result.update({"status":"exact_name_match" if exact else "ein_name_mismatch_review","ein":str(org.get("ein") or ein.group(1)),"legal_name":org.get("name"),"source_url":API+"/organizations/"+ein.group(1)+".json"})
            if latest:
                result.update({"annual_revenue":latest["totrevenue"],"fiscal_year":latest.get("tax_prd_yr"),"revenue_status":"filing_found_entity_review_required" if not exact else "filing_found_exact_name"})
            return result
        except (urllib.error.URLError,TimeoutError,ValueError,KeyError) as e:
            result["error"]=type(e).__name__
    try:
        data=get_json(API+"/search.json?q="+urllib.parse.quote(name))
        matches=[x for x in (data.get("organizations") or []) if norm(x.get("name"))==norm(name)]
        result["candidates"]=[{"legal_name":x.get("name"),"ein":str(x.get("ein")),"state":x.get("state"),"source_url":API+"/organizations/"+str(x.get("ein"))+".json","status":"name_only_unverified"} for x in matches[:5]]
        result["status"]="exact_name_candidates_require_organizer_confirmation" if matches else "no_exact_name_match"
    except (urllib.error.URLError,TimeoutError,ValueError) as e:
        result["error"]=type(e).__name__
    return result
def packet(b,org,finance):
    years=sorted({int(d["event_year"]) for e in org.get("evidence",[]) for d in e.get("cycle_decisions",[]) if str(d.get("event_year","")).isdigit()})
    original=[]
    for e in org.get("evidence",[]):
        if not str(e.get("url","")).startswith(("https://","http://")):continue
        original.append({"url":e["url"],"title":e.get("title"),"document_date":e.get("document_date") or e.get("published") or None,
            "publication_date_verified":bool(e.get("published")),"source":e.get("source"),"window_stage":e.get("window_stage"),
            "counterevidence":e.get("counterevidence_flags",[]),
            "event_cycles":[{"year":d.get("event_year"),"stage":d.get("stage"),"excerpt":str(d.get("evidence_excerpt") or "")[:350],"same_year_commitment":d.get("commitment_evidence_same_year",False),"multi_year_ambiguity":d.get("multi_year_sentence",False)} for d in e.get("cycle_decisions",[])]})
    checks={"legal_entity_verified":"unknown","revenue_verified":"unknown","recurring_event_verified":"unknown","scope_verified":"unknown","decision_owner_verified":"unknown","decision_ahead_verified":"unknown","incumbent_checked":"unknown","external_advisor_path_verified":"unknown"}
    # A filing candidate alone never establishes that it is the actual conference organizer.
    risks=list(org.get("commitment_flags") or [])
    if BLOCK.intersection(org.get("window_stages") or []):risks.append("Active host/venue procurement indexed; resolve specific event year")
    if finance.get("status")=="ein_name_mismatch_review":risks.append("Filing entity name differs from discovery organizer")
    status="conflict-check" if risks else "research-next" if original and years and any(e.get("window_stage")=="possible_pre_rfp" for e in org.get("evidence",[])) else "early-watch"
    missing=list(checks)
    return {"key":b["key"],"name":b["name"],"suggested_research_bucket":status,"qualified":False,
      "event_years":[{"year":y,"commitment_status":"unknown; source check required","decision_status":"unknown; source check required"} for y in years],
      "financial_research":finance,"evidence":original,"evidence_checks":checks,"unresolved_checks":missing,
      "counterevidence":risks,"research_priority":(60 if status=="research-next" else 20 if status=="conflict-check" else 0)+min(15,len(original)*5),
      "one_next_step":"Confirm the exact event-year venue/planner decision and authority in dated organizer minutes" if years else "Verify a future overnight conference year from the organizer's own event calendar",
      "limitations":"Indexed evidence and EIN name searches are research clues, not independent proof of a current unawarded contract, conference spend, decision authority, or paid advisor fit."}
def main():
    feed=read("signals.json");briefs=read("briefs.json")
    by_org={o.get("key"):o for o in feed.get("organizations",[])}
    previous=read("qualification_packets.json")
    prev={p.get("key"):p for p in previous.get("packets",[])}
    packets=[]
    for b in briefs.get("briefs",[]):
        org=by_org.get(b.get("key"),{})
        old=prev.get(b.get("key"),{})
        fin=old.get("financial_research") or {}
        if not fin or fin.get("status")=="unverified":
            fin=finance_lookup(b["name"],b.get("financial") or {})
        packets.append(packet(b,org,fin))
    # Preserve old packets if the scanner temporarily drops an organization.
    keys={p["key"] for p in packets}
    packets.extend(p for k,p in prev.items() if k not in keys)
    packets.sort(key=lambda p:(-p["research_priority"],p["name"]))
    result={"generated_at":datetime.now(timezone.utc).isoformat(),"source":"Signal Forge indexed public sources and free ProPublica Nonprofit Explorer API","qualified_count":0,"packets":packets}
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Evidence packets:",len(packets),"research next:",sum(p["suggested_research_bucket"]=="research-next" for p in packets),"qualified: 0")
if __name__=="__main__":main()
