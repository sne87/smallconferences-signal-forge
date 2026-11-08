#!/usr/bin/env python3
"""Preserve ChatGPT-synthesized public research against scan-time checkout races.

Combines a fetched remote data/briefs.json with locally regenerated source
intelligence. No lead becomes qualified. A changed source fingerprint makes an
older summary STALE, rather than silently reasserting it as current.
"""
import json
import sys
from pathlib import Path

LOCAL = Path("data/briefs.json")
def read(p):
    try:
        d=json.loads(Path(p).read_text(encoding="utf-8"))
        return d if isinstance(d,dict) else {}
    except (OSError,ValueError):
        return {}

def merge(remote_file):
    local=read(LOCAL)
    remote=read(remote_file)
    fresh={x.get("key"):x for x in remote.get("briefs",[]) if isinstance(x,dict) and x.get("key")}
    n=0;stale=0
    for item in local.get("briefs",[]):
        older=fresh.get(item.get("key"))
        if not older or not older.get("ai_summary"): continue
        if item.get("ai_summary") and str(item.get("ai_reviewed_at") or "")>str(older.get("ai_reviewed_at") or ""):
            continue
        item["ai_summary"]=older["ai_summary"]
        item["ai_source"]=older.get("ai_source","")
        item["ai_reviewed_at"]=older.get("ai_reviewed_at","")
        if item.get("fingerprint")!=older.get("fingerprint"):
            item["ai_status"]="stale_source_change_recheck_required"
            item["ai_source_fingerprint"]=older.get("fingerprint","")
            stale+=1
        else:
            item["ai_status"]=older.get("ai_status","cached_previous_summary")
            item.pop("ai_source_fingerprint",None)
        n+=1
    LOCAL.write_text(json.dumps(local,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Merged",n,"prior public ChatGPT summaries,",stale,"require updated source verification")

if __name__=="__main__":
    merge(sys.argv[1] if len(sys.argv)>1 else "/tmp/signal-forge-remote-briefs.json")
