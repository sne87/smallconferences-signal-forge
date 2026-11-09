#!/usr/bin/env python3
"""Reconcile public social research written externally with GitHub scan output.

Remote ChatGPT source-referenced posts are never silently overwritten by
stale GitHub Actions checkouts. This preserves evidence links, not qualification.
"""
import hashlib,json,sys
from pathlib import Path
LOCAL=Path("data/social_watch.json")
def read(p):
    try:
        x=json.loads(Path(p).read_text(encoding='utf-8'))
        return x if isinstance(x,dict) else {}
    except (OSError,ValueError,TypeError):
        return {}
def key(item):
    u=item.get('url','')
    return str(item.get('id') or hashlib.sha256(u.split('#')[0].lower().encode()).hexdigest()[:20])
def merge(remote_path):
    local=read(LOCAL)
    remote=read(remote_path)
    old=remote.get('items',[])
    if not isinstance(old,list):old=[]
    cur=local.get('items',[])
    if not isinstance(cur,list):cur=[]
    merged={}
    # Prefer remote if both have the same direct post link, because an
    # externally checked latest record may add verification and context.
    for item in cur+old:
        if not isinstance(item,dict) or not str(item.get('url','')).startswith('https://'):continue
        item['id']=key(item)
        if item['id'] in merged:
            old_item=merged[item['id']]
            if str(item.get('first_seen',''))>str(old_item.get('first_seen','')):
                item['first_seen']=old_item.get('first_seen','')
        merged[item['id']]=item
    joined=sorted(merged.values(),key=lambda x:(x.get('last_seen',''),x.get('index_date','')),reverse=True)[:180]
    local['items']=joined
    local['public_posts_retained']=len(joined)
    local['latest_external_reconciliation']=remote.get('generated_at','')
    LOCAL.parent.mkdir(parents=True,exist_ok=True)
    LOCAL.write_text(json.dumps(local,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Merged public social evidence',len(joined),'posts, remote records',len(old))
if __name__=='__main__':merge(sys.argv[1] if len(sys.argv)>1 else '/tmp/signal-forge-remote-social.json')
